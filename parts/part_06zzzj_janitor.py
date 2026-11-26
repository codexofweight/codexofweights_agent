# ---- Daily janitor (2026-11-26). Cleaning of state, log and old facts already exists (trim_state, memory_audit, the weekly archive); this part adds the two missing things. ----
# 1) Dictionaries that grow without a limit are cut to their newest entries once a day.
# 2) One short lesson per finished day, built from the agent's own numbers WITHOUT a model (no limits spent), appended to memory/lessons.md (kept to the last 90 days).
_JAN_DICTS = {"skipped": 300, "stop_guard_fail": 100, "lab_sent": 120, "dev_seen": 80, "need_hist": 60, "tries": 500}
def jan_lesson(day, y):
    """One line of facts and one rule of thumb for a finished day. y is the day record of the health pulse."""
    act = y.get("post", 0) + y.get("reply", 0); calls = y.get("calls", 0); fails = y.get("fails", 0); pf = y.get("pf") or {}; pc = y.get("pc") or {}
    bad = sorted(((pf.get(n, 0) / float(pc.get(n, 0) + pf.get(n, 0) or 1), n) for n in pf if pf.get(n, 0) >= 10), reverse=True)
    why = sorted((y.get("why") or {}).items(), key=lambda kv: -kv[1])[:2]
    facts = "%s: %d posts, %d replies, %d blocked by the check, model failures %d%%" % (day, y.get("post", 0), y.get("reply", 0), y.get("blocked", 0), round(100.0 * fails / (calls + fails)) if calls + fails else 0)
    if bad: facts += "; least reliable: %s (%d%% failed)" % (bad[0][1], round(bad[0][0] * 100))
    if why: facts += "; main skips: " + ", ".join("%s x%d" % kv for kv in why)
    if any("stop-intent guard unavailable" in k and v >= 5 for k, v in (y.get("why") or {}).items()): rule = "replies wait when the stop check has no model: keep one reliable provider free for it"
    elif bad and bad[0][0] > 0.3: rule = "move %s later in the chains until it recovers" % bad[0][1]
    elif y.get("blocked", 0) > act and y.get("blocked", 0) >= 4: rule = "the check blocks more than is sent: review how drafts are written"
    elif act == 0: rule = "no action this day: look for the cause (limits, pause, project mode)"
    else: rule = "stable day, nothing to change"
    return facts + ". Rule: " + rule + "."
def jan_run():
    if ST.get("janitor_day") == today: return
    ST["janitor_day"] = today; cut = 0
    for k, mx in _JAN_DICTS.items():
        d = ST.get(k)
        if isinstance(d, dict) and len(d) > mx * 1.5: ST[k] = dict(list(d.items())[-mx:]); cut += 1
    ds = sorted((ST.get("hl") or {}).get("days") or {}); line = None
    if ds and (ST.get("hl") or {})["days"][ds[-1]].get("calls"): line = jan_lesson(ds[-1], ST["hl"]["days"][ds[-1]])
    if line and MEM_TOKEN and LIVE:
        t, sh = mem_get("memory/lessons.md")
        L = [x for x in (t or "").splitlines() if x.strip()]
        if not any(x.startswith(ds[-1]) for x in L): mem_put("memory/lessons.md", "\n".join((L + [line])[-90:]) + "\n", sh, "daily lesson")
    return cut, line
@on_tick
def _janitor_tick():
    try: jan_run()
    except Exception as ex: print("janitor failed:", type(ex).__name__, flush=True)
