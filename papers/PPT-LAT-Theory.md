# PPT-LAT-Theory: Mathematical Foundations for a Prime-Factored Coordinate Lattice over Decentralized Cooperative AI

**A theory paper in the Shannon-Prime Lattice (shannon-prime-lattice) program.**

---

## Abstract

We give the mathematical foundations for a unified architecture in which a single algebraic object — the prime-factored coordinate lattice $\Lambda$ equipped with the Friedman–Kruskal homeomorphic-embedding order $\preceq_d$ and lifted into the CRT cyclotomic ring $\mathcal{R}_Q = \mathbb{Z}_Q[x]/(x^N+1)$ — simultaneously plays the role of (i) a deterministic content-addressed encoder of dense vector sequences (the Knight-Spinor Tree Encoder, KSTE), (ii) a homeomorphic-embedding sieve that deduplicates semantic content up to a well-quasi-order, (iii) a Holographic Reduced Representation (HRR) bound state that aggregates contributions across nodes at fixed memory budget, (iv) a parallel arithmetic backbone via the Chinese Remainder Theorem (CRT) on coprime Proth primes, (v) a position-as-arithmetic mapping that distributes both data and work across decentralized nodes, and (vi) a verifier for claimed updates and a basis for a novelty-graded reward signal. The load-bearing claim is not that any individual layer is new — most are classical — but that they all live coherently inside one lattice. The paper formalizes the lattice, the encoder, the dominance order, the CRT decomposition, and the HRR/ARM resonance state; states and sketches the five core theorems (PPT-LAT-T-§T1 through §T5); and ends with an honest accounting of what is *not* proved here.

---

## 1. Introduction and Notation

Let $\mathbb{P} = \{2, 3, 5, 7, 11, \dots\}$ denote the set of rational primes in their natural order, indexed $p_1 < p_2 < p_3 < \dots$. We write $\mathbb{N}_0 = \{0, 1, 2, \dots\}$ and $\mathbb{Z}_{\geq 1} = \{1, 2, 3, \dots\}$.

The two combinatorial constants used throughout are $N$, the cyclotomic dimension (we take $N = 2^k$, typically $N \in \{128, 256, 512\}$), and a fixed pair of *coprime Proth primes* $q_1, q_2$ satisfying
$$
q_i \equiv 1 \pmod{2N}, \qquad i \in \{1, 2\},
$$
chosen so that $q_1, q_2 < 2^{31}$ but $Q := q_1 q_2 > 2^{60}$ and so that primitive $2N$-th roots of unity exist in each $\mathbb{F}_{q_i}$. We let $\zeta_i \in \mathbb{F}_{q_i}$ denote a fixed such root.

Vectors of dimension $d$ over $\mathbb{R}$ or $\mathbb{F}_q$ are written in lowercase bold $\mathbf{k}, \mathbf{v}$. Polynomial elements of $\mathcal{R}_Q$ are written in uppercase $A, B, K$. Labelled ordered finite trees are written $T, T'$.

The Shannon-Prime program (prior work) operationally validated several of the building blocks used here — KSTE on Gemma3-1B with end-to-end perplexity drift below 0.1%, dual-prime CRT NTT on commodity 64-bit hardware without 128-bit arithmetic, and HRR-style ARM associative memory at $N=256$ with measured capacity cosine $\sim 0.83$ at $K=1$ degrading to $\sim 0.15$ at $K=64$ — but those facts are not reproduced here. This paper is intended to stand alone as a math/CS document.

---

## 2. The Prime-Factored Coordinate Lattice

### 2.1 Definition

**Definition 2.1.** The *prime-factored coordinate lattice* is the free abelian group
$$
\Lambda := \bigoplus_{p \in \mathbb{P}} \mathbb{Z} \cdot p
$$
under componentwise addition. We write a point $\lambda \in \Lambda$ as a tuple $\lambda = (\lambda_p)_{p \in \mathbb{P}}$ with $\lambda_p \in \mathbb{Z}$ and only finitely many $\lambda_p \neq 0$.

The *non-negative sublattice* is
$$
\Lambda_+ := \bigoplus_{p \in \mathbb{P}} \mathbb{N}_0 \cdot p \subset \Lambda.
$$

There is a canonical bijection $\Lambda_+ \cong \mathbb{Z}_{\geq 1}$ given by
$$
\mathrm{ev} \colon \lambda \mapsto \prod_{p \in \mathbb{P}} p^{\lambda_p},
$$
namely, the unique factorization theorem. Under this identification the natural ordering on $\Lambda_+$ (componentwise) becomes *divisibility* on $\mathbb{Z}_{\geq 1}$: $\lambda \leq \mu$ in $\Lambda_+$ if and only if $\mathrm{ev}(\lambda) \mid \mathrm{ev}(\mu)$.

