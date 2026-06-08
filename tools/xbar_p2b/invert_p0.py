# invert_p0.py — XBAR-P2b PHASE 0: inversion existence proof + golden targets
# (CONTRACT-XBAR-P2b §1). The TEACHER is the GOLD INSTRUMENT — the hand-written,
# twice-validated gemma-4-12B forward (paper-04 oracle lineage) — made
# differentiable. No transformers, no third-party forward (the GGUF lesson).
#
# Per span: freeze everything; optimize k trainable entry vectors substituted
# for an n-token span; loss = KL(teacher || student) over the continuation,
# teacher-forced on corpus tokens. Two regularization arms:
#   Arm F: free vectors + soft-min top-K manifold penalty (logsumexp).
#   Arm H: convex-hull — softmax weights over the K nearest embedding rows.
# NOTE the student sequence is SHORTER by (n-k): positions shift; KL compares
# distributions at corresponding continuation TOKENS (the gist setup).
#
# Receipts: JSON per run (args echoed, per-span kl curves, manifold diagnostics)
# + golden vectors (.pt) + XBE1 payloads (post-embed-scale f32) for the 2060
# parity gate G-P2b-3. Banner echoes EVERY arg (the getenv discipline).
#
# Usage (cloud, A100-class):
#   python invert_p0.py --model-dir /workspace/gemma-4-12b-bucket \
#       --tokens wiki_tokens.txt --spans 50 --arm F --k 2 --n 6 --steps 300
# Local syntax/shape smoke (no model needed):
#   python invert_p0.py --toy --spans 2 --steps 20 --arm F
#   python invert_p0.py --toy --spans 2 --steps 20 --arm H
import argparse, json, struct, sys, time, os, math
import torch

p = argparse.ArgumentParser()
p.add_argument("--model-dir", default=None, help="bucket dir: model.safetensors + config.json")
p.add_argument("--tokens", default=None, help="whitespace token-id corpus fixture")
p.add_argument("--out", default="p0_out")
p.add_argument("--arm", choices=["F", "H"], required=True)
p.add_argument("--spans", type=int, default=50)
p.add_argument("--k", type=int, default=2)
p.add_argument("--n", type=int, default=6)
p.add_argument("--ctx", type=int, default=64, help="context tokens before the span")
p.add_argument("--cont", type=int, default=24, help="continuation tokens scored")
p.add_argument("--steps", type=int, default=300)
p.add_argument("--lr", type=float, default=0.05)
p.add_argument("--K", type=int, default=64, help="neighbor count (both arms)")
p.add_argument("--lam", type=float, default=0.1, help="Arm F manifold penalty weight")
p.add_argument("--tau", type=float, default=1.0, help="Arm F soft-min temperature")
p.add_argument("--seed", type=int, default=20260609)
p.add_argument("--xbe1-row", type=int, default=9, help="row stamped into exported XBE1 payloads")
p.add_argument("--toy", action="store_true", help="tiny synthetic model — code-path smoke only")
p.add_argument("--device", default=None)
args = p.parse_args()
dev = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
torch.manual_seed(args.seed)
os.makedirs(args.out, exist_ok=True)

print("== invert_p0 banner (full arg echo) ==")
for kk, vv in sorted(vars(args).items()): print(f"   {kk} = {vv}")
print(f"   device = {dev}, torch {torch.__version__}")

# ───────────────────────── weights ─────────────────────────
if args.toy:
    E, NL, NH, V = 96, 4, 4, 512
    HD_S, NKV_S, HD_G, NKV_G = 24, 2, 48, 1
    SW, EPS, CAP = 8, 1e-6, 30.0
    GLOBALS = {1, 3}
    g = torch.Generator().manual_seed(7)
    W = {}
    def mk(*s): return (torch.randn(*s, generator=g) * 0.02).to(torch.bfloat16)
    W["embed"] = mk(V, E)
    for L in range(NL):
        glob = L in GLOBALS
        hd, nkv = (HD_G, NKV_G) if glob else (HD_S, NKV_S)
        pre = f"L{L}."
        W[pre+"in_n"] = torch.ones(E); W[pre+"q_n"] = torch.ones(hd); W[pre+"k_n"] = torch.ones(hd)
        W[pre+"pa_n"] = torch.ones(E); W[pre+"pf_n"] = torch.ones(E); W[pre+"po_n"] = torch.ones(E)
        W[pre+"Wq"] = mk(NH*hd, E); W[pre+"Wk"] = mk(nkv*hd, E)
        if not glob: W[pre+"Wv"] = mk(nkv*hd, E)
        W[pre+"Wo"] = mk(E, NH*hd)
        W[pre+"Wg"] = mk(4*E, E); W[pre+"Wu"] = mk(4*E, E); W[pre+"Wd"] = mk(E, 4*E)
        W[pre+"scalar"] = torch.tensor(0.3)
    W["out_n"] = torch.ones(E)
    toks = torch.randint(0, V, (4096,), generator=g).tolist()
    PLAIN = True
