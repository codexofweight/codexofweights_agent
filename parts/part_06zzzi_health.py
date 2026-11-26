# ---- Health pulse and a quiet Telegram (2026-11-25). ----
# The agent counts its own day (actions, blocked texts, model failures) and compares it with its own last week: green / yellow / red.
# The owner gets ONE morning message: the state, the numbers, what deviates, what waits for a decision. Notices that only inform (reply pause, models silent, low-power mode) are not sent; they are counted into that message.
# /health shows the same on demand. A red state is the only thing sent in the middle of the day (once a day).
_HL_QUIET = (("Пауза ответов и комментариев", "пауза ответов"), ("⚠️ Сторож: модели не отвечают", "модели не отвечали подряд"), ("Режим экономии", "режим экономии лимитов"))
def _hl():
    w = ST.setdefault("hl", {}); w.setdefault("days", {}); w.setdefault("cur", {"day": today}); w.setdefault("last_act", time.time()); w.setdefault("alert_day", "")
    return w
def _hl_roll(w):
    c = w["cur"]
    if c.get("day") != today:
        w["days"][c.get("day", today)] = {k: v for k, v in c.items() if k != "day"}
        for k in sorted(w["days"])[:-14]: w["days"].pop(k, None)
        w["cur"] = {"day": today}
    return w["cur"]
def _hl_add(key, n=1):
    c = _hl_roll(_hl()); c[key] = c.get(key, 0) + n
_lg_before_hl = log
def log(kind, **kw):
    r = _lg_before_hl(kind, **kw)
    try:
        if kind in ("post", "reply"): _hl_add(kind); _hl()["last_act"] = time.time()
        elif kind in ("blocked_by_verifier", "send_failed", "reply_unverified"): _hl_add("blocked" if kind == "blocked_by_verifier" else "unsent")
        elif kind == "skip":
            wy = _hl_roll(_hl()).setdefault("why", {}); k_ = str(kw.get("why", "?"))[:60]
            if k_ in wy or len(wy) < 12: wy[k_] = wy.get(k_, 0) + 1
    except Exception: pass
    return r
_tg_before_hl = tg
def tg(text, *a, **k):
    try:
        for pre, name in _HL_QUIET:
            if str(text).startswith(pre):
                q = _hl_roll(_hl()).setdefault("quiet", {}); q[name] = q.get(name, 0) + 1; return
    except Exception: pass
    return _tg_before_hl(text, *a, **k)
def _hl_rate(d): n = d.get("calls", 0) + d.get("fails", 0); return (d.get("fails", 0) / float(n)) if n else 0.0
def hl_judge(day):
    """(status, [reasons]) for a finished day, compared with up to 7 days before it."""
    w = _hl(); y = w["days"].get(day) or {}; prev = [w["days"][k] for k in sorted(w["days"]) if k < day][-7:]
    act = y.get("post", 0) + y.get("reply", 0); b_act = (sum(p.get("post", 0) + p.get("reply", 0) for p in prev) / float(len(prev))) if prev else 0
    b_fr = (sum(_hl_rate(p) for p in prev) / float(len(prev))) if prev else 0; fr = _hl_rate(y); bl = y.get("blocked", 0)
    red, yel = [], []
    if act == 0 and b_act >= 3 and not ST.get("focus_on"): red.append("за сутки ни одного поста и ответа (обычно около %d)" % round(b_act))
    if bl >= 6 and bl > act: red.append("проверка заблокировала %d текстов, отправлено %d" % (bl, act))
    if y.get("fails", 0) >= 20 and fr > 0.5: red.append("больше половины вызовов моделей неудачны (%d%%)" % round(fr * 100))
    if not red:
        if fr > 0.15 and fr > 2 * b_fr: yel.append("сбоев моделей %d%% (обычно %d%%)" % (round(fr * 100), round(b_fr * 100)))
        if len(prev) >= 3 and b_act >= 3 and act < 0.3 * b_act: yel.append("действий %d при обычных %d" % (act, round(b_act)))
        if sum((y.get("quiet") or {}).values()) >= 5: yel.append("много тихих остановок: " + ", ".join("%s ×%d" % kv for kv in (y.get("quiet") or {}).items()))
    return ("red" if red else "yellow" if yel else "green"), red + yel
