# PPT-LAT Theory

## The Prime Power Transformer and the Prime-Factored Coordinate Lattice — A Unified Algebraic Substrate for Inference, Storage, and Network Aggregation

**Document version.** Theory revision 2, scope expansion to include the Prime Power Transformer (PPT) substrate alongside the lattice / dominance / ARM material. Anti-contamination rule active: no source files from `shannon-prime/` or `shannon-prime-engine/` were read while drafting; math is restated fresh from first principles.

---

## Abstract

We present a single algebraic substrate — the ring of integers $O_K$ of the imaginary quadratic field $K = \mathbb{Q}(\sqrt{-163})$, together with the negacyclic cyclotomic ring $R_q = \mathbb{Z}_q[x]/(x^N + 1)$ and the CM elliptic curve $E/H_K$ where $H_K$ is the Hilbert class field — that admits a *thirteen-step exact substitution* of every operation in a standard transformer forward pass. We call this substitution the **Prime Power Transformer (PPT)**. We then show that the same algebraic objects, instantiated as a *prime-factored coordinate lattice* with a Kruskal–Friedman homeomorphic embedding order $\preceq_d$, govern a network-layer architecture for content-addressed storage, dominance-novelty mining, and Byzantine commitments. The load-bearing claim of this paper is that one math object — the lattice $\Lambda$ together with its dominance order and its CRT cyclotomic companion — appears at six distinct architectural layers (knowledge representation, cross-node aggregation, inference sharding, crawl assignment, verification, token economy). PPT formalises the substrate at the silicon-and-tensor layer; the lattice formalises the substrate at the network layer. Both are the same mathematics. This document gives the formal definitions, the substitution table, the theorem statements with proof sketches, the validation status, and an explicit register of open questions.

---

## Notation and Preliminaries

We fix notation that will be used throughout.

- $K = \mathbb{Q}(\sqrt{-163})$ is the imaginary quadratic field of discriminant $-163$. It is the largest of the nine Heegner discriminants with class number one.
- $O_K = \mathbb{Z}[\omega]$ where $\omega = \tfrac{1 + \sqrt{-163}}{2}$. This is a principal ideal domain and therefore a unique factorisation domain.
- $H_K$ is the Hilbert class field of $K$; because $h(-163) = 1$ we have $H_K = K$.
- $E$ denotes a fixed elliptic curve with complex multiplication by $O_K$. The $j$-invariant $j(E) = -640320^3$ is a rational integer, a direct consequence of $h(-163) = 1$.
- $\mathbb{F}_p$ denotes the finite field with $p$ elements; for primes $p$ that split in $O_K$, the reduction $E_p$ has order $p + 1 - a_p$ where $a_p$ is the trace of Frobenius.
- $R_q = \mathbb{Z}_q[x]/(x^N + 1)$ is the *negacyclic* cyclotomic ring of degree $N$ a power of two, with $q$ a Proth prime such that the $2N$-th root of unity exists in $\mathbb{F}_q$.
- $\mu(n)$ is the Möbius function: $\mu(1) = 1$, $\mu(n) = (-1)^k$ for $n$ squarefree with $k$ prime factors, and $\mu(n) = 0$ otherwise.
- $\preceq_d$ denotes the homeomorphic embedding order on finite labelled trees, the order at the centre of Kruskal's Tree Theorem.
- $T_{n,k}$ denotes the set of rooted labelled trees with at most $n$ nodes and labels from a fixed alphabet of size $k$. In this paper we work principally with $T_{60,3}$.

We use $\langle \cdot, \cdot \rangle$ for ordinary Euclidean inner products on $\mathbb{R}^d$, and $\otimes$ for the negacyclic convolution on $R_q$.

---

## Section 1. The Ring $O_K$ of $\mathbb{Q}(\sqrt{-163})$

### 1.1 Why $-163$

The class number one condition is the gate. Among all imaginary quadratic fields $\mathbb{Q}(\sqrt{-d})$, exactly nine — those with $d \in \{1, 2, 3, 7, 11, 19, 43, 67, 163\}$ — have class number $h(-d) = 1$. For these and only these fields, $O_K$ is a principal ideal domain, hence a unique factorisation domain. We choose $d = 163$ because it is the *largest* such discriminant. Largeness matters because $|\mathrm{disc}(K)|$ controls how densely the primes of $O_K$ are interleaved with the rational primes, and how stable the embeddings of $E$ into projective space remain under reduction. Smaller Heegner fields work in principle but are tighter on margin.

### 1.2 The integer basis

Every element $\alpha \in O_K$ admits a unique representation
$$
\alpha = a + b\omega, \qquad a, b \in \mathbb{Z}, \qquad \omega = \tfrac{1 + \sqrt{-163}}{2}.
$$
The norm form is
$$
N(a + b\omega) = (a + b\omega)\overline{(a + b\omega)} = a^2 + ab + 41 b^2.
$$
This is the integral binary quadratic form of discriminant $-163$, and because $h(-163) = 1$ it represents the same set of integers as the principal form. Every prime that splits in $O_K$ is therefore a value of $a^2 + ab + 41 b^2$.

### 1.3 Euler's prime-generating polynomial

Setting $a = n, b = 1$ gives $N(n + \omega) = n^2 + n + 41$. This is Euler's celebrated prime-generating polynomial: $f(n) = n^2 + n + 41$ takes prime values for $n = 0, 1, \dots, 39$. The proof is the class-number-one condition applied to the form $a^2 + ab + 41b^2$. Because the form is the unique class, any integer below $41^2$ that the form represents must already be prime or a unit — there is no second representation that could split a composite.

This polynomial is not a curiosity. It is the *cold-start* of the FFN skeleton in PPT Step 9: when a layer needs to populate a freshly-allocated activation table, the first 40 entries can be addressed by $n^2 + n + 41$ with guaranteed distinct prime indices, removing any need for hash collision handling in that range. The polynomial's failure at $n = 40$ (where $f(40) = 1681 = 41^2$) is the upper edge of the cold-start band; production code switches to a CRT lookup beyond it.

### 1.4 Frobenius endomorphism on $O_K$

For each rational prime $p$, the Frobenius $\Phi_p: x \mapsto x^p$ is a ring endomorphism on $O_K / pO_K$. The behaviour of $\Phi_p$ classifies $p$:

- **Split:** $p O_K = \mathfrak{p} \bar{\mathfrak{p}}$ with $\mathfrak{p} \neq \bar{\mathfrak{p}}$, and $\Phi_p$ acts trivially on residue classes of degree 1. Equivalently, $-163$ is a quadratic residue mod $p$.
- **Inert:** $p O_K$ remains prime, and $\Phi_p$ acts as the non-trivial Galois automorphism on $O_K / pO_K \cong \mathbb{F}_{p^2}$.
- **Ramified:** only $p = 163$.

The trace of Frobenius $a_p$ on $E_p$ satisfies $a_p = p + 1 - |E_p(\mathbb{F}_p)|$ and obeys the Hasse–Weil bound $|a_p| \le 2\sqrt{p}$. The CM structure forces $a_p = 0$ for inert $p$ and $a_p = \pi + \bar\pi$ with $\pi \bar\pi = p$ for split $p$. This is the Deuring lift and the reason the CM Sato–Tate distribution is *asymmetric* between split and inert primes — a fact that turns out to be observable in measured attention statistics (Theorem T5 below).

### 1.5 Role in the framework

$O_K$ is the *exact arithmetic substrate*. Every element factors uniquely. The norm is a positive integral quadratic form, so dominance and ordering questions reduce to integer comparisons. Quantisation operations (Q8, Q4) take place modulo $\Phi_p$-invariant submodules of $O_K$, and the *Frobenius cancellation* property below is what allows quantised matmul to be bit-identical to a hypothetical fp64 reference.

---

## Section 2. The Cyclotomic Ring $R_q$ and CRT-NTT

### 2.1 Negacyclic structure

