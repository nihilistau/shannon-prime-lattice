# _t2h_spmodel_gate.py — THE ARTIFACT GATE, gold-instrument edition: parse the
# .sp-model container directly, dequant OK_Q8 (w = q * s/127), run the PROVEN
# torch forward (4.68 on safetensors), score chunk-0 [256,512) vs ORACLE 4.6776.
# Validates the TRANSCODED ARTIFACT in minutes; the C-engine forward is already
# E2B-gate-proven and is not the variable under test.
import json, struct, sys, time
_log = open(r"C:\Users\Knack\AppData\Local\Temp\_t2h_gate.log", "a", buffering=1, encoding="utf-8")
sys.stdout = _log; sys.stderr = _log
import numpy as np
import torch
torch.set_num_threads(6)

SPM = r"D:\F\shannon-prime-repos\models\gemma4-12b-st.sp-model"
TOKENS = r"D:\F\shannon-prime-repos\_g4_12b_wiki_tokens.txt"
ORACLE = 4.6776

f = open(SPM, "rb")
hdr = f.read(512)
magic, vmaj, vmin, hsz, arch_id = struct.unpack_from("<IHHII", hdr, 0)
assert magic == 0x444D5053, hex(magic)
vocab, tcount = struct.unpack_from("<II", hdr, 312)
table_off, data_off = struct.unpack_from("<QQ", hdr, 320)
print(f"sp-model: arch {arch_id} vocab {vocab} tensors {tcount} data@{data_off}", flush=True)

tab = {}
f.seek(table_off)
for _ in range(tcount):
    e = f.read(256)
    name = e[:80].split(b"\0")[0].decode()
    dtype, ndims = struct.unpack_from("<II", e, 80)
    dims = struct.unpack_from("<8Q", e, 88)
    off, sz = struct.unpack_from("<QQ", e, 152)
    tab[name] = (dtype, ndims, dims, off, sz)

def f32(name):                                       # F32 tensor -> torch
    dt, nd, dims, off, sz = tab[name]
    assert dt == 1, (name, dt)
    f.seek(data_off + off)
    return torch.from_numpy(np.frombuffer(f.read(sz), "<f4").copy())

def q8(name):                                        # OK_Q8 + .scale -> torch f32 [rows, cols]
    dt, nd, dims, off, sz = tab[name]
    assert dt == 10, (name, dt)
    cols, rows = int(dims[0]), int(dims[1])
    f.seek(data_off + off)
    codes = np.frombuffer(f.read(rows * cols), np.int8).reshape(rows, cols)
    sdt, snd, sdims, soff, ssz = tab[name + ".scale"]
    f.seek(data_off + soff)
    scale = np.frombuffer(f.read(rows * 4), "<f4")
    w = codes.astype(np.float32) * (scale[:, None] / 127.0)
    return torch.from_numpy(w)

def q8_rows(name, r0, r1):                           # row range of an OK_Q8 tensor
    dt, nd, dims, off, sz = tab[name]
    cols = int(dims[0])
    f.seek(data_off + off + r0 * cols)
    codes = np.frombuffer(f.read((r1 - r0) * cols), np.int8).reshape(r1 - r0, cols)
    sdt, snd, sdims, soff, ssz = tab[name + ".scale"]
    f.seek(data_off + soff + r0 * 4)
    scale = np.frombuffer(f.read((r1 - r0) * 4), "<f4")
    return torch.from_numpy(codes.astype(np.float32) * (scale[:, None] / 127.0))

E, NL, NH = 3840, 48, 16
EPS, CAP, SW = 1e-6, 30.0, 1024
GLOBALS = {5, 11, 17, 23, 29, 35, 41, 47}
HD = {True: 512, False: 256}; NKV = {True: 1, False: 8}
rope_tab = f32("rope_freqs.weight")
print(f"rope_freqs[{rope_tab.numel()}] [63:66]={rope_tab[63:66].tolist()}", flush=True)

def rms(x, w):
    return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + EPS) * w

def rope(x, theta, use_tab):
    Tn, H, D = x.shape; half = D // 2
    j = torch.arange(half, dtype=torch.float64)
    inv = theta ** (-2.0 * j / D)
    if use_tab: inv = inv / rope_tab[:half].double()
    ang = torch.arange(Tn, dtype=torch.float64)[:, None] * inv[None, :]
    cos, sin = torch.cos(ang).float(), torch.sin(ang).float()
    x1, x2 = x[..., :half], x[..., half:]
    c, s = cos[:, None, :], sin[:, None, :]
    return torch.cat([x1 * c - x2 * s, x1 * s + x2 * c], dim=-1)

