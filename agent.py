"""Loader of the Codex of Weights agent. The code is split into parts/part_*.py files (one per area) that run in order in one shared namespace:
part_01_core (settings, charter, Protocols, models, checks), part_02_memory, part_03_adapters (platforms), part_04_research, part_05_tools_sandbox,
part_06_owner_chat (Telegram, first contact), part_06a_private_lab, part_06b_selfmap, part_06c_bio, part_06d_backup_identity,
part_06e_transparency, part_06f_housekeeping, part_06g_search, part_06h_config (limits, model routing, micro-roles), part_06i_projects (long tasks, research, skills), part_06j_health, part_06k_content, part_07_main_loop (the cycle).
To change one area, edit only its file. The files below are pinned by hash: if any of them differs, the agent does not start.
Only these three are pinned, not every part_*.py (added 2026-11-15, after an external review flagged that
everything past part_01 was log-only, never enforced). They were picked because each one alone can defeat
every other safety check if it is silently changed: part_01_core (the checks themselves - verify/guard_json/
the Codex pin), part_05_tools_sandbox (the only thing standing between a self-written tool and the real
filesystem/network), part_06_owner_chat (LIVE/STOP/approval - what decides whether anything is actually sent).
The rest (adapters, memory, research, projects, ...) change too often for a hand-updated hash to be practical
here, and a change to them cannot bypass these three gates - so they stay log-only, printed into the public
run log so a silent change is still visible after the fact, same as before."""
import os, sys, glob, hashlib
PINNED_SHA256 = {
    "part_01_core.py": "f5d8934cb8b31643f6a1b5df79af04e6ec7c472e18ff0e4194e394d0a43b26dc",
    "part_05_tools_sandbox.py": "0a3d3de9f02b4c26cdb213b6b3ed64bdd21bf50571161fdb37ceaf9315b2773c",
    "part_06_owner_chat.py": "5fab7aed548643cb44afa21cb4a87c5acfc4e25098a47dfdeeca4919438648e8",
}   # update the matching entry here together with a deliberate change of that file
_D = os.path.dirname(os.path.abspath(__file__))
# The code lives in parts/ (one file per area). Files still lying next to agent.py are used only if the same name is not in parts/ (so a half-finished move never breaks a run).
_found = {os.path.basename(f): f for f in glob.glob(os.path.join(_D, "part_*.py"))}
_found.update({os.path.basename(f): f for f in glob.glob(os.path.join(_D, "parts", "part_*.py"))})
def _load_order():      # parts/ORDER.txt is the explicit load order; a part missing from it runs just before the main loop, the alphabetical order is only the fallback
    try: L = [x.strip() for x in open(os.path.join(_D, "parts", "ORDER.txt"), encoding="utf-8").read().splitlines() if x.strip() and not x.strip().startswith("#")]
    except Exception: return sorted(_found)
    L = [x for x in L if x in _found]; extra = sorted(k for k in _found if k not in L); i = L.index("part_07_main_loop.py") if "part_07_main_loop.py" in L else len(L)
    return L[:i] + extra + L[i:]
_parts = [_found[k] for k in _load_order()]
if not _parts: sys.exit("no part_*.py files found (parts/ or next to agent.py) - agent halted")
for _name, _want in PINNED_SHA256.items():
    _p = _found.get(_name)
    if not _p or hashlib.sha256(open(_p, "rb").read()).hexdigest() != _want: sys.exit("%s differs from the pinned hash - agent halted" % _name)
for _f in _parts + [os.path.join(_D, "CHARTER.md"), os.path.join(_D, "FACTS.md")]:      # printed into the public run log: any silent change becomes visible
    try: print("sha256", os.path.basename(_f), hashlib.sha256(open(_f, "rb").read()).hexdigest()[:16], flush=True)
    except Exception: pass
# --- Stabilisation (2026-11-20): one bad part must never take the agent down silently. ---
# Core parts (pinned + part_01..part_04 + part_07 main loop) must load, otherwise the agent halts loudly.
# Every OTHER part runs under a guard: if it raises, or if it overwrites a function/module that existed before it
# (e.g. "import http.client" replacing the agent's own http()), the damage is rolled back, the part is skipped and the
# failure is remembered in _PART_FAILS (the watchdog part tells the owner in Telegram).
import types as _types
_PART_FAILS = []
_CORE = set(PINNED_SHA256) | {"part_02_memory.py", "part_03_adapters.py", "part_04_research.py", "part_07_main_loop.py"}
def _ldr_run(G, files, fails, core):      # everything lives in locals: parts share globals() and must not be able to break the loader itself
    def kind(v):
        if isinstance(v, _types.ModuleType): return "m"
        return "f" if callable(v) else None
    def snap(): return {k: v for k, v in list(G.items()) if not k.startswith("__") and kind(v)}
    prot = ("verify", "guard_json", "tool_blocks")      # safety checks defined in the pinned parts: no other part may replace them, not even with another function
    orig = {}
    for f in files:
        bn = os.path.basename(f)
        for k in prot:
            if k not in orig and callable(G.get(k)): orig[k] = G[k]
        if bn in core or bn.startswith("part_01") or bn.startswith("part_07"):
            exec(compile(open(f, encoding="utf-8").read(), f, "exec"), G); continue
        before = snap()
        try:
            exec(compile(open(f, encoding="utf-8").read(), f, "exec"), G)
            bad = [k for k, v in before.items() if kind(G.get(k)) != kind(v)] + [k for k in prot if k in orig and G.get(k) is not orig[k]]
            for k in [k for k in prot if k in orig and G.get(k) is not orig[k]]: before[k] = orig[k]
            if bad:
                for k in bad: G[k] = before[k]
                fails.append((bn, "clobbered " + ",".join(sorted(bad))[:200]))
                print("PART_GUARD", bn, "overwrote", bad, "- restored", flush=True)
        except BaseException as ex:
            if isinstance(ex, KeyboardInterrupt): raise
            for k, v in before.items():                    # roll back anything the half-run part replaced
                if G.get(k) is not v: G[k] = v
            for k in prot:
                if k in orig and G.get(k) is not orig[k]: G[k] = orig[k]
            fails.append((bn, "%s: %s" % (type(ex).__name__, str(ex)[:160])))
            print("PART_GUARD", bn, "FAILED to load:", type(ex).__name__, str(ex)[:200], "- skipped", flush=True)
_ldr_run(globals(), _parts, _PART_FAILS, _CORE)
