# lessons.md — Shannon-Prime session learnings

Running log of hard-won lessons. Newest on top. Each entry: what happened, the root cause,
the rule that prevents the repeat. Receipts-first: cite the run/commit where it applies.

---

## 2026-06-18 — The boundary thesis: the substrate wins on the container, never on the content

This is the keystone lesson of unifying XBAR onto the exact-integer O_K substrate (Q(√−163), the
dual-prime negacyclic CRT-NTT). Ten receipts split cleanly into two piles, and the split IS the lesson.

**What the integer substrate WON — every win was about EXACTNESS, not about structure.**
The Ring-3 bind re-carried onto native `sp_pr_mul`/NTT is **256/256 bit-identical** to the integer
reference, the ±1 carrier recall is **lossless** vs float, and the superposition vector M is
**byte-identical across 8 summation permutations** where the float M diverges 4.44e-15 (non-associative).
The Frobenius π^k integer Ring-2 store (Theorem-T4 form) reconstructs **sub-ULP at 24 bits** at 0.76× the
float store. These are all the same property: the substrate is an **indestructible algebraic container** —
exact bind, exact integer store, reduction-order immunity (a *correctness* guarantee, not a speed trick).
Receipts: engine `0019b86` (Leg A), `dbe4103`/`d076797` (Frobenius), `15e7051` (full organism native).

**What number-theoretic STRUCTURE LOST — four honest negatives, each measured-inert, all kept on record.**
(a) Dirichlet-character carriers (Leg B, `d7d96fe`) *do* Heegner-order native coherence (Weil bound:
random 0.0355 > OK(−67) 0.0153 > OK(−163) 0.0086) but recall got WORSE (spiky small-period spectrum =
poor self-unbind) and C2 SimHash was unchanged (random projection washes coherence out) — random ±1 stays
the carrier. (b) Möbius square-free compression of the dense Ring-3 M (`1e70763`) fails — M is 99.6% dense,
divisor-recon error 1.35× the signal. (c) lzma/zlib entropy coding on the Frobenius residual (`e6d17bb`) is
dead weight (1.02×) — the int8 residual is incompressible high-entropy. (d) T2-Möbius on the real
gemma-4-12b embeddings (`ac76c8e`) reconstructs composite rows *worse than random* — trained embeddings
have no multiplicative index structure (token IDs are BPE merge ranks).

**THE RULE: the value of the exact-integer substrate is the algebraic CONTAINER (bind / store /
reduction-order immunity), NOT structure imposed on the high-entropy CONTENT.** Before reaching for a
number-theoretic transform (Möbius, Dirichlet characters, divisor sieves) to *compress or organize the
payload*, ask whether the payload actually carries that structure — and MEASURE it cheaply first
(coherence sweep, density check, reconstruction-vs-random) before building. The chaos is bound *inside* the
rigid order; it is not made orderly *by* it. Corollary for the public record: keep the design-proposal vs
validated distinction explicit — T2 (Möbius) was a theory-paper proposal never empirically validated; T4
(Frobenius) was validated 6-sig-fig on Gemma3-1B and is the lever that actually shipped (the model-weight
T4 quantization is the next step — NOT Möbius).

---

## 2026-06-17 — Three lessons from closing C2 Memo curator + Ring-3 Path A

**(i) Verify Gemini reframes against the substrate — then MEASURE the fix before shipping it.**
Gemini proposed: "dot IS Hamming for ±1 vectors, so replace your dot-product resolver with XOR+popcount —
it's a clean isomorphism." The direction (Hamming-space resolver) was right. The mechanism was wrong
as-built: our centroids are real-valued projection outputs (`R@K`, K float) carrying magnitude, NOT ±1
sign bits. For real centroids `dot ≠ r − 2·Hamming`. An r-sweep measurement settled it: sign-binarize at
r=32 collapses the bit-gap to −1 (regression), recovers at r≥128, ships at r=256 (bit-gap +19, reduction-
order-immune address). **Rule: when a collaborator reframes the mechanism elegantly, honor the direction,
fix the mechanics, and run a sweep (not a single-point) to confirm before committing to the design.**
Receipt: C2 r-sweep in `CONTRACT-XBAR-C2-memo-curator-loop.md` §3, engine `6dd87b9` (discrete resolver).

