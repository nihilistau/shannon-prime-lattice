#!/usr/bin/env python3
"""
G-PONCELET-CORR — the kill-test for the "Euler/Poncelet confidence oracle".

CLAIM UNDER TEST (from the June DSpark thread): a drafted token's acceptance can be
predicted by mapping its hidden state to a point on the CM elliptic curve E/O_K and
testing closure via Euler's criterion (the Legendre symbol of rhs = x^3+Ax+B mod q1).

PRE-REGISTERED PREDICTION: the verdict is a ~50/50 coin, statistically INDEPENDENT of
byte-exact acceptance (phi ~= 0). If so, the oracle is dead on arrival and is filed as
an honest negative (same shelf as the nine refuted B3 recall signals, STATE sec 4).

WHY THIS IS A FAIR (NON-CIRCULAR) TEST: the synthetic mode does NOT assume independence.
It derives the integer residue x DETERMINISTICALLY from the same latent signal s that
drives acceptance (x = quantize(s)). So if the Legendre test carried ANY acceptance
information, phi would be nonzero. It is not: QR-ness of quantize(s) is uncorrelated with
s, because the Legendre symbol is a number-theoretic property that the projection scrambles.

MODES
  (default) synthetic pre-demonstration  -- runnable with no engine, gives the receipt now.
  --live <jsonl>  -- the real gate. Each line: {"residue": <int>, "accepted": 0|1}
                     emitted by the engine during spec_step (residue = the int the oracle
                     would score for that drafted position; accepted = byte-exact argmax match).

This is dependency-free (no numpy/scipy).
Gate: G-PONCELET-CORR.  Repro:  python g_poncelet_corr.py        (synthetic)
                                python g_poncelet_corr.py --live draft_log.jsonl
"""
import argparse, json, math, random, sys

Q1 = 1073738753  # frozen Shannon-Prime CRT prime (Theory sec 2.3)


