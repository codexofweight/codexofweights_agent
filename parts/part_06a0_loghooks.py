# ---- Hooks for log, chat context and tick (2026-11-27). Features register here instead of wrapping a function again. ----
# on_tick(fn): fn() runs once per round after the base tick (the loop itself is in part_06zzzf0_hooks.py).
# on_context(fn): fn() returns text appended to the owner-chat context (start it with a blank line); on_context_front(fn): fn() returns text put BEFORE the context (end it with a blank line).
# Log hooks:
# on_log_pre(fn): fn(kind, kw) runs BEFORE the line is written and may change kw (privacy scrubbing).
# on_log(fn): fn(kind, kw) runs AFTER the line is written, in the order of registration (= the load order of the parts). A failing hook never stops the others and never breaks log().
LOG_PRE, LOG_POST = [], []
def on_log_pre(fn):
    if fn not in LOG_PRE: LOG_PRE.append(fn)
    return fn
def on_log(fn):
    if fn not in LOG_POST: LOG_POST.append(fn)
    return fn
_lg_before_hooks = log
def log(kind, **kw):
    for _h in LOG_PRE:
        try: _h(kind, kw)
        except Exception: pass
    r = _lg_before_hooks(kind, **kw)
    for _h in LOG_POST:
        try: _h(kind, kw)
        except Exception: pass
    return r
TICK_HOOKS = []
def on_tick(fn):
    if fn not in TICK_HOOKS: TICK_HOOKS.append(fn)
    return fn
CTX_FRONT, CTX_AFTER = [], []
def on_context_front(fn):
    if fn not in CTX_FRONT: CTX_FRONT.append(fn)
    return fn
def on_context(fn):
    if fn not in CTX_AFTER: CTX_AFTER.append(fn)
    return fn
_ac_before_hooks = agent_context
def agent_context():
    c = _ac_before_hooks()
    for _h in CTX_AFTER:
        try: c += _h() or ""
        except Exception: pass
    for _h in reversed(CTX_FRONT):
        try: c = (_h() or "") + c
        except Exception: pass
    return c
