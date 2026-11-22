# ---- Self-map v0 (2026-11-22): measured facts about how the agent really behaves. It only records and reports; it decides nothing except one brake. ----
# 1. Per day: replies that passed the verifier, replies blocked, and the main reasons (numbers in reasons are folded together). The owner can ask the chat "why do you block?" and the answer comes from SELF-STATE.
# 2. Brake against waste: 6 blocked replies in a row (a verifier that is down, or a stream of bad drafts) pause replies and comments for an hour with ONE message to the owner. Nothing is lost: the messages
#    stay unhandled (respond returns "retry", settle does not count the tries) and are handled after the pause. Posts and the owner chat are not affected.
# 3. A block because the verifier was unavailable says nothing about the quality of replies: it is not a weight signal (see part_06zzzc).
# 4. The chat gets the real command list, so it stops inventing command names.
import re as _sm_re
_SM_BRAKE_N, _SM_BRAKE_S = 6, 3600
def _smr():
    w = ST.setdefault("smap", {}); w.setdefault("days", {}); w.setdefault("recent", []); w.setdefault("brake_until", 0); w.setdefault("last_b", "")
    return w
def _sm_day():
    w = _smr(); d = w["days"].setdefault(today, {"p": 0, "b": 0, "why": {}})
    for k in sorted(w["days"])[:-30]: w["days"].pop(k, None)
    return d
def sm_braking(): return float(_smr().get("brake_until", 0) or 0) > time.time()
_lg_before_sm = log
def log(kind, **kw):
    r = _lg_before_sm(kind, **kw)
    try:
        w = _smr()
        if kind == "reply": _sm_day()["p"] += 1; w["recent"] = (w["recent"] + ["p"])[-_SM_BRAKE_N:]
        elif kind == "blocked_by_verifier" and "uri" in kw:
            d = _sm_day(); d["b"] += 1; k = _sm_re.sub(r"\d+", "#", str(kw.get("reason", "") or "no reason"))[:50]; d["why"][k] = d["why"].get(k, 0) + 1
            if len(d["why"]) > 12: d["why"].pop(min(d["why"], key=d["why"].get), None)
            w["last_b"] = now().isoformat(timespec="seconds"); w["recent"] = (w["recent"] + ["b"])[-_SM_BRAKE_N:]
            if len(w["recent"]) >= _SM_BRAKE_N and all(x == "b" for x in w["recent"]) and not sm_braking():
                w["brake_until"] = time.time() + _SM_BRAKE_S; w["recent"] = []
                tg("Пауза ответов и комментариев на час: %d подряд заблокировано проверкой (последняя причина: %s). Посты и чат с тобой работают, сообщения не потеряются." % (_SM_BRAKE_N, k))
    except Exception: pass
    return r
_rs_before_sm = respond
def respond(au, handle, their, thread, uid, send, mode="reply"):
    if sm_braking(): return "retry"      # no model call is spent while the brake is on
    return _rs_before_sm(au, handle, their, thread, uid, send, mode)
_se_before_sm = settle
def settle(key, failed):
    if failed and sm_braking(): return False      # a pause must not use up the three tries of a message
    return _se_before_sm(key, failed)
def sm_line():
    w = _smr(); d = w["days"].get(today) or {"p": 0, "b": 0, "why": {}}
    top = sorted(d["why"].items(), key=lambda kv: -kv[1])[:3]
    s = "reply checks today: %d passed, %d blocked" % (d["p"], d["b"]) + ("; main block reasons: " + "; ".join("%s x%d" % kv for kv in top) if top else "")
    if sm_braking(): s += "; REPLIES ARE PAUSED for %d more minutes after a run of blocks" % max(1, int((w["brake_until"] - time.time()) / 60))
    return s + "."
_ss_before_sm = self_state
def self_state():
    r = _ss_before_sm()
    try: return r + " " + sm_line()
    except Exception: return r
def sm_weekly():
    w = _smr(); days = sorted(w["days"])[-7:]
    p = sum(w["days"][k]["p"] for k in days); b = sum(w["days"][k]["b"] for k in days); why = {}
    for k in days:
        for r_, n_ in w["days"][k]["why"].items(): why[r_] = why.get(r_, 0) + n_
    top = sorted(why.items(), key=lambda kv: -kv[1])[:3]
    return "Карта себя: за %d дн. ответов прошло %d, заблокировано %d%s." % (len(days), p, b, ("; частые причины: " + "; ".join("%s x%d" % kv for kv in top)) if top else "")
try: WEEKLY_EXTRA.append(sm_weekly)
except Exception: pass
CHAT_SYS += (" Your real commands are ONLY these (name no others; if unsure, say /more shows the list): " + MORE_TEXT.replace("\n\n", " || ").replace("\n", " | ")[:1100])
