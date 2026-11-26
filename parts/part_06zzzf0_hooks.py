# ---- Hooks (2026-11-26). New features register themselves here instead of wrapping a function again. ----
# on_tick(fn): fn() runs once per round after the base tick, in the order of registration (= the load order of the parts). A failing hook is logged and never stops the others.
# Older parts still wrap functions; their number only goes down (scripts/redefs.py keeps the list and refuses new silent overrides).
TICK_HOOKS = []
def on_tick(fn):
    if fn not in TICK_HOOKS: TICK_HOOKS.append(fn)
    return fn
_pt_before_hooks = proj_tick
def proj_tick():
    _pt_before_hooks()
    for _h in list(TICK_HOOKS):
        try: _h()
        except Exception as ex: print("tick hook %s failed: %s" % (getattr(_h, "__name__", "?"), type(ex).__name__), flush=True)
