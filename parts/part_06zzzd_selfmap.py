# ---- Self-map v0 (2026-11-22, fix 2026-11-24): measured facts + brake against wasted cycles. ----
# 1. Per day: replies that passed the verifier, replies blocked, and the main reasons.
# 2. Brake against waste:
#    - 6 blocked replies in a row (verifier down / bad drafts) OR
#    - 6 "stop-intent guard unavailable" skips in a row
#    → pause replies and comments for 1 hour. ONE message to the owner.
#    Messages stay unhandled (respond returns "retry", settle does not count tries).
#    Posts and owner chat are not affected.
# 3. Extra: when stop-intent guard fails once, set a 30-minute cooldown so the agent
#    does not burn model calls on every message every cycle while providers are down.
# 4. A block because the verifier was unavailable is not a weight signal.
# 5. The chat gets the real command list.
import re as _sm_re
_SM_BRAKE_N, _SM_BRAKE_S = 6, 3600
_SM_GUARD_COOL = 1800          # 30 min cooldown after stop-intent guard unavailable
def _smr():
    w = ST.setdefault("smap", {}); w.setdefault("days", {}); w.setdefault("recent", []); w.setdefault("brake_until", 0); w.setdefault("last_b", ""); w.setdefault("guard_until", 0)
    return w
def _sm_day():
    w = _smr(); d = w["days"].setdefault(today, {"p": 0, "b": 0, "g": 0, "why": {}})
    for k in sorted(w["days"])[:-30]: w["days"].pop(k, None)
    return d
def sm_braking(): return float(_smr().get("brake_until", 0) or 0) > time.time()
def sm_guard_cooling(): return float(_smr().get("guard_until", 0) or 0) > time.time()
def _sm_trip_brake(why):
    w = _smr()
    if sm_braking(): return
    w["brake_until"] = time.time() + _SM_BRAKE_S; w["recent"] = []
    tg("Пауза ответов и комментариев на час: %d подряд сбоев (%s). Посты и чат с тобой работают, сообщения не потеряются." % (_SM_BRAKE_N, why))
@on_log
def _sm_log(kind, kw):
    try:
        w = _smr()
        if kind == "reply":
            _sm_day()["p"] += 1; w["recent"] = (w["recent"] + ["p"])[-_SM_BRAKE_N:]
        elif kind == "blocked_by_verifier" and "uri" in kw:
            d = _sm_day(); d["b"] += 1
            k = _sm_re.sub(r"\d+", "#", str(kw.get("reason", "") or "no reason"))[:50]
            d["why"][k] = d["why"].get(k, 0) + 1
            if len(d["why"]) > 12: d["why"].pop(min(d["why"], key=d["why"].get), None)
            w["last_b"] = now().isoformat(timespec="seconds"); w["recent"] = (w["recent"] + ["b"])[-_SM_BRAKE_N:]
            if len(w["recent"]) >= _SM_BRAKE_N and all(x == "b" for x in w["recent"]):
                _sm_trip_brake(k)
        elif kind == "skip" and "stop-intent guard unavailable" in str(kw.get("why", "")):
            d = _sm_day(); d["g"] = d.get("g", 0) + 1
            w["guard_until"] = time.time() + _SM_GUARD_COOL
            w["recent"] = (w["recent"] + ["g"])[-_SM_BRAKE_N:]
            if len(w["recent"]) >= _SM_BRAKE_N and all(x == "g" for x in w["recent"]):
                _sm_trip_brake("stop-intent guard unavailable")
    except Exception: pass
_rs_before_sm = respond
def respond(au, handle, their, thread, uid, send, mode="reply"):
    # No model calls while the long brake is on, or while stop-intent guard is known to be down.
    if sm_braking() or sm_guard_cooling(): return "retry"
    if gut_muted(handle, uid): return None
    tk = gut_begin(uid, thread, mode, their)
    if tk == "skip": return None
    return gut_end(uid, _rs_before_sm(au, handle, their, thread, uid, send, mode), tk)
_se_before_sm = settle
def settle(key, failed):
    if failed and (sm_braking() or sm_guard_cooling()): return False
    return _se_before_sm(key, failed)
def sm_line():
    w = _smr(); d = w["days"].get(today) or {"p": 0, "b": 0, "g": 0, "why": {}}
    top = sorted(d.get("why", {}).items(), key=lambda kv: -kv[1])[:3]
    s = "reply checks today: %d passed, %d blocked, %d guard-down" % (d.get("p", 0), d.get("b", 0), d.get("g", 0))
    if top: s += "; main block reasons: " + "; ".join("%s x%d" % kv for kv in top)
    if sm_braking(): s += "; REPLIES ARE PAUSED for %d more minutes" % max(1, int((w["brake_until"] - time.time()) / 60))
    elif sm_guard_cooling(): s += "; stop-intent guard cooling %d more min" % max(1, int((w["guard_until"] - time.time()) / 60))
    return s + "."
_ss_before_sm = self_state
def self_state():
    r = _ss_before_sm()
    try: return r + " " + sm_line()
    except Exception: return r
def sm_weekly():
    w = _smr(); days = sorted(w["days"])[-7:]
    p = sum(w["days"][k].get("p", 0) for k in days); b = sum(w["days"][k].get("b", 0) for k in days); g = sum(w["days"][k].get("g", 0) for k in days); why = {}
    for k in days:
        for r_, n_ in w["days"][k].get("why", {}).items(): why[r_] = why.get(r_, 0) + n_
    top = sorted(why.items(), key=lambda kv: -kv[1])[:3]
    return "Карта себя: за %d дн. ответов прошло %d, заблокировано %d, guard-down %d%s." % (len(days), p, b, g, ("; частые причины: " + "; ".join("%s x%d" % kv for kv in top)) if top else "")
try: WEEKLY_EXTRA.append(sm_weekly)
except Exception: pass
CHAT_SYS += (" Your real commands are ONLY these (name no others; if unsure, say /more shows the list): " + MORE_TEXT.replace("\n\n", " || ").replace("\n", " | ")[:1100])