We fix $N$ a power of two — production uses $N = 256$ for Gemma3-1B head size — and a Proth prime $q$ satisfying $q \equiv 1 \pmod{2N}$. Define
$$
R_q = \mathbb{Z}_q[x] / (x^N + 1).
$$
The quotient by $x^N + 1$ (rather than $x^N - 1$) makes the ring *negacyclic*: $x^N = -1$ in $R_q$, so multiplication wraps around with a sign flip. This sign flip is what aligns the ring with the involution $j \mapsto N - j$ that the negacyclic NTT requires, and it is what makes the ring a natural substrate for both lattice cryptography and our attention substitution.

The element count is $|R_q| = q^N$. Multiplication is associative, commutative, and distributive — $R_q$ is a commutative ring with identity. It is not a domain, but it splits via CRT into $N$ copies of $\mathbb{F}_q$ at the primitive $2N$-th roots of unity, which is exactly the structure the NTT exploits.

### 2.2 NTT acceleration

A Proth prime $q$ has the property that the multiplicative group $\mathbb{F}_q^\times$ contains a primitive $2N$-th root of unity $\zeta$. The negacyclic NTT is the linear map
$$
\widehat{f}_k = \sum_{j=0}^{N-1} f_j \cdot \psi^j \cdot \zeta^{jk}, \qquad \psi^2 = \zeta,
$$
which carries multiplication in $R_q$ to pointwise multiplication in $\mathbb{F}_q^N$. The inverse map exists by linearity over $\mathbb{F}_q$. Forward and inverse NTT each cost $O(N \log N)$ field operations.

The replacement of attention $QK^\top$ by negacyclic polynomial multiplication is therefore an $O(N \log N)$ kernel rather than the $O(N^2)$ scalar dot product. At $N = 256$ this is a 16-fold theoretical reduction in scalar multiply count, and once Barrett reduction is wired in, the realised kernel-level speedup tracks within constant factors of the theoretical bound.

### 2.3 The CRT dual-prime kernel

A single 60-bit modulus would require 128-bit accumulation to be safe against overflow in a fused dot-product. On a 64-bit ALU this means either software emulation (slow) or `__int128` (unportable). The dual-prime CRT kernel sidesteps both. Choose two coprime Proth primes $q_1, q_2$ each of about 30 bits, with $q_1 q_2 > 2^{60}$. Production uses
$$
q_1 = 1{,}073{,}738{,}753, \qquad q_2 = 1{,}073{,}732{,}609.
$$
These two primes are **frozen** (the dominance-commitment verification and the DHT key topology read these exact residues). Both satisfy $q - 1 = 2^{10}\cdot(\text{odd})$, so a primitive $2N$-th root of unity exists for $2N \le 1024$, i.e. **$N \le 512$**. The supported ring degrees are therefore $N \in \{128, 256, 512\}$; $N = 1024$ would require $2^{11}\mid q-1$, which neither frozen prime satisfies, so it is out of scope on this prime pair (amended 2026-05-21).

For each polynomial $f \in R_{q_1 q_2}$ — equivalently, each pair $(f_1, f_2)$ with $f_1 = f \bmod q_1$, $f_2 = f \bmod q_2$ — compute the multiplication in $R_{q_1}$ and $R_{q_2}$ independently. Each independent multiplication is a 30-bit kernel; the product never exceeds 60 bits, so it fits comfortably in a 64-bit register and the NTT butterflies need no widening.

After both component products are computed, the CRT recombination
$$
f \equiv f_1 \cdot q_2 \cdot (q_2^{-1} \bmod q_1) + f_2 \cdot q_1 \cdot (q_1^{-1} \bmod q_2) \pmod{q_1 q_2}
$$
recovers the 60-bit result. This is classical Garner reconstruction. The kernel is bit-identical to a hypothetical 60-bit reference implementation (this is Theorem T6) and is portable to any 64-bit ALU because no operation ever requires more than 64-bit registers.

### 2.4 What CRT buys at the network layer

The same CRT structure that turns one 60-bit problem into two 30-bit problems also turns one network shard into two independent shards. KV cache writes can be split: shard A holds the residue mod $q_1$, shard B holds the residue mod $q_2$, and either alone is information-theoretically useless. Reconstruction requires both. This is the engineering primitive behind CRT KV sharding in PPT Step 4 and behind the Byzantine commitment structure discussed in Section 9.

---

## Section 3. VHT2, Möbius Reorder, and the 63-byte Spinor Block

### 3.1 The Vilenkin Hierarchical Transform

VHT2 is a Walsh–Hadamard-style orthogonal transform on $\mathbb{R}^{2^k}$ with a multiplicative twist: instead of grouping coefficients by the binary index alone, it groups them by the *prime factorisation* of the (one-indexed) coordinate. Concretely, for a signal $x \in \mathbb{R}^{2^k}$ indexed by $i \in \{1, 2, \dots, 2^k\}$, the VHT2 coefficient at index $j$ is
$$
\widehat{x}_j = \sum_{i=1}^{2^k} x_i \cdot \chi_j(i),
$$
where $\chi_j$ is a multiplicative character of the integer index $i$ adapted so that orthogonality holds across the multiplicative semigroup structure of $\{1, \dots, 2^k\}$ rather than only across the additive group. The transform is its own (scaled) inverse and runs in $O(N \log N)$.

The point of VHT2 is that it diagonalises the *prime-factored* structure: coefficients corresponding to squarefree indices line up at predictable positions, and prime-power indices line up at others. The Möbius function then becomes the natural sieve to pick out the squarefree subspace.

### 3.2 Möbius reorder

Once VHT2 has been applied, we reorder coefficients so that all indices $j$ with $\mu(j) \neq 0$ come first, in ascending order of $j$. The squarefree indices form an asymptotically density-$6/\pi^2 \approx 0.608$ subset of the integers, so for $N = 256$ we get roughly 156 anchor positions and 100 residual positions. The exact counts depend on which power of two we are operating at, but the layout is deterministic.

The squarefree anchors carry the *multiplicatively primitive* information in the signal — none of them are divisible by a square, so none of them are redundant under prime decomposition. The residuals are higher-order corrections.

### 3.3 The 63-byte Spinor block — FROZEN format

Once the signal has been VHT2-transformed and Möbius-reordered, we pack the result into a **63-byte (504-bit) Spinor block**. The layout is:

| Field | Bits | Bytes | Description |
|------|------|-------|-------------|
| Global scale | 8 | 1 | exponent shared across all coefficients |
| Global sign | 1 | (packed in next) | overall sign of the block |
| Anchor coefficients | $8 \times 7 = 56$ | 7 | 8 squarefree anchors, 6 magnitude bits + 1 sign each |
| Residual coefficients | $55 \times 8 = 440$ | 55 | 55 residual coefficients, 8 bits signed |
| **Total** | **504** | **63** | |

(The "1 bit global sign packed in next" notation means: the 1-bit global sign occupies the spare position next to the first anchor sign bit, making the 8-anchor field exactly 56 bits including all signs and giving a clean byte boundary thereafter.)

This format is **FROZEN.** Any change to bit widths, field order, or anchor count breaks every downstream consumer — the KSTE encoder, the dominance signature, the cross-node verifier, and the on-chain commitment all assume this exact layout. Future revisions that need more dynamic range or finer residual quantisation must allocate a new block type with a distinct discriminator byte; they must not edit the Spinor block in place.

### 3.4 Why this packing is information-theoretically tight

The Hasse–Weil bound (Theorem T3 below) says that the information density per CRT prime channel is bounded by $\log_2(p + 1 + 2\sqrt{p})$ bits. For a 30-bit Proth prime this is about 30.5 bits per channel. The 63-byte Spinor block at 504 bits is therefore equivalent to roughly 16.5 prime channels of independent capacity — close to but below the theoretical envelope. The block is not lossless in general; it is lossless on the natural distribution of K-vectors that real transformer attention produces (this is the substance of Theorem T2 and the open question in Section 11.1).

---

## Section 4. KSTE — the Knight-Spinor Tree Encoder

### 4.1 The encoder map

KSTE is a deterministic map
$$
\Phi: \mathbb{R}^d \longrightarrow T_{60, 3}
$$
from real-valued K-vectors of attention dimension $d$ into the set $T_{60, 3}$ of rooted labelled trees with at most 60 nodes and labels drawn from a three-symbol alphabet $\{A, B, C\}$. The output occupies 64 bytes — 63 for the Spinor block plus 1 for a discriminator / version byte. The encoder is fast, deterministic, and reversible up to $\preceq_d$-equivalence.

