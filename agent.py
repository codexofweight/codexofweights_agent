"""Loader of the Codex of Weights agent. The code is split into part_*.py files (one per area) that run in order in one shared namespace:
part_01_core (settings, charter, Protocols, models, checks), part_02_memory, part_03_adapters (platforms), part_04_research, part_05_tools_sandbox,
part_06_owner_chat (Telegram, first contact), part_06a_private_lab, part_06b_selfmap, part_06c_bio, part_06d_backup_identity,
part_06e_transparency, part_06f_housekeeping, part_06g_search, part_06h_config (limits, model routing, micro-roles), part_06i_projects (long tasks, research, skills), part_06j_health, part_06k_content, part_07_main_loop (the cycle).
To change one area, edit only its file. The core file is pinned by hash below: if it differs, the agent does not start."""
import os, sys, glob, hashlib
CORE_SHA256 = "03f6a9ef342b4e0830d445868d6d26c8c0553be8617782706cb569cd7eef2c60"      # part_01_core.py; update here together with a deliberate change of the core
_D = os.path.dirname(os.path.abspath(__file__))
_parts = sorted(glob.glob(os.path.join(_D, "part_*.py")))
if not _parts: sys.exit("no part_*.py files next to agent.py - agent halted")
_core = os.path.join(_D, "part_01_core.py")
if not os.path.exists(_core) or hashlib.sha256(open(_core, "rb").read()).hexdigest() != CORE_SHA256: sys.exit("part_01_core.py differs from the pinned hash - agent halted")
for _f in _parts + [os.path.join(_D, "CHARTER.md"), os.path.join(_D, "FACTS.md")]:      # printed into the public run log: any silent change becomes visible
    try: print("sha256", os.path.basename(_f), hashlib.sha256(open(_f, "rb").read()).hexdigest()[:16], flush=True)
    except Exception: pass
for _f in _parts:
    exec(compile(open(_f, encoding="utf-8").read(), _f, "exec"), globals())
