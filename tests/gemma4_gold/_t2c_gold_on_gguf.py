# _t2c_gold_on_gguf.py — THE DISCRIMINATOR: my proven-gold forward (PPL 4.68 on the
# official bf16) run on the QAT GGUF's OWN dequantized tensors + ITS rope_freqs table.
# Same fixture, same window. Single-digit => llama.cpp's gemma4 forward is broken.
# ~400 => the GGUF conversion damaged the content.
import json, struct, sys, time, glob
# Self-owned log: the detached-powershell pipe dies ~45-90s in (writes block,
# OMP spin-waits burn CPU). Bypass the pipe entirely.
_log = open(r"D:\F\shannon-prime-repos\_t2c_self.log", "a", buffering=1, encoding="utf-8")
sys.stdout = _log; sys.stderr = _log
import os
# OMP/oneDNN livelock at ~45s under per-layer alloc churn (3 runs reproduced,
# wedge layer varies, wall-clock constant). Kill threading entirely: reliable > fast.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import faulthandler; faulthandler.enable(file=_log)
import numpy as np
import torch
torch.set_num_threads(1)

GG = glob.glob(sys.argv[3] if len(sys.argv) > 3 else r"D:\Files\Models\Gemma4\gemma-4-12B-it-QAT-Q4_0\*.gguf")[0]
TOKENS = r"D:\F\shannon-prime-repos\_g4_12b_wiki_tokens.txt"
SWAP = sys.argv[2] if len(sys.argv) > 2 else ""     # "", "sc", "sc+norms", "sc+norms+embed"

# ---- safetensors reader (for hybrid tensor-class swaps) ----
BUCKET = r"D:\Files\Models\Gemma4\gemma-4-12b-bucket"
sf = open(BUCKET + r"\model.safetensors", "rb")
shn = struct.unpack("<Q", sf.read(8))[0]
shdr = json.loads(sf.read(shn)); sbase = 8 + shn
def st(nm):                                          # bf16 -> f32 torch
    e = shdr["model.language_model." + nm]; o, en = e["data_offsets"]
    sf.seek(sbase + o)
    raw = np.frombuffer(sf.read(en - o), dtype="<u2")
    x = (raw.astype(np.uint32) << 16).view(np.float32).copy()
    return torch.from_numpy(x.reshape(e["shape"]) if len(e["shape"]) > 1 else x)
print(f"SWAP mode: '{SWAP}'", flush=True)

# ---- GGUF reader ----
f = open(GG, "rb")
def u32(): return struct.unpack("<I", f.read(4))[0]
def u64(): return struct.unpack("<Q", f.read(8))[0]
def gstr(): return f.read(u64()).decode("utf-8", "replace")
def gval(t):
    if t in (0, 1, 7): return struct.unpack("<B" if t != 1 else "<b", f.read(1))[0]
    if t in (2, 3): return struct.unpack("<H" if t == 2 else "<h", f.read(2))[0]
    if t == 4: return u32()
    if t == 5: return struct.unpack("<i", f.read(4))[0]
    if t == 6: return struct.unpack("<f", f.read(4))[0]
    if t == 8: return gstr()
    if t == 10: return u64()
    if t == 11: return struct.unpack("<q", f.read(8))[0]
    if t == 12: return struct.unpack("<d", f.read(8))[0]
    raise ValueError(t)
assert f.read(4) == b"GGUF"
ver, n_t, n_kv = u32(), u64(), u64()
kv = {}
for _ in range(n_kv):
    k = gstr(); t = u32()
    if t == 9:
        it, n = u32(), u64()
        sz = {0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}
        if it == 8:
            for _ in range(n): f.seek(u64(), 1)
            kv[k] = None
        elif n > 64:
            f.seek(sz[it] * n, 1); kv[k] = None
        else:
            kv[k] = [gval(it) for _ in range(n)]
    else:
        kv[k] = gval(t)
tens = {}
for _ in range(n_t):
    nm = gstr(); nd = u32()
    dims = [u64() for _ in range(nd)]
    ty = u32(); off = u64()
    tens[nm] = (ty, dims, off)
