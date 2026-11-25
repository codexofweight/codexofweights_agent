# ---- Quiet log (2026-11-25). The public log keeps what the agent DID (posts, replies, blocks, mutes, finds) and a short digest of what it did NOT do. ----
# Before: every skipped message was a line (73% of the log, 1.1 MB). Now skips are counted and written as ONE "digest" line per hour: reasons with counts, model calls/failures, providers on pause.
# Everything else in the chain (self-state, weights, the stop-guard brake) still sees every skip, only the file line and the console line are dropped.
import atexit, contextlib, io
_DG = {"skips": {}, "last": 0.0, "f0": {}}
def _dg_flush(force=False):
    try:
        t = time.time(); u = usage(); fails = {n: v for n, v in (u.get("fails") or {}).items() if v}
        if not force and t - _DG["last"] < 3600: return
        new_f = {n: v - _DG["f0"].get(n, 0) for n, v in fails.items() if v - _DG["f0"].get(n, 0) > 0}
        if not _DG["skips"] and not new_f: _DG["last"] = t; return
        d = {"skips": dict(sorted(_DG["skips"].items(), key=lambda kv: -kv[1])), "models": {n: [u["calls"].get(n, 0), v] for n, v in {**{k: 0 for k in u["calls"]}, **fails}.items()},
             "paused_min": {n: int((c - t) // 60) for n, c in COOL.items() if c > t}}
        _lg_before_q("digest", **d); _DG["skips"] = {}; _DG["f0"] = dict(fails); _DG["last"] = t
    except Exception as ex: print("digest failed:", type(ex).__name__, flush=True)
_lg_before_q = log
def log(kind, **kw):
    if kind != "skip": return _lg_before_q(kind, **kw)
    why = str(kw.get("why", "?"))[:90]; _DG["skips"][why] = _DG["skips"].get(why, 0) + 1
    g = globals(); p0 = g["P"]
    g["P"] = lambda x, *a: os.devnull if x == "logs/actions.jsonl" else p0(x, *a)
    try:
        with contextlib.redirect_stdout(io.StringIO()): return _lg_before_q(kind, **kw)
    finally: g["P"] = p0
atexit.register(lambda: _dg_flush(True))
# state never grows without bound: the attempt counter keeps its newest 500 keys
_pt_before_q = proj_tick
def proj_tick():
    _pt_before_q()
    try:
        tr = ST.get("tries")
        if isinstance(tr, dict) and len(tr) > 500: ST["tries"] = dict(list(tr.items())[-500:])
        _dg_flush()
    except Exception as ex: print("quiet log failed:", type(ex).__name__, flush=True)
# a post that could not be made is not retried every round: 2 hours of rest first (no model calls meanwhile)
def _post_rest(fn):
    def w(*a, **k):
        if float(ST.get("post_rest_until", 0) or 0) > time.time(): return None
        r = fn(*a, **k)
        if not r: ST["post_rest_until"] = time.time() + 7200
        return r
    return w
make_free_post = _post_rest(make_free_post); make_protocol_post = _post_rest(make_protocol_post)
