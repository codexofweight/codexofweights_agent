# ---- Log hooks (2026-11-27). Features that watch the log or clean it register here instead of wrapping log() again. ----
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
