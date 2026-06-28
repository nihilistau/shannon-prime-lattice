#!/usr/bin/env bash
# G-REGROUND — Stage 0 from-clean regression battery (REBUILD ROADMAP §3 Stage 0).
# Purpose: prove the proven organism still runs GREEN before any extension. CONSOLIDATE before EXTEND.
#
# Two tiers:
#   [HERE]  conformance + the spec-decode kill-test — runnable in any python3 env (run now).
#   [METAL] the GPU/daemon gates — run on the dev box (RTX 2060, CUDA build, native PowerShell per
#           KEYSTONE §10). This script PRINTS those commands; it does not assume your CUDA env.
#
# Usage:  bash run_stage0_battery.sh            (runs [HERE] tier, lists [METAL] tier)
# Gate:   G-REGROUND = every row below GREEN from a clean checkout.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"          # shannon-prime-lattice
REPOS="$(cd "$ROOT/.." && pwd)"                       # D:\F\shannon-prime-repos
pass=0; fail=0
run() { echo "── $1"; if eval "$2" >/tmp/sb.$$ 2>&1; then echo "   GREEN"; pass=$((pass+1)); else echo "   RED (see output)"; tail -8 /tmp/sb.$$; fail=$((fail+1)); fi; }

echo "================ G-REGROUND :: [HERE] tier (conformance) ================"
run "G-OKF-CONFORM (papers bundle)"      "cd '$ROOT' && python3 tools/okf_validate.py papers --quiet"
run "G-MEM-OKF-CONFORM (anti-rebuild store)" "cd '$ROOT' && printf '' | python3 tools/okf_mem.py verify --root memory-okf"
run "G-PONCELET-CORR (kill-test, synthetic)" "cd '$ROOT/staging/specdecode' && python3 g_poncelet_corr.py >/dev/null"
run "G-FOUNDATION-ROUTING (served KV via ABI, not private float)" "cd '$ROOT/staging/foundation-routing' && python3 g_foundation_routing.py >/dev/null"

echo
echo "================ G-REGROUND :: [METAL] tier (run on the dev box) ================"
echo "Run these in the engine/system build env; each must reproduce its STATE/KEYSTONE row."
cat <<'METAL'
  # --- substrate / forward (shannon-prime-system-engine, CUDA build) ---
  ctest -R M_GEMMA4                       # PPT forward bit-exact (gemma-4-12B)
  ctest -R M_QWEN36                       # qwen35moe 256-expert MoE top-1 bit-exact
  # G-BYTEEXACT-FORWARD-12B               # SP_BYTEEXACT off 4.6665 / on 4.6569, run-to-run bit-identical
  # C4 SP_MTP loop:  tests/sp_toks.c SP_MTP=1   (expect 2.67x fewer forwards, bit_identical_to_greedy=1)
  #
  # --- served organism (start daemon, then the harness gates) ---
  _e2e_seed_serve.bat                     # daemon :3000 (eot/auto-recall/forget/decide/nightshift/persist)
  run_agency.bat                          # KAIROS scheduler + consolidation hook
  #   then, in shannon-prime-harness:
  python tests/g_daemon_e2e.py            # H1  daemon inference + SSE
  python tests/g_tool_calling_e2e.py      # H2  ephemeral <tool> calling
  python tests/g_memory_tools_e2e.py      # H3  list/remember/forget
  python tests/g_agency_loop_e2e.py       # H4  forget/decide/merge round
  python tests/g_kairos_tick_e2e.py       # H5  heartbeat (idle-gated)
  python tests/g_conversation_memory_e2e.py # H6  SHORT/MID/LONG tiers
  python tests/g_hook_e2e.py              # H7  post-turn consolidation hook
  # G-CHAT-B3-WC-DEPLOY                    # learned W_c recall + foreign-reject (served chat)
  # G-JUDGE-BATTERY                        # deterministic Jaccard recall/reject gate
METAL
echo
echo "================ also during Stage 0 (not a gate, a deliverable) ================"
echo "  Engine<->core fork-tax inventory: list duplicated forwards/dequant/row_bytes/arch-id enums"
echo "  (RFC-001 §10.6); each item de-duped or ticketed. Make shannon-prime-system the one source."
echo
echo "──────── [HERE] tier: $pass GREEN / $fail RED ────────"
[ "$fail" -eq 0 ] && echo "VERDICT (here-tier): GREEN — now run the [METAL] tier on the dev box." || echo "VERDICT (here-tier): RED"
exit $fail