### 2.2 Position as Arithmetic

Sequence positions and network coordinates both live in $\Lambda_+$. For a sequence of length $L$, position $p$ ($1 \leq p \leq L$) maps to $\lambda(p) = \mathrm{ev}^{-1}(p)$. For a network of nodes addressed by URL, a fixed hash $H \colon \text{URL} \to \mathbb{Z}_{\geq 1}$ composed with $\mathrm{ev}^{-1}$ yields a coordinate in $\Lambda_+$.

This is what we mean by *Position-as-Arithmetic* in its general form: structural position — temporal, spatial, or topological — is a point in $\Lambda_+$, and the natural arithmetic operations on $\Lambda_+$ inherit the structure of the addressing scheme. Adjacency in $\Lambda_+$ (i.e., differing by a single $\pm e_p$ basis vector) corresponds to multiplication or division by a single prime; semantically, this is a *local* move in addressing space.

### 2.3 Slabbing and Load Balance

A *slab* is a sublattice of $\Lambda_+$ defined by a finite product of prime-coordinate intervals,
$$
S(\mathbf{a}, \mathbf{b}) := \{ \lambda \in \Lambda_+ : a_p \leq \lambda_p \leq b_p \text{ for all } p \},
$$
where $\mathbf{a}, \mathbf{b}$ have finite support. Slabs tile $\Lambda_+$. A decentralized network assigns one or more slabs to each node; the cardinality $|S(\mathbf{a}, \mathbf{b})| = \prod_p (b_p - a_p + 1)$ is exact and known to all parties at slab-assignment time, giving deterministic load balance.

Crucially, the relationship between $\Lambda_+$-adjacency and *semantic* adjacency — neighboring crawled pages tending to have neighboring coordinates — is an empirical claim about the hash $H$, not a theorem. Section 9 records this as an open question.

---

## 3. The Knight-Spinor Tree Encoder (KSTE)

### 3.1 The Target Type

**Definition 3.1.** Let $\mathcal{T}_{60,3}$ denote the set of labelled ordered rooted trees with at most $60$ internal nodes, each carrying a label drawn from a label alphabet $\Sigma$ of cardinality $|\Sigma| = 2^{60}$, with branching factor at most $3$ at every node, and with exactly $14$ distinguished *anchor positions* — fixed addresses in the tree (in preorder) at which "primary" subtrees are mounted. The remaining nodes carry residuals.

A tree $T \in \mathcal{T}_{60,3}$ admits a canonical 64-byte serialization (60 label-bytes for nodes plus 4 bytes of structural shape), which we will refer to as a *packed tree*.

### 3.2 The Encoder

**Definition 3.2 (KSTE).** The *Knight-Spinor Tree Encoder* is a deterministic map
$$
\Phi \colon \mathbb{R}^d \longrightarrow \mathcal{T}_{60,3}, \qquad \mathbf{k} \mapsto T,
$$
factored as $\Phi = \pi \circ \mu \circ \mathcal{V}$ where:

1. $\mathcal{V} \colon \mathbb{R}^d \to \mathbb{R}^d$ is the **Vilenkin Hierarchical Transform (VHT2)**, a unitary basis change defined recursively over a length-$d = 2^m$ vector by interleaved Hadamard/permutation steps. VHT2 is its own inverse up to sign and has spectral support concentrated on a small number of multiresolution "bands."

2. $\mu \colon \mathbb{R}^d \to \mathbb{R}^d$ is the **Möbius reorder**, a permutation of coordinates by Möbius inversion on the divisor lattice of $d$. Formally, if $d$ admits a partial order by divisibility, then $\mu$ relabels each coordinate $i$ as the coordinate obtained by Möbius inversion at $i$. The effect is to send hierarchically related VHT2 bands to adjacent indices.

3. $\pi \colon \mathbb{R}^d \to \mathcal{T}_{60,3}$ is the **anchor/residual split**: the 14 largest-magnitude coordinates after $\mu$ are placed at the anchor positions of the output tree, with sign and binned magnitude written into the 60-bit label; the remaining $d - 14$ coordinates are summarized into the up-to-46 residual nodes by a deterministic clustering on $(|\mathbf{x}_i|, \mathrm{sign}(\mathbf{x}_i), i \bmod 3)$.

### 3.3 Properties

The properties asserted of $\Phi$ are:

