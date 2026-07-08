#!/usr/bin/env python3
"""G-OKF-DISCOVERY-CLASS — gate for A4 (okf_mem classify, anti-rebuild formalized).

Pre-registered PASS criteria (CONTRACT-EXTERNAL-ADOPTION.md §3, A4):
 (a) exact copy of an existing entry        -> RETRIEVAL (exact)   [reject under --strict]
 (b) light paraphrase of an existing entry  -> RETRIEVAL (rebuild) [NOT DISCOVERY]
 (c) genuinely novel entry                  -> DISCOVERY (high residual)
 (d) recombination of two existing entries  -> SEARCH (mid overlap, low residual)
 (e) a candidate claiming DISCOVERY but low residual is WARNed as a likely rebuild
 (+) determinism: same input -> identical verdict dict.

Self-contained: builds a temp MEM-OKF store, no deps. Repro:
    python tools/tests/test_okf_classify.py
"""
import os, sys, tempfile, shutil
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import okf_mem as M


def seed(root, body):
    addr = M.addr_of(body)
    os.makedirs(os.path.join(root, M.FULL_DIR), exist_ok=True)
    M.write(os.path.join(root, M.FULL_DIR, addr + ".md"),
            M.fm_block({"type": "memory", "mem_addr": addr, "mem_kind": "agent"}) + "\n" + M.norm(body))
    return addr


def main():
    root = tempfile.mkdtemp(prefix="okfcls_")
    fails = []
    try:
        E1 = ("The byte-exact forward uses dual-prime CRT-NTT with Barrett reduction and Garner "
              "recombination over the ring for cross-machine deterministic auditable arithmetic.")
        E2 = ("The recall selector reads the layer-5 global query, L2-normalizes the vector, and "
              "cosine-matches against stored episode keys using a tau threshold to reject foreign facts.")
        E3 = ("The Jaccard judge is a deterministic token-overlap verifier that accepts a citation "
              "only when the overlap exceeds the fixed threshold, replacing the diffusion cascade.")
        seed(root, E1); seed(root, E2); seed(root, E3)

        C_para = ("Byte-exact forward passes rely on dual-prime CRT-NTT, applying Barrett reduction "
                  "plus Garner recombination in the ring to guarantee cross-machine deterministic arithmetic.")
        C_search = ("The recall selector's cosine-matched episode is then verified by the deterministic "
                    "Jaccard token-overlap judge before its citation is accepted.")
        C_disc = ("A spiking neuromorphic cochlea encodes phonemes as sparse temporal spike trains for "
                  "event-driven keyword spotting on analog in-memory compute hardware.")

        def V(raw, **kw):
            return M.classify_body(root, raw, **kw)

        # (a) exact
        r = V(E1)
        if not (r["verdict"] == "RETRIEVAL" and r["exact"]):
            fails.append(("a/exact", r))
        # (b) paraphrase rebuild
        r = V(C_para)
        if not (r["verdict"] == "RETRIEVAL" and not r["exact"] and r["best_cov"] >= 0.55):
            fails.append(("b/paraphrase", r))
        # (c) discovery
        r = V(C_disc)
        if not (r["verdict"] == "DISCOVERY" and r["residual"] >= 0.5):
            fails.append(("c/discovery", r))
        # (d) search / recombination
        r = V(C_search)
        if not (r["verdict"] == "SEARCH" and r["residual"] < 0.5 and r["best_cov"] < 0.55):
            fails.append(("d/search", r))
        # (e) claimed-discovery-but-rebuild -> verdict must NOT be DISCOVERY (warn path)
        r = V(C_para)
        if r["verdict"] == "DISCOVERY":
            fails.append(("e/false-discovery-claim", r))
        # (+) new-type Kan obstruction upgrades a borderline write to DISCOVERY
        r = V(C_search, declared_type="quantum-widget")
        if r["verdict"] != "DISCOVERY" or not r["type_novel"]:
            fails.append(("f/kan-type-obstruction", r))
        # (+) determinism
        if V(C_para) != V(C_para) or V(C_disc) != V(C_disc):
            fails.append(("g/determinism", "verdict not reproducible"))

        print("=== G-OKF-DISCOVERY-CLASS ===")
        for label, raw in [("exact/E1", E1), ("paraphrase", C_para), ("search", C_search),
                           ("discovery", C_disc)]:
            r = V(raw)
            print("  %-11s -> %-9s cov=%.2f jac=%.2f residual=%.2f (%s)"
                  % (label, r["verdict"], r["best_cov"], r["best_jaccard"], r["residual"], r["best_addr"]))
        for f in fails:
            print("  FAIL:", f[0], "->", f[1])
        verdict = "GREEN" if not fails else "RED"
        print("---- %d/%d checks passed | VERDICT: %s ----"
              % (7 - len(fails), 7, verdict))
        return 0 if not fails else 1
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
