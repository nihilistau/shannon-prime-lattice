# _t2e_tensor_diff.py — MECHANISM HUNT: direct value-level diff, K_M GGUF dequant
# vs official safetensors (same source checkpoint). Per-row cosine + rope-permutation
# detection on Q/K. Run from %TEMP% (self-logging).
import json, struct, sys, glob
_log = open(r"C:\Users\Knack\AppData\Local\Temp\_t2e.log", "a", buffering=1, encoding="utf-8")
sys.stdout = _log; sys.stderr = _log
import numpy as np
import torch
torch.set_num_threads(1)

GG = glob.glob(r"D:\Files\Models\Gemma4\gemma-4-12b-it-Q4_K_M\*.gguf")[0]
BUCKET = r"D:\Files\Models\Gemma4\gemma-4-12b-bucket"
print("gguf:", GG, flush=True)

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
        elif n > 64: f.seek(sz[it] * n, 1)
        else: [gval(it) for _ in range(n)]
        kv[k] = None
    else: kv[k] = gval(t)
tens = {}
for _ in range(n_t):
    nm = gstr(); nd = u32()
    dims = [u64() for _ in range(nd)]
    ty = u32(); off = u64()
    tens[nm] = (ty, dims, off)
align = kv.get("general.alignment", 32)
data0 = (f.tell() + align - 1) // align * align