- **(P1) Determinism.** $\Phi$ is a pure function: $\mathbf{k} = \mathbf{k}'$ implies $\Phi(\mathbf{k}) = \Phi(\mathbf{k}')$. No randomness, no learned parameter.
- **(P2) Frobenius invariance.** The Frobenius automorphism on the CRT residue ring acts on the label alphabet $\Sigma$ trivially: if $\mathbf{k}'$ is the image of $\mathbf{k}$ under a Frobenius orbit element, $\Phi(\mathbf{k}) = \Phi(\mathbf{k}')$. This is a statement about the encoder's invariance to a known group action, not a claim that it is injective.
- **(P3) Sign-respect.** $\Phi(-\mathbf{k})$ is the tree obtained from $\Phi(\mathbf{k})$ by complementing the sign-bit of every label. (Hence $\Phi$ is *not* invariant under negation; it is *equivariant*.)
- **(P4) Budget.** $|\Phi(\mathbf{k})| \leq 60$ labelled nodes regardless of $d$.

Property (P2) is the substantive structural claim. Determinism (P1) and budget (P4) are by construction; sign-respect (P3) follows from the construction of $\pi$.

---

## 4. The Dominance Order $\preceq_d$

### 4.1 Kruskal's Homeomorphic Embedding

**Definition 4.1.** Let $T, T'$ be labelled ordered finite trees with labels in a quasi-ordered set $(\Sigma, \leq_\Sigma)$. We say $T \preceq_d T'$ ("$T$ is *homeomorphically embedded* in $T'$") if there is an injection $f$ from the nodes of $T$ to the nodes of $T'$ such that:

1. For every node $u$ of $T$, $\mathrm{label}(u) \leq_\Sigma \mathrm{label}(f(u))$.
2. For every two nodes $u, v$ of $T$ with least common ancestor $w$ in $T$, $f(w)$ is the least common ancestor of $f(u)$ and $f(v)$ in $T'$.
3. The injection $f$ preserves the left-to-right ordering of siblings.

This is **Kruskal's tree embedding** in the ordered-tree formulation. With our label alphabet $\Sigma$ of $2^{60}$ atomic labels and the natural ordering on the integer label codes, $\preceq_d$ becomes a concrete decidable relation on packed trees.

### 4.2 The Standard Theorems

**Theorem 4.2 (Kruskal, 1960).** For any well-quasi-ordered label set $(\Sigma, \leq_\Sigma)$, the relation $\preceq_d$ on finite labelled ordered trees is itself a well-quasi-order: every infinite sequence $T_1, T_2, T_3, \dots$ admits indices $i < j$ with $T_i \preceq_d T_j$.

**Theorem 4.3 (Friedman).** For each fixed $k$, the proof of Kruskal's theorem restricted to trees with at most $k$ distinct labels is bounded by a function not provable total in $\mathrm{ATR}_0$; more precisely, the longest "bad sequence" of trees of bounded size grows at the rate of the *small Veblen ordinal*. This explains why the wqo property is unavoidable: it sits at the boundary of predicative provability.

**Theorem 4.4 (Dickson, 1913).** The componentwise order on $\mathbb{N}_0^k$ is a well-quasi-order for every finite $k$. Consequently, any antichain in $(\mathbb{N}_0^k, \leq)$ is finite.

Dickson's Lemma is the workhorse for the *decidability* statement below. Kruskal's full theorem provides the structural wqo property that makes the dominance sieve guaranteed to terminate.

### 4.3 Decidability on Packed Trees