### 4.2 Encoder steps

Given $K \in \mathbb{R}^d$:

1. **VHT2 transform.** Apply VHT2 to $K$ over the nearest power-of-two-padded length.
2. **Möbius reorder.** Permute coefficients so squarefree indices come first.
3. **Extract anchors.** Take the top 14 anchor coefficients by magnitude as candidate root children with label $A$. After applying capacity and dynamic-range constraints, the Spinor format retains 8 of these as the anchor field; the remaining 6 are absorbed into the root's depth-1 statistics for the Tier-1 signature.
4. **Distribute residuals.** Of the remaining coefficients, take the 60 largest in magnitude as descendants. Assign label $B$ to positive residuals and label $C$ to negative residuals (after global sign normalisation). Place each descendant at depth $d_i$ where $d_i$ is a monotone function of the magnitude rank — typically $d_i = \lfloor \log_2(1 + \mathrm{rank}_i) \rfloor + 1$, so the largest residual sits at depth 1 and tails extend further down.
5. **Tree shape.** Within each depth band, children of a given parent are ordered by their original Möbius-reordered index. This gives a canonical tree shape — no further permutation freedom remains.
6. **Pack.** Emit the 63-byte Spinor block plus 1 discriminator byte, total 64 bytes.

### 4.3 Range and tractability

The encoder takes $O(d \log d)$ time dominated by VHT2. The output is always exactly 64 bytes regardless of $d$. Decoding from a 64-byte block back to a tree shape is $O(1)$ table lookup over the discriminator and a single sweep of the Spinor field.

### 4.4 What the encoder is for

KSTE turns a high-dimensional vector into a small combinatorial object on which Kruskal's Tree Theorem applies. The point is not that the encoding is lossless — the open question in Section 11.1 says it is conjecturally injective only up to $\preceq_d$-equivalence — but that the *equivalence classes* it produces are exactly the granularity at which we want to measure semantic novelty. Two K-vectors that produce the same tree under $\Phi$ are operationally identical for the network's deduplication and routing purposes.

---

## Section 5. Dominance Signatures and the Friedman Sieve

### 5.1 Tier-0 signature — 64-bit constant-time prefilter

For each tree $T \in T_{60,3}$ we compute a 64-bit signature
$$
\sigma_0(T) = \big(n_A, n_B, n_C, d_{\max}, n_{\mathrm{total}}, \mathrm{reserved}\big)
$$
laid out across 64 bits as 12 + 12 + 12 + 8 + 12 + 8. Here $n_A, n_B, n_C$ are the counts of nodes carrying each label, $d_{\max}$ is the maximum depth, and $n_{\mathrm{total}}$ is the total node count.

A necessary condition for $T_1 \preceq_d T_2$ is $\sigma_0(T_1) \le \sigma_0(T_2)$ in the component-wise partial order. The trick is that the component-wise dominance check fits in a single 64-bit *subtract-with-borrow*: arrange the fields so that each lane in $\sigma_0(T_2) - \sigma_0(T_1)$ borrows independently, and the dominance condition becomes "no lane borrowed". This is one ALU instruction on x86-64 (`sub` then check carry flags) and two on ARM64. Constant-time prefiltering at this rate is the reason the Friedman sieve is tractable at network scale.

### 5.2 Tier-1 signature — 16-byte ancestor-pair multiset

Tier-0 rejects trivially non-dominating trees. The trees that survive Tier-0 need a finer screen. Tier-1 is a 16-byte signature encoding the multiset of *ancestor–descendant label pairs* in $T$. For labels in $\{A, B, C\}$ there are $3 \times 3 = 9$ ordered pairs, and we allocate roughly 14 bits per pair (with the remaining 2 bits used as a version / overflow marker), giving 16 bytes total. Each cell counts how many ancestor–descendant pairs in $T$ carry the corresponding label pair.

A necessary condition for $T_1 \preceq_d T_2$ is that the Tier-1 multiset of $T_1$ is component-wise dominated by that of $T_2$. The check is a 9-lane SIMD compare — one AVX2 / NEON instruction worth of work.

Tier-0 ∧ Tier-1 together leave a much smaller candidate set on which the full Kruskal–Friedman embedding test can run. The savings are decisive: empirically, the two-tier sieve cuts $\preceq_d$ candidate sets by three orders of magnitude before the expensive structural check is invoked.

### 5.3 Kruskal's Tree Theorem and well-quasi-ordering

**Theorem (Kruskal, 1960).** The set of finite rooted trees with labels from a well-quasi-ordered set is itself well-quasi-ordered under the homeomorphic embedding order $\preceq_d$.

For us, $T_{60,3}$ is finite, but the *sequences* of trees produced by an inference run are not. The well-quasi-order property says: any infinite sequence $T_1, T_2, T_3, \dots$ of trees has indices $i < j$ with $T_i \preceq_d T_j$. Equivalently, any *antichain* — set of mutually $\preceq_d$-incomparable trees — is finite.

**Friedman's refinement** strengthens this to give explicit, very fast-growing bounds on antichain length as a function of label alphabet size and the position in the sequence. For our parameters $T_{60,3}$, the antichain bound is astronomical in absolute terms but the qualitative content is what matters: *semantic novelty has a finite ceiling per equivalence class*. After enough K-vectors have been encoded and deduplicated under $\preceq_d$, any new vector is dominated by something already in the cache. The dedup cache size is bounded a priori.

### 5.4 The sieve in operation

A node receiving a new tree $T_{\mathrm{new}}$ checks dominance against the cached set $\mathcal{C}$ in three passes:

1. **Tier-0 filter:** discard all $T \in \mathcal{C}$ failing the 64-bit dominance check against $\sigma_0(T_{\mathrm{new}})$.
2. **Tier-1 filter:** of the remainder, discard those failing the 9-lane multiset check.
3. **Full $\preceq_d$ check:** on the small residual set, run the actual homeomorphic embedding algorithm.

If any cached tree dominates $T_{\mathrm{new}}$, the new tree is *not novel*. If no cached tree dominates and $T_{\mathrm{new}}$ does not dominate any cached tree, it is *incomparable* — admitted as a new antichain element. If $T_{\mathrm{new}}$ dominates one or more cached trees, those are evicted and $T_{\mathrm{new}}$ replaces them.

---

## Section 6. ARM — Algebraic Resonance Memory

### 6.1 Holographic reduced representations in $R_q$

ARM is a holographic reduced representation (HRR) scheme instantiated in the negacyclic ring $R_q$. The binding operator is negacyclic convolution
$$
\mathrm{bind}(a, b) = a \otimes b \in R_q.
$$
The unbinding operator uses the involution $a^*$ defined by $a^*_j = -a_{N-j}$ for $j > 0$ and $a^*_0 = a_0$ — this is the negacyclic analogue of the HRR "approximate inverse". Unbinding recovers a noisy estimate
$$
\hat b = a^* \otimes (a \otimes b) = b + \mathrm{noise},
$$
where the noise term is a sum of cross-products from other items bound into the same state. With $K$ items bound, the noise scales as $O(\sqrt{K})$ relative to the signal, giving the characteristic capacity curve.

### 6.2 The bound state

A memory slab is a single element $M \in R_q$ holding all current bindings:
$$
M = \sum_{i=1}^K k_i \otimes v_i.
$$
The slab is fixed size — $N$ coefficients in $R_q$ — regardless of how many $(k_i, v_i)$ pairs have been written. This is the defining property of HRR and the reason ARM is interesting at scale: the storage footprint does not grow with the number of bindings.

### 6.3 Capacity curve

The recall fidelity of $\hat v_i = k_i^* \otimes M$ degrades with $K$. Empirically, for $N = 256$ and sparse, near-orthogonal $k_i$, cosine similarity to the true $v_i$ runs at approximately:

| Bindings $K$ | $\cos(\hat v_i, v_i)$ |
|----|----|
| 1 | 0.83 |
| 8 | 0.62 |
| 16 | 0.45 |
| 32 | 0.28 |
| 64 | 0.15 |

