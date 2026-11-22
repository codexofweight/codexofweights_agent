# ---- Weights v1 (2026-11-21): the agent's slow, bounded memory of what proved reliable. OBSERVATION MODE: it records and reports, it decides nothing yet. ----
# The core (honesty, no manipulation, stop requests, transparency, the Protocols) is NOT here and cannot be here: weights only exist for items named mod:, style:, tip: or make:;
# anything else (for example core:honesty) is refused. Three speeds per item: f (fast, hours-days, decays by half every day), m (medium, weeks, moves only when at least 3 signals of one sign
# arrived within 7 days), s (slow, identity: statistics only, never changed by the agent). Signals come from checks that can be verified (module ran or failed, the verifier blocked or passed
# a reply) and from the owner's decisions (rare, three times as heavy, and the anchor against the agent grading itself). Likes, praise and engagement are never used.
# Brakes: every step is capped, a day's total movement per item is capped, values stay within -1..1, a conflict between the owner and the agent's own average is noted as a tension.
# The record lives in the private memory repo (PRIVATE_KEYS has "wt"). Stored: ST["wt"]. No new commands: the picture is in the weekly report and in /status all.
WT_OBS_DAYS = 45
_WT_OK = re.compile(r"^(mod|style|tip|make):[\w.\-]{1,40}$")
def _wtr():
    w = ST.setdefault("wt", {})
    w.setdefault("v", 1); w.setdefault("since", now().isoformat(timespec="seconds")); w.setdefault("on", False); w.setdefault("items", {}); w.setdefault("log", []); w.setdefault("tension", []); w.setdefault("n", 0)
    return w
def _wt_clamp(x, lo=-1.0, hi=1.0): return max(lo, min(hi, x))
def wt_signal(item, value, source="internal", why=""):
    """Record one signal. Returns False when the item is not allowed (the core is never an item) or the input is not a number."""
    if not isinstance(item, str) or not _WT_OK.match(item) or source not in ("internal", "owner"): return False
    try: v = _wt_clamp(float(value))
    except Exception: return False
    w = _wtr(); t = time.time(); it = w["items"].setdefault(item, {"f": 0.0, "m": 0.0, "sa": 0.0, "sn": 0, "ts": t, "day": today, "dsum": 0.0, "rec": []})
    dt = max(0.0, (t - it.get("ts", t)) / 86400.0)
    if dt: it["f"] *= 0.5 ** dt; it["m"] *= 0.95 ** dt
    it["ts"] = t
    if it.get("day") != today: it["day"] = today; it["dsum"] = 0.0
    wgt = 3.0 if source == "owner" else 1.0
    step = _wt_clamp(0.30 * v * wgt, -0.5, 0.5)
    room = max(0.0, 1.0 - it["dsum"])                       # a day's total movement per item is capped
    if abs(step) > room: step = room if step > 0 else -room
    if it["f"] and (step > 0) == (it["f"] > 0): step *= max(0.1, 1.0 - abs(it["f"]))   # soft edges: the closer to the limit, the smaller the step (no absolute certainty, for or against)
    it["f"] = _wt_clamp(it["f"] + step, -0.95, 0.95); it["dsum"] += abs(step)
    it["rec"] = [r for r in it["rec"] if t - r[0] < 7 * 86400][-19:] + [[t, v]]
    same = [r[1] for r in it["rec"] if (r[1] > 0) == (v > 0)]
    if len(same) >= 3: it["m"] = _wt_clamp(it["m"] + 0.1 * (sum(same) / len(same) - it["m"]), -0.95, 0.95)   # inertia: the medium layer moves only on a repeated direction
    it["sa"] = round(it["sa"] + v, 3); it["sn"] += 1                                           # the slow layer only collects statistics
    if source == "owner" and abs(it["m"]) >= 0.3 and (it["m"] > 0) != (v > 0):
        w["tension"] = (w["tension"] + [[today, item, "owner %s vs own average %+.2f" % ("approves" if v > 0 else "rejects", it["m"])]])[-10:]
    w["log"] = (w["log"] + [[now().isoformat(timespec="seconds"), item, round(v, 2), source, str(why)[:40]]])[-150:]; w["n"] += 1
    if len(w["items"]) > 200:
        for k in sorted(w["items"], key=lambda k: w["items"][k].get("ts", 0))[:len(w["items"]) - 200]: w["items"].pop(k, None)
    return True
def wt_days():
    try: return _ss_age_days(_wtr()["since"])
    except Exception: return 0.0
def wt_effective(item):
    """What a decision may read. In observation mode (the default, first 45 days or until the owner switches it on) every item is neutral: 0.0."""
    w = _wtr()
    if not w.get("on"): return 0.0
    it = w["items"].get(item)
    return 0.0 if not it else _wt_clamp(0.5 * it.get("f", 0.0) + 0.5 * it.get("m", 0.0))
def wt_line():
    w = ST.get("wt")
    if not w: return ""
    return "weights: %s, day %d of %d, %d items, %d signals." % ("ACTIVE" if w.get("on") else "observation only", wt_days(), WT_OBS_DAYS, len(w.get("items", {})), w.get("n", 0))
def wt_weekly():
    w = ST.get("wt")
    if not w or not w.get("items"): return "Веса: режим наблюдения, сигналов пока нет."
    top = sorted(w["items"].items(), key=lambda kv: -(abs(kv[1]["f"]) + abs(kv[1]["m"])))[:5]
    s = "Веса (%s, день %d из %d): " % ("влияют" if w.get("on") else "только наблюдение", wt_days(), WT_OBS_DAYS) + "; ".join("%s быстрый %+.2f средний %+.2f (сигналов %d)" % (k, v["f"], v["m"], v["sn"]) for k, v in top)
    if w.get("tension"): s += ". Напряжение: " + "; ".join("%s %s" % (t[1], t[2]) for t in w["tension"][-2:])
    return s[:600]
try: WEEKLY_EXTRA.append(wt_weekly)
except Exception: pass
_log_before_wt = log
def log(kind, **kw):
    r = _log_before_wt(kind, **kw)
    try:
        if kind == "blocked_by_verifier": wt_signal("style:reply", -0.3, "internal", "verifier blocked a reply")
        elif kind == "reply": wt_signal("style:reply", 0.05, "internal", "reply passed the verifier")
        elif kind == "post": wt_signal("style:post", 0.05, "internal", "post passed the verifier")
    except Exception: pass
    return r