else:
    assert args.model_dir and args.tokens, "--model-dir and --tokens required (or --toy)"
    f = open(os.path.join(args.model_dir, "model.safetensors"), "rb")
    hn = struct.unpack("<Q", f.read(8))[0]
    hdr = json.loads(f.read(hn)); base = 8 + hn
    def T_disk(name):
        e = hdr[name]; off, end = e["data_offsets"]
        f.seek(base + off)
        raw = torch.frombuffer(bytearray(f.read(end - off)), dtype=torch.bfloat16)
        return raw.reshape(e["shape"])
    cfg = json.load(open(os.path.join(args.model_dir, "config.json")))["text_config"]
    E, NL, NH, V = cfg["hidden_size"], cfg["num_hidden_layers"], cfg["num_attention_heads"], cfg["vocab_size"]
    HD_S, NKV_S = cfg["head_dim"], cfg["num_key_value_heads"]
    HD_G, NKV_G = cfg["global_head_dim"], cfg["num_global_key_value_heads"]
    SW, EPS, CAP = cfg["sliding_window"], cfg["rms_norm_eps"], cfg["final_logit_softcapping"]
    GLOBALS = {i for i, t in enumerate(cfg["layer_types"]) if t == "full_attention"}
    P_ = "model.language_model."
    PLAIN = T_disk(P_+"layers.0.input_layernorm.weight").float().mean().item() > 0.5
    print(f"loading {NL}-layer weights to {dev} (bf16)…", flush=True)
    t0 = time.time(); W = {}
    W["embed"] = T_disk(P_+"embed_tokens.weight").to(dev)
    for L in range(NL):
        pre_d, pre = P_+f"layers.{L}.", f"L{L}."
        glob = L in GLOBALS
        W[pre+"in_n"] = T_disk(pre_d+"input_layernorm.weight").float().to(dev)
        W[pre+"q_n"]  = T_disk(pre_d+"self_attn.q_norm.weight").float().to(dev)
        W[pre+"k_n"]  = T_disk(pre_d+"self_attn.k_norm.weight").float().to(dev)
        W[pre+"pa_n"] = T_disk(pre_d+"post_attention_layernorm.weight").float().to(dev)
        W[pre+"pf_n"] = T_disk(pre_d+"pre_feedforward_layernorm.weight").float().to(dev)
        W[pre+"po_n"] = T_disk(pre_d+"post_feedforward_layernorm.weight").float().to(dev)
        W[pre+"Wq"] = T_disk(pre_d+"self_attn.q_proj.weight").to(dev)
        W[pre+"Wk"] = T_disk(pre_d+"self_attn.k_proj.weight").to(dev)
        if not glob: W[pre+"Wv"] = T_disk(pre_d+"self_attn.v_proj.weight").to(dev)
        W[pre+"Wo"] = T_disk(pre_d+"self_attn.o_proj.weight").to(dev)
        W[pre+"Wg"] = T_disk(pre_d+"mlp.gate_proj.weight").to(dev)
        W[pre+"Wu"] = T_disk(pre_d+"mlp.up_proj.weight").to(dev)
        W[pre+"Wd"] = T_disk(pre_d+"mlp.down_proj.weight").to(dev)
        W[pre+"scalar"] = T_disk(pre_d+"layer_scalar").float().flatten()[0].to(dev)
        if L % 8 == 0: print(f"  L{L} ({time.time()-t0:.0f}s)", flush=True)
    W["out_n"] = T_disk(P_+"norm.weight").float().to(dev)
    toks = [int(x) for x in open(args.tokens)]
    print(f"weights resident ({time.time()-t0:.0f}s); corpus {len(toks)} tokens")

for kk in list(W):  # toy path: move to device
    if args.toy: W[kk] = W[kk].to(dev)
EMBED = W["embed"]                       # [V,E] bf16
ESCALE = float(E) ** 0.5

# ───────────────────────── gold forward (differentiable) ─────────────────────────
def rms(x, w):
    h = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + EPS)
    return h * (w if PLAIN else (1.0 + w))