**(ii) Two classes of metric-bug: ratio-vs-margin at low N, and harness self-checks too weak to catch layout errors.**
R3.1 BIND shipped with an SNR *ratio* (`signal/noise`) as the separation metric; at N=2 the ratio can be
large but the absolute margin tiny — the metric looked healthy while hiding a degenerate case.
Fix: switch to `margin = signal − noise` (the signed gap) which is linear and correctly flags N=2 ambiguity.
Catch: also add an episode-size sanity check in the harness (assert `ep.k == expected_layers` before computing
centroid). The organism step-1 clamp fix (`_c2_ep_wiki` format uses 512-padded globals; ep_audio was padded
to 2048 via the gemma4 CUDA jagged SWA path → clamp to 512 caught by the size mismatch in the harness).
**Rule: write `margin = signal − noise`, not `signal/noise`; always assert harness tensor shapes against the
contract layout before running any gate that depends on them.**
Receipt: R3.1 `G-R3-BIND` margin fix commit `23539b7`; organism clamp commit `6600cf4`.

**(iii) Sandbox bash mount serves stale or truncated reads right after a Windows-side Edit — use /tmp
for hererdocs and verify via Windows MCP for D:\\Files and repo-root _xbar.**
The Cowork bash tool mounts only the four lattice/engine/system/system-engine repo subfolders. After a
Windows-side `Edit` call the mount may serve a cached or truncated version of the file until the next
mount refresh. Pattern: write transient payloads via `heredoc > /tmp/file`, not into the repo path
directly; for paths outside the repo (D:\\Files, repo-root `_xbar/`, creds) use Windows-MCP FileSystem
or PowerShell — the sandbox mount simply does not reach them. **Rule: trust the Read tool for repo
files post-Edit; for out-of-repo paths use Windows-MCP; never pipe bash-side reads of a just-edited
repo file into a gate output without verifying the write succeeded first.**
Receipt: organism artifact at `D:\F\shannon-prime-repos\_xbar\p2b\kai3` (out-of-mount).

---

## 2026-06-17 — Three lessons from closing XBAR P3.3/P3.4 + the GNA EAR on silicon

**(i) A multi-path store will silently swallow a single-path hook — let the cheap gate fail-fast.**
`gemma4_decode_cuda` has TWO prefill stores: the graph-capture path AND the velocity path. Under
recall/replay `use_graph` is FALSE, so the **velocity** path is the one that actually runs. The first
cut of P3.3 `SP_REPLAY` hooked only the graph store → the inject was inert (the gate would have read as
a no-op). The cheap **E2B** fail-fast leg of `G-P3-SHARED` caught it in ~2 minutes — *before* paying the
12B-metal cost. **Rule: when a hot path has more than one code route for the same operation, hook ALL of
them, and run the cheapest representative gate first so an inert seam surfaces for pennies, not for a
full 12B run.** Fix = inject at both stores (graph ~L2516 + velocity ~L2825).

**(ii) Well-formed primitives compose at their boundaries with zero new code.** P3.4's PPL scorer **is**
`gemma4_decode_cuda` in `SP_G4_SCORE` mode; `SP_REPLAY` is a flag on that same decode. So the recall-quality
gate (`G-P3-PPL`, +1.38% < 2%) composed `SP_REPLAY ∘ SP_G4_SCORE` with **zero new engine code**. When each
stage is a clean flag on the one decode, gates snap together — this is the payoff of the null-floor discipline
(one untouched decode, behaviour added only via off-by-default knobs).