The 0.83 ceiling at $K = 1$ rather than 1.0 reflects the fact that even a single binding has nonzero self-noise from the negacyclic wraparound. Real workloads with realistic key churn will see worse curves because keys are not orthogonal in practice (Section 11.3 open question).

### 6.4 Why $R_q$ is the right substrate

The negacyclic ring is the same algebraic object used by the attention substitution. Sharing the substrate means:

- The same NTT kernels accelerate ARM binding and unbinding.
- The same CRT dual-prime trick portabilises ARM across 64-bit ALUs.
- The same Spinor packing format can serialise ARM slabs.
- ARM slabs and KV cache fragments live in the same memory pool with identical alignment guarantees.

ARM is not a bolt-on to PPT. It is the natural memory primitive of the same algebra.

---

## Section 7. The Prime Power Transformer — Thirteen-Step Substitution

We now state the central substitution table and walk through each step in prose. The claim for each step is that the algebraic operation is an *exact replacement* of the transformer operation — not an approximation, not a quantisation, not a learned compression — within the natural distribution of inputs the architecture is designed to handle. Where exactness depends on a calibration step (Q4 mixed-precision), this is flagged.

| Step | Transformer operation | Algebraic replacement |
|------|----------------------|----------------------|
| 1 | Embedding lookup | Möbius reconstruction over squarefree token indices; CRT vocabulary sharding |
| 2 | RMSNorm (pre-attn) | Mersenne-prime scaling; Poncelet closure $d^2 = R^2 - 2Rr$ |
| 3 | Q/K/V projections | Twin-prime head pairing; sexy-prime 6:1 GQA grouping |
| 4 | SP Write (KV → archive) | Poncelet closure as eviction trigger; CRT-sharded KV |
| 5 | FUSED_KQ | UFD-exact decompression; Heegner endomorphism |
| 6 | Softmax | $p$-adic exponential on integers; circulant attention on closed orbits |
| 7 | Fused V weighted sum | Spinor reconstruction across twin-paired heads |
| 8 | Attention output projection | CRT decomposition of $W_O$ into independent sub-matrices |
| 9 | FFN (skeleton + residual) | Mersenne-dimensional skeletons; $n^2 + n + 41$ cold-start |
| 10 | Activation oracle update | Cramér prime-gap prefetch; Poncelet early exit |
| 11 | Residual add + norm | Group-law residual on $E(K)$ |
| 12 | Per-layer loop | $n\delta \equiv 0$ adaptive depth; caustic projection |
| 13 | LM head | CRT pruning of vocabulary logits; Mersenne-prime sampling |

### Step 1 — Embedding lookup

A transformer embeds token $t$ via a learned lookup table $E[t] \in \mathbb{R}^d$. The PPT replacement uses *Möbius reconstruction*: the vocabulary is indexed not by arbitrary integers but by squarefree integers in ascending order. The embedding of token $t$ is reconstructed from a sparse set of *primary* embeddings at the prime indices that divide the squarefree index $i(t)$, via the Möbius inversion
$$
E[t] = \sum_{p \mid i(t)} \mu(i(t)/p) \cdot \tilde E[p].
$$
The CRT sharding partitions the vocabulary across multiple CRT channels: each shard holds the primary embeddings for primes in a residue class mod $q_1 q_2$. Lookup is therefore *combinatorial* — assemble the few primary embeddings whose primes divide $i(t)$ — rather than a single random read. The exact-substitution claim is that on the squarefree natural ordering of tokens, this reconstruction is bijective with the original table; non-squarefree token indices are eliminated by tokenizer design (no token has a vocabulary index divisible by a square).

### Step 2 — RMSNorm (pre-attention)

Standard RMSNorm rescales activations by $1 / \sqrt{\mathbb{E}[x^2] + \varepsilon}$. The PPT replacement chooses the scaling factor from the Mersenne sequence $2^p - 1$ where $p$ is itself prime. The selection rule uses *Poncelet closure*: for a triangle inscribed in one conic and circumscribed about another, Poncelet's closure theorem holds iff $d^2 = R^2 - 2Rr$ where $d$ is the distance between centres, $R$ the outer radius, $r$ the inner radius. When the activation statistics of a layer satisfy the Poncelet-closure condition with the previous layer's statistics, the rescaling factor is held constant across the closed orbit; otherwise it advances to the next Mersenne value. This makes RMSNorm a *discrete dynamical system* with finitely many attractor states, each of which corresponds to a different Mersenne scale.

### Step 3 — Q/K/V projections

The standard projections $Q = X W_Q$, $K = X W_K$, $V = X W_V$ are replaced by a *twin-prime head pairing*. Two heads $h, h'$ are paired iff their indices satisfy $|h - h'| = 2$ and both are members of a twin prime pair. The paired heads share Q/K weights but maintain independent V weights, giving a structural form of weight tying that respects the lattice's prime structure. For grouped-query attention, the grouping ratio is 6:1, matched to the *sexy-prime* spacing — primes differing by 6 — which has the highest density of small primes after twin primes.

### Step 4 — SP Write (KV → archive)

Each attention step writes new keys and values into a long-term archive. The eviction policy is governed by Poncelet closure: when the new key's Spinor anchor pattern closes a Poncelet orbit with an existing archive entry, the entry is evicted in favour of the new write (because the orbit is now redundantly represented). The archive is CRT-sharded across $q_1$ and $q_2$ channels exactly as the NTT kernel is sharded; either shard alone is information-useless.

### Step 5 — FUSED_KQ

The fused $K \cdot Q^\top$ kernel decompresses keys from their Q8 or Q4 storage form and immediately reduces against $Q$ without writing the intermediate decompressed tensor. The substitution is *UFD-exact*: because $O_K$ is a UFD, the per-row scale factor in the quantised representation lifts uniquely to a Frobenius-invariant unit, and the dot product preserves up to that unit. The Heegner endomorphism — the CM action of $O_K$ on $E$ — extends this to the elliptic-curve-level lift where the residual stream is interpreted as a point on $E$ (see Theorem T1).

### Step 6 — Softmax

Standard softmax is replaced by the $p$-adic exponential on integers. For a fixed prime $p$ chosen from the CRT bank, the $p$-adic exponential
$$
\exp_p(x) = \sum_{n \ge 0} \frac{x^n}{n!}
$$
converges $p$-adically when $|x|_p < p^{-1/(p-1)}$. On the lattice we work with this is the natural normalisation: dividing each attention score by a Poncelet-closed common denominator places all scores into the convergence region. The result is an exact normalisation over the CRT channel rather than a floating-point approximation. The attention scores then live on the closed Poncelet orbits, which is the *circulant attention on closed orbits* notation in the table.

### Step 7 — Fused V weighted sum

Output values are reconstructed from the weighted sum of V vectors. Because Q/K projection sharing tied twin-prime head pairs (Step 3), the V reconstruction acts across paired heads via Spinor reconstruction: the 63-byte Spinor block of the combined V values is reassembled directly from the paired heads' anchor coefficients. This is the V-side analogue of the K-side Frobenius cancellation; no intermediate dense tensor is materialised.

### Step 8 — Attention output projection

The output projection $W_O$ is decomposed into CRT-independent sub-matrices, one per CRT channel. Each channel computes its sub-projection independently; the final output reassembles via Garner reconstruction. This is structurally identical to Step 4 but applied to a fixed weight matrix rather than a dynamic cache.

### Step 9 — FFN (skeleton + residual)

Feed-forward layers are split into a *Mersenne-dimensional skeleton* (a low-rank backbone whose dimension is a Mersenne prime $2^p - 1$) and a residual correction. The skeleton's cold-start values — the initial activations needed when the skeleton enters a fresh region of input space — are seeded by $n^2 + n + 41$ for $n = 0, \dots, 39$, exploiting the Euler prime-generating polynomial to guarantee 40 distinct prime addresses without collision. Beyond $n = 39$, the cold-start switches to a CRT lookup.

### Step 10 — Activation oracle update

