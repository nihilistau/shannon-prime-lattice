#!/usr/bin/env python3
"""okf_mem.py - the content-addressed tiered memory tool (MEM-OKF).

One format, two callers:
  * AGENT working memory  - text concepts, addressed by sha256(body)[:16].
  * XBAR/NIGHTSHIFT episodes - latent episodes, addressed by their C2 256-bit
    LSH signature (passed in as --addr); the "full" tier is a blob pointer to
    the Ring-2 / Optane payload.

Three disclosure tiers, all OKF concepts, all linked by the address:
  Tier-0  LUT.md        one row/object: addr | kind | keys | one-line summary | status | ->sum
  Tier-1  sum/<addr>.md the distilled, in-context summary (points down: mem_full)
  Tier-2  full/<addr>.md the complete context (text) OR a blob pointer (episode)

The address is the join key to the PoUW receipt ledger (every write receipted by
hash). Content-addressing gives free dedup + an auditable integrity gate
(G-MEM-OKF-CONFORM via `verify`). No third-party deps.
"""
import argparse, hashlib, os, re, sys, datetime

LUT_NAME = "LUT.md"
SUM_DIR  = "sum"
FULL_DIR = "full"
LUT_HEADER = ("| addr | kind | keys | summary | status | sum |\n"
              "|---|---|---|---|---|---|\n")

# MEM-OKF v2 policy vocabulary (see PPT-LAT-MEM-OKF-V2-SPEC + ADR-004).
MEM_CLASSES    = {"private-secret", "counterfact", "same-template", "fact",
                  "preference", "persona", "episodic-event"}
MEM_DELIVERIES = {"attr-gate-strict", "systemecho", "two-stage", "recite",
                  "system", "pass"}  # "route:<t>" also allowed (checked by prefix)
MEM_DECLINES   = {"attribute-absent", "family-ambiguous", "low-margin", "zero-inference"}
# class -> default delivery (the proven mapping; per-entry field overrides).
CLASS_DEFAULT_DELIVERY = {
    "private-secret": "attr-gate-strict", "counterfact": "systemecho",
    "same-template": "systemecho",  # two-stage REFUTED (G-MEMPOLICY-V3); delivery is perfect
    "fact": "recite", "preference": "system",  # given selection, so use systemecho + low-confidence
    "persona": "system", "episodic-event": "recite"}

def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def norm(body):
    return body.replace("\r\n", "\n").strip() + "\n"

def addr_of(body):
    return hashlib.sha256(norm(body).encode("utf-8")).hexdigest()[:16]

def fm_block(d):
    out = ["---"]
    for k, v in d.items():
        if isinstance(v, list):
            out.append(k + ": [" + ", ".join(str(x) for x in v) + "]")
        else:
            out.append(k + ": " + str(v))
    out.append("---")
    return "\n".join(out) + "\n"

