#!/usr/bin/env python3
"""okf_frontmatter_pia.py -- idempotent SP-OKF frontmatter prepender for the PUBLIC
Position_Is_Arithmetic repo (papers/ + posts/ bundles). Purely additive: prepends a YAML
frontmatter block to every targeted *.md that does NOT already start with '---'. Never alters
existing body content. Spec: shannon-prime-lattice/papers/SP-OKF-PROFILE.md.

Type derivation (per SP-OKF vocabulary §2), by location/basename:
  papers/NN-*/paper.md          -> paper-bite     (the digestible "Papers series" note)
  papers/NN-*/README.md         -> paper-bite     (companion summary of the same bite)
  papers/NN-*/receipts.md       -> gate-receipt   (ledger-slice of proven results)
  papers/NN-*/repro/*.md        -> gate-receipt   (reproduction receipts: EXPECTED/README)
  posts/*.md                    -> log            (chronological field notes / updates)

title  <- first '# ' heading (fallback: filename stem)
description <- first prose sentence (fallback: title)
timestamp <- file mtime (UTC)
SP fields default receipts-first: sp_status ACTIVE, sp_gate none, sp_commit TBD, sp_repro none.

Writes LF line endings (the repo's HEAD convention) for the whole file, so a stray CRLF copy on
disk is normalised back toward HEAD while the body bytes are otherwise untouched.

Usage: python okf_frontmatter_pia.py <Position_Is_Arithmetic-root> [--dry-run]
"""
import os, re, sys, datetime

def derive_type(relpath):
    parts = relpath.replace("\\", "/").split("/")
    top = parts[0]
    base = parts[-1]
    if top == "posts":
        return "log"
    if top == "papers":
        if "repro" in parts:
            return "gate-receipt"
        if base == "receipts.md":
            return "gate-receipt"
        # paper.md and README.md (the bite + its companion summary)
        return "paper-bite"
    # not a target bundle
    return None

KEYWORDS = ["xbar", "kairos", "gemma4", "gemma3", "byteexact", "byte-exact", "ntt", "crt",
            "spinor", "arm", "frobenius", "frob", "ring3", "vsa", "memo", "curator", "kv",
            "recall", "librarian", "ablation", "organism", "dp4a", "oracle", "daemon",
            "two-ring", "memory", "compression", "determinism", "exact-integer"]

def derive_tags(relpath, typ):
    low = relpath.lower()
    tags = [typ]
    for kw in KEYWORDS:
        if kw in low and kw not in tags:
            tags.append(kw)
    return tags[:6]

def first_heading(lines):
    for ln in lines:
        s = ln.strip()
        if s.startswith("# "):
            return s[2:].strip()
    return None

def first_prose(lines):
    in_code = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not s or s.startswith("#") or s.startswith("|") or s.startswith(">") \
                or s.startswith("- ") or s.startswith("* ") or s.startswith("---"):
            continue
        txt = re.sub(r"\s+", " ", s)
        txt = txt.replace("**", "").replace("`", "").replace("*", "")
        m = re.search(r"^(.{20,200}?[.!?])(\s|$)", txt)
        cand = m.group(1) if m else txt[:200]
        return cand.strip()
    return None

def yaml_escape(s):
    if any(c in s for c in [":", "#", "\"", "'", "[", "]", "{", "}", ",", "&", "*"]) or s != s.strip():
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print("usage: okf_frontmatter_pia.py <Position_Is_Arithmetic-root> [--dry-run]")
        return 2
    root = args[0]
    dry = "--dry-run" in flags
    done = skipped = nontarget = 0
    targets = []
    for dp, _, fns in os.walk(root):
        if "/.git" in dp.replace(os.sep, "/") or "\\.git" in dp:
            continue
        for fn in fns:
            if fn.endswith(".md"):
                targets.append(os.path.join(dp, fn))
    targets.sort()
    for path in targets:
        rel = os.path.relpath(path, root)
        typ = derive_type(rel)
        if typ is None:
            nontarget += 1
            continue
        raw = open(path, encoding="utf-8").read()
        if raw.startswith("---"):
            skipped += 1
            continue
        # normalise to LF for the whole file (repo HEAD convention); body bytes otherwise intact
        body = raw.replace("\r\n", "\n").replace("\r", "\n")
        lines = body.splitlines()
        title = first_heading(lines) or os.path.basename(path)[:-3]
        desc = first_prose(lines) or title
        if len(desc) > 200:
            desc = desc[:197].rstrip() + "..."
        tags = derive_tags(rel, typ)
        mtime = os.path.getmtime(path)
        ts = datetime.datetime.utcfromtimestamp(mtime).strftime("%Y-%m-%dT%H:%M:%SZ")
        relres = "./" + rel.replace(os.sep, "/")
        fm = []
        fm.append("---")
        fm.append(f"type: {typ}")
        fm.append(f"title: {yaml_escape(title)}")
        fm.append(f"description: {yaml_escape(desc)}")
        fm.append("tags: [" + ", ".join(tags) + "]")
        fm.append(f"timestamp: {ts}")
        fm.append(f"resource: {relres}")
        fm.append("sp_status: ACTIVE")
        fm.append("sp_gate: none")
        fm.append("sp_commit: TBD")
        fm.append("sp_repro: none")
        fm.append("---")
        fm.append("")
        block = "\n".join(fm) + "\n"
        if dry:
            print(f"[DRY {typ:13s}] {rel}")
        else:
            open(path, "w", encoding="utf-8", newline="").write(block + body)
            print(f"[frontmattered {typ:13s}] {rel}")
        done += 1
    print(f"---- {'would prepend' if dry else 'prepended'} {done} | skipped {skipped} (had fm) | non-target {nontarget} ----")
    return 0

if __name__ == "__main__":
    sys.exit(main())
