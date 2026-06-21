#!/usr/bin/env python3
"""okf_frontmatter_targets.py -- idempotent SP-OKF frontmatter prepender driven by an EXPLICIT
{relative-path: type} map, for the lighter pass over the lattice/engine/system repos' genuine
knowledge docs (top-level + docs/). Purely additive: prepend YAML frontmatter to a targeted *.md
only if it does NOT already start with '---'. Body bytes untouched (normalised to LF).
Spec: shannon-prime-lattice/papers/SP-OKF-PROFILE.md.

Usage: python okf_frontmatter_targets.py <repo-root> <map.tsv> [--dry-run]
  map.tsv: lines of "<relpath>\t<type>" ; '#'-comment lines ignored.
"""
import os, re, sys, datetime

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
            in_code = not in_code; continue
        if in_code: continue
        if not s or s.startswith(("#", "|", ">", "- ", "* ", "---")):
            continue
        txt = re.sub(r"\s+", " ", s).replace("**", "").replace("`", "").replace("*", "")
        m = re.search(r"^(.{20,200}?[.!?])(\s|$)", txt)
        return (m.group(1) if m else txt[:200]).strip()
    return None

def yesc(s):
    if any(c in s for c in [":", "#", "\"", "'", "[", "]", "{", "}", ",", "&", "*"]) or s != s.strip():
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv[1:]
    if len(args) < 2:
        print("usage: okf_frontmatter_targets.py <repo-root> <map.tsv> [--dry-run]"); return 2
    root, mapf = args[0], args[1]
    pairs = []
    for ln in open(mapf, encoding="utf-8"):
        ln = ln.rstrip("\n")
        if not ln.strip() or ln.lstrip().startswith("#"): continue
        rel, typ = ln.split("\t")
        pairs.append((rel.strip(), typ.strip()))
    done = skipped = missing = 0
    for rel, typ in pairs:
        path = os.path.join(root, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            print(f"[MISSING] {rel}"); missing += 1; continue
        raw = open(path, encoding="utf-8").read()
        if raw.startswith("---"):
            print(f"[skip had-fm] {rel}"); skipped += 1; continue
        body = raw.replace("\r\n", "\n").replace("\r", "\n")
        lines = body.splitlines()
        title = first_heading(lines) or os.path.basename(path)[:-3]
        desc = first_prose(lines) or title
        if len(desc) > 200: desc = desc[:197].rstrip() + "..."
        mtime = os.path.getmtime(path)
        ts = datetime.datetime.utcfromtimestamp(mtime).strftime("%Y-%m-%dT%H:%M:%SZ")
        fm = ["---", f"type: {typ}", f"title: {yesc(title)}", f"description: {yesc(desc)}",
              f"tags: [{typ}]", f"timestamp: {ts}", f"resource: ./{rel}",
              "sp_status: ACTIVE", "sp_gate: none", "sp_commit: TBD", "sp_repro: none", "---", ""]
        block = "\n".join(fm) + "\n"
        if dry:
            print(f"[DRY {typ:15s}] {rel}")
        else:
            open(path, "w", encoding="utf-8", newline="").write(block + body)
            print(f"[frontmattered {typ:15s}] {rel}")
        done += 1
    print(f"---- {'would prepend' if dry else 'prepended'} {done} | skipped {skipped} | missing {missing} ----")
    return 0

if __name__ == "__main__":
    sys.exit(main())