toks = [int(x) for x in open(TOKENS)]
N_CTX = 512
ids = toks[:N_CTX]
uniq = sorted(set(ids)); rowmap = {t: i for i, t in enumerate(uniq)}
erows = torch.cat([q8_rows("token_embd.weight", t, t + 1) for t in uniq])
x = erows[[rowmap[t] for t in ids]] * (float(E) ** 0.5)
del erows
print(f"gathered {len(uniq)} embed rows", flush=True)

causal = torch.triu(torch.full((N_CTX, N_CTX), float("-inf")), diagonal=1)
pos = torch.arange(N_CTX)
swa = causal.clone(); swa[pos[:, None] - pos[None, :] >= SW] = float("-inf")

t0 = time.time()
for L in range(NL):
    g = L in GLOBALS
    hd, nkv = HD[g], NKV[g]
    theta = 1e6 if g else 1e4
    p = f"blk.{L}."
    an, qn, kn = f32(p+"attn_norm.weight"), f32(p+"attn_q_norm.weight"), f32(p+"attn_k_norm.weight")
    pan, fn, pfn = f32(p+"post_attention_norm.weight"), f32(p+"ffn_norm.weight"), f32(p+"post_ffw_norm.weight")
    sc = float(f32(p+"layer_output_scale.weight")[0])
    Wq, Wk, Wo = q8(p+"attn_q.weight"), q8(p+"attn_k.weight"), q8(p+"attn_output.weight")
    Wv = None if g else q8(p+"attn_v.weight")
    h = rms(x, an)
    q = (h @ Wq.t()).view(N_CTX, NH, hd)
    k_raw = (h @ Wk.t()).view(N_CTX, nkv, hd)
    v = k_raw.clone() if g else (h @ Wv.t()).view(N_CTX, nkv, hd)
    q = rms(q, qn); k = rms(k_raw, kn)
    v = v * torch.rsqrt(v.pow(2).mean(-1, keepdim=True) + EPS)
    q = rope(q, theta, g); k = rope(k, theta, g)
    grp = NH // nkv
    kx = k.repeat_interleave(grp, dim=1); vx = v.repeat_interleave(grp, dim=1)
    att = torch.softmax(torch.einsum("qhd,khd->hqk", q, kx) + (causal if g else swa)[None], dim=-1)
    out = torch.einsum("hqk,khd->qhd", att, vx).reshape(N_CTX, NH * hd)
    x = x + rms(out @ Wo.t(), pan)
    del Wq, Wk, Wo, Wv
    Wg, Wu, Wd = q8(p+"ffn_gate.weight"), q8(p+"ffn_up.weight"), q8(p+"ffn_down.weight")
    h = rms(x, fn)
    gate = h @ Wg.t(); up = h @ Wu.t()
    act = 0.5 * gate * (1.0 + torch.tanh(0.7978845608028654 * (gate + 0.044715 * gate**3)))
    x = x + rms((act * up) @ Wd.t(), pfn)
    x = x * sc
    del Wg, Wu, Wd
    print(f"  L{L} |x| {x.norm():.3e} ({time.time()-t0:.0f}s)", flush=True)

x = rms(x, f32("output_norm.weight"))
V = vocab
logits = torch.empty(N_CTX, V, dtype=torch.float32)
CH = 16384
for r0 in range(0, V, CH):
    r1 = min(r0 + CH, V)
    logits[:, r0:r1] = x @ q8_rows("token_embd.weight", r0, r1).t()
logits = torch.tanh(logits / CAP) * CAP
logp = torch.log_softmax(logits, dim=-1)
first = N_CTX // 2
nll = -logp[torch.arange(N_CTX - 1), torch.tensor(toks[1:N_CTX])]
scored = nll[first - 1:]
ppl = float(torch.exp(scored.mean()))
rel = (ppl - ORACLE) / ORACLE
print(f"ARTIFACT GATE: sp-model OK_Q8 PPL = {ppl:.4f} vs gold {ORACLE} -> {rel*100:+.2f}%  [{time.time()-t0:.0f}s]", flush=True)
print(("PASS" if abs(rel) <= 0.08 else "FAIL") + " (8% telemetry floor)", flush=True)