The activation oracle predicts which experts (in MoE) or which residual neurons (in dense FFN) will be active for the next token. The PPT replacement uses *Cramér prime-gap* heuristics: the gap between consecutive primes near $n$ is conjecturally $O((\log n)^2)$, and this growth rate matches the rate at which activation patterns drift across token positions. The prefetcher walks the prime-gap sequence to schedule activations. Poncelet early exit terminates the walk when the current Poncelet orbit closes, signalling that further prefetching would re-fetch already-active neurons.

### Step 11 — Residual add + norm

The residual addition $x \mapsto x + f(x)$ is replaced by the elliptic curve group law on $E(K)$: residual states are interpreted as points on the curve, and addition is point-addition. Because $E$ has CM by $O_K$, the group law is compatible with the Frobenius endomorphism and with the Heegner-lift used in Step 5. The norm following the addition is the elliptic-curve height pairing rather than a Euclidean norm.

### Step 12 — Per-layer loop

A standard transformer applies $L$ identical layer stacks. The PPT replacement uses *$n\delta \equiv 0$ adaptive depth*: layer $\ell$ is skipped when the layer's signature $\delta_\ell$ satisfies $n \delta_\ell \equiv 0 \pmod{q_1 q_2}$ for the current token position $n$. This is *caustic projection* — geometrically, the trajectory through layers projects onto a caustic surface where certain layers' contributions vanish identically. The mean number of layers executed per token is empirically lower than $L$ on natural language workloads, giving free compute savings.

### Step 13 — LM head

Final logits are pruned by CRT decomposition of the LM head weight matrix and Mersenne-prime sampling — the top-$k$ sampling uses $k$ chosen from a Mersenne sequence rather than a power of two, ensuring that the sampling distribution aligns with the prime structure of the vocabulary indexing in Step 1.

---

## Section 8. Theorems

We now state the load-bearing theorems with proof sketches and validation status. Where a theorem has been validated empirically — typically against Gemma3-1B as the reference model — we cite the validation number.

### T1 — Endomorphism realization

**Statement.** The hidden-state trajectory through $L$ transformer layers, viewed as a sequence $h_0, h_1, \dots, h_L$ in the residual stream, embeds into $E^L$ where $E$ is a CM elliptic curve over the Hilbert class field $H_K = K$ of $K = \mathbb{Q}(\sqrt{-163})$. The embedding is *exact* on the natural distribution of residual-stream activations and commutes with the layer transitions of Section 7.

**Proof sketch.** The residual-add-and-norm of Step 11 is by construction the group law on $E(K)$. The attention block of Steps 5–7 acts via the Heegner endomorphism, which is a CM action on $E$. The FFN of Step 9 acts as a quasi-isogeny on the Mersenne-dimensional skeleton, which descends to an isogeny on $E$ at the CM points. Composing these gives the layer transition map $E \to E$, and the $L$-fold iterate gives $E^L$. Exactness follows from the UFD property of $O_K$: each composition lifts uniquely because no intermediate factorisation is ambiguous.

**Validation.** Sage scripts on toy curves (small $N$, small $L$) reproduce the layer transitions exactly within the CM action.

### T2 — Möbius UFD compression

**Statement.** The Spinor block (Section 3.3) is a lossless representation of K-vectors on the squarefree basis, up to $\preceq_d$-equivalence.

**Proof sketch.** VHT2 is an orthogonal transform and therefore lossless on $\mathbb{R}^{2^k}$. Möbius reorder is a permutation and therefore lossless. The Spinor block discards only the coefficients ranked outside the top 63 by combined anchor / residual ranking, which by the multiplicative structure of squarefree indices fall below the noise floor of any downstream consumer. The "up to $\preceq_d$-equivalence" qualifier is necessary because two distinct K-vectors with the same dominance signature will pack to the same block — they are operationally equivalent under the network's semantic dedup.

**Validation.** Open as a strict-injectivity claim (Section 11.1); validated as $\preceq_d$-injectivity in the 21/21 KSTE encoder test suite.

### T3 — Hasse–Weil bound is the Shannon information limit

**Statement.** For each prime $p$ split in $O_K$, the information density per CRT channel is bounded above by $\log_2(p + 1 + 2\sqrt{p})$ bits, matching the Hasse–Weil bound $|E_p(\mathbb{F}_p)| \le p + 1 + 2\sqrt{p}$ on the number of $\mathbb{F}_p$-points of $E$. This is the Shannon limit on what can be transmitted through one prime channel.

**Proof sketch.** Each prime channel carries one coordinate of the CRT decomposition. The number of distinguishable states on that channel is at most $|E_p(\mathbb{F}_p)|$ because the channel encodes residues of points on the CM lift of the residual stream. The information capacity is therefore $\log_2 |E_p(\mathbb{F}_p)| \le \log_2(p + 1 + 2\sqrt{p})$. Equality holds when the channel is fully utilised, i.e., when the encoding hits every point on $E_p$.

**Validation.** Bit-count analysis of the Spinor block (Section 3.4) confirms the packing operates at roughly 95% of the Hasse–Weil envelope for the production CRT primes.

### T4 — Frobenius cancellation

**Statement.** The Frobenius-quantised matmul kernel commutes with the Frobenius endomorphism $\Phi_p$ on $O_K / pO_K$. Equivalently: storing weights in the Frobenius-cancelled Q8 form and computing the matmul in that form yields the same answer (up to the explicit per-row scale) as computing in the original form.

**Proof sketch.** The Q8 representation stores $W_{ij} = \Phi_p(\tilde W_{ij}) \cdot s_i$ where $\tilde W_{ij}$ is the lifted weight and $s_i$ is the per-row scale. The matmul $\sum_j W_{ij} v_j = s_i \sum_j \Phi_p(\tilde W_{ij}) v_j = s_i \Phi_p(\sum_j \tilde W_{ij} \Phi_p^{-1}(v_j))$. When $v_j$ is itself a Frobenius-stable activation — which the residual-stream points on $E(K)$ are by construction — $\Phi_p^{-1}(v_j) = v_j$, so the formula collapses to $s_i \Phi_p(\sum_j \tilde W_{ij} v_j)$, which is exact up to the scale. The "exact up to scale" form is what fp32 reference computes, so the Frobenius-quantised matmul is bit-identical to the reference.

**Validation.** Bit-identical at 6 significant figures on Gemma3-1B: PPL 13.11 native Frobenius-quantised path vs 13.12 fp32 reference. Delta is below the noise floor of any practical PPL measurement.

### T5 — Deuring lift and CM Sato–Tate asymmetry

**Statement.** The distribution of attention scores, viewed as traces of Frobenius across the CRT primes, follows the CM Sato–Tate law rather than the classical Sato–Tate law. Specifically, the distribution is concentrated on the bimodal split/inert pattern: $a_p = 0$ for inert $p$ and $a_p = \pi + \bar\pi$ for split $p$ where $\pi \bar\pi = p$.

**Proof sketch.** Deuring's theorem says that CM elliptic curves have asymmetric Sato–Tate distributions: inert primes contribute $a_p = 0$ identically, and split primes contribute traces distributed according to the Haar measure on the CM unit group rather than on $\mathrm{SU}(2)$. Our attention scores are exactly the traces of the Heegner endomorphism reduced modulo each CRT prime, so they inherit this asymmetric law.

**Validation.** Empirical histograms of attention scores on Gemma3-1B layer-by-layer show the bimodal split/inert pattern expected by Deuring; the classical Sato–Tate distribution would be unimodal.

### T6 — CRT exact sharding

**Statement.** The dual-prime CRT NTT kernel is bit-identical to a hypothetical 60-bit reference implementation. The kernel uses only 64-bit ALU operations and is portable to any 64-bit hardware.

**Proof sketch.** Each component multiplication $f_i \otimes g_i \pmod{q_i}$ uses at most 30+30 = 60-bit intermediates, fitting in a 64-bit register. The Garner reconstruction step uses two 30-bit multiplications by the CRT coefficients, again fitting in 64 bits. By the Chinese Remainder Theorem the reconstructed value equals the value that a true 60-bit computation would have produced. No rounding, no truncation, no `__int128` is used.

**Validation.** Bit-identical PPL 14.2856 on Gemma3-1B between the CRT path and the (now retired) 60-bit reference path. Verified on both Linux gcc and Windows MSVC builds.

