# _t2g_perm_hunt.py — extract the layer permutation: for each GGUF blk.L, find which
# safetensors layer it actually matches (argmax cosine over a window).
import json, struct, sys, glob
_log = open(r"C:\Users\Knack\AppData\Local\Temp\_t2g.log", "a", buffering=1, encoding="utf-8")
sys.stdout = _log; sys.stderr = _log
import numpy as np
import torch
torch.set_num_threads(1)

GG = glob.glob(r"D:\Files\Models\Gemma4\gemma-4-12b-it-Q4_K_M\*.gguf")[0]
BUCKET = r"D:\Files\Models\Gemma4\gemma-4-12b-bucket"
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

def cosm(a, b):
    a = a / (a.norm(dim=1, keepdim=True) + 1e-9)
    b = b / (b.norm(dim=1, keepdim=True) + 1e-9)
    return float((a * b).sum(1).mean())

# ffn_down has same shape on ALL layers [3840 rows x 15360] -> cross-match any pair.
# Cache ST ffn_down for all layers once? 48 x 226MB f32 = too big. Window approach:
# for each blk L in 0..23, test ST layers in [L-5, L+6] window.
print("blk.L.ffn_down -> best-matching ST layer (window L-5..L+6):", flush=True)
gcache = {}
for L in range(24):
    g = deq(f"blk.{L}.ffn_down.weight")
    best = (-1, -2.0); row = []
    for j in range(max(0, L - 5), min(48, L + 7)):
        c = cosm(g, st(f"layers.{j}.mlp.down_proj.weight"))
        row.append((j, round(c, 3)))
        if c > best[1]: best = (j, c)
    print(f"  blk{L:2d} -> ST L{best[0]} (cos {best[1]:.4f})   {row}", flush=True)
print("DONE", flush=True)
