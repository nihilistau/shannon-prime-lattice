---
type: index
title: MEM-OKF LUT (Tier-0, always-loadable)
description: Keyword -> one-line agent-readable summary -> content address; follow addr to sum/ then full/.
tags: [mem-okf, lut, tier-0, index]
timestamp: 2026-06-21T09:53:50Z
resource: tools/okf_mem.py
sp_status: ACTIVE
sp_gate: G-MEM-OKF-CONFORM
sp_commit: TBD
sp_repro: python tools/okf_mem.py verify --root <root>
---

# MEM-OKF LUT

Lookup before you build. `python tools/okf_mem.py lookup --root <root> <kw>`

| addr | kind | keys | summary | status | sum |
|---|---|---|---|---|---|
| ff117f99ae5d99c5 | agent | rewind,persistent-kv,kvdecode,decode,ABI,L1,sp_session_register_kvdecode_backend,rust crate,do not rebuild | Rewind already exists: L1 verb sp_session_register_kvdecode_backend, impl gemma4_kv_decode_logits via sp_daemon Rust crates. DO NOT REBUILD. | GREEN | sum/ff117f99ae5d99c5.md |
| f615ee7764fe3ce1 | agent | byte-exact,SP_BYTEEXACT,exact-integer,islands,CRT-NTT,dual-prime,auditability,dsp_smoke | Byte-exact 12B forward done+gated. Linear algebra already in tools/sp_dsp_smoke; only the 4 islands were new. = exact arithmetic, NOT compression. | GREEN | sum/f615ee7764fe3ce1.md |
| 2637657d74257930 | agent | recall,W_c,wc_head,SP_B3_WC,autonomous,librarian,selector,latent,diffusion judge,head-to-head | Autonomous recall LIVE on 12B: learned W_c head (SP_B3_WC), 360/361 + 50/50 reject. Deployed selector is LATENT. Diffusion judge must beat it head-to-head before earning a build. | GREEN | sum/2637657d74257930.md |
| c2sig_9f3a1b2c0d4e5f60 | episode | episode,ep_n_div_000,C2-sig,nightshift,lobster | Curated novel-needle episode; full context = latent KV blob in Ring-2/Optane, addressed by C2 LSH sig. | ACTIVE | sum/c2sig_9f3a1b2c0d4e5f60.md |
| 6b18bacf0d343a09 | agent | nightshift,curator,idle scheduler,assembly,B4,SP_B4_NIGHTSHIFT,SP_B3_DISPOSER,pouw_ledger,kairos,distill,do not rebuild | NIGHTSHIFT curator = assembly: B4 hook + SP_B3_DISPOSER=2 ablation oracle + pouw_ledger open/append + KAIROS tick loop (curator seam named) + curator/*.py. Build the glue, NOT a new scheduler. | DESIGN | sum |
| 8c863dec97d079b3 | agent | diffjudge,G-DIFFJUDGE-OOD-H2H,diffusion wins,N5b justified,40-char truncation,verify the verifier,result-line,verbose capture,embeddings required benign | DIFFUSION WINS the OOD kill-test (94.4% vs W_c 28.3% @K8, reject 98%>=96.9%) -> Phase-5/N5b JUSTIFIED. My 'INVALID/no-tags' call was MY error: grepped the harness 40-char result-line (benign 'embeddings required...overriding' init warning) not the full reply (real tags K4N/X3K + <channel>thought, verbose-probe confirmed). parse_tag has no gt-fallback. LESSON: grep the verbose full capture not the truncated result-line; verify the verifier. | GREEN | sum/8c863dec97d079b3.md |
| 6f5d228dc1990c87 | agent | n5b,reservoir,resident weight,diffusion judge,dequant,H2D upload,disk IO,design refuted,GPU dequant,VRAM hot cache,SP_DG_RESERVOIR,do not rebuild | N5b resident reservoir (dg_resident_pt, SP_DG_RESERVOIR, default-off, byte-identical) ENGAGES - 143 tensor clones to host heap (telemetry-confirmed) - but gives ~NO speedup: warm query 743s ~= cold 785s, ~186s/step either way. The one-time clone is only ~7s; the ~186s/step is the per-forward DEQUANT->f32 + cudaMalloc + H2D upload, which the host reservoir doesn't touch. Diffusion judge is dequant+upload-bound, not disk-bound. REAL LEVER (N5c) = upload PACKED OK_Q4B to VRAM + GPU-side dequant per forward, or a VRAM hot-expert LRU cache. Also: test_diffjudge_denoise IGNORES SP_DJ_LIMIT (ran full 90+50 corpus). cuda_forward.cu change left UNCOMMITTED. | RED | sum/6f5d228dc1990c87.md |