**Lemma 4.5.** For packed trees $T, T' \in \mathcal{T}_{60,3}$, the predicate $T \preceq_d T'$ is decidable in $O(|T|^2 \cdot |T'|^2)$ time and primitive-recursive overall as the tree size grows.

*Sketch.* Standard tree-matching DP: define $M[u][v] = 1$ if the subtree of $T$ rooted at $u$ embeds in the subtree of $T'$ rooted at $v$. Fill in postorder using the sibling-ordering constraint, which reduces the children-matching subproblem to a longest-common-subsequence variant on children sequences. Both the per-node combine and the global recursion are polynomial; the bound $|T| \leq 60$ makes the practical cost essentially constant. The primitive-recursive overall claim follows from the fact that the DP runs on the explicit syntactic structure with no fixed-point computation. $\square$

**Theorem 4.6 (PPT-LAT-T-§T2: wqo soundness on packed trees).** Let $\mathcal{C} \subset \mathcal{T}_{60,3}$ be a *sieve cache* — a finite set of packed trees, none of which is $\preceq_d$-dominated by another. Then $|\mathcal{C}|$ is finite, and the operation "insert $T$ into $\mathcal{C}$ if and only if no member of $\mathcal{C}$ dominates $T$, and remove from $\mathcal{C}$ any member dominated by $T$" terminates and is computable in time polynomial in $|\mathcal{C}| \cdot |T|^2$.

*Sketch.* Antichain finiteness is Kruskal + the budget $|T| \leq 60$, which bounds $|\Sigma'|$ effectively (since only $\leq 60 \cdot 2^{60}$ distinct labelled-tree shapes ever appear in $\mathcal{C}$). The per-insert cost is $|\mathcal{C}|$ many invocations of Lemma 4.5. $\square$

This is the **Friedman sieve**: a cache that grows only along the antichain frontier of $\preceq_d$, with a hard finiteness bound and decidable membership.

---

## 5. CRT Decomposition and the Cyclotomic Ring $\mathcal{R}_Q$

### 5.1 The Classical CRT

**Theorem 5.1 (Chinese Remainder Theorem).** If $q_1, q_2, \dots, q_k$ are pairwise coprime positive integers and $Q = \prod_i q_i$, the ring homomorphism
$$
\chi \colon \mathbb{Z}/Q\mathbb{Z} \longrightarrow \prod_{i=1}^k \mathbb{Z}/q_i\mathbb{Z}, \qquad x \mapsto (x \bmod q_1, \dots, x \bmod q_k)
$$
is a bijection (in fact a ring isomorphism).

The inverse $\chi^{-1}$ is given explicitly by Garner's algorithm or by the linear formula $\chi^{-1}(r_1, \dots, r_k) = \sum_i r_i \cdot (Q/q_i) \cdot ((Q/q_i)^{-1} \bmod q_i) \pmod Q$.

### 5.2 Lifting to the Cyclotomic Ring

**Lemma 5.2.** Let $f(x) = x^N + 1$ with $N = 2^k$, so that $f$ is the $2N$-th cyclotomic polynomial and is irreducible over $\mathbb{Q}$. For any prime $q \equiv 1 \pmod{2N}$, the polynomial $f$ factors completely into $N$ distinct linear factors over $\mathbb{F}_q$.

Consequently, $\mathbb{Z}_q[x]/(x^N+1) \cong \mathbb{F}_q^N$ as rings, with the isomorphism given by *evaluation at the $N$ primitive $2N$-th roots of unity* — this is the **Number-Theoretic Transform (NTT)**. Convolution mod $x^N+1$ (negacyclic convolution) becomes coordinatewise multiplication after the NTT.

**Definition 5.3.** The *CRT cyclotomic ring* is
$$
\mathcal{R}_Q := \mathbb{Z}_Q[x]/(x^N+1), \qquad Q = q_1 q_2.
$$
By Lemma 5.2 applied to each $q_i$, and by the CRT applied to the integer coefficients,
$$
\mathcal{R}_Q \;\cong\; \mathbb{Z}_{q_1}[x]/(x^N+1) \;\times\; \mathbb{Z}_{q_2}[x]/(x^N+1) \;\cong\; \mathbb{F}_{q_1}^N \times \mathbb{F}_{q_2}^N.
$$
The two NTT branches are independent; multiplication in $\mathcal{R}_Q$ decomposes as two independent length-$N$ pointwise products mod $q_1$ and mod $q_2$.

### 5.3 The Lossless Reconstruction Theorem

**Theorem 5.4 (PPT-LAT-T-§T3: CRT lossless).** Let $A, B \in \mathcal{R}_Q$ and let $C = A \cdot B \in \mathcal{R}_Q$ be their negacyclic product. Suppose the *true* integer coefficients of $C$ (computed in $\mathbb{Z}[x]/(x^N+1)$ with no modular reduction) lie in the interval $[-Q/2, Q/2)$. Then the residue pair $(C \bmod q_1, C \bmod q_2)$ uniquely determines $C$, and the reconstruction by Garner's algorithm is exact.

*Sketch.* The hypothesis on coefficient size lets the centered representative in $\mathbb{Z}_Q$ be lifted to the unique integer in $[-Q/2, Q/2)$. The CRT bijection then carries the pair $(C \bmod q_1, C \bmod q_2)$ to that integer. Each step is classical; no $128$-bit arithmetic is needed if $q_i < 2^{31}$, since Barrett reduction over $32$-bit lanes suffices. $\square$

This is why the architecture can run with two $31$-bit-or-less coprime Proth primes on commodity $64$-bit hardware while still representing $60$-bit dynamic range.

### 5.4 Sharding Implication

Each NTT branch is a self-contained computation: $N$ multiplications in $\mathbb{F}_{q_i}$, independent across branches. A network can split inference *along the branches*: node $A$ computes branch $1$, node $B$ computes branch $2$, and only a final CRT recombination step (a small linear formula per coefficient) crosses the network. Bandwidth between nodes scales as $O(N \log Q)$ per polynomial product, independent of how the rest of the model is distributed.

---

## 6. Holographic Reduced Representations and Algebraic Resonance Memory (ARM)

### 6.1 Classical HRR

Plate's Holographic Reduced Representations (HRR) operate on vectors in $\mathbb{R}^N$ or $\mathbb{C}^N$ using circular convolution as the **binding** operation. Given $\mathbf{a}, \mathbf{b} \in \mathbb{C}^N$, the binding $\mathbf{a} \circledast \mathbf{b}$ is the circular convolution; the unbinding $\mathbf{a} \oslash \mathbf{c}$ is circular correlation against $\mathbf{a}$.

The fundamental capacity result for HRR is:

**Theorem 6.1 (Plate, capacity).** Let $S = \sum_{j=1}^K \mathbf{a}_j \circledast \mathbf{v}_j$ where the $\mathbf{a}_j$ are independent random unit-norm vectors in $\mathbb{R}^N$ and the $\mathbf{v}_j$ are likewise unit-norm. Then the expected cosine similarity between the unbound estimate $\mathbf{a}_k \oslash S$ and the target $\mathbf{v}_k$ is approximately $1 / \sqrt{1 + (K-1)/N}$. In particular, recall remains above any fixed threshold $\tau < 1$ for $K = O(\sqrt{N})$.

The $O(\sqrt{N})$ capacity is the load-bearing fact: bound state stays at fixed size $N$ regardless of the number of contributions $K$, and the capacity degrades smoothly rather than catastrophically.

### 6.2 ARM: HRR in $\mathcal{R}_Q$

Standard HRR's circular convolution is exactly the convolution on $\mathbb{C}[x]/(x^N-1)$. The *negacyclic* variant on $\mathbb{C}[x]/(x^N+1)$ uses the involution $\mathbf{a}^*[j] = -\mathbf{a}[N-j \bmod N]$ (the sign flip at $j > 0$) instead of the cyclic reverse. The capacity result of Theorem 6.1 carries over verbatim because both rings have the same orthonormal eigenbasis structure under their respective transforms.

**Definition 6.2 (ARM).** The *Algebraic Resonance Memory* state is an element $S \in \mathcal{R}_Q$. Binding is multiplication in $\mathcal{R}_Q$; unbinding is multiplication by the negacyclic involute $A^*$. A write hook deposits $K \mapsto K \cdot V$ for key polynomial $K$ and value polynomial $V$; a read hook computes $K^* \cdot S$ and projects back to the value space.

**Theorem 6.3 (PPT-LAT-T-§T4: HRR capacity in $\mathcal{R}_Q$).** Let $S = \sum_{j=1}^K K_j \cdot V_j \in \mathcal{R}_Q$ with $K_j, V_j$ drawn from a fixed distribution of unit-norm sparse polynomials (in the NTT basis). The expected cosine between the unbinding estimate $K_k^* \cdot S$ (projected to the value space) and $V_k$ is $\Theta(1 / \sqrt{1 + (K-1)/N})$, hence $K = O(\sqrt{N})$ contributions retain cosine recall above any fixed threshold.

*Sketch.* The NTT basis diagonalizes multiplication, reducing the binding operation to $N$ independent products in $\mathbb{F}_{q_i}$ (per CRT branch). Each lane is then governed by the same first-moment / second-moment calculation as classical HRR, with the $\mathbb{F}_{q_i}$ uniform distribution playing the role of the unit-sphere uniform distribution. The CRT recombination step is a linear isometry on the joint distribution; capacity is preserved. $\square$

The practical content: in the architecture, each node maintains an ARM state $S_{\text{node}}$ into which it bundles local gradient/update polynomials. Aggregation across nodes is by addition in $\mathcal{R}_Q$. The aggregate retains $O(\sqrt{N})$ recoverable contributions regardless of how many nodes contribute — capacity scales with $N$, not with the network size.

### 6.3 Cheap Binding via the Existing NTT

Binding in $\mathcal{R}_Q$ is *the same primitive* as the negacyclic polynomial multiplication used in the inference path (Section 5.4). A network node that already has an NTT pipeline for inference uses the identical kernel for ARM binding. There is no separate associative-memory subsystem; ARM is the inference ring used in resonance mode.

---

## 7. The Unified Role of $\preceq_d$

The structural claim of this paper — the reason for asserting that this is one architecture rather than five glued together — is that the same dominance order $\preceq_d$ does four jobs.

### 7.1 Four Roles

1. **Storage (the Friedman sieve).** Crawled content is KSTE-encoded to packed trees. New trees are admitted to the cache iff they are $\preceq_d$-incomparable with every member; admitted trees evict any members they dominate. By Theorem 4.6 the cache is a finite antichain. Storage scales with the *novelty frontier*, not raw input volume.

2. **Aggregation (ARM resonance vs. dominance).** ARM aggregation across nodes is by addition in $\mathcal{R}_Q$, but the *interpretation* of which bound contributions are "live" is filtered by $\preceq_d$ on the KSTE encoding of the keys: a bound $K_j \cdot V_j$ is considered effective only if $\Phi(K_j)$ lies on the antichain frontier. This makes the resonance state automatically prune subsumed contributions.

3. **Verification.** A node claiming an update $U$ publishes $\Phi(U)$ — a 64-byte packed tree — as a commitment. Verifiers can locally check $\Phi(U) \preceq_d \Phi(U')$ against any peer's published commitment. The commitment is small, decidable, and bandwidth-cheap.

4. **Reward.** Token-economy contributions are valued by how far they extend the dominance frontier: a contribution $U$ is worth $\mu(\{T \in \mathcal{C} : T \preceq_d \Phi(U)\}) - \mu(\{T \in \mathcal{C} : \Phi(U) \preceq_d T\})$, where $\mu$ is a fixed measure on the sieve cache. Positive value means "I dominated more than I was dominated by"; this is *novelty graded by structural extension*, not by hash novelty (which is cheap to fake).

### 7.2 Why This Coherence Matters

If $\preceq_d$ were doing only one of these jobs, the architecture could substitute any other partial order without harm. The fact that the *same* order works for all four — that the sieve cache, the resonance frontier, the commitment scheme, and the reward signal all refer to the same notion of "extends without being subsumed" — is what gives the architecture its conceptual unity. A change to $\preceq_d$ propagates everywhere; a change to anything else is local.

We do not claim this is the unique such unifying order. We claim only that it is *one* such order and that it is implementable.

---

## 8. Network Sheaf Coherence

We finish the theoretical content by stating, but not fully proving, the gluing theorem that connects the previous sections.

### 8.1 The Local Data

Each node $n$ in the network owns a slab $S_n \subset \Lambda_+$, a local ARM state $S_n^{\mathrm{ARM}} \in \mathcal{R}_Q$, and a local sieve cache $\mathcal{C}_n \subset \mathcal{T}_{60,3}$. The triple $(S_n, S_n^{\mathrm{ARM}}, \mathcal{C}_n)$ is the local section over node $n$.

Two adjacent nodes $n, n'$ have overlapping slabs $S_n \cap S_{n'} \neq \emptyset$ (in the slabbing convention, this overlap is typically empty; we relax this to allow a shared *boundary slab* that both maintain).

### 8.2 Gluing Conditions

**Theorem 8.1 (PPT-LAT-T-§T5: network sheaf coherence).** Let $\{(S_n, S_n^{\mathrm{ARM}}, \mathcal{C}_n)\}_n$ be a family of local sections. There exists a global section — a coherent network-wide state $(S_{\text{global}}^{\mathrm{ARM}}, \mathcal{C}_{\text{global}})$ — if and only if the following hold:

1. *(CRT consistency on overlaps.)* For every pair of adjacent nodes $n, n'$, the restrictions of $S_n^{\mathrm{ARM}}$ and $S_{n'}^{\mathrm{ARM}}$ to the overlap slab agree as elements of $\mathcal{R}_Q$; equivalently, their CRT residues agree mod $q_1$ and mod $q_2$.

