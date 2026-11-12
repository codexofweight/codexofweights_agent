"""Loader of the Codex of Weights agent. The code is split into part_*.py files (one per area) that run in order in one shared namespace:
part_01_core (settings, charter, models, checks), part_02_memory, part_03_adapters (platforms), part_04_research, part_05_tools_sandbox,
part_06_owner_chat (Telegram, first contact), part_07_main_loop (the cycle). To change one area, edit only its file."""
import os, sys, glob
_D = os.path.dirname(os.path.abspath(__file__))
_parts = sorted(glob.glob(os.path.join(_D, "part_*.py")))
if not _parts: sys.exit("no part_*.py files next to agent.py - agent halted")
for _f in _parts:
    exec(compile(open(_f, encoding="utf-8").read(), _f, "exec"), globals())