def deq(nm):
    ty, dims, off = tens[nm]
    n_in = int(dims[0]); rows = int(np.prod(dims[1:])) if len(dims) > 1 else 1
    n = n_in * rows
    f.seek(data0 + off)
    if ty == 0: x = np.frombuffer(f.read(4 * n), "<f4").copy()
    elif ty == 12:
        nb = n // 256
        raw = np.frombuffer(f.read(144 * nb), np.uint8).reshape(nb, 144)
        d = raw[:, 0:2].copy().view("<f2").astype(np.float32)
        dmin = raw[:, 2:4].copy().view("<f2").astype(np.float32)
        scl = raw[:, 4:16]; q = raw[:, 16:144]
        y = np.empty((nb, 256), np.float32)
        for j in range(8):
            if j < 4:
                sc = (scl[:, j] & 63).astype(np.float32); mn = (scl[:, j + 4] & 63).astype(np.float32)
            else:
                sc = ((scl[:, j + 4] & 0xF) | ((scl[:, j - 4] >> 6) << 4)).astype(np.float32)
                mn = ((scl[:, j + 4] >> 4) | ((scl[:, j] >> 6) << 4)).astype(np.float32)
            qcol = q[:, (j // 2) * 32:(j // 2) * 32 + 32]
            nib = (qcol & 0xF) if j % 2 == 0 else (qcol >> 4)
            y[:, j * 32:(j + 1) * 32] = (d * sc[:, None]) * nib - (dmin * mn[:, None])
        x = y.reshape(-1)
    elif ty == 14:
        nb = n // 256
        raw = np.frombuffer(f.read(210 * nb), np.uint8).reshape(nb, 210)
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
            y[:, base+0:base+32] = sch[:, isx + 0] * q1
            y[:, base+32:base+64] = sch[:, isx + 2] * q2
            y[:, base+64:base+96] = sch[:, isx + 4] * q3
            y[:, base+96:base+128] = sch[:, isx + 6] * q4
        x = (y * d).reshape(-1)
    else: raise ValueError((nm, ty))
    return torch.from_numpy(x.reshape(rows, n_in) if rows > 1 else x)

sf = open(BUCKET + r"\model.safetensors", "rb")
shn = struct.unpack("<Q", sf.read(8))[0]
shdr = json.loads(sf.read(shn)); sbase = 8 + shn
def st(nm):
    e = shdr["model.language_model." + nm]; o, en = e["data_offsets"]
    sf.seek(sbase + o)
    raw = np.frombuffer(sf.read(en - o), dtype="<u2")
    x = (raw.astype(np.uint32) << 16).view(np.float32).copy()
    return torch.from_numpy(x.reshape(e["shape"]) if len(e["shape"]) > 1 else x)

def rowcos(a, b):                                   # mean per-row cosine
    a = a / (a.norm(dim=1, keepdim=True) + 1e-9)
    b = b / (b.norm(dim=1, keepdim=True) + 1e-9)
    return (a * b).sum(1)

def neox_perm(t, n_head, hd):                       # interleaved->half-split row reorder
    # row r within head: even rows first then odd (the classic convert permute_qk)
    out = t.view(n_head, hd, -1)
    idx = torch.cat([torch.arange(0, hd, 2), torch.arange(1, hd, 2)])
    return out[:, idx, :].reshape(t.shape[0], -1)

PAIRS = [("blk.0.attn_q.weight", "layers.0.self_attn.q_proj.weight", 16, 512),
         ("blk.0.attn_k.weight", "layers.0.self_attn.k_proj.weight", 8, 256),
         ("blk.5.attn_q.weight", "layers.5.self_attn.q_proj.weight", 16, 512),
         ("blk.5.attn_k.weight", "layers.5.self_attn.k_proj.weight", 1, 512),
         ("blk.0.attn_output.weight", "layers.0.self_attn.o_proj.weight", 0, 0),
         ("blk.0.ffn_gate.weight", "layers.0.mlp.gate_proj.weight", 0, 0),
         ("blk.0.ffn_down.weight", "layers.0.mlp.down_proj.weight", 0, 0),
         ("blk.5.ffn_down.weight", "layers.5.mlp.down_proj.weight", 0, 0)]
for gnm, snm, nh, hd in PAIRS:
    g = deq(gnm); s = st(snm)
    if g.shape != s.shape:
        print(f"{gnm}: SHAPE {tuple(g.shape)} vs {tuple(s.shape)} MISMATCH", flush=True); continue
    c = rowcos(g, s)
    line = f"{gnm}: direct cos mean {c.mean():.5f} min {c.min():.5f}"
    if nh:                                          # try the classic q/k permutation both ways
        cp = rowcos(neox_perm(g, nh, g.shape[0] // nh), s)
        line += f" | perm(g) cos {cp.mean():.5f}"
    print(line, flush=True)

# embed rows (token 1000..1004) K_M Q4_K vs ST
ge = deq("token_embd.weight")[1000:1005]
se = st("embed_tokens.weight")[1000:1005]
print("embed rows 1000-1004 cos:", [round(float(x), 5) for x in rowcos(ge, se)], flush=True)

# scalars + norms quick re-print for the K_M (is K_M's scalar set == ST?)
gs = np.array([float(deq(f"blk.{L}.layer_output_scale.weight")[0]) for L in range(8)])
ss = np.array([float(st(f"layers.{L}.layer_scalar")[0]) for L in range(8)])
print("K_M scalars[0:8]:", np.round(gs, 4).tolist(), flush=True)
print("ST  scalars[0:8]:", np.round(ss, 4).tolist(), flush=True)

# provenance metadata
for k in sorted(kv):
    if k.startswith("general.") and kv[k] is not None:
        print(f"  kv {k} = {kv[k]}", flush=True)

# per-layer cosine curve: revision-drift (smooth) vs structural cliff (globals?)
print("\nper-layer cos(GGUF,ST) attn_q | ffn_down  (* = global layer):", flush=True)
for L in range(48):
    cq = rowcos(deq(f"blk.{L}.attn_q.weight"), st(f"layers.{L}.self_attn.q_proj.weight")).mean()
    cd = rowcos(deq(f"blk.{L}.ffn_down.weight"), st(f"layers.{L}.mlp.down_proj.weight")).mean()
    print(f"  L{L:2d}{'*' if L % 6 == 5 else ' '} q {cq:.4f}  down {cd:.4f}", flush=True)
print("DONE", flush=True)