**(iii) GNA: the OpenVINO toolchain is self-consistent only as a single ABI island.** The pip OpenVINO wheel
**lacks the GNA plugin** (Intel removed it after the 2023.3 line). Mixing the pip runtime with the 2023.3
*archive* runtime ABI-fails both ways. **The only working path is the archive's self-consistent 2023.3 runtime
via `setupvars`** (+ system py3.8). And two GNA conv constraints bite at lowering time: **no padding** (GNA is
VALID-only → encoder conv `padding=1→0`) and **filters must be a multiple of 4** (CTC head `33→36`, dummy
channels sliced). With those, POT GNA-native i16 PTQ recovers full FP32 token-recovery (0.877) and the
front-end runs on the physical GNA 2.0 at 0.877 == emu == FP32. Full recipe: memory
`reference_gna_openvino_toolchain`.

---

## 2026-06-16 — KAI-2 FINAL VERDICT (t10): Phase-1 GREEN, Phase-2 BOUNDED at the sequence-positional wall

This closes G-KAIROS-2. The "FIX (next pass)" prescribed in the RESOLVED entry below (manifold-anchor
loss → on-manifold softmax head → 512-event held-out corpus) was executed in full across t8→t10. It
**solved the off-manifold degeneracy** — and revealed a second, deeper wall underneath it that a
fixed-width learned packet cannot cross.

**t10 — the maximally-constrained packet (every excuse removed).** k=16 (above the EMB capacity floor),
`--fakeq` OK_Q4B teacher, on-manifold softmax head over an N=158 event-vocab subset, KL-only objective,
80/20 held-out split, and the now-correctly-wired sharp head temperature `tau=0.2` (the t9 bug was
`tau=args.tau` instead of `tau=args.head_tau` → soft blend; the one-line fix is in `train_kai2_codec.py`).
Receipts: HF `results_kai2/kai2_k16_t10/` (STATUS rc=0, train.log, 8 packets).
  - **`[manifold-gate] val mean max-cos to embed table = 0.9913`** (random baseline ~0.07; t9 was 0.70).
    The codec now emits clean, un-smeared, near-discrete on-manifold token equivalents — exactly the
    design intent. The manifold problem (cos 0.078 = noise, in the RESOLVED entry) is GONE.
  - **`BEST val_KL = 0.9157 @ epoch 6`** (held-out). It plateaus there — never drops below ~0.92 across
    all 10 epochs. **That plateau was the mathematical warning shot:** even restricted to real-token
    vectors, the projection could fit the manifold (cos→0.99) but could NOT move the teacher's decision
    distribution onto the salient pivot.

**The metal gate (12B OK_Q4B, 2060, held-out EVAL_EVENTS, clocks pinned 1680):**
```
case=salient  TEXT->ACTION [sel] | EMB(n=25)->ACTION [PASS] | PACKET(k=16)->NO_OP [miss]
case=idle     TEXT->NO_OP  [sel] | EMB(n=16)->NO_OP  [PASS] | PACKET(k=16)->NO_OP [PASS]
PHASE-1 EMB-DELIVERY GATE: 2/2 PASS    G-KAIROS-2 PACKET GATE: 1/2
```
Receipt: `_xbar/p2b/kai2_t10_gate.log`, `KAI2_GATE_EXIT=3`.

**THE DEFINITIVE FINDING (verified, not theory):** the wall is **sequence-positional**, and it is not any
of the three things we feared.
  - NOT the seam — `gemma4_kv_inject` delivers (EMB 2/2, including n=25 on the salient case).
  - NOT manifold distance — we reached cos 0.9913.
  - NOT raw capacity — EMB pivots at n≥16.
  What remains: a **fixed-width static linear packet cannot replicate the sequence-positional interplay
  of the original ~25-token stream without destroying attention routing.** The attention heads do not
  just read *which* features are present; they read *how those features are distributed across
  positions*. A 16-vector summary — even when each vector is a clean on-manifold token — compresses out
  the directional/positional variance the model uses to compute the decision shift. This is the P2.b
  k=2 generation wall (recognition top-1 0.462) reappearing at k=16: compression-vs-sequence, not
  compression-vs-manifold. The `EMB` control passes precisely because it preserves the ordered,
  per-position real-token sequence.

