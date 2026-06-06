# _t2_manual_forward.py — THE GOLD REFERENCE: gemma-4-12b forward written by hand
# from the full-precision safetensors. No transformers, no llama.cpp — raw tensor ops.
# Architecture per the bucket config + our twice-implemented, parity-gated port:
#   embed*sqrt(E) | 48 layers: RMSNorm -> QKV (V-less globals: V = raw K proj) ->
#   QK-norm -> RoPE (SWA theta 1e4 full-rot; global theta 1e6 partial 0.25 via the
#   proportional factor table) -> GQA attn (scale 1.0, SWA window 1024) -> o_proj ->
#   post_attn norm -> +res | pre_ffn norm -> GeGLU(gelu_tanh) -> down -> post_ffn
#   norm -> +res | x *= layer_scalar | final norm -> tied head -> softcap 30.
import json, struct, sys, time
import numpy as np
import torch
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
torch.set_num_threads(8)

BUCKET = r"D:\Files\Models\Gemma4\gemma-4-12b-bucket"
TOKENS = r"D:\F\shannon-prime-repos\_g4_12b_wiki_tokens.txt"

f = open(BUCKET + r"\model.safetensors", "rb")
hn = struct.unpack("<Q", f.read(8))[0]
hdr = json.loads(f.read(hn)); base = 8 + hn

def T(name):
    e = hdr[name]; off, end = e["data_offsets"]
    f.seek(base + off)
    raw = torch.frombuffer(bytearray(f.read(end - off)), dtype=torch.bfloat16)
    return raw.reshape(e["shape"])

cfg = json.load(open(BUCKET + r"\config.json"))["text_config"]
E, NL, NH = cfg["hidden_size"], cfg["num_hidden_layers"], cfg["num_attention_heads"]
HD_S, NKV_S = cfg["head_dim"], cfg["num_key_value_heads"]
HD_G, NKV_G = cfg["global_head_dim"], cfg["num_global_key_value_heads"]
SW, EPS, CAP = cfg["sliding_window"], cfg["rms_norm_eps"], cfg["final_logit_softcapping"]
GLOBALS = {i for i, t in enumerate(cfg["layer_types"]) if t == "full_attention"}
print(f"E={E} NL={NL} NH={NH} swa(hd={HD_S},nkv={NKV_S}) glob(hd={HD_G},nkv={NKV_G}) sw={SW} cap={CAP}")

P = "model.language_model."
embed = T(P + "embed_tokens.weight")                       # [V, E] bf16

# norm-convention check: plain w vs (1+w)
for nm in ("layers.0.input_layernorm.weight", "norm.weight", "layers.0.self_attn.q_norm.weight"):
    w = T(P + nm).float()
    print(f"  norm {nm}: mean {w.mean():.4f} min {w.min():.4f} max {w.max():.4f}")
# (means ~1.0 => PLAIN x_hat*w; means ~0 => (1+w). Decided below.)
PLAIN = T(P + "layers.0.input_layernorm.weight").float().mean().item() > 0.5
print(f"  -> norm convention: {'PLAIN x*w' if PLAIN else '(1+w)'}")

scalars = torch.stack([T(P + f"layers.{L}.layer_scalar").float() for L in range(NL)]).flatten()
print("layer_scalar[0..7]:", [round(v, 4) for v in scalars[:8].tolist()])
print("  (engine printed   [0.053, 0.166, 0.256, 0.516, 0.377, 0.355, 0.346, 0.297] — off-by-one check)")

def rms(x, w):                                             # x [..., D] f32; gemma rmsnorm
    h = x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + EPS)
    return h * (w if PLAIN else (1.0 + w))