def parse_fm(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, m.group(2)

def ensure_root(root):
    os.makedirs(os.path.join(root, SUM_DIR), exist_ok=True)
    os.makedirs(os.path.join(root, FULL_DIR), exist_ok=True)
    lut = os.path.join(root, LUT_NAME)
    if not os.path.exists(lut):
        with open(lut, "w", encoding="utf-8") as f:
            f.write(fm_block({
                "type": "index", "title": "MEM-OKF LUT (Tier-0, always-loadable)",
                "description": "Keyword -> one-line agent-readable summary -> content address; follow addr to sum/ then full/.",
                "tags": ["mem-okf", "lut", "tier-0", "index"], "timestamp": now_iso(),
                "resource": "tools/okf_mem.py", "sp_status": "ACTIVE",
                "sp_gate": "G-MEM-OKF-CONFORM", "sp_commit": "TBD",
                "sp_repro": "python tools/okf_mem.py verify --root <root>"}))
            f.write("\n# MEM-OKF LUT\n\nLookup before you build. `python tools/okf_mem.py lookup --root <root> <kw>`\n\n")
            f.write(LUT_HEADER)
    idx = os.path.join(root, "index.md")
    if not os.path.exists(idx):
        with open(idx, "w", encoding="utf-8") as f:
            f.write(fm_block({
                "type": "index", "title": "MEM-OKF bundle index",
                "description": "Content-addressed tiered memory. Tier-0 LUT.md, Tier-1 sum/, Tier-2 full/.",
                "tags": ["mem-okf", "index"], "timestamp": now_iso(),
                "resource": "papers/MEMORY-OKF-PROFILE.md", "sp_status": "ACTIVE",
                "sp_gate": "G-MEM-OKF-CONFORM", "sp_commit": "TBD",
                "sp_repro": "python tools/okf_mem.py verify --root <root>"}))
            f.write("\n# MEM-OKF bundle\n\nSee [MEMORY-OKF-PROFILE](../papers/MEMORY-OKF-PROFILE.md). Start at [LUT.md](LUT.md).\n")

def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def lut_rows(root):
    txt = read(os.path.join(root, LUT_NAME))
    rows = []
    for line in txt.split("\n"):
        if line.startswith("|") and not line.startswith("| addr") and not line.startswith("|---"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 6:
                rows.append(cells)
    return rows

def write_lut(root, rows):
    txt = read(os.path.join(root, LUT_NAME))
    head = txt.split(LUT_HEADER)[0]
    body = "".join("| " + " | ".join(r) + " |\n" for r in rows)
    write(os.path.join(root, LUT_NAME), head + LUT_HEADER + body)

def cmd_add(a):
    ensure_root(a.root)
    if a.full_file:
        full_body = read(a.full_file)
    elif a.blob_ref:
        full_body = ("BLOB POINTER (Tier-2 = external payload)\n\nblob: " + a.blob_ref +
                     "\nkind: " + a.kind + "\nFull context is the latent/binary payload at the blob path "
                     "(Ring-2 / Optane). Address = C2 LSH signature / provided id.\n")
    elif not sys.stdin.isatty():
        full_body = sys.stdin.read()
    else:
        print("add: need --full-file, --blob-ref, or piped stdin", file=sys.stderr)
        return 2
    addr = a.addr if a.addr else addr_of(full_body)
    common = {"type": "memory", "title": a.title or a.summary[:60], "description": a.summary,
              "timestamp": now_iso(), "resource": a.commit or "TBD", "sp_status": a.status,
              "sp_gate": a.gate, "sp_commit": a.commit or "TBD", "sp_repro": a.repro or "none",
              "mem_kind": a.kind, "mem_addr": addr}
    # MEM-OKF v2 policy block (additive; OKF-permitted producer keys).
    if a.mem_class:
        delivery = a.delivery or CLASS_DEFAULT_DELIVERY.get(a.mem_class, "recite")
        common["mem_class"] = a.mem_class
        common["mem_delivery"] = delivery
        common["mem_authority"] = a.authority or (
            "private" if a.mem_class == "private-secret"
            else "overrides-prior" if a.mem_class in ("counterfact", "same-template")
            else "supplements")
        if a.retrieval_key:
            common["mem_retrieval_key"] = a.retrieval_key
        elif a.mem_class == "private-secret":
            common["mem_retrieval_key"] = "exact-token"
        # class-default decline: a private-secret is zero-inference-safe by construction.
        decl = a.decline_when or ("zero-inference,attribute-absent" if a.mem_class == "private-secret" else "")
        if decl:
            common["mem_decline_when"] = decl
            common["mem_decline_message"] = a.decline_message or "I have a record for that entity, but it does not include that specific detail."
        if a.confidence is not None:
            common["mem_confidence"] = a.confidence
    full_fm = dict(common); full_fm["tags"] = a.keys.split(",") + [a.kind, "tier-2"]; full_fm["mem_tier"] = "full"
    write(os.path.join(a.root, FULL_DIR, addr + ".md"), fm_block(full_fm) + "\n" + norm(full_body))
    detail = a.detail if a.detail else (read(a.detail_file) if a.detail_file else a.summary)
    sum_fm = dict(common); sum_fm["tags"] = a.keys.split(",") + [a.kind, "tier-1"]
    sum_fm["mem_tier"] = "summary"; sum_fm["mem_full"] = addr
    write(os.path.join(a.root, SUM_DIR, addr + ".md"),
          fm_block(sum_fm) + "\n# " + (a.title or a.summary) + "\n\n" + norm(detail) +
          "\nFull context: [full/" + addr + ".md](../full/" + addr + ".md)\n")
    rows = [r for r in lut_rows(a.root) if r[0] != addr]
    # v2: surface the policy hint at Tier-0 (progressive disclosure of policy, not just content)
    summ = a.summary.replace("|", "/").strip()
    if a.mem_class:
        summ = "[" + a.mem_class + "/" + common["mem_delivery"] + "] " + summ
    rows.append([addr, a.kind, a.keys.replace("|", "/").strip(), summ,
                 a.status, "sum/" + addr + ".md"])
    write_lut(a.root, rows)
    print("added " + addr + "  [" + a.kind + "/" + a.status + "]  " + a.summary)
    return 0

def cmd_lookup(a):
    q = a.query.lower()
    hits = [r for r in lut_rows(a.root) if q in r[2].lower() or q in r[3].lower()]
    if not hits:
        print("(no LUT match for '" + a.query + "')"); return 0
    for r in hits:
        print(r[0] + "  [" + r[1] + "/" + r[4] + "]  " + r[3] + "\n        keys: " + r[2] + "  -> expand " + r[0])
    return 0

def cmd_expand(a):
    sub = FULL_DIR if a.full else SUM_DIR
    p = os.path.join(a.root, sub, a.addr + ".md")
    if not os.path.exists(p):
        print("(no " + sub + "/" + a.addr + ".md)", file=sys.stderr); return 2
    sys.stdout.write(read(p)); return 0

def cmd_verify(a):
    errs, warns, n = [], [], 0
    fulls, sums = set(), set()
    fd = os.path.join(a.root, FULL_DIR)
    if os.path.isdir(fd):
        for fn in os.listdir(fd):
            if not fn.endswith(".md"): continue
            addr = fn[:-3]; fulls.add(addr); n += 1
            fm, body = parse_fm(read(os.path.join(fd, fn)))
            if fm.get("mem_addr") != addr:
                errs.append("full/" + fn + ": mem_addr " + str(fm.get("mem_addr")) + " != " + addr)
            if fm.get("mem_kind") == "agent" and addr_of(body) != addr:
                errs.append("full/" + fn + ": sha256(body)[:16]=" + addr_of(body) + " != " + addr + " (text tampered)")
            # ---- MEM-OKF v2 policy conformance (only for policied entries) ----
            mc = fm.get("mem_class")
            if mc:
                if mc not in MEM_CLASSES:
                    errs.append("full/" + fn + ": mem_class '" + str(mc) + "' not in vocab")
                dv = fm.get("mem_delivery", "")
                if dv and dv not in MEM_DELIVERIES and not dv.startswith("route:"):
                    errs.append("full/" + fn + ": mem_delivery '" + dv + "' not in vocab")
                # safety monotonicity: a secret must never carry a leaky delivery.
                if mc == "private-secret" and dv not in ("attr-gate-strict",):
                    errs.append("full/" + fn + ": private-secret with unsafe delivery '" + dv + "' (must be attr-gate-strict)")
                dw = fm.get("mem_decline_when", "")
                if mc == "private-secret" and "zero-inference" not in dw:
                    errs.append("full/" + fn + ": private-secret missing zero-inference decline")
                if dw:
                    for w in [x.strip() for x in dw.strip("[]").split(",") if x.strip()]:
                        if w not in MEM_DECLINES:
                            errs.append("full/" + fn + ": decline-when '" + w + "' not in vocab")
                    if not fm.get("mem_decline_message"):
                        warns.append("full/" + fn + ": decline-when set but no decline-message")
    sd = os.path.join(a.root, SUM_DIR)
    if os.path.isdir(sd):
        for fn in os.listdir(sd):
            if not fn.endswith(".md"): continue
            addr = fn[:-3]; sums.add(addr)
            fm, _ = parse_fm(read(os.path.join(sd, fn)))
            if fm.get("mem_full") not in fulls:
                errs.append("sum/" + fn + ": mem_full " + str(fm.get("mem_full")) + " unresolved")
    lut_addrs = {r[0] for r in lut_rows(a.root)}
    for r in lut_rows(a.root):
        if r[0] not in fulls: errs.append("LUT " + r[0] + ": no full/")
        if r[0] not in sums:  errs.append("LUT " + r[0] + ": no sum/")
        if not r[2] or not r[3]: errs.append("LUT " + r[0] + ": empty keys/summary")
    for addr in (fulls | sums) - lut_addrs:
        warns.append("orphan " + addr + " (not in LUT)")
    for w in warns: print("  warn:", w)
    for e in errs:  print("  ERROR:", e)
    verdict = "GREEN" if not errs else "RED"
    print("---- G-MEM-OKF-CONFORM: " + str(n) + " objects | " + str(len(errs)) + " errors | " + str(len(warns)) + " warnings ----")
    print("VERDICT: " + verdict)
    return 0 if not errs else 1

def main():
    ap = argparse.ArgumentParser(description="MEM-OKF content-addressed tiered memory")
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--root", default=os.environ.get("MEM_OKF_ROOT", "memory-okf"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add", parents=[parent]); p.set_defaults(fn=cmd_add)
    p.add_argument("--kind", default="agent", choices=["agent", "episode"])
    p.add_argument("--keys", required=True); p.add_argument("--summary", required=True)
    p.add_argument("--title"); p.add_argument("--detail"); p.add_argument("--detail-file")
    p.add_argument("--full-file"); p.add_argument("--blob-ref"); p.add_argument("--addr")
    p.add_argument("--status", default="ACTIVE"); p.add_argument("--gate", default="none")
    p.add_argument("--commit"); p.add_argument("--repro")
    # MEM-OKF v2 policy block
    p.add_argument("--mem-class", dest="mem_class", choices=sorted(MEM_CLASSES),
                   help="v2: sets the default retrieval/delivery/decline policy")
    p.add_argument("--delivery", help="v2: override delivery (systemecho|attr-gate-strict|two-stage|recite|system|route:<t>)")
    p.add_argument("--authority", help="v2: overrides-prior|supplements|private")
    p.add_argument("--retrieval-key", dest="retrieval_key", help="v2: l5-question|exact-token|c2-sig")
    p.add_argument("--decline-when", dest="decline_when", help="v2: comma list (attribute-absent,family-ambiguous,low-margin,zero-inference)")
    p.add_argument("--decline-message", dest="decline_message", help="v2: fixed decline string")
    p.add_argument("--confidence", type=float, default=None)
    p = sub.add_parser("lookup", parents=[parent]); p.set_defaults(fn=cmd_lookup); p.add_argument("query")
    p = sub.add_parser("expand", parents=[parent]); p.set_defaults(fn=cmd_expand)
    p.add_argument("addr"); p.add_argument("--full", action="store_true")
    p = sub.add_parser("verify", parents=[parent]); p.set_defaults(fn=cmd_verify)
    a = ap.parse_args(); sys.exit(a.fn(a))

if __name__ == "__main__":
    main()