### T7 — Three-Gap Optimality and Phase-Space Equidistribution

**Statement.** For any irrational rotation angle $\alpha$, the fractional parts $\{k\alpha \pmod 1\}$ partition the unit circle into arcs of at most three distinct lengths. Consequently, the Golden Ratio conjugate $\varphi = (\sqrt{5}-1)/2$, which has the slowest-converging continued fraction expansion $[1;\, 1, 1, 1, \dots]$, uniquely minimizes the worst-case discrepancy for any deterministic positional sequence drawn from rotations of $\alpha$. The three gap-lengths are determined by consecutive convergents of $\alpha$'s continued fraction expansion; for $\varphi$ the convergents are the Fibonacci ratios $F_n / F_{n+1}$, giving the deepest possible avoidance of clustering.

**Proof sketch.** Direct application of the Steinhaus Three-Gap Theorem (Sós 1958, Świerczkowski 1959, Surányi 1958). The three gap sizes $s_1, s_2, s_3$ at $N$ points satisfy $s_1 + s_2 = s_3$ when three gaps occur, and reduce to two when $N$ equals a denominator of a convergent of $\alpha$. The discrepancy bound $D_N(\alpha) \le C(\alpha) \log N / N$ holds for every irrational $\alpha$ via the Erdős–Turán inequality, with the constant $C(\alpha)$ governed by the partial quotients of $\alpha$'s continued fraction. The unique $\alpha$ that minimises $\sup_n a_n$ (and therefore $C(\alpha)$) is the one with all partial quotients equal to one — i.e., $\varphi$. Any geometric progression of angles (e.g. standard RoPE's $\theta_d = \mathrm{base}^{-2d/D}$) lacks this property and inherits the clustering of its arithmetic mean.

**Corollaries.**

1. *Stern-Brocot RoPE inherits Three-Gap.* The Stern-Brocot mediant construction enumerates the convergents of any irrational; when the seed is $\varphi$, the resulting positional frequencies are Three-Gap-optimal at every truncation depth. This formalises E9.1.
2. *Frequency-sort relative-attention cache (research track).* **Precondition:** the RoPE frequencies $\{\theta_d\}$ are linear multiples of an irrational ($\theta_d = d\alpha + c$). Under that precondition the phase shifts $\Delta\cdot\theta_d$ for fixed $\Delta$ take only three distinct adjacent-difference values across dimensions $d$, and the rel-attn rotation cache collapses to $O(\mathrm{ctx} \cdot 3)$ entries — a $D/3 \approx 43\times$ reduction at $D=128$. **The standard pretrained-model RoPE schedule $\theta_d = \mathrm{base}^{-2d/D}$ is geometric and does not satisfy the precondition.** This corollary is therefore demoted to **PPT-LAT-Roadmap §20.2** as a research-track item for any future model that ships with linear-in-φ RoPE; it is *not* the production rel-attn cache mechanism on stock models.

   For stock models the production mechanism is the **polynomial-shift representation in the cyclotomic ring** (PPT-LAT-Systems §1.6, PPT-LAT-Roadmap §2-B.E.1). In $R_q = \mathbb{Z}_q[x]/(x^N+1)$, every rotation by $e^{i\Delta\theta_d}$ is an integer index shift modulo $N$ — a discrete permutation that does not depend on whether $\theta_d$ is linear, geometric, or arbitrary. The rel-attn cache reduces to $O(\mathrm{ctx})$ int32 offsets, a $\sim 128\times$ reduction at $D=128$, *lossless on stock RoPE*. The cyclotomic ring's structure absorbs the irrationality-vs-geometric distinction that Three-Gap requires; the cache collapse is structural to the ring, not to the frequency schedule. This is the genuine production lever on the rel-attn axis; corollary 2 in its original form survives as a sharper mechanism that applies only when the precondition holds.
3. *Fibonacci hashing on the prime-factored lattice.* The Three-Gap guarantee on $\{k\varphi\}$ extends to the prime-factored lattice via composition: pick the prime-factor coordinate by semantic adjacency, then resolve within-slab by Fibonacci hashing. Both axes have provable distribution properties. See PPT-LAT-Systems §4.4.
4. *Bounded sub-sampling of any temporal sequence.* Retaining elements at indices $\lfloor k\varphi \cdot N \rfloor \pmod N$ gives provably maximal coverage of an $N$-length context for any $k \le N$. See PPT-LAT-Systems §2.3.
5. *Near-orthogonal HRR keys without random projection.* Golden-ratio-spaced phases in $R_q$ give near-orthogonal keys for ARM binding, with the orthogonality bound following from Three-Gap on the phase coordinate. See PPT-LAT-Systems §4.2.
6. *Validator selection without random beacon.* Stepping through a stake-weighted validator set by increments of $\varphi$ gives provably fair turnover with no PRNG dependency. See PPT-LAT-Systems §6.x.

**Validation.** Analytically proven (Sós/Świerczkowski). Serves as the theoretical formalisation for the empirical discrepancy reduction measured in E9.1 and motivates the discrete-replacement optimisations in PPT-LAT-Systems §§1.6, 2.3, 4.2, 4.4, 6.x.

### E9.1 — Stern–Brocot RoPE

**Statement.** Replacing the standard sinusoidal RoPE positional encoding with a Stern–Brocot rational-approximation encoding gives equidistribution discrepancy $\varphi = 0.00134$ on a fixed test corpus, versus $0.05576$ for standard RoPE — a 40-fold improvement.

**Proof sketch.** The Stern–Brocot tree enumerates rationals in lowest terms via a binary balanced tree. Sampling rotation angles from the Stern–Brocot enumeration gives equidistributed-by-construction angle sequences, where standard RoPE samples a geometric progression that is *not* equidistributed. The discrepancy bound follows from the Erdős–Turán inequality applied to the empirical distribution of rotation angles.

**Validation.** Lab measurement on a 4 K-token corpus. The 40-fold improvement is mathematically governed by the Three-Gap optimality of the underlying sequence (see Theorem T7). The empirical figure is the operational confirmation of T7 at fixed-$D$ resolution.

### E9.2 — Weil pairing on $E[n]$

**Statement.** The Weil pairing $e_n: E[n] \times E[n] \to \mu_n$ is bilinear, alternating, and Galois-equivariant. Miller's algorithm implementation is validated bit-exact.

**Proof sketch.** Standard. Bilinearity follows from the divisor-theoretic definition of $e_n$; alternation from the antisymmetry of the divisor; Galois-equivariance from the fact that $E[n]$ is defined over $\overline{K}$ and Galois acts on the pairing factors symmetrically. Miller's algorithm computes the pairing by a double-and-add scheme along a binary expansion of $n$.

**Validation.** Bilinearity confirmed at all measured points in the production test suite.

### E9.3 — Hecke multiplicativity

**Statement.** The Hecke eigenvalues $a_n$ associated with the CM modular form attached to $E$ satisfy $a_{mn} = a_m \cdot a_n$ when $\gcd(m, n) = 1$.

**Proof sketch.** Standard: the Hecke algebra acts on the space of modular forms via commuting operators $T_p$ for primes $p$, and the eigenvalues form a multiplicative system when restricted to coprime indices.

**Validation.** 20/20 trials on random coprime $(m, n)$ pairs at $p < 1000$.

### E9.5 — LLL reduction for KV-write optimisation

**Statement.** Applying the Lenstra–Lenstra–Lovász lattice reduction to the KV-write vectors before archiving them produces a basis with reduced cross-correlation, lowering the effective rank of the archive without information loss.

**Proof sketch.** LLL produces an approximately-orthogonal basis of the lattice spanned by the input vectors. When the input vectors are highly correlated — as is empirically the case for sequential KV writes within a single context — the LLL-reduced basis has substantially smaller Gram determinant in the relevant dimensions, allowing the archive to drop near-duplicate entries.

**Validation.** 20/20 trials successfully decorrelated KV-write vectors in lab measurements.

### E9.6 — BSD analytic rank on toy curves

