# _t2b_gguf_forensics.py — GGUF vs official safetensors, tensor-level diff.
# Question: where does the GGUF (and thus llama.cpp AND our transcoder) diverge
# from the checkpoint that scores PPL 4.68? Suspects: norm weights (+1 converter
# inheritance), layer_scalar values, embed scale.
import json, struct, sys, glob
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GG = glob.glob(r"D:\Files\Models\Gemma4\gemma-4-12B-it-QAT-Q4_0\*.gguf")[0]
BUCKET = r"D:\Files\Models\Gemma4\gemma-4-12b-bucket"
print("gguf:", GG)

# ---- minimal GGUF reader ----
f = open(GG, "rb")
def u32(): return struct.unpack("<I", f.read(4))[0]
def u64(): return struct.unpack("<Q", f.read(8))[0]
def gstr(): return f.read(u64()).decode("utf-8", "replace")
def gval(t):
    if t == 0: return struct.unpack("<B", f.read(1))[0]
    if t == 1: return struct.unpack("<b", f.read(1))[0]
    if t == 2: return struct.unpack("<H", f.read(2))[0]
    if t == 3: return struct.unpack("<h", f.read(2))[0]
    if t == 4: return u32()
    if t == 5: return struct.unpack("<i", f.read(4))[0]
    if t == 6: return struct.unpack("<f", f.read(4))[0]
    if t == 7: return bool(struct.unpack("<B", f.read(1))[0])
    if t == 8: return gstr()
    if t == 9:
        it, n = u32(), u64()
        return [gval(it) for _ in range(n)]
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
        if n > 64:                                  # skip giant arrays (vocab/merges)
            sz = {0:1,1:1,2:2,3:2,4:4,5:4,6:4,7:1,10:8,11:8,12:8}
            if it == 8:
                for _ in range(n): f.seek(u64(), 1)
            else: f.seek(sz[it] * n, 1)
            kv[k] = f"<array t{it} n{n}>"
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
pos = f.tell()
data0 = (pos + align - 1) // align * align

for k in sorted(kv):
    if "scal" in k or "logit" in k or "rope" in k or "norm" in k or "atten" in k:
        print(f"  kv {k} = {kv[k]}")

def gtensor(nm):                                    # F32 tensors only
    ty, dims, off = tens[nm]
    assert ty == 0, (nm, ty)
    n = int(np.prod(dims))
    f.seek(data0 + off)
    return np.frombuffer(f.read(4 * n), dtype="<f4").copy()

# ---- safetensors reader (bf16 -> f32) ----
sf = open(BUCKET + r"\model.safetensors", "rb")
hn = struct.unpack("<Q", sf.read(8))[0]
hdr = json.loads(sf.read(hn)); sbase = 8 + hn
def stensor(nm):
    e = hdr["model.language_model." + nm]; o, en = e["data_offsets"]
    sf.seek(sbase + o)
    raw = np.frombuffer(sf.read(en - o), dtype="<u2")
    return ((raw.astype(np.uint32) << 16).view(np.float32)).copy()

def cmp(gnm, snm, k=5):
    if gnm not in tens:
        print(f"  {gnm}: NOT IN GGUF"); return
    g = gtensor(gnm); s = stensor(snm)
    d0 = float(np.abs(g - s).max()) if g.shape == s.shape else -1
    d1 = float(np.abs(g - (s + 1.0)).max()) if g.shape == s.shape else -1
    print(f"  {gnm} vs {snm}: n {g.size}/{s.size}")
    print(f"    gguf {np.round(g[:k], 4).tolist()}  st {np.round(s[:k], 4).tolist()}")
    print(f"    max|g-s| {d0:.5f}   max|g-(s+1)| {d1:.5f}")

print("\n--- NORMS (the +1 question) ---")
cmp("blk.0.attn_norm.weight", "layers.0.input_layernorm.weight")
cmp("blk.0.attn_q_norm.weight", "layers.0.self_attn.q_norm.weight")
cmp("blk.5.attn_k_norm.weight", "layers.5.self_attn.k_norm.weight")
cmp("blk.0.post_attention_norm.weight", "layers.0.post_attention_layernorm.weight")
cmp("blk.0.ffn_norm.weight", "layers.0.pre_feedforward_layernorm.weight")
cmp("blk.0.post_ffw_norm.weight", "layers.0.post_feedforward_layernorm.weight")
cmp("output_norm.weight", "norm.weight")

print("\n--- LAYER SCALARS ---")
st_sc = np.array([stensor(f"layers.{L}.layer_scalar")[0] for L in range(48)])
gg_sc = None
for cand in ("blk.0.layer_output_scale", "blk.0.out_scale.weight", "blk.0.attn_output_scale"):
    if cand in tens: print("  found", cand)
names = [n for n in tens if "scal" in n.lower() or "out_scale" in n.lower()]
print("  gguf scalar-ish tensors:", names[:6], "..." if len(names) > 6 else "")
if names:
    base = names[0].split(".")[0]
    nm_fmt = names[0].replace("blk.0", "blk.{}").replace("blk.1", "blk.{}")
    try:
        gg_sc = np.array([gtensor(nm_fmt.format(L))[0] for L in range(48)])
        print("  gguf[0:8]:", np.round(gg_sc[:8], 4).tolist())
        print("  st  [0:8]:", np.round(st_sc[:8], 4).tolist())
        print("  max|diff|:", float(np.abs(gg_sc - st_sc).max()),
              " max|gg-st[shift+1]|:", float(np.abs(gg_sc[:-1] - st_sc[1:]).max()))
        print("  ratio gg/st [0:12]:", np.round(gg_sc[:12] / st_sc[:12], 4).tolist())
    except Exception as e:
        print("  scalar walk failed:", e)