align = kv.get("general.alignment", 32)
data0 = (f.tell() + align - 1) // align * align

def f16_f32(a):                                     # vectorized half->float via numpy
    return a.view("<u2").astype("<u2").view(np.uint16).astype(np.uint32), None
def deq(nm):
    ty, dims, off = tens[nm]
    n_in = int(dims[0]); rows = int(np.prod(dims[1:])) if len(dims) > 1 else 1
    n = n_in * rows
    f.seek(data0 + off)
    if ty == 0:                                     # F32
        x = np.frombuffer(f.read(4 * n), "<f4").copy()
    elif ty == 1:                                   # F16
        x = np.frombuffer(f.read(2 * n), "<f2").astype(np.float32)
    elif ty == 2:                                   # Q4_0: 18B/32 (lean transients)
        nb = n // 32
        raw = np.frombuffer(f.read(18 * nb), np.uint8).reshape(nb, 18)
        d = raw[:, :2].copy().view("<f2").astype(np.float32)        # [nb,1]
        qs = raw[:, 2:]
        x = np.empty((nb, 32), np.float32)
        x[:, :16] = (qs & 0xF).astype(np.float32)
        x[:, 16:] = (qs >> 4).astype(np.float32)
        x -= 8.0
        x *= d
        x = x.reshape(-1)
        del raw, qs, d
    elif ty == 8:                                   # Q8_0: 34B/32
        nb = n // 32
        raw = np.frombuffer(f.read(34 * nb), np.uint8).reshape(nb, 34)
        d = raw[:, :2].copy().view("<f2").astype(np.float32)
        q = raw[:, 2:].view(np.int8).astype(np.float32)
        x = (q * d).reshape(-1)
    elif ty == 12:                                  # Q4_K: 144B/256 (d,dmin f16 + scales[12] + qs[128])
        nb = n // 256
        raw = np.frombuffer(f.read(144 * nb), np.uint8).reshape(nb, 144)
        d = raw[:, 0:2].copy().view("<f2").astype(np.float32)       # [nb,1]
        dmin = raw[:, 2:4].copy().view("<f2").astype(np.float32)
        scl = raw[:, 4:16]                                          # packed 6-bit scales/mins
        q = raw[:, 16:144]
        y = np.empty((nb, 256), np.float32)
        for j in range(8):                          # 8 sub-blocks of 32
            if j < 4:
                sc = (scl[:, j] & 63).astype(np.float32)
                mn = (scl[:, j + 4] & 63).astype(np.float32)
            else:
                sc = ((scl[:, j + 4] & 0xF) | ((scl[:, j - 4] >> 6) << 4)).astype(np.float32)
                mn = ((scl[:, j + 4] >> 4) | ((scl[:, j] >> 6) << 4)).astype(np.float32)
            qcol = q[:, (j // 2) * 32:(j // 2) * 32 + 32]
            nib = (qcol & 0xF) if j % 2 == 0 else (qcol >> 4)
            y[:, j * 32:(j + 1) * 32] = (d * sc[:, None]) * nib - (dmin * mn[:, None])
        x = y.reshape(-1)
    elif ty == 14:                                  # Q6_K: 210B/256
        nb = n // 256
        raw = np.frombuffer(f.read(210 * nb), np.uint8).reshape(nb, 210)
        ql = raw[:, :128]; qh = raw[:, 128:192]
        sc = raw[:, 192:208].view(np.int8).astype(np.float32)       # [nb,16]
        d = raw[:, 208:210].copy().view("<f2").astype(np.float32)   # [nb,1]
        y = np.empty((nb, 256), np.float32)
        for half in range(2):                       # two 128-halves, vectorized inside
            qlh = ql[:, half*64:(half+1)*64]; qhh = qh[:, half*32:(half+1)*32]
            sch = sc[:, half*8:(half+1)*8]
            l = np.arange(32)
            q1 = ((qlh[:, :32] & 0xF) | (((qhh >> 0) & 3) << 4)).astype(np.int8) - 32
            q2 = ((qlh[:, 32:] & 0xF) | (((qhh >> 2) & 3) << 4)).astype(np.int8) - 32
            q3 = ((qlh[:, :32] >> 4) | (((qhh >> 4) & 3) << 4)).astype(np.int8) - 32
            q4 = ((qlh[:, 32:] >> 4) | (((qhh >> 6) & 3) << 4)).astype(np.int8) - 32
            isx = (l // 16)                                          # [32] -> 0/1
            base = half * 128
            y[:, base+0:base+32]   = sch[:, isx + 0] * q1
            y[:, base+32:base+64]  = sch[:, isx + 2] * q2
            y[:, base+64:base+96]  = sch[:, isx + 4] * q3
            y[:, base+96:base+128] = sch[:, isx + 6] * q4
        x = (y * d).reshape(-1)
    else:
        raise ValueError(f"{nm}: unsupported gguf type {ty}")
    t = torch.from_numpy(x.reshape(rows, n_in) if rows > 1 else x)
    out = t.to(torch.bfloat16) if rows > 1 else t.float().clone()
    del t, x
    return out

E, NL, NH = 3840, 48, 16
EPS, CAP, SW = 1e-6, 30.0, 1024
GLOBALS = {5, 11, 17, 23, 29, 35, 41, 47}
HD = {True: 512, False: 256}; NKV = {True: 1, False: 8}

# STREAMING: the host is RAM-starved (available ~0). Hold ONE layer at a time;
# embed is row-gathered for input and chunk-streamed for the tied head. Peak ~1.5GB.
print("streaming mode: row-gather embed + per-layer load/compute/free", flush=True)
t0 = time.time()
torch.set_num_threads(4)

def st_rows(r0, r1):                                # safetensors embed rows [r0,r1) bf16->f32
    e = shdr["model.language_model.embed_tokens.weight"]
    o = e["data_offsets"][0]
    sf.seek(sbase + o + r0 * 3840 * 2)
    raw = np.frombuffer(sf.read((r1 - r0) * 3840 * 2), dtype="<u2")
    return torch.from_numpy(((raw.astype(np.uint32) << 16).view(np.float32)).reshape(r1 - r0, 3840).copy())

def deq_rows(nm, r0, r1):                           # dequant rows [r0,r1) of a 2D tensor
    if "embed" in SWAP: return st_rows(r0, r1)
    ty, dims, off = tens[nm]
    n_in = int(dims[0])
    if ty == 12:                                    # Q4_K rows (144B/256)
        rb = n_in // 256 * 144
        f.seek(data0 + off + r0 * rb)
        nb = (r1 - r0) * (n_in // 256)
        raw = np.frombuffer(f.read(rb * (r1 - r0)), np.uint8).reshape(nb, 144)
        d = raw[:, 0:2].copy().view("<f2").astype(np.float32)
        dmin = raw[:, 2:4].copy().view("<f2").astype(np.float32)
        scl = raw[:, 4:16]; q = raw[:, 16:144]
        y = np.empty((nb, 256), np.float32)
        for j in range(8):
            if j < 4:
                sc = (scl[:, j] & 63).astype(np.float32)
                mn = (scl[:, j + 4] & 63).astype(np.float32)
            else:
                sc = ((scl[:, j + 4] & 0xF) | ((scl[:, j - 4] >> 6) << 4)).astype(np.float32)
                mn = ((scl[:, j + 4] >> 4) | ((scl[:, j] >> 6) << 4)).astype(np.float32)
            qcol = q[:, (j // 2) * 32:(j // 2) * 32 + 32]
            nib = (qcol & 0xF) if j % 2 == 0 else (qcol >> 4)
            y[:, j * 32:(j + 1) * 32] = (d * sc[:, None]) * nib - (dmin * mn[:, None])
        return torch.from_numpy(y.reshape(r1 - r0, n_in))
    if ty == 14:                                    # Q6_K rows
        rb = n_in // 256 * 210
        f.seek(data0 + off + r0 * rb)
        nb = (r1 - r0) * (n_in // 256)
        raw = np.frombuffer(f.read(rb * (r1 - r0)), np.uint8).reshape(nb, 210)
        ql = raw[:, :128]; qh = raw[:, 128:192]
        sc = raw[:, 192:208].view(np.int8).astype(np.float32)
        d = raw[:, 208:210].copy().view("<f2").astype(np.float32)
        y = np.empty((nb, 256), np.float32)
        for half in range(2):
            qlh = ql[:, half*64:(half+1)*64]; qhh = qh[:, half*32:(half+1)*32]
            sch = sc[:, half*8:(half+1)*8]
            l = np.arange(32); isx = l // 16; base = half * 128
            q1 = ((qlh[:, :32] & 0xF) | (((qhh >> 0) & 3) << 4)).astype(np.int8) - 32
            q2 = ((qlh[:, 32:] & 0xF) | (((qhh >> 2) & 3) << 4)).astype(np.int8) - 32
            q3 = ((qlh[:, :32] >> 4) | (((qhh >> 4) & 3) << 4)).astype(np.int8) - 32
            q4 = ((qlh[:, 32:] >> 4) | (((qhh >> 6) & 3) << 4)).astype(np.int8) - 32
            y[:, base+0:base+32]   = sch[:, isx + 0] * q1
            y[:, base+32:base+64]  = sch[:, isx + 2] * q2
            y[:, base+64:base+96]  = sch[:, isx + 4] * q3
            y[:, base+96:base+128] = sch[:, isx + 6] * q4
        y *= d
        return torch.from_numpy(y.reshape(r1 - r0, n_in))
    raise ValueError(ty)

rope_tab = {}
if "rope_freqs.weight" in tens:
    rope_tab[True] = torch.from_numpy(np.asarray(deq("rope_freqs.weight"), np.float32).reshape(-1))
    rf = rope_tab[True]
    print(f"  rope_freqs[{rf.numel()}]: [0..3]={rf[:4].tolist()} [63..66]={rf[63:67].tolist()}")

NORMMAP = [("an", "attn_norm", "input_layernorm"), ("qn", "attn_q_norm", "self_attn.q_norm"),
           ("kn", "attn_k_norm", "self_attn.k_norm"),
           ("pan", "post_attention_norm", "post_attention_layernorm"),
           ("fn", "ffn_norm", "pre_feedforward_layernorm"),
           ("pfn", "post_ffw_norm", "post_feedforward_layernorm")]

def load_layer(L, verbose=False):
    g = L in GLOBALS
    p = f"blk.{L}."
    sp = f"layers.{L}."
    W = {}
    for short, gn, sn in NORMMAP:
        if "norms" in SWAP: W[short] = st(sp + sn + ".weight").float()
        else:               W[short] = deq(p + gn + ".weight").float()
    for short, gn in [("q", "attn_q"), ("k", "attn_k"), ("o", "attn_output"),
                      ("g", "ffn_gate"), ("u", "ffn_up"), ("d", "ffn_down")]:
        W[short] = deq(p + gn + ".weight")
    if not g: W["v"] = deq(p + "attn_v.weight")
    if "sc" in SWAP: W["sc"] = float(st(sp + "layer_scalar")[0])
    else:            W["sc"] = float(deq(p + "layer_output_scale.weight")[0])
    return W
print(f"  embed ready {time.time()-t0:.0f}s; layer_output_scale[0:8] = "
      f"{[round(float(deq(f'blk.{L}.layer_output_scale.weight')[0]),4) for L in range(8)]}", flush=True)

def rms(x, w):
    return x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + EPS) * w

def rope(x, theta, use_tab):
    Tn, H, D = x.shape; half = D // 2
    j = torch.arange(half, dtype=torch.float64)
    inv = theta ** (-2.0 * j / D)
    if use_tab:                                     # the GGUF's own factor table
        inv = inv / rope_tab[True][:half].double()
    ang = torch.arange(Tn, dtype=torch.float64)[:, None] * inv[None, :]
    cos, sin = torch.cos(ang).float(), torch.sin(ang).float()
    x1, x2 = x[..., :half], x[..., half:]
    c, s = cos[:, None, :], sin[:, None, :]
    return torch.cat([x1 * c - x2 * s, x1 * s + x2 * c], dim=-1)

toks = [int(x) for x in open(TOKENS)]
N_CTX = int(sys.argv[1]) if len(sys.argv) > 1 else 512
ids = toks[:N_CTX]
uniq = sorted(set(ids))
rowmap = {t: i for i, t in enumerate(uniq)}
erows = torch.cat([deq_rows("token_embd.weight", t, t + 1) for t in uniq])   # [U, E] f32
x = erows[[rowmap[t] for t in ids]] * (float(E) ** 0.5)
del erows
print(f"  gathered {len(uniq)} unique embed rows", flush=True)
causal = torch.triu(torch.full((N_CTX, N_CTX), float("-inf")), diagonal=1)
pos = torch.arange(N_CTX)
swa = causal.clone(); swa[pos[:, None] - pos[None, :] >= SW] = float("-inf")

t0 = time.time()
for L in range(NL):
    g = L in GLOBALS
    hd, nkv = HD[g], NKV[g]
    theta = 1e6 if g else 1e4
    W = load_layer(L)
    h = rms(x, W["an"]).to(torch.bfloat16)
    q = (h @ W["q"].t()).float().view(N_CTX, NH, hd)
    k_raw = (h @ W["k"].t()).float().view(N_CTX, nkv, hd)
    v = k_raw.clone() if g else (h @ W["v"].t()).float().view(N_CTX, nkv, hd)
    q = rms(q, W["qn"])
    k = rms(k_raw, W["kn"])
    v = v * torch.rsqrt(v.pow(2).mean(-1, keepdim=True) + EPS)
    q = rope(q, theta, g); k = rope(k, theta, g)
    grp = NH // nkv
    kx = k.repeat_interleave(grp, dim=1); vx = v.repeat_interleave(grp, dim=1)
    att = torch.softmax(torch.einsum("qhd,khd->hqk", q, kx) + (causal if g else swa)[None], dim=-1)
    out = torch.einsum("hqk,khd->qhd", att, vx).reshape(N_CTX, NH * hd)
    ao = (out.to(torch.bfloat16) @ W["o"].t()).float()
    x = x + rms(ao, W["pan"])
    h = rms(x, W["fn"]).to(torch.bfloat16)
    gate = (h @ W["g"].t()).float()
    up = (h @ W["u"].t()).float()
    act = 0.5 * gate * (1.0 + torch.tanh(0.7978845608028654 * (gate + 0.044715 * gate**3)))
    dn = ((act * up).to(torch.bfloat16) @ W["d"].t()).float()
    x = x + rms(dn, W["pfn"])
    x = x * W["sc"]
    del W, h, q, k_raw, v, k, kx, vx, att, out, ao, gate, up, act, dn
    print(f"  L{L} |x| {x.norm():.3e} ({time.time()-t0:.0f}s)", flush=True)

x = rms(x, st("norm.weight").float() if "norms" in SWAP else deq("output_norm.weight").float())
xb = x.to(torch.bfloat16)
V = int(np.prod(tens["token_embd.weight"][1][1:]))
logits = torch.empty(N_CTX, V, dtype=torch.float32)
CH = 16384
for r0 in range(0, V, CH):                          # stream the tied head
    r1 = min(r0 + CH, V)
    chunk = deq_rows("token_embd.weight", r0, r1).to(torch.bfloat16)
    logits[:, r0:r1] = (xb @ chunk.t()).float()
    del chunk
logits = torch.tanh(logits / CAP) * CAP
logp = torch.log_softmax(logits, dim=-1)
first = N_CTX // 2
nll = -logp[torch.arange(N_CTX - 1), torch.tensor(toks[1:N_CTX])]
scored = nll[first - 1:]
print(f"GGUF-WEIGHTS GOLD-FORWARD PPL (targets [{first},{N_CTX})): "
      f"{torch.exp(scored.mean()).item():.4f}  (n={len(scored)})  [{time.time()-t0:.0f}s]")
for p in range(first - 1, first + 2):
    row = logits[p]
    mx, mi = row.max(0)
    print(f"  pos {p}: max {mx.item():.4f} (id {mi.item()})  target[{toks[p+1]}] "
          f"{row[toks[p+1]].item():.4f}  nll {nll[p].item():.4f}")