def rope(x, theta, partial):                               # x [T, H, D]; neox pairing (i, i+D/2)
    Tn, H, D = x.shape
    half = D // 2
    j = torch.arange(half, dtype=torch.float64)
    inv = theta ** (-2.0 * j / D)
    if partial is not None:                                # proportional table: freeze j >= partial*half*2
        keep = int(partial * half * 2)                     # 0.25*512 = 128 dims => first 64 pairs rotate
        inv[keep // 2:] = 0.0
    ang = torch.arange(Tn, dtype=torch.float64)[:, None] * inv[None, :]      # [T, half]
    cos, sin = torch.cos(ang).float(), torch.sin(ang).float()
    x1, x2 = x[..., :half], x[..., half:]
    c, s = cos[:, None, :], sin[:, None, :]
    return torch.cat([x1 * c - x2 * s, x1 * s + x2 * c], dim=-1)

toks = [int(x) for x in open(TOKENS)]
N_CTX = int(sys.argv[1]) if len(sys.argv) > 1 else 512
ids = torch.tensor(toks[:N_CTX])
print(f"chunk: {N_CTX} tokens, first 6: {ids[:6].tolist()}")

t0 = time.time()
x = embed[ids].float() * (float(E) ** 0.5)                 # [T, E]
mask_base = torch.full((N_CTX, N_CTX), float("-inf"))
causal = torch.triu(mask_base, diagonal=1)
pos = torch.arange(N_CTX)
swa_mask = causal.clone()
swa_mask[pos[:, None] - pos[None, :] >= SW] = float("-inf")

for L in range(NL):
    g = L in GLOBALS
    hd, nkv = (HD_G, NKV_G) if g else (HD_S, NKV_S)
    theta, partial = (1e6, 0.25) if g else (1e4, None)
    pre = P + f"layers.{L}."
    h = rms(x, T(pre + "input_layernorm.weight").float())
    hb = h.to(torch.bfloat16)
    q = (hb @ T(pre + "self_attn.q_proj.weight").t()).float().view(N_CTX, NH, hd)
    k_raw = (hb @ T(pre + "self_attn.k_proj.weight").t()).float().view(N_CTX, nkv, hd)
    if g:                                                  # attention_k_eq_v: V = RAW K projection
        v = k_raw.clone()
    else:
        v = (hb @ T(pre + "self_attn.v_proj.weight").t()).float().view(N_CTX, nkv, hd)
    q = rms(q, T(pre + "self_attn.q_norm.weight").float())
    k = rms(k_raw, T(pre + "self_attn.k_norm.weight").float())
    v = v * torch.rsqrt(v.pow(2).mean(-1, keepdim=True) + EPS)   # WEIGHTLESS V-norm
    q = rope(q, theta, partial)
    k = rope(k, theta, partial)
    grp = NH // nkv
    kx = k.repeat_interleave(grp, dim=1)                   # [T, NH, hd]
    vx = v.repeat_interleave(grp, dim=1)
    att = torch.einsum("qhd,khd->hqk", q, kx)              # scale = 1.0 (gemma4)
    att = att + (causal if g else swa_mask)[None]
    att = torch.softmax(att, dim=-1)
    out = torch.einsum("hqk,khd->qhd", att, vx).reshape(N_CTX, NH * hd)
    ao = (out.to(torch.bfloat16) @ T(pre + "self_attn.o_proj.weight").t()).float()
    x = x + rms(ao, T(pre + "post_attention_layernorm.weight").float())
    h = rms(x, T(pre + "pre_feedforward_layernorm.weight").float()).to(torch.bfloat16)
    gate = (h @ T(pre + "mlp.gate_proj.weight").t()).float()
    up   = (h @ T(pre + "mlp.up_proj.weight").t()).float()
    act = 0.5 * gate * (1.0 + torch.tanh(0.7978845608028654 * (gate + 0.044715 * gate**3)))
    dn = ((act * up).to(torch.bfloat16) @ T(pre + "mlp.down_proj.weight").t()).float()
    x = x + rms(dn, T(pre + "post_feedforward_layernorm.weight").float())
    x = x * scalars[L]
    if L % 8 == 0: print(f"  L{L} |x| {x.norm():.3e}  ({time.time()-t0:.0f}s)", flush=True)

x = rms(x, T(P + "norm.weight").float())
logits = (x.to(torch.bfloat16) @ embed.t()).float()
logits = torch.tanh(logits / CAP) * CAP
print(f"forward done {time.time()-t0:.0f}s")

logp = torch.log_softmax(logits, dim=-1)
first = N_CTX // 2
tgt = torch.tensor(toks[1:N_CTX])
nll = -logp[torch.arange(N_CTX - 1), tgt]
scored = nll[first - 1:]
print(f"GOLD chunk-0 PPL (targets [{first},{N_CTX})): {torch.exp(scored.mean()).item():.4f}  (n={len(scored)})")
for p in range(first - 1, first + 3):
    row = logits[p]
    mx, mi = row.max(0)
    print(f"  pos {p}: max {mx.item():.4f} (id {mi.item()})  target[{toks[p+1]}] {row[toks[p+1]].item():.4f}  nll {nll[p].item():.4f}")