**VERDICT.** Phase-1 (latent residual-entry interrupt seam, `gemma4_kv_inject`) = **GREEN / verified
production asset** — a continuous raw-vector injection into the Layer-0 residual space forces a 12B dense
model to pivot its entire execution path, *provided the vectors preserve sequence integrity*. Phase-2
(the learned fixed-width single-event codec, `KAI2Codec`) = **BOUNDED / research frontier** — the strongest
possible packet (sharp, on-manifold, above-capacity) was the decisive test and it failed the salient
pivot. The research phase for the compressed single-event codec is **closed**; the physical limit is
isolated.

**FREEZE.** The injection harness (`test_gemma4_cuda.c run_kai2_packet_gate`, the `gemma4_kv_inject` seam
+ `SP_XBAR_EMB`, the `SP_KAI2_*` knobs) is frozen as a verified asset. The proof that moved was always
training-side; the serve path is sound. No further codec-compression cycles.

**PIVOT.** Replace the artificial k=16 summary bottleneck with gemma-4's native continuous-modality port:
stream sequential **40ms / 640-float / 16kHz frames** through the `audio_token_id=258881` mask
(`masked_scatter` into `inputs_embeds`, raw/unscaled). This feeds the downstream GNA/CNN work an
uncompressed, sequential feature tape — the exact structure the EMB control proves passes the metal gate
— instead of a fixed-width compressed packet the codec proves does not.

**The meta-lesson of the whole arc:** when a learned-compression artifact fails an on-metal behavioral
gate, walk the controls in order — (1) plumbing ({0,trained} content sweep), (2) on-manifold control
(real embeddings), (3) capacity ladder, (4) offline manifold-distance check, (5) THEN held-out
generalization. We paid for skipping straight to "retrain/quant-match" four times. And watch the
held-out loss *plateau*, not just its floor: a metric that fits one geometry (cos→0.99) while refusing
to move another (val_KL stuck at 0.92) is telling you the bottleneck is structural, not a capacity or
tuning problem.

---

## 2026-06-16 — KAI-2 latent interrupt: the AltUp injection war

### L0 (process, the one that keeps costing us). READ FIRST. Use what's already on the roadmap.
The operator has had to prime my context at every turn this session, and the AltUp / audio-projection
injection point was **already on the KAIROS roadmap** — I re-derived it from scratch over multiple
build/sweep cycles instead of reading `ROADMAP-KAIROS.md` + `RFC-XBAR` + the gemma4 forward code first.
**Rule:** before touching a phase, read `prompt.md` → `ENVIRONMENT.md` → `SESSION-HANDOFF.md` →
the active CONTRACT/RFC/ROADMAP → the actual code (cuda_forward.cu) + `git log`. The doc map in
`prompt.md §5/§8` is binding, not optional. The audio port was a known target; pointing it out should
not have been necessary.

### L1. Gemma-4 is AltUp — a single-stream residual override is diluted to zero.
gemma-4-unified maintains the residual as the **0th of N AltUp prediction streams**, predicted-and-
corrected across all 48 layers, with **per-layer embeddings (PLE) gathered from the token id** feeding
every block (`cuda_forward.cu` ~L3360 `k_ple_gather_at` from `dseq[dpos]`; ~L3432 `k_altup_gate` folds
it back into `dx` at every layer). The KAI-2 inject seam (`gemma4_kv_inject`, L3355-3357) overrode **only
the 0th stream at one position, post-embed**. The AltUp predictors + the placeholder token's PLE
"corrected" that override back toward the placeholder state ⇒ injection erased.