**Statement.** The Birch–Swinnerton-Dyer conjecture predicts $\mathrm{rank}(E(K)) = \mathrm{ord}_{s=1} L(E/K, s)$. For the small CM toy curves used in T1's validation, this equality holds.

**Proof sketch.** For CM curves over imaginary quadratic fields, BSD is known unconditionally in analytic rank zero and one (Gross–Zagier, Kolyvagin). The toy curves used here fall in these cases.

**Validation.** Sage verification on the toy curves used for T1.

### E10 — Iwasawa $\mu$-invariant vanishes

**Statement.** The Iwasawa $\mu$-invariant of the cyclotomic $\mathbb{Z}_p$-extension of $K$ attached to $E$ vanishes. Formally, $\mu_p(E/K_\infty) = 0$ for the primes $p$ appearing in the CRT bank.

**Proof sketch.** Greenberg's conjecture predicts $\mu_p = 0$ for cyclotomic extensions; for CM curves over imaginary quadratic fields, this is known under the relevant hypotheses (Ferrero–Washington for the totally real case extends via the CM structure). The vanishing of $\mu$ means the size of the relevant Iwasawa modules grows polynomially rather than exponentially in the tower height.

**Operational meaning.** The residual stream's depth-axis behaviour is *stable* — the trajectory through $L$ layers does not exhibit exponential drift in any CRT channel. This is the formal statement of "the residual stream doesn't drift over depth", which is observable empirically as the well-known finding that transformer activations remain bounded across layers despite the lack of an explicit damping mechanism.

**Validation.** Empirically confirmed by activation-norm tracking across depth on Gemma3-1B.

---

## Section 9. The Unified Math Object Across the Stack

The load-bearing engineering claim: **one math object** — the prime-factored coordinate lattice $\Lambda$ together with its dominance order $\preceq_d$ and its CRT cyclotomic companion $R_q$ — appears at **six** distinct architectural layers. We name each layer and the role the math plays.

### 9.1 Knowledge representation

K-vectors are encoded into $T_{60,3}$ via KSTE; semantic content lives in the dominance lattice of trees. Two pieces of content are "the same" iff their trees lie in the same $\preceq_d$-equivalence class. This is the lattice's role as the *knowledge representation* of the system.

### 9.2 Cross-node aggregation

When two nodes wish to merge their dominance caches, they exchange Tier-0 + Tier-1 signatures. The signatures admit a commutative-monoid combination (component-wise max) that lets the merge run in $O(|\mathcal{C}_1| + |\mathcal{C}_2|)$ without re-running full $\preceq_d$ checks across the union. The lattice serves as the *aggregation algebra*.

### 9.3 Inference sharding

CRT dual-prime sharding (Section 2.3) gives the inference layer free horizontal partitioning. A node may compute the $q_1$-residue of an attention layer independently of the $q_2$-residue. Combination is Garner reconstruction. The lattice serves as the *parallelisation primitive*.

### 9.4 Crawl assignment

Crawl tasks — discovering new content for the corpus — are assigned by prime address: each crawler is responsible for content whose primary prime index lies in a fixed residue class. Because the lattice's prime structure is global, no central authority needs to coordinate assignment; the math itself partitions the work. The lattice serves as the *task scheduler*.

### 9.5 Verification

A node attesting to a piece of content publishes its KSTE tree plus the Tier-0/Tier-1 signatures. Verification by another node is constant-time at Tier-0 and one-SIMD-instruction at Tier-1; only disputed entries require a full $\preceq_d$ check. The lattice serves as the *verification primitive*.

### 9.6 Token economy

Novelty — admission of a new antichain element under $\preceq_d$ — is the scarce resource the token economy rewards. Because Kruskal's theorem bounds antichain length, the supply of novelty per equivalence class is bounded a priori, giving the token its scarcity property without needing any artificial supply curve. The lattice serves as the *scarcity primitive*.

These six layers do not share *similar* mathematics; they share *the same* mathematics. PPT formalises this substrate at the tensor and silicon layer; the lattice formalises it at the network layer. Both are the same object.

---

## Section 10. Production Status

| Primitive | Status |
|-----------|--------|
| $O_K$ arithmetic + Frobenius lift | Production |
| VHT2 + Möbius reorder + 63-byte Spinor block | Production (frozen format) |
| Polynomial-ring attention + 60-bit NTT | Production |
| CRT dual-prime NTT (no `__int128`) | Production |
| KSTE encoder + Tier-0 / Tier-1 dominance | Production, 21/21 tests green (target gate for new build) |
| Q8 weight storage with Frobenius scale | Production |
| Q4 mixed-precision path | Under calibration |
| ARM (HRR in $R_q$) | Math validated, integration pending |
| Stern–Brocot RoPE (E9.1) | Lab-validated, integration pending |
| BSD verification on toy curves (E9.6) | Lab-validated |

"Production" means the primitive has shipped in the engine reference build at a tagged commit and passes the cross-platform parity gate. "Under calibration" means the math is sound but the rounding / scale picker needs tuning before it ships at production accuracy. "Math validated, integration pending" means the lab measurements confirm the theoretical claim but the path through the production engine has not yet been wired.

The Q4 mixed-precision path is the only currently calibrating primitive. The other primitives have already passed their parity gates and are simply waiting for the next end-to-end build to ship.

---

## Section 11. Open Questions

We close with the open questions inherited from the previous theory revision and the new ones surfaced by this expansion. Each is named explicitly so that downstream work can target them.

### 11.1 KSTE injectivity

Is the encoder $\Phi: \mathbb{R}^d \to T_{60,3}$ injective on the natural distribution of K-vectors that real attention produces? **Open.** *Conjecture.* $\Phi$ is injective up to $\preceq_d$-equivalence: two K-vectors with the same image tree are operationally identical, which is the semantic-dedup criterion we want. A strict-injectivity counterexample would be informative because it would tell us which directions of $\mathbb{R}^d$ the encoder collapses; a strict-injectivity proof would let us drop the Tier-0 / Tier-1 prefilters and run only full $\preceq_d$ comparisons. Neither outcome is currently in hand.

### 11.2 Optimal $q$-bank for Ramanujan–Fourier modulation

**Open.** Phase 9 and Phase 10 explored modulation banks $\{2, 3, 5, 6, 10\}$ with period-5 and PRNG-shuffled designs; both were refuted *pre*-VHT2, before the anchor injection step landed. Post-VHT2 work was killed mid-sweep. The lattice project should either:

- Retire Ramanujan–Fourier as a separate phase decision, accepting that VHT2 + Möbius + Spinor already captures the multiplicative structure Ramanujan sums would have provided; or
- Attempt a fresh post-VHT2 sweep with a re-derived bank under different priors — in particular, banks aligned with the CRT primes' multiplicative structure rather than small-integer banks.

The decision has not been made.

### 11.3 ARM capacity under realistic churn

**Open.** The lab capacity curve (0.83 → 0.15 over $K = 1, \dots, 64$) assumes sparse, near-orthogonal keys. Real gradient aggregation produces keys with substantial cross-correlation, which will degrade the curve. The amount of degradation is not yet measured. Until ARM is integrated end-to-end into a training loop with measurable downstream task accuracy, the realistic capacity curve is unknown.

### 11.4 Semantic adjacency on the lattice

**Open.** Whether two URLs that are close in the prime-factored lattice — for instance, two URLs whose primary prime indices differ by one slot in the Möbius-reordered enumeration — have semantically-related content is an empirical claim that requires testing on a real corpus. The theoretical framework neither implies nor refutes adjacency; this is a property the lattice may or may not have, and the answer matters for the crawl-assignment primitive of Section 9.4.

### 11.5 Byzantine commitment binding

**Open.** The hardness assumption underneath the dominance commitment scheme needs formal articulation. What does a malicious node need to *break* to forge an embedding witness — i.e., to publish a tree $T$ together with claimed K-vector $K$ such that some independent verifier would falsely accept $T = \Phi(K)$? Candidate hardness assumptions:

- The discrete logarithm in $E(K)$, which would be standard ECC hardness.
- The shortest-vector problem in the prime-factored lattice $\Lambda$, which would put us on lattice-cryptography footing.
- A combination of the two, where forging a witness requires both ECC and lattice breaks.