def _hl_line(day):
    st, why = hl_judge(day); y = (_hl()["days"].get(day) or {})
    name = {"green": "зелёное, всё в норме", "yellow": "жёлтое, есть отклонение", "red": "красное, нужно внимание"}[st]
    L = ["Состояние: %s. За %s: постов %d, ответов %d, заблокировано проверкой %d, сбоев моделей %d%%." % (name, day, y.get("post", 0), y.get("reply", 0), y.get("blocked", 0), round(_hl_rate(y) * 100))]
    if why: L.append("Что не так: " + "; ".join(why) + ".")
    q = y.get("quiet") or {}
    if q and st == "green": L.append("Тихо отмечено: " + ", ".join("%s ×%d" % kv for kv in q.items()) + ".")
    return "\n".join(L), st
def daily_digest():
    if now().hour < 6 or ST.get("digest_day") == today: return
    ST["digest_day"] = today; w = _hl(); _hl_roll(w); ds = sorted(w["days"])
    L = [_hl_line(ds[-1])[0]] if ds else ["Состояние: данных за прошлые сутки ещё нет, считаю с сегодняшнего дня."]
    if ST.get("asks"): L.append("Ждут твоего решения: " + "; ".join("#%s %s %s" % (a["id"], a["kind"], (a.get("name") or a.get("text") or "")[:60]) for a in ST["asks"]) + ". Ответь «да»/«нет» или напиши, что поменять.")
    L.append("Подробнее: /health, /status.")
    tg("\n\n".join(L))
def pulse_command(c, raw=None):
    w = _hl(); c0 = _hl_roll(w); ds = sorted(w["days"])
    t = ["Сегодня (пока): постов %d, ответов %d, заблокировано %d, сбоев моделей %d%%." % (c0.get("post", 0), c0.get("reply", 0), c0.get("blocked", 0), round(_hl_rate(c0) * 100))]
    if ds: t.insert(0, _hl_line(ds[-1])[0])
    pr = c0.get("pr") or {}; nm = {"1": "чат с тобой", "2": "ответы и проверки", "3": "посты", "4": "чтение и планы", "5": "лаборатория и память"}
    if pr: t.append("Вызовы моделей сегодня по контурам: " + ", ".join("%s %d" % (nm.get(k, k), v) for k, v in sorted(pr.items())))
    t.append("Последние дни (посты+ответы / сбои моделей): " + (", ".join("%s %d/%d%%" % (k[5:], w["days"][k].get("post", 0) + w["days"][k].get("reply", 0), round(_hl_rate(w["days"][k]) * 100)) for k in ds[-7:]) or "пока нет данных"))
    try: t.append("\nПамять и состояние:\n" + health_report())
    except Exception: pass
    tg("\n".join(t))
EXT_CMDS["/health"] = pulse_command
@on_tick
def _health_tick():
    try:
        w = _hl(); c = _hl_roll(w); u = usage(); c["calls"] = sum(u["calls"].values()); c["fails"] = sum(u["fails"].values()); c["pf"] = dict(u["fails"]); c["pc"] = dict(u["calls"])
        red = ""
        if c["fails"] >= 20 and _hl_rate(c) > 0.5: red = "больше половины вызовов моделей сегодня неудачны (%d%%)" % round(_hl_rate(c) * 100)
        elif time.time() - w["last_act"] > 86400 and not econ_mode() and not ST.get("focus_on") and ST.get("hl_started") and time.time() - ST["hl_started"] > 86400: red = "больше суток ни одного поста и ответа"
        ST.setdefault("hl_started", time.time())
        if red and w["alert_day"] != today: w["alert_day"] = today; _tg_before_hl("Состояние красное: " + red + ". Подробнее: /health.")
    except Exception as ex: print("health tick failed:", type(ex).__name__, flush=True)