### L2. The 4-way invariance diagnostic — how to prove a seam is inert without a retrain.
Added `SP_KAI2_INJSCALE` (scale the injected vector) + `SP_KAI2_INJ_NOPLE` (zero the placeholder PLE)
knobs and swept. **The decision output was byte-identical across:** packet content (t3 vs t4, diff-RMS
0.996), magnitude (0× / 1× / 62× / 1000×), and PLE on/off. `INJSCALE=0` (no content) == `INJSCALE=1`
(full trained packet). Two takeaways:
  - **Scale-invariance is expected, not "inert":** the first thing every layer does is RMSNorm the
    residual (L3377), which divides out magnitude. A 62× sweep changing nothing only proves magnitude
    is normalized away — it does NOT prove the seam works. Don't over-read a scale null.
  - **`INJSCALE=0 == INJSCALE=1` IS the decisive plumbing receipt:** if zero-content and trained-content
    produce identical tokens, the injected positions never reach the readout. That's a serve-path
    structural fact, isolated from the codec/objective. **Method: when a learned artifact is inert on
    metal, sweep a content knob {0, trained} on the SAME build before blaming training.**

### L3. The codec was never the problem — separate optimization from plumbing early.
The codec hit **KL 0.032** (t4) — capacity proven 35× over the t2 floor. A perfect codec was inert on
metal because of L1. **Rule:** when a cloud-trained artifact fails the on-metal gate, first prove the
serve path can be moved by the artifact AT ALL (the {0,trained} sweep) before spending another train cycle.

### L4. KAI-2 codec training mechanics that worked (t2→t5):
  - **Save-best, not save-last.** t3 hit KL 0.307 @ep42 then bounced to 0.576 @ep79 (lr too hot); the
    trainer exported the endpoint ⇒ the gate tested the wrong codec. Track min-KL, save that state.
  - **Cosine-anneal the LR.** Flat lr=3e-3 oscillated out of the basin (1.04@ep45, 0.74@ep78). Cosine
    3e-3→0 settled INTO it: t4 = monotone glide to 0.032. Peak-then-anneal beats flat.
  - **KL is not the gate.** The pivot (salient→ACTION ≤2 steps) + selectivity 2×2 is. A higher KL under
    the *correct* (AltUp-constrained) forward is worth more than a low KL on a bypassed forward.
  - **Telemetry in the trainer:** pre-distillation teacher-selectivity check (abort if teacher isn't
    selective on the scaffold — a template-less prompt lobotomizes instruction-following) + per-epoch
    `mean_KL` + `KL_curve` printed. Flat-from-start = mode collapse; decreasing = learning.

### L5. The fix — Option 2: distill through the SAME AltUp gauntlet the metal runs (the native audio port).
gemma-4 already designates `audio_token_id=258881` as the continuous-modality token: an externally-
supplied 0th-stream embedding at that token, with normal PLE/AltUp gathers. That IS our injection port.
  - **Training (`train_kai2_codec.py`):** feed real `input_ids` with `PLACEHOLDER_ID` (=audio_token_id,
    config-driven) at the k soft positions, and a **forward hook on `embed_tokens`** that overwrites ONLY
    the 0th-stream embedding at those positions with the codec vectors — the mechanical twin of the
    engine seam. PLE/AltUp fire on the placeholder ids exactly as on metal. The codec must now learn a
    vector that **survives the 48-layer prediction crossfire**, not one that bypasses it.
  - **Serving (`test_gemma4_cuda.c` run_kai2_packet_gate):** each soft position is a placeholder token
    (`prefill(ph,1)` with `gemma4_kv_inject` active), so the engine's PLE gather matches training.
  - **Both sides use the same placeholder id** ⇒ the two forwards are bit-faithful; KL-min transfers.
  - Status: t5 fired (Option-2 trainer), engine rebuilt with placeholder harness. Gate PENDING.