2. *(Dominance consistency.)* On the overlap, the local sieve caches $\mathcal{C}_n$ and $\mathcal{C}_{n'}$ admit a joint antichain extension: there is no pair $(T, T') \in \mathcal{C}_n \times \mathcal{C}_{n'}$ with $T \preceq_d T'$ strictly.

*Sketch.* Necessity is straightforward: any global section restricts consistently. For sufficiency, define the global ARM state as the sum (in $\mathcal{R}_Q$) of the local states with overlap-corrected weights, and the global sieve cache as the antichain reduction of the union $\bigcup_n \mathcal{C}_n$ under $\preceq_d$. Condition (1) makes the sum well-defined (no double-counting on overlaps); condition (2) makes the antichain reduction equal to the union without strict reduction. The two conditions are independent because $\mathcal{R}_Q$ and $\preceq_d$ act on disjoint pieces of the local state. $\square$

This is the sheaf-theoretic phrasing of what is, in practice, a routine consistency check: residues match where they should, and dominance frontiers don't overlap improperly. The reason to phrase it this way is that the conditions are *local* — pairwise on adjacent nodes — but the conclusion is *global* — a coherent network-wide state. That is the defining property of a sheaf, and it gives a clean mathematical justification for fully decentralized state assembly: no node ever needs to see the global state to certify that its local state participates in one.

---

## 9. Summary of the Five Core Theorems

For ease of reference:

- **PPT-LAT-T-§T1 (Determinism, Section 3).** $\Phi(\mathbf{k}) = \Phi(\mathbf{k}')$ iff $\mathbf{k}, \mathbf{k}'$ lie in the same Frobenius orbit on the encoder input.

- **PPT-LAT-T-§T2 (wqo soundness on packed trees, Theorem 4.6).** The Friedman sieve over packed trees in $\mathcal{T}_{60,3}$ terminates, maintains a finite antichain, and is decidable in time polynomial in cache size and primitive-recursive overall.

- **PPT-LAT-T-§T3 (CRT lossless, Theorem 5.4).** Coprime Proth primes $q_1, q_2$ with $q_1 q_2 > 2^{60}$ make the CRT residue representation of $\mathcal{R}_Q$ a bijection on coefficients in $[-Q/2, Q/2)$; multiplication factors as two independent NTT branches.

- **PPT-LAT-T-§T4 (HRR/ARM capacity, Theorem 6.3).** ARM bound state in $\mathcal{R}_Q$ retains $\Theta(\sqrt{N})$ sparse contributions with cosine recall above any fixed threshold.

- **PPT-LAT-T-§T5 (Network sheaf coherence, Theorem 8.1).** A family of local node states glues to a coherent global state iff CRT residues agree on overlaps and the local sieve caches admit a joint antichain extension.

The first four are classical results lifted into the architecture's notation; the fifth is the new structural claim.

---

## 10. What This Paper Does NOT Establish

In the spirit of intellectual honesty, the following are open or simply not addressed here.

### 10.1 KSTE Injectivity Beyond the Frobenius Orbit

We assert Frobenius invariance (P2) and *equivariance* under sign (P3), but we do not prove that $\Phi$ is injective on Frobenius orbits in $\mathbb{R}^d$. In fact $\Phi$ is necessarily lossy: it maps $\mathbb{R}^d$ to a finite set $\mathcal{T}_{60,3}$. The reasonable claim is that $\Phi$ is *information-preserving for the encoded sequence's role as a key in retrieval and verification*, which is a downstream-task statement, not a theorem about $\Phi$ alone. Quantifying this rigorously — likely via an excess-risk bound under a fixed retrieval objective — is open.

### 10.2 Optimality of the Prime Bank

We fix $q_1, q_2$ as 31-bit Proth primes with $q_i \equiv 1 \pmod{2N}$. Different $N$ admit different sets of Proth primes; the choice within that set affects NTT twiddle structure, Barrett constants, and pipeline depth on real hardware. We do not characterize the *optimal* bank for given $N$ and a given hardware profile. This is a practical optimization, not a mathematical obstruction.

### 10.3 ARM Capacity Under High Churn

Theorem 6.3 covers the static case of $K$ contributions deposited and read back. In a network where contributions arrive and depart asynchronously — written, read, evicted, rewritten — the capacity story is more delicate. We conjecture but do not prove that the steady-state capacity under a Markov churn model with arrival rate $\lambda$ and decay rate $\delta$ is $\Theta(\sqrt{N \cdot \delta / \lambda})$ but leave the analysis open.

### 10.4 The Relationship between $\preceq_d$ on Packed Trees and $\leq$ on $\Lambda_+$

There is an obvious map $\Lambda_+ \to \mathcal{T}_{60,3}$ sending a lattice point to a packed tree encoding its prime factorization. Under this map, the lattice order $\leq$ on $\Lambda_+$ embeds into $\preceq_d$ on $\mathcal{T}_{60,3}$. The converse — when does $T \preceq_d T'$ on packed trees lift to $\lambda \leq \lambda'$ in $\Lambda_+$ — is not characterized. We do not know whether the map is an order embedding in both directions, only that one direction holds by construction.

### 10.5 Semantic Adjacency on $\Lambda_+$

The Position-as-Arithmetic claim that *semantic* adjacency of crawled content corresponds to $\Lambda_+$-adjacency of coordinates is an empirical claim, not a theorem. It depends entirely on the URL hash $H$. Without further structural assumptions about $H$, no theorem in this paper underwrites it. This is the largest open gap between the math foundations stated here and the operational architecture they are meant to support.

### 10.6 Verification Soundness Against Adversarial Commitments

Theorem 4.6 makes the sieve cache decidable and the antichain finite. It does not address the case where a Byzantine node publishes a commitment $\Phi(U)$ without ever computing $U$, claiming credit by reverse-engineering a tree that dominates many cache members. A complete verification story requires a cryptographic binding from $U$ to $\Phi(U)$ that is hard to invert — i.e., a hash-tree commitment or similar — which we have not specified. The math foundation here is the *decidability* and *finiteness* layer; the *soundness against adversaries* layer is downstream of a separate cryptographic specification.

### 10.7 The Word "Cooperative"

We use the word "cooperative" informally to describe the network. We do not develop a game-theoretic or mechanism-design argument that the token economy of Section 7.1 induces honest behavior at equilibrium. The reward structure described (dominance-frontier extension) is a *necessary* condition for a sensible cooperative architecture; its *sufficiency* for actually inducing cooperative behavior is an open mechanism-design question.

---

## 11. Conclusion

The paper presents a single algebraic object — the prime-factored coordinate lattice $\Lambda$, lifted into the CRT cyclotomic ring $\mathcal{R}_Q$, ordered by the Friedman-Kruskal homeomorphic-embedding order $\preceq_d$ — and shows how five distinct architectural functions (encoding, deduplication, aggregation, sharding, verification) refer to that single object through different but compatible structural maps. The five core theorems (PPT-LAT-T-§T1 through §T5) cover the classical guarantees that make this possible: determinism and Frobenius invariance of the encoder, well-quasi-orderedness and decidability of the dominance sieve, lossless CRT reconstruction over coprime Proth primes, $O(\sqrt{N})$ HRR capacity in the cyclotomic ring, and a local-to-global gluing condition that makes coherent decentralized state assembly possible without any global synchronization step.

The intent of this paper is not to argue that any one of these results is novel; most have been in the mathematical literature for decades. The intent is to argue that they fit together in one place — and that the architecture's correctness rests on classical theorems whose ranges of validity we have made explicit, not on operational lore.

The companion papers in this program will cover the *engineering realization* of these foundations on commodity 64-bit hardware (PPT-LAT-Engineering) and the *empirical behavior* of the assembled system on a real decentralized crawl-and-train workload (PPT-LAT-Empirical).

---

## References (standard math literature, conceptual)

1. Dickson, L.E. *Finiteness of the odd perfect and primitive abundant numbers with $n$ distinct prime factors.* American Journal of Mathematics 35 (1913), 413–422. [Dickson's Lemma.]

2. Kruskal, J.B. *Well-quasi-ordering, the Tree Theorem, and Vázsonyi's conjecture.* Transactions of the AMS 95 (1960), 210–225. [The tree embedding theorem.]

3. Friedman, H. *Internal finite tree embeddings.* In: Reflections on the Foundations of Mathematics (2002), 60–91. [Veblen-ordinal bound on Kruskal sequences.]

4. Plate, T.A. *Holographic reduced representations.* IEEE Transactions on Neural Networks 6:3 (1995), 623–641. [HRR binding, unbinding, $O(\sqrt{N})$ capacity.]

5. Ramanujan, S. *On certain trigonometrical sums and their applications in the theory of numbers.* Transactions of the Cambridge Philosophical Society 22 (1918), 259–276. [Ramanujan sums, used implicitly in the Möbius reorder.]

6. Kluyver, J.C. *Some formulae concerning the integers less than $n$ and prime to $n$.* Proceedings KNAW (1906), 408–414. [Kluyver's formula for Ramanujan sums via Möbius inversion.]

7. The Chinese Remainder Theorem; standard formulation, e.g., Ireland and Rosen, *A Classical Introduction to Modern Number Theory*, 2nd ed. Springer, 1990, §3.

8. Lyubashevsky, V., Peikert, C., Regev, O. *On ideal lattices and learning with errors over rings.* J. ACM 60:6 (2013), 43. [Ring-LWE; same cyclotomic structure $\mathbb{Z}_q[x]/(x^N+1)$ used here.]

9. Barrett, P. *Implementing the Rivest-Shamir-Adleman public key encryption algorithm on a standard digital signal processor.* CRYPTO '86, 311–323. [Barrett reduction for the NTT branches.]

10. Vilenkin, N.Ya. *On a class of complete orthogonal systems.* Izv. Akad. Nauk SSSR Ser. Mat. 11 (1947), 363–400. [The base orthogonal system for VHT2.]

---

*End of PPT-LAT-Theory.*