def legendre(a, p):
    """1 if a is a quadratic residue mod p, p-1 if non-residue, 0 if a==0 mod p."""
    a %= p
    if a == 0:
        return 0
    return pow(a, (p - 1) // 2, p)


def oracle_verdict(x, A, B, q=Q1):
    """Exactly the thread's oracle: rhs = x^3 + A x + B mod q; accept iff Legendre(rhs)==1."""
    x %= q
    rhs = (x * x % q * x % q + A * x % q + B) % q
    return 1 if legendre(rhs, q) == 1 else 0


def phi_and_chi2(table):
    """2x2 contingency [[n00,n01],[n10,n11]] -> (phi coefficient, chi-square)."""
    n00, n01 = table[0]
    n10, n11 = table[1]
    n = n00 + n01 + n10 + n11
    if n == 0:
        return 0.0, 0.0
    num = (n11 * n00 - n10 * n01)
    den = (n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)
    phi = num / math.sqrt(den) if den > 0 else 0.0
    chi2 = n * (phi ** 2)  # for a 2x2 table, chi^2 = N * phi^2
    return phi, chi2


def contingency(verdicts, accepts):
    t = [[0, 0], [0, 0]]
    for v, a in zip(verdicts, accepts):
        t[v][a] += 1
    return t


def report(verdicts, accepts, label, ab):
    n = len(verdicts)
    qr = sum(verdicts) / n
    acc = sum(accepts) / n
    table = contingency(verdicts, accepts)
    phi, chi2 = phi_and_chi2(table)
    # chi^2 with 1 dof: 3.841 = p<0.05 critical value
    sig = "SIGNIFICANT (oracle carries info!)" if chi2 > 3.841 else "not significant (independent)"
    print(f"\n[{label}]  N={n}  curve(A,B)={ab}")
    print(f"  QR / 'on-manifold' rate : {qr:.4f}   (predicted ~0.5 = a coin)")
    print(f"  byte-exact accept rate  : {acc:.4f}")
    print(f"  contingency [v][a]      : {table}")
    print(f"  phi coefficient         : {phi:+.4f}   (predicted ~0.0)")
    print(f"  chi^2 (1 dof)           : {chi2:.3f}   -> {sig}")
    return {"label": label, "N": n, "qr_rate": qr, "accept_rate": acc,
            "phi": phi, "chi2": chi2, "table": table, "AB": ab, "significant": chi2 > 3.841}


def synthetic(n, seed=20260628):
    rng = random.Random(seed)
    SCALE = 1_000_003  # quantization gain mimicking a hidden-state -> integer projection
    Z = 0.52           # threshold -> base accept rate ~0.30 (illustrative; result is robust to it)
    s_list, acc_list, res_list = [], [], []
    for _ in range(n):
        s = rng.gauss(0.0, 1.0)          # the TRUE latent that drives acceptance
        accepted = 1 if s > Z else 0      # a real, graded acceptance signal
        x = int(round(s * SCALE)) % Q1    # residue DERIVED from the same s (the fair part)
        s_list.append(s); acc_list.append(accepted); res_list.append(x)
    results = []
    # robustness: several curve params -- the verdict must be a coin for all of them.
    for ab in [(1, 1), (7, 13), (486662, 1), (0, 7)]:
        verdicts = [oracle_verdict(x, ab[0], ab[1]) for x in res_list]
        results.append(report(verdicts, acc_list, f"synthetic A={ab[0]} B={ab[1]}", ab))
    # also: does the verdict track the CONTINUOUS latent at all? (point-biserial-ish)
    v0 = [oracle_verdict(x, 1, 1) for x in res_list]
    m1 = sum(s for s, v in zip(s_list, v0) if v == 1) / max(1, sum(v0))
    m0 = sum(s for s, v in zip(s_list, v0) if v == 0) / max(1, len(v0) - sum(v0))
    print(f"\n  mean latent | verdict=1 : {m1:+.4f}")
    print(f"  mean latent | verdict=0 : {m0:+.4f}   (predicted ~equal => verdict ignores the signal)")
    return results


def live(path):
    verdicts, accepts = [], []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            verdicts.append(oracle_verdict(int(r["residue"]), r.get("A", 1), r.get("B", 1)))
            accepts.append(int(r["accepted"]))
    if not verdicts:
        print("no records in live log"); return [], False
    return [report(verdicts, accepts, "LIVE (engine spec_step)", (1, 1))], True


def verdict_line(results):
    # GREEN = kill confirmed (oracle is a coin: |phi| small AND not significant for all rows)
    killed = all(abs(r["phi"]) < 0.03 and not r["significant"] for r in results)
    print("\n" + "=" * 64)
    if killed:
        print("G-PONCELET-CORR: VERDICT = GREEN (oracle KILLED).")
        print("  rho ~= 0 across all curves -> the Euler/Legendre test carries no")
        print("  acceptance information. File as honest negative; use byte-exact")
        print("  verify (T8) for correctness and a learned head (B3-WC) for scheduling.")
    else:
        print("G-PONCELET-CORR: VERDICT = RED (oracle shows correlation -- investigate).")
    print("=" * 64)
    return killed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", metavar="JSONL", help="engine draft-token log; runs the real gate")
    ap.add_argument("-n", type=int, default=20000, help="synthetic sample size")
    args = ap.parse_args()
    print("G-PONCELET-CORR -- killing the Euler/Poncelet confidence oracle")
    print(f"q1 = {Q1}  (frozen);  Legendre accept iff rhs^((q1-1)/2) == 1")
    if args.live:
        results, ok = live(args.live)
        if not ok:
            return 2
    else:
        print("MODE: synthetic pre-demonstration (residue derived from the true accept signal)")
        results = synthetic(args.n)
    killed = verdict_line(results)
    return 0 if killed else 1


if __name__ == "__main__":
    sys.exit(main())
