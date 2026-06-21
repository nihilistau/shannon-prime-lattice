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
| 6b18bacf0d343a09 | agent | nightshift,curator,idle scheduler,assembly,B4,SP_B4_NIGHTSHIFT,SP_B3_DISPOSER,pouw_ledger,kairos,distill,do not rebuild | NIGHTSHIFT curator = assembly: B4 hook + SP_B3_DISPOSER=2 ablation oracle + pouw_ledger open/append + KAIROS tick loop (curator seam named) + curator/*.py. Build the glue, NOT a new scheduler. | DESIGN | sum/6b18bacf0d343a09.md |
| 3d6944428f356826 | agent | nightshift,curator,ep.tok,ep.secret,ep.txt,B4,persistence,prerequisite,routes.rs,disposer,do not rebuild | Live B4 episodes on disk = ONLY ep.k/v/mf. Ablation oracle needs ep.secret+ep.tok (skips live, routes.rs:906). Curator step 0 = extend B4 hook to write ep.txt+ep.tok. SpinorReceipt hash-only. | DESIGN | sum/3d6944428f356826.md |
