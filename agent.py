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
    "part_01_core.py": "4fc9a336c5e423e7a58b0ce4c65163389e2713695e1aff29f02c0195bc552ae2",
    "part_05_tools_sandbox.py": "0a3d3de9f02b4c26cdb213b6b3ed64bdd21bf50571161fdb37ceaf9315b2773c",
    "part_06_owner_chat.py": "a72b3c6b6b5e4af7dd757dc16b581587f9ee48408f56f2f89c960369cac37e34",
}   # update the matching entry here together with a deliberate change of that file
_D = os.path.dirname(os.path.abspath(__file__))
# The code lives in parts/ (one file per area). Files still lying next to agent.py are used only if the same name is not in parts/ (so a half-finished move never breaks a run).
_found = {os.path.basename(f): f for f in glob.glob(os.path.join(_D, "part_*.py"))}
_found.update({os.path.basename(f): f for f in glob.glob(os.path.join(_D, "parts", "part_*.py"))})
_parts = [_found[k] for k in sorted(_found)]
if not _parts: sys.exit("no part_*.py files found (parts/ or next to agent.py) - agent halted")
for _name, _want in PINNED_SHA256.items():
    _p = _found.get(_name)
    if not _p or hashlib.sha256(open(_p, "rb").read()).hexdigest() != _want: sys.exit("%s differs from the pinned hash - agent halted" % _name)
for _f in _parts + [os.path.join(_D, "CHARTER.md"), os.path.join(_D, "FACTS.md")]:      # printed into the public run log: any silent change becomes visible
    try: print("sha256", os.path.basename(_f), hashlib.sha256(open(_f, "rb").read()).hexdigest()[:16], flush=True)
    except Exception: pass
for _f in _parts:
    exec(compile(open(_f, encoding="utf-8").read(), _f, "exec"), globals())