### L6. Operational (cloud/shell) — don't re-pay these.
  - **WSL is Ubuntu-20.04: pip has NO `--break-system-packages`** (and doesn't need it). Plain
    `pip install numpy torch --index-url .../cpu` works. Don't reach for the flag.
  - **PowerShell→WSL quoting eats nested quotes and `$`.** Write Python/bash to a FILE via a `<<'EOF'`
    heredoc (single-quoted delimiter = no expansion), run by path. Never inline complex `python3 -c "..."`.
  - **Detached cloud launch = `Start-Process wsl -ArgumentList '-e','bash','/home/.../go.sh'`** (direct
    arg, survives the ~40s MCP foreground cap). Receipts go to HF, never the warm-VM waiter tail. (Full
    recipe: `_xbar/p2b/colab.md`.)
  - **Long local gate/build runs exceed the 40s cap** → `Start-Process cmd /c '... > log 2>&1'` detached,
    tail the log. Pin GPU clocks (`--lock-gpu-clocks=1680`); the 2060 can't lock mem clock.

---

## 2026-06-16 — CORRECTION (the above L1/L5 were against the WRONG model)

Everything in the "AltUp gauntlet / Option 2" entry above was diagnosed against **gemma3n**, which was
the wrong model. The real `google/gemma-4-12B` config (`/mnt/d/Files/Models/Gemma4/gemma-4-12b-bucket/
config.json`) says: `architectures=['Gemma4UnifiedForConditionalGeneration']`, `model_type=gemma4_unified`,
**`hidden_size_per_layer_input = 0`** ⇒ **NO per-layer embeddings, NO AltUp.** Single residual stream;
K/V computed straight off `hidden_states`. (It does have MoE blocks + SWA + K==V + softcap.)

- That is why `SP_KAI2_INJ_NOPLE` did nothing: there is no PLE in gemma4 (engine `if(PL)` block is dead,
  PL=0). The "AltUp dilutes the inject" story is FALSE for this model.
- Native audio (from the real `modular_gemma4_unified.py`): `inputs_embeds.masked_scatter(audio_mask,
  audio_features)` at `audio_token_id=258881` positions — post-embed, pre-decoder, **raw/unscaled**
  (the LM is called with `inputs_embeds=`, so `embed_scale=sqrt(hidden)` is bypassed; text rows scaled,
  audio rows raw). The engine seam (embed×scale then overwrite `dx` with raw packet) and the t5 training
  hook (overwrite placeholder rows with raw codec) BOTH match this. So scale + arch are consistent.

**THE ACTUAL ROOT CAUSE (verified, not theory):** there are TWO inject seams in `cuda_forward.cu` and
I used the unproven one.
  - **PROVEN:** `SP_XBAR_EMB` (lines ~2645-2680) in the ONE-SHOT `gemma4_decode_cuda` loop — embed `dx`,
    `cudaMemcpy(dx, payload_row)` before the layer stack. This is the P2.a / X-R1 seam that scored 15/15
    incorporation. Residual injection at this point DOES steer the 12B.
  - **INERT:** `gemma4_kv_inject` (line ~3615) feeding the seam at `g4_kv_step` L3355-3357 in the
    PERSISTENT-KV decode path. The KAI-2 gate uses this path and it is content/scale-invariant
    (INJSCALE 0==1==62==1000, placeholder or junk) — the override never reaches the decision.
  - The gap between these two paths is the OPEN pending task **#222** ("reconcile gemma4_kv_decode
    first-token boundary vs one-shot gemma4_decode_cuda"). The KAI-2 packet should run through the
    PROVEN `SP_XBAR_EMB` one-shot seam (or #222 must be closed so the kv-path seam matches it) — NOT a
    fresh seam. The codec is fine (t5 KL 0.042 clean); the serve path is the wrong/unreconciled seam.

**Process failure (the expensive one):** the injection mechanism was already PROVEN and documented
(RFC-XBAR P1/P2.a, X-R1). I re-derived it, built a new seam, and chased the wrong model — instead of
routing the packet through the existing proven `SP_XBAR_EMB` path. Read the RFC for what's already
solved before building; "is there already a proven primitive for this?" must be the first question.

## 2026-06-16 — KAI-2 RESOLVED: Phase-1 delivery GREEN; Phase-2 codec = off-manifold degeneracy

The whole KAI-2 arc resolved cleanly once the right controls were run (in the right order — which I did
NOT do first; see process lesson). Receipts, in sequence:

1. **Phase-1 EMB-delivery control (the floor of truth).** Inject the event's REAL token embeddings
   (`sp_arena_dequant_row(token_embd)` × `sqrt(E)`) through `gemma4_kv_inject`. Result on metal (12B
   OK_Q4B, 2060): **salient→ACTION, idle→NO_OP, 2/2**. The residual-entry latent-interrupt SEAM DELIVERS.
   It was never broken — my "seam bug / AltUp dilution / wrong-model" diagnoses were all wrong (gemma4
   has NO AltUp; `hidden_size_per_layer_input=0`; audio is a `masked_scatter` into inputs_embeds, raw).
2. **Capacity ladder (EMB capped to first k real embeddings).** salient pivot: k=4 NO_OP, k=8 NO_OP,
   **k=16 ACTION**, k=25 ACTION. The model's residual-stream Shannon floor for a ~25-tok event is
   ~16 positions. k=4 was below it ⇒ no codec could ever win at k=4. NECESSARY, not sufficient.
3. **The codec never transfers — at any k, any quant regime.** Four cloud cycles, all PACKET→NO_OP while
   EMB passes: t4 (bypass k4 KL0.042), t5 (Option-2 hook k4), t6 (--fakeq OK_Q4B weight-quant k4 KL0.156),
   t7 (--fakeq k16 KL0.192). Quant-aware did NOT help; capacity (k16) did NOT help.
4. **THE RECEIPT — offline cosine diagnostic (`_xbar/p2b/_cos_diag.py`).** Each of the t7 k=16 codec
   vectors, max cosine to ANY of 262144 embedding rows: **mean 0.078, max 0.120** vs a **random gaussian
   vector's 0.070**. The codec output is statistically **indistinguishable from noise** w.r.t. the
   embedding manifold (inter-vector cos 0.047 = not collapsed, just 16 distinct noise dirs).

**VERDICT:** the single `nn.Linear`, distilling forward-KL-at-decision over only **8 events**, found a
DEGENERATE off-manifold shortcut — a per-event noise direction that nudges the 8 training-forward decision
logits enough to minimize KL, with zero grounding in the model's semantic geometry. The metal forward
operates strictly on the learned manifold, so those noise vectors are sheared to nothing. Low training KL
was overfitting, not learning. This is the precise mechanism behind P2.b's known "sub-usable" (recognition
top-1 0.462) compression result.

**Why the failure hid for 4 cycles:** KL-at-decision over a tiny corpus is satisfiable off-manifold. The
gate tested the train events (memorized), not held-out. ALWAYS gate generalization (held-out events), and
ALWAYS run the on-manifold control (real embeddings) + the offline manifold-distance check BEFORE blaming
quantization/plumbing/capacity. The cosine diagnostic that solved it costs zero GPU and should have been
run after t5.

**FIX (next pass, NOT more quant-matching):** (a) manifold-anchor loss — per codec vector, min cosine
distance to the event's real token embeddings, blended `L = L_KL + λ·L_anchor` (high λ early to pull
on-manifold first); (b) corpus 8 → ~512 events (template grammar) with an 80/20 split; the gate becomes
pivot-on-HELD-OUT. Engine/harness are verified assets — do NOT touch them; the work is entirely in the
distillation objective + corpus.

## Standing meta-lesson
The recurring failure mode (operator has flagged it 20+ times across the project): **re-deriving a
solved thing instead of reading the code/commits/memory/roadmap.** The math is proven; the methods are
banked. Default to READ → then act. The roadmaps and RFCs are ground truth for *intent*; the tree +
`git log` are ground truth for *state*. Memory primes; neither replaces reading.