def rope(x, theta, partial):
    Tn, H, D = x.shape
    half = D // 2
    j = torch.arange(half, dtype=torch.float64, device=x.device)
    inv = theta ** (-2.0 * j / D)
    if partial is not None:
        keep = int(partial * half * 2)
        inv = inv.clone(); inv[keep // 2:] = 0.0
    ang = torch.arange(Tn, dtype=torch.float64, device=x.device)[:, None] * inv[None, :]
    cos, sin = torch.cos(ang).float(), torch.sin(ang).float()
    x1, x2 = x[..., :half], x[..., half:]
    c, s = cos[:, None, :], sin[:, None, :]
    return torch.cat([x1 * c - x2 * s, x1 * s + x2 * c], dim=-1)

def forward_logits(x):                   # x: [T,E] f32 PRE-scaled entry stream
    n = x.shape[0]
    pos = torch.arange(n, device=x.device)
    causal = torch.triu(torch.full((n, n), float("-inf"), device=x.device), diagonal=1)
    swa = causal.clone(); swa[pos[:, None] - pos[None, :] >= SW] = float("-inf")
    for L in range(NL):
        glob = L in GLOBALS
        hd, nkv = (HD_G, NKV_G) if glob else (HD_S, NKV_S)
        theta, partial = (1e6, 0.25) if glob else (1e4, None)
        pre = f"L{L}."
        h = rms(x, W[pre+"in_n"]); hb = h.to(torch.bfloat16)
        q = (hb @ W[pre+"Wq"].t()).float().view(n, NH, hd)
        k_raw = (hb @ W[pre+"Wk"].t()).float().view(n, nkv, hd)
        v = k_raw.clone() if glob else (hb @ W[pre+"Wv"].t()).float().view(n, nkv, hd)
        q = rms(q, W[pre+"q_n"]); k = rms(k_raw, W[pre+"k_n"])
        v = v * torch.rsqrt(v.pow(2).mean(-1, keepdim=True) + EPS)
        q = rope(q, theta, partial); k = rope(k, theta, partial)
        grp = NH // nkv
        kx = k.repeat_interleave(grp, dim=1); vx = v.repeat_interleave(grp, dim=1)
        att = torch.einsum("qhd,khd->hqk", q, kx) + (causal if glob else swa)[None]
        att = torch.softmax(att, dim=-1)
        out = torch.einsum("hqk,khd->qhd", att, vx).reshape(n, NH * hd)
        ao = (out.to(torch.bfloat16) @ W[pre+"Wo"].t()).float()
        x = x + rms(ao, W[pre+"pa_n"])
        h = rms(x, W[pre+"pf_n"]).to(torch.bfloat16)
        gate = (h @ W[pre+"Wg"].t()).float(); up = (h @ W[pre+"Wu"].t()).float()
        act = 0.5 * gate * (1.0 + torch.tanh(0.7978845608028654 * (gate + 0.044715 * gate**3)))
        dn = ((act * up).to(torch.bfloat16) @ W[pre+"Wd"].t()).float()
        x = x + rms(dn, W[pre+"po_n"])
        x = x * W[pre+"scalar"]
    x = rms(x, W["out_n"])
    logits = (x.to(torch.bfloat16) @ EMBED.t()).float()
    return torch.tanh(logits / CAP) * CAP

def embed_ids(ids):                      # [T] -> [T,E] f32, pre-scaled (×√E)
    return EMBED[ids].float() * ESCALE

def xbe1_write(path, vecs, row):         # vecs [k,E] f32 POST-embed-scale
    with open(path, "wb") as fo:
        fo.write(struct.pack("<8i", 0x31454258, 1, vecs.shape[0], row, vecs.shape[1], 0, 0, 0))
        fo.write(vecs.detach().cpu().numpy().astype("<f4").tobytes())

# ───────────────────────── span sampling + inversion ─────────────────────────
CTX, N, K_, CONT = args.ctx, args.n, args.k, args.cont
rng = torch.Generator().manual_seed(args.seed)
receipts = {"args": vars(args), "spans": []}
emb_f = EMBED.float()                    # [V,E] for neighbor searches (GPU)
emb_norm = emb_f / emb_f.norm(dim=1, keepdim=True).clamp_min(1e-8)

for si in range(args.spans):
    start = int(torch.randint(1, len(toks) - (CTX + N + CONT) - 2, (1,), generator=rng))
    ids = torch.tensor(toks[start:start + CTX + N + CONT], device=dev)
    ctx_ids, span_ids, cont_ids = ids[:CTX], ids[CTX:CTX+N], ids[CTX+N:]
    # teacher: full sequence, distributions at the continuation positions
    with torch.no_grad():
        t_log = forward_logits(embed_ids(ids))
        rows_t = torch.arange(CTX + N - 1, CTX + N + CONT - 1, device=dev)
        t_lp = torch.log_softmax(t_log[rows_t], dim=-1)          # [CONT,V]
        # baseline: span REMOVED entirely (how much does the span matter?)
        b_log = forward_logits(embed_ids(torch.cat([ctx_ids, cont_ids])))
        rows_b = torch.arange(CTX - 1, CTX + CONT - 1, device=dev)
        b_lp = torch.log_softmax(b_log[rows_b], dim=-1)
        kl_drop = torch.sum(t_lp.exp() * (t_lp - b_lp), dim=-1).mean().item()
    # trainable params per arm (embedding-space, PRE-scale)
    span_mean = emb_f[span_ids].mean(0)
    if args.arm == "H":
        sim = emb_norm @ (span_mean / span_mean.norm().clamp_min(1e-8))
        nb_idx = torch.topk(sim, args.K).indices                 # [K]
        logits_h = torch.zeros(K_, args.K, device=dev, requires_grad=True)
        params = [logits_h]
        def make_e(): return torch.softmax(logits_h, dim=-1) @ emb_f[nb_idx]
    else:
        e_free = (span_mean.repeat(K_, 1) + 0.01 * torch.randn(K_, E, device=dev)).detach().requires_grad_(True)
        params = [e_free]
        def make_e(): return e_free
    opt = torch.optim.Adam(params, lr=args.lr)
    kl0 = None
    for step in range(args.steps):
        opt.zero_grad()
        e_hat = make_e()                                          # [k,E] pre-scale
        x = torch.cat([embed_ids(ctx_ids), e_hat * ESCALE, embed_ids(cont_ids)], dim=0)
        s_log = forward_logits(x)
        rows_s = torch.arange(CTX + K_ - 1, CTX + K_ + CONT - 1, device=dev)
        s_lp = torch.log_softmax(s_log[rows_s], dim=-1)
        kl = torch.sum(t_lp.exp() * (t_lp - s_lp), dim=-1).mean()
        loss = kl
        if args.arm == "F":
            d2 = torch.cdist(e_hat, emb_f).pow(2)                 # [k,V]
            softmin = -args.tau * torch.logsumexp(-d2 / args.tau, dim=-1)
            loss = loss + args.lam * softmin.mean() / E
        loss.backward(); opt.step()
        if kl0 is None: kl0 = kl.item()
    with torch.no_grad():
        e_hat = make_e()
        d_near = torch.cdist(e_hat, emb_f).min(dim=-1).values
        diag = {"dist_nearest_tok": [round(v, 4) for v in d_near.tolist()]}
        if args.arm == "H":
            ww = torch.softmax(logits_h, dim=-1)
            diag["hull_entropy"] = [round(float(-(w * w.clamp_min(1e-12).log()).sum()), 3) for w in ww]
        rec = {"span": si, "start": start, "span_ids": span_ids.tolist(),
               "kl_start": round(kl0, 5), "kl_final": round(kl.item(), 5),
               "kl_span_dropped": round(kl_drop, 5), **diag}
        receipts["spans"].append(rec)
        torch.save(e_hat.cpu(), os.path.join(args.out, f"golden_s{si}_{args.arm}.pt"))
        xbe1_write(os.path.join(args.out, f"golden_s{si}_{args.arm}.xbe1"),
                   e_hat * ESCALE, args.xbe1_row)
        print(f"[span {si:3d}] kl {kl0:.4f} -> {kl.item():.4f}  (span-dropped {kl_drop:.4f})  "
              f"d_tok {diag['dist_nearest_tok']}", flush=True)

# ── G-P2b-0 telemetry summary (telemetry-then-pin: NO pass/fail printed yet) ──
fin = [r["kl_final"] for r in receipts["spans"]]
drp = [r["kl_span_dropped"] for r in receipts["spans"]]
rat = [f / max(d, 1e-9) for f, d in zip(fin, drp)]
receipts["summary"] = {
    "spans": len(fin),
    "kl_final_median": sorted(fin)[len(fin)//2],
    "kl_dropped_median": sorted(drp)[len(drp)//2],
    "recovery_ratio_median": sorted(rat)[len(rat)//2],   # kl_final / kl_dropped: <1 = inversion recovered span info
}
json.dump(receipts, open(os.path.join(args.out, f"receipts_{args.arm}.json"), "w"), indent=1)
print(f"\nSUMMARY arm={args.arm}: median kl_final {receipts['summary']['kl_final_median']:.4f} "
      f"vs span-dropped {receipts['summary']['kl_dropped_median']:.4f} "
      f"(recovery ratio {receipts['summary']['recovery_ratio_median']:.3f}; <1 = the k vectors carry span information)")
print(f"receipts -> {args.out}/receipts_{args.arm}.json (+ golden .pt / .xbe1 per span)")
