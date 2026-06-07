# _t2j_mixed_sim.py — MIXED recipe: OK_Q8 (per-row) for ffn_down + embed, OK_Q4B rest. — OK_Q4B FORMAT SIMULATION through the gold instrument:
# quantize the safetensors weights per-32-block (s = maxabs/7 ROUNDED THROUGH f16,
# codes = clamp(round(w/s_f16), -7, 7), w_hat = codes * s_f16), run the proven
# forward, score vs gold 4.6776. De-risks the C/CUDA Q4B investment in minutes.
import json, struct, sys, time
_log = open(r"C:\Users\Knack\AppData\Local\Temp\_t2l_sym16.log", "a", buffering=1, encoding="utf-8")
sys.stdout = _log; sys.stderr = _log
import numpy as np
import torch
torch.set_num_threads(3)

BUCKET = r"D:\Files\Models\Gemma4\gemma-4-12b-bucket"
TOKENS = r"D:\F\shannon-prime-repos\_g4_12b_wiki_tokens.txt"
ORACLE = 4.6776

sf = open(BUCKET + r"\model.safetensors", "rb")
shn = struct.unpack("<Q", sf.read(8))[0]
shdr = json.loads(sf.read(shn)); sbase = 8 + shn

def st_raw(nm):
    e = shdr["model.language_model." + nm]; o, en = e["data_offsets"]
    sf.seek(sbase + o)
    raw = np.frombuffer(sf.read(en - o), dtype="<u2")
    x = (raw.astype(np.uint32) << 16).view(np.float32).copy()
    return x.reshape(e["shape"]) if len(e["shape"]) > 1 else x

def q4b(w):                                          # per-32-block sim, f16 scale discipline
    rows, cols = w.shape
    nb = cols // 16
    blk = w[:, :nb * 16].reshape(rows, nb, 16)
    s = np.abs(blk).max(axis=2) / 7.0                # [rows, nb]
    s = s.astype(np.float16).astype(np.float32)      # ROUND THROUGH f16 (stored form)
    s[s == 0] = 1.0
    codes = np.clip(np.round(blk / s[:, :, None]), -7, 7)
    out = (codes * s[:, :, None]).reshape(rows, nb * 16)
    if nb * 16 < cols:                               # tail (cols%32) — gemma4 dims are /32 clean
        out = np.concatenate([out, w[:, nb * 16:]], axis=1)
    return torch.from_numpy(out.astype(np.float32))

def q8row(w):                                        # per-row OK_Q8 sim (q*s/127)
    s = np.abs(w).max(axis=1, keepdims=True)
    s[s == 0] = 1.0
    codes = np.clip(np.round(w / s * 127.0), -127, 127)
    return torch.from_numpy((codes * s / 127.0).astype(np.float32))

KEEP_Q8 = ("mlp.down_proj",)
def stq(nm):
    w = st_raw(nm)
    return q8row(w) if any(k in nm for k in KEEP_Q8) else q4b(w)
def stf(nm): return torch.from_numpy(st_raw(nm))     # f32 (norms/scalars)

E, NL, NH = 3840, 48, 16
EPS, CAP, SW = 1e-6, 30.0, 1024
GLOBALS = {5, 11, 17, 23, 29, 35, 41, 47}
HD = {True: 512, False: 256}; NKV = {True: 1, False: 8}

