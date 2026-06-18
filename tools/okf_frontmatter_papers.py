#!/usr/bin/env python3
"""okf_frontmatter_papers.py -- one-shot, idempotent SP-OKF frontmatter prepender for the
lattice papers/ bundle. Purely additive: prepends a YAML frontmatter block to every *.md that
does NOT already start with '---'. Never alters existing body content. Spec: SP-OKF-PROFILE.md.

Usage: python okf_frontmatter_papers.py <papers-dir>
"""
import os, re, sys, datetime

# headline GREENs we trivially upgrade from ACTIVE (rest stay ACTIVE).
GREEN_FILES = {
    "PPT-LAT-STATE.md", "CONTRACT-BYTEEXACT-forward.md", "PPT-LAT-Roadmap.md",
}

def derive_type(name):
    if name.startswith("CONTRACT-"):
        return "contract"
    if name == "PPT-LAT-Roadmap.md" or name.startswith("ROADMAP-"):
        return "roadmap"
    if name == "PPT-LAT-STATE.md":
        return "project-state"
    if name.startswith("PPT-LAT-L1-ABI-"):
        return "abi"
    if (name.startswith("SESSION-CLOSED-") or name.startswith("SESSION-STATE-")
            or name.startswith("SESSION-PLAN-") or name.startswith("RELEASE-")):
        return "session-handoff"
    if name.startswith("RUNBOOK-"):
        return "runbook"
    # everything else (DESIGN-, RFC-, PPT-LAT-RFC-, MODE_D*, PLAN-, SPEC-, SP-LAT-FRONTENDS,
    # GGUF-INVEST-, PHASE-4-MEMO-, PPT-LAT-Theory, PPT-LAT-Systems*, PPT-LAT-SP-MODEL-*) -> design
    return "design"

KEYWORDS = ["xbar", "kairos", "gemma4", "gemma3", "hexagon", "speed", "byteexact",
            "kai2", "kai3", "ntt", "crt", "spinor", "arm", "qwen", "moe", "vulkan",
            "cuda", "ptx", "hvx", "vtcm", "tokenizer", "diffusion", "pouw", "memo",
            "frob", "ring3", "vsa", "abi", "l1", "l3", "cpu", "gpu", "wire"]

def derive_tags(name, typ):
    low = name.lower()
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
        # take up to the first sentence end or ~200 chars
        txt = re.sub(r"\s+", " ", s)
        # strip markdown emphasis markers lightly
        txt = txt.replace("**", "").replace("`", "")
        m = re.search(r"^(.{20,200}?[.!?])(\s|$)", txt)
        cand = m.group(1) if m else txt[:200]
        return cand.strip()
    return None

def yaml_escape(s):
    # quote if it contains characters that would break a simple scalar
    if any(c in s for c in [":", "#", "\"", "'", "[", "]", "{", "}", ",", "&", "*"]) or s != s.strip():
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s

def main():
    if len(sys.argv) < 2:
        print("usage: okf_frontmatter_papers.py <papers-dir>")
        return 2
    root = sys.argv[1]
    done = skipped = 0
    for name in sorted(os.listdir(root)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        raw = open(path, encoding="utf-8").read()
        if raw.startswith("---"):
            skipped += 1
            continue
        lines = raw.splitlines()
        typ = derive_type(name)
        title = first_heading(lines) or name[:-3]
        desc = first_prose(lines) or title
        if len(desc) > 200:
            desc = desc[:197].rstrip() + "..."
        tags = derive_tags(name, typ)
        mtime = os.path.getmtime(path)
        ts = datetime.datetime.utcfromtimestamp(mtime).strftime("%Y-%m-%dT%H:%M:%SZ")
        status = "GREEN" if name in GREEN_FILES else "ACTIVE"
        fm = []
        fm.append("---")
        fm.append(f"type: {typ}")
        fm.append(f"title: {yaml_escape(title)}")
        fm.append(f"description: {yaml_escape(desc)}")
        fm.append("tags: [" + ", ".join(tags) + "]")
        fm.append(f"timestamp: {ts}")
        fm.append(f"resource: shannon-prime-lattice/papers/{name}")
        fm.append(f"sp_status: {status}")
        fm.append("sp_gate: none")
        fm.append("sp_commit: TBD")
        fm.append("sp_repro: none")
        fm.append("---")
        fm.append("")
        block = "\n".join(fm)
        # preserve original newline style: detect CRLF
        if "\r\n" in raw:
            block = block.replace("\n", "\r\n")
        open(path, "w", encoding="utf-8", newline="").write(block + raw)
        done += 1
        print(f"[frontmattered] {typ:16s} {name}")
    print(f"---- prepended {done} files | skipped {skipped} (already had frontmatter) ----")
    return 0

if __name__ == "__main__":
    sys.exit(main())