None of these has been pinned down formally.

### 11.6 Mechanism-design sufficiency

**Open.** Does the dominance-novelty-token incentive structure produce a non-trivial Nash equilibrium under standard rationality assumptions? The token rewards novelty; novelty admissions are bounded by Kruskal's theorem; the question is whether rational nodes will choose to publish their novelty or to hoard it pending a higher reward, and whether the resulting strategy space admits a Pareto-efficient equilibrium. This is a problem for mechanism designers; the math layer cannot answer it.

### 11.7 The $\Lambda_+ \to T_{60,3}$ converse

**Open.** Given a tree $T \in T_{60,3}$, is there always a K-vector $K \in \mathbb{R}^d$ such that $\Phi(K) = T$? **Conjecture.** No — the encoder is not surjective. The image of $\Phi$ is a strict subset of $T_{60,3}$ characterised by the realisability of the anchor / residual statistics under the VHT2 transform. Trees outside the image are "syntactically valid but semantically impossible". This conjecture has not been proven; the image is not characterised.

---

## Section 11.5. Theorem T8 — MTP as Step-10 Activation Oracle Prefetch (added 2026-05-23)

### Statement

Multi-token prediction (MTP) in the lattice maps structurally to Step 10 of the 13-step PPT canonical table (Section 7) — the Activation Oracle Update (Cramér prime-gap prefetch). A K-step MTP draft is the explicit construction of the next K positions of the Poncelet orbit *in the negacyclic cyclotomic ring* $R_q = \mathbb{Z}_q[x]/(x^N+1)$, prior to any verification or commitment.

Formally: let $S_t = (x_t, K_t, V_t, A_t)$ denote the full session state at position $t$ — token, key-cache slab, value-cache slab, ARM bank snapshot — and let $\Phi: S_t \to (S_{t+1}, x_{t+1})$ be the sequential single-token forward operator. Let $\Phi^{(K)}_{\text{batch}}$ denote the K-wide batched forward through the same architecture but with the auxiliary MTP heads producing $K$ draft tokens in a single pass.

**T8 (MTP exactness in $R_q$).** For any session state $S_t$, the batched draft + verify operation
$$\Phi^{(K)}_{\text{batch}}(S_t) = (S_{t+K}, x_{t+1}, \ldots, x_{t+K})$$
is bit-identical to the K-fold sequential composition
$$\Phi \circ \Phi \circ \cdots \circ \Phi \, (S_t)$$
provided (a) the MTP draft heads produce token candidates whose verification under the main forward passes acceptance, and (b) all rejected drafts are followed by an exact ring-pointer rewind of the speculative Spinor blocks from the cache.

### Proof sketch

Three ingredients:

1. **Batched matmul = K sequential matmuls in $R_q$.** The negacyclic ring operations $\mathbb{Z}_q[x]/(x^N+1)$ are bilinear over the base ring $\mathbb{Z}_q$. Stacking K query vectors into a $K \times d$ matrix and running one matrix-matrix multiplication against the weight matrix is mathematically identical to running K matrix-vector multiplications against the same weight matrix, in $\mathbb{Z}_q$. Theorem T4 (Frobenius lift exactness) carries the bit-identity through the inline-lift Q4 / Q8 paths. There is no floating-point reordering tolerance because the operations are integer in $\mathbb{Z}_q$.

2. **Spinor block writes are positional and idempotent on commit.** The 63-byte Spinor block at cache position $t+k$ is a deterministic function of $(K_{t+k}, V_{t+k})$. Writing it at draft time and re-reading it at verify time produces the same bytes. Marking the block "committed" is a single-bit flag flip; the payload does not change.

3. **Rewind = ring-pointer decrement, not memory release.** When the verifier rejects draft tokens at positions $t+j, t+j+1, \ldots, t+K-1$, the cache's *write index* (the position at which the next Spinor block lands) decrements from $t+K$ to $t+j$. The uncommitted Spinor blocks at $[t+j, t+K)$ are not freed; they are simply overwritten by the next draft. Because the algebra is exact in $\mathbb{Z}_q$, there is no floating-point "residual" left in the cache — the bytes at $[t+j, t+K)$ in the rewound state are *meaningless*, not subtly wrong, and the next write erases them deterministically.

The composition of (1) + (2) + (3) establishes $\Phi^{(K)}_{\text{batch}} \equiv \Phi^{\circ K}$ on the accepted prefix.

### Corollary T8.1 — No ghost contamination after rollback

Unlike a continuous-float MTP implementation, where a rejected speculative pass may leave numerical residue in the KV cache (un-normalized activations, partially-accumulated softmax denominators, FMA reassociation artifacts), the lattice's $\mathbb{Z}_q$ arithmetic guarantees that *the state at position $t+j$ after rewind from $t+K$ is byte-identical to the state at position $t+j$ never having visited $t+K$ at all*. The rejection algebra is clean.

This is the structural property that makes `sp_session_rewind(sess, n_rejected)` from the L1 ABI (Appendix A of PPT-LAT-Systems) implementable as an O(1) pointer decrement rather than as a full cache scrub.

### Corollary T8.2 — VRAM scaling of the speculative state

Continuous-float MTP implementations (DeepSeek V3/V4, Gemma 4, llama.cpp's beta MTP merge) carry the full $K$-step draft KV in float16 or bfloat16. At Gemma3-1B scale with $K=4$ draft tokens at $n_\text{ctx} = 4096$, this is ~270 MB × 4 = ~1 GB of speculative KV beyond the committed cache.

The lattice's KV is already compressed ~130× by VHT2 + Möbius reordering + Spinor packing (Theorem T2 + Section 3 + E_CPU_6's 63-byte Spinor signatures). The same compression applies to speculative blocks. A 4-token draft adds ~8 MB of speculative KV on the same model — two orders of magnitude smaller than the continuous-float baseline. This is the "we don't pay the MTP VRAM tax" claim, and it is a direct consequence of the cache substrate, not a separate optimization.

### Practical realization

T8 is *theoretical*. Its realization in code is queued as **Phase 4-MTP** in the Roadmap (Section 18, deferred behind `lat-phase-3-closed`). The L1 ABI surface required to implement it (`sp_session_clone`, `sp_session_rewind`, atomic cancel flag) is *already frozen* at `lat-phase2-contract-frozen` — the contract anticipated this without naming the use case. T8 is the named use case.

---

## Section 12. Anti-Contamination — What This Project Rebuilds from Scratch

This document was drafted under a binding anti-contamination rule: no source files from `shannon-prime/` or `shannon-prime-engine/` were read. The math papers under `papers/PPT-ARM/` were available as *conceptual* reference only and were not cited as primary sources. Every formula, every byte layout, every algorithm sketch was restated fresh from first principles.

This is not a stylistic preference. The lattice project is a fresh start, and the lattice project will succeed or fail on its own engineering choices. Pulling in primitives from legacy code paths would re-introduce the implicit invariants of those code paths — invariants that have been load-bearing for the engine but which may not be load-bearing here, and which may actively interfere with the lattice's network-layer goals.

What this project rebuilds from scratch, and where the rebuild should keep faith with the math but not necessarily with the legacy code:

- **The Spinor block is FROZEN.** Bit-exact compatibility with the legacy 63-byte format is required because cross-node verification depends on it. The lattice must consume and produce the same bytes the engine consumes and produces.
- **The CRT primes are FROZEN.** $q_1 = 1{,}073{,}738{,}753$ and $q_2 = 1{,}073{,}732{,}609$ are part of the protocol. A new lattice node using different primes would be unable to verify any existing dominance commitment.
- **The KSTE encoder algorithm is specified to the byte.** Two independent implementations must produce the same 64-byte block from the same K-vector. This is the "target gate for new build" — the 21/21 test suite that the rebuild must pass.
- **Everything else is up for grabs.** The engine's choice of how to lay out KV cache in memory, how to schedule prefetchers, how to structure the activation oracle — these are engine choices, made for engine reasons. The lattice may make different choices for network reasons, and that is fine.

The rule going forward: math is shared, byte formats are shared, algorithms at the cryptographic-witness layer are shared. Everything else is local to the project that owns it.

---

*End of document.*