def rms(x, w): return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + EPS) * w
def rope(x, theta, partial):
    Tn, H, D = x.shape; half = D // 2
    j = torch.arange(half, dtype=torch.float64)
    inv = theta ** (-2.0 * j / D)
    if partial is not None: inv[int(partial * half * 2) // 2:] = 0.0
    ang = torch.arange(Tn, dtype=torch.float64)[:, None] * inv[None, :]
    cos, sin = torch.cos(ang).float(), torch.sin(ang).float()
    x1, x2 = x[..., :half], x[..., half:]
    c, s = cos[:, None, :], sin[:, None, :]
    return torch.cat([x1 * c - x2 * s, x1 * s + x2 * c], dim=-1)

toks = [int(x) for x in open(TOKENS)]
N_CTX = 512
ids = toks[:N_CTX]
uniq = sorted(set(ids)); rowmap = {t: i for i, t in enumerate(uniq)}
emb = shdr["model.language_model.embed_tokens.weight"]; eo = emb["data_offsets"][0]
def emb_rows(r0, r1):
    sf.seek(sbase + eo + r0 * 3840 * 2)
    raw = np.frombuffer(sf.read((r1 - r0) * 3840 * 2), dtype="<u2")
    return q8row((raw.astype(np.uint32) << 16).view(np.float32).reshape(r1 - r0, 3840).copy())
erows = torch.cat([emb_rows(t, t + 1) for t in uniq])
x = erows[[rowmap[t] for t in ids]] * (float(E) ** 0.5)
del erows
print(f"mixed sim (Q8: down_proj+embed): {len(uniq)} embed rows gathered", flush=True)

causal = torch.triu(torch.full((N_CTX, N_CTX), float("-inf")), diagonal=1)
pos = torch.arange(N_CTX)
swa = causal.clone(); swa[pos[:, None] - pos[None, :] >= SW] = float("-inf")

t0 = time.time()
for L in range(NL):
    g = L in GLOBALS
    hd, nkv = HD[g], NKV[g]
    theta, partial = (1e6, 0.25) if g else (1e4, None)
    p = f"layers.{L}."
    h = rms(x, stf(p + "input_layernorm.weight"))
    q = (h @ stq(p + "self_attn.q_proj.weight").t()).view(N_CTX, NH, hd)
    k_raw = (h @ stq(p + "self_attn.k_proj.weight").t()).view(N_CTX, nkv, hd)
    v = k_raw.clone() if g else (h @ stq(p + "self_attn.v_proj.weight").t()).view(N_CTX, nkv, hd)
    q = rms(q, stf(p + "self_attn.q_norm.weight"))
    k = rms(k_raw, stf(p + "self_attn.k_norm.weight"))
    v = v * torch.rsqrt(v.pow(2).mean(-1, keepdim=True) + EPS)
    q = rope(q, theta, partial); k = rope(k, theta, partial)
    grp = NH // nkv
    kx = k.repeat_interleave(grp, dim=1); vx = v.repeat_interleave(grp, dim=1)
    att = torch.softmax(torch.einsum("qhd,khd->hqk", q, kx) + (causal if g else swa)[None], dim=-1)
    out = torch.einsum("hqk,khd->qhd", att, vx).reshape(N_CTX, NH * hd)
    x = x + rms(out @ stq(p + "self_attn.o_proj.weight").t(), stf(p + "post_attention_layernorm.weight"))
    h = rms(x, stf(p + "pre_feedforward_layernorm.weight"))
    gate = h @ stq(p + "mlp.gate_proj.weight").t()
    up = h @ stq(p + "mlp.up_proj.weight").t()
    act = 0.5 * gate * (1.0 + torch.tanh(0.7978845608028654 * (gate + 0.044715 * gate**3)))
    x = x + rms((act * up) @ stq(p + "mlp.down_proj.weight").t(), stf(p + "post_feedforward_layernorm.weight"))
    x = x * float(st_raw(p + "layer_scalar")[0])
    print(f"  L{L} |x| {x.norm():.3e} ({time.time()-t0:.0f}s)", flush=True)

x = rms(x, stf("norm.weight"))
V = 262144
logits = torch.empty(N_CTX, V, dtype=torch.float32)
for r0 in range(0, V, 16384):
    r1 = min(r0 + 16384, V)
    logits[:, r0:r1] = x @ emb_rows(r0, r1).t()
logits = torch.tanh(logits / CAP) * CAP
logp = torch.log_softmax(logits, dim=-1)
first = N_CTX // 2
nll = -logp[torch.arange(N_CTX - 1), torch.tensor(toks[1:N_CTX])]
ppl = float(torch.exp(nll[first - 1:].mean()))
rel = (ppl - ORACLE) / ORACLE
print(f"SYM-16 Q4B+Q8 SIM: PPL = {ppl:.4f} vs gold {ORACLE} -> {rel*100:+.2f}%  [{time.time()-t0:.0f}s]", flush=True)
