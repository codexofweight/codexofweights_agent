# ---- Interface (2026-11-23): buttons in Telegram and a status in plain Russian. No model calls: everything is built from real data. ----
# 1. /menu: inline buttons (status, projects, limits, pause, settings, memory, development) and four always-visible buttons at the bottom. Button presses are turned into ordinary commands
#    BEFORE the existing message loop sees them (the http function is wrapped for getUpdates), so the owner check and every command work exactly as when typed. Only the owner's chat is accepted.
# 2. The list of commands in the "/" menu of the bot is set once (setMyCommands) and again only when the list changes.
# 3. /status is a few plain Russian lines with a verdict first; /status all keeps the full technical picture.
import hashlib as _mn_hl, json as _mn_js
_MN_LABELS = {"меню": "/menu", "состояние": "/status", "проекты": "/projects", "лимиты": "/limits"}
_MN_MENUS = {
 "main": ("Меню Лума. Что нужно?", [[("Состояние", "c:/status"), ("Проекты", "c:/projects")], [("Лимиты", "c:/limits"), ("Пауза", "c:/stop"), ("Продолжить", "c:/start")],
          [("Настройки", "m:set"), ("Память", "m:mem"), ("Развитие", "m:dev")], [("Все команды", "c:/more")]]),
 "set": ("Настройки. Нажми, что показать.", [[("Модели", "c:/settings model"), ("Маршрут", "c:/settings route")], [("Общие значения", "c:/settings cfg"), ("Площадки", "c:/platforms")],
          [("Первые контакты", "c:/reach"), ("Цепочка циклов", "c:/autorun")], [("Ежедневная работа", "c:/autoproj"), ("Назад", "m:main")]]),
 "mem": ("Память и знания.", [[("Биография", "c:/bio"), ("Подсказки", "c:/tip")], [("Здоровье", "c:/health"), ("Интуиция", "c:/intuition")], [("Контент", "c:/content"), ("Назад", "m:main")]]),
 "dev": ("Развитие.", [[("Проекты (все)", "c:/projects all"), ("Свои модули", "c:/own")], [("Ежедневная работа", "c:/autoproj"), ("Карта", "c:/map")],
        [("Как делать модуль", "c:/make"), ("Как делать разведку", "c:/scout")], [("Назад", "m:main")]]),
}
_MN_CMDS = [("menu", "Меню с кнопками"), ("status", "Состояние агента"), ("projects", "Проекты"), ("limits", "Лимиты моделей"), ("stop", "Пауза"), ("start", "Продолжить"), ("make", "Новое расширение"),
            ("scout", "Разведка на GitHub"), ("own", "Свои модули"), ("autoproj", "Ежедневная работа"), ("settings", "Настройки"), ("more", "Все команды")]
_http_before_mn = http
def _mn_api(method, body): return _http_before_mn("%s/bot%s/%s" % (TGB, TG_TOKEN, method), body)
def _mn_markup(rows): return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}
def _mn_nav(name, chat_id, mid):
    text, rows = _MN_MENUS.get(name) or _MN_MENUS["main"]
    try: _mn_api("editMessageText", {"chat_id": chat_id, "message_id": mid, "text": text, "reply_markup": _mn_markup(rows)})
    except Exception: _mn_api("sendMessage", {"chat_id": chat_id, "text": text, "reply_markup": _mn_markup(rows)})
def _mn_owner_id():
    """Who may command the agent: TG_OWNER_ID if set, else the chat id when it is a private chat (positive); in a group without TG_OWNER_ID the sender cannot be checked."""
    o = os.environ.get("TG_OWNER_ID", "").strip()
    return o or (str(TG_CHAT) if str(TG_CHAT).isdigit() else "")
def _mn_rewrite(r):
    oid = _mn_owner_id()
    for u in r.get("result", []):
        cq = u.get("callback_query")
        if not cq and oid and str(((u.get("message") or {}).get("from") or {}).get("id")) != oid and str(((u.get("message") or {}).get("chat") or {}).get("id")) == str(TG_CHAT): u.pop("message", None); continue      # right chat, wrong sender
        if cq:
            m = cq.get("message") or {}; chat = m.get("chat") or {}; d = str(cq.get("data") or ""); u.pop("callback_query", None)
            if not TG_CHAT or str(chat.get("id")) != str(TG_CHAT): continue      # only the owner's chat
            if oid and str((cq.get("from") or {}).get("id")) != oid: continue      # and only the owner
            try: _mn_api("answerCallbackQuery", {"callback_query_id": cq.get("id")})
            except Exception: pass
            if d.startswith("m:"): _mn_nav(d[2:], chat.get("id"), m.get("message_id"))
            elif d.startswith("c:"): u["message"] = {"chat": chat, "text": d[2:]}
        else:
            m = u.get("message") or {}; t = (m.get("text") or "").strip().lower()
            if t in _MN_LABELS and TG_CHAT and str((m.get("chat") or {}).get("id")) == str(TG_CHAT): m["text"] = _MN_LABELS[t]
def http(url, body=None, headers=None, method=None):
    r = _http_before_mn(url, body, headers, method)
    try:
        if "/getUpdates" in str(url) and isinstance(r, dict): _mn_rewrite(r)
    except Exception as ex: print("menu rewrite failed:", type(ex).__name__, flush=True)
    return r
def menu_command(c, raw=None):
    if not (TG_TOKEN and TG_CHAT): return
    try:
        if not ST.get("kb_set") or "keys" in (raw or c):
            ST["kb_set"] = True
            _mn_api("sendMessage", {"chat_id": TG_CHAT, "text": "Кнопки внизу включены: Меню, Состояние, Проекты, Лимиты.", "reply_markup": {"keyboard": [[{"text": "Меню"}, {"text": "Состояние"}], [{"text": "Проекты"}, {"text": "Лимиты"}]], "resize_keyboard": True, "is_persistent": True}})
        text, rows = _MN_MENUS["main"]; _mn_api("sendMessage", {"chat_id": TG_CHAT, "text": text, "reply_markup": _mn_markup(rows)})
    except Exception as ex: print("menu failed:", type(ex).__name__, flush=True); tg("Меню не открылось, но все команды работают. Список: /more")
def mn_setup():
    h = _mn_hl.sha1(_mn_js.dumps(_MN_CMDS).encode()).hexdigest()[:10]
    if ST.get("cmds_hash") == h or not (TG_TOKEN and TG_CHAT): return
    try: _mn_api("setMyCommands", {"commands": [{"command": a, "description": b} for a, b in _MN_CMDS]}); ST["cmds_hash"] = h
    except Exception as ex: print("setMyCommands failed:", type(ex).__name__, flush=True)
_pt_before_mn = proj_tick
def proj_tick():
    _pt_before_mn()
    mn_setup()
def _ru_cut(s, n=70):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
def _ru_goal(g):
    """A project goal for the owner: the internal English instruction is dropped, the text is cut at a word."""
    g = str(g); m = re.match(r"Build one small own module .*? for this need of the agent: (.*?)(?:\. Why it matters:.*)?$", g, re.S)
    if m: return "модуль: " + _ru_cut(m.group(1))
    pre = "Find open-source ideas on GitHub useful for the agent on this topic: "
    return ("разведка: " + _ru_cut(g[len(pre):])) if g.startswith(pre) else _ru_cut(g)
def _ru_ago(sec):
    m = int(sec / 60)
    return "%d мин назад" % m if m < 90 else ("%d ч назад" % round(m / 60) if m < 2880 else "%d дн. назад" % round(m / 1440))
def _ru_limits():
    out = []
    try:
        for l in limits_report().splitlines():
            head = l.split(", токенов")[0]; mm = re.search(r"вызовов (\d+)/(\d+)", head)
            if mm and int(mm.group(2)): out.append((head.split(":")[0].strip(), int(mm.group(1)), int(mm.group(2))))
    except Exception: pass
    return out
def ru_status():
    probs = []; L = []
    try:
        allp = proj_all(); act = [q for q in allp if q.get("status") == "active"]; wait = [q for q in allp if q.get("status") == "waiting_owner"]; fin = [q for q in allp if q.get("status") in ("done", "failed", "paused")]
        if act: L.append("Проекты: сейчас делаю «%s» (шаг: %s)%s." % (_ru_goal(act[0]["goal"]), (act[0].get("data") or {}).get("stage") or "ещё не начат", ("; в очереди ещё %d" % (len(act) - 1)) if len(act) > 1 else ""))
        elif not wait: L.append("Проекты: сейчас ничего не делаю.")
        for q in wait:
            probs.append("есть проект, который ждёт тебя")
            L.append("Ждёт твоего решения: «%s». %s" % (_ru_goal(q["goal"]), ("Посмотри варианты и выбери: /scout make %s НОМЕР." % q["id"]) if q.get("kind") == "scout" else ("Да: /approve %s, нет: /reject %s." % (q["id"], q["id"]))))
        if fin: L.append("Завершённых проектов %d: уйдут в архив сами через 3 дня после завершения." % len(fin))
    except Exception: L.append("Проекты: не смог прочитать.")
    try:
        mods = own_manifest()["modules"]; off = ST.get("own_off", {})
        if mods:
            L.append("Свои модули: " + "; ".join("%s %s" % (x["file"], ("отключён (%s)" % off[x["file"]]) if off.get(x["file"]) else "работает") for x in mods) + ".")
            if any(off.get(x["file"]) for x in mods): probs.append("отключён модуль")
    except Exception: pass
    wd = ST.get("wd_alert") or {}; last = max(wd.values()) if wd else 0
    if ST.get("paused"): probs.append("агент на паузе")
    if last and time.time() - last < 7200: probs.append("недавно была тревога сторожа")
    L.append("Цепочка циклов: %s, агент %s, тихий режим %s. Последняя тревога сторожа: %s." % ("включена" if ST.get("autorun", True) else "выключена", "на паузе" if ST.get("paused") else "работает", "включён" if (ST.get("quiet_until") or 0) > time.time() else "выключен", _ru_ago(time.time() - last) if last else "не было"))
    lim = _ru_limits(); near = [x for x in lim if x[1] >= 0.8 * x[2]]
    if near:
        probs.append("лимиты моделей почти исчерпаны")
        L.append("Лимиты: " + "; ".join("%s %d из %d" % x for x in near) + ". Из-за этого ответы могут задерживаться до сброса (около 03:00 по Москве).")
    elif lim: L.append("Лимиты: в порядке.")
    try:
        d = (ST.get("smap") or {}).get("days", {}).get(today) or {"p": 0, "b": 0}
        L.append("Проверка ответов сегодня: прошло %d, заблокировано %d." % (d["p"], d["b"]))
        if sm_braking(): probs.append("ответы на паузе после серии блокировок"); L.append("Ответы на паузе: подряд было заблокировано слишком много. Сама возобновится.")
    except Exception: pass
    try:
        w = ST.get("wt")
        if w: L.append("Веса: %s (день %d из %d, сигналов %d)." % ("влияют на решения" if w.get("on") else "пока только наблюдают", wt_days(), WT_OBS_DAYS, w.get("n", 0)))
    except Exception: pass
    try: L.append(ap_line())
    except Exception: pass
    return ("Всё в порядке." if not probs else "Обрати внимание: " + "; ".join(probs) + ".") + "\n\n" + "\n".join(L) + "\n\nКнопки: /menu. Всё подробно: /status all."
_status_before_mn = status_command
def status_command(c, raw=None):
    a = (raw or c).split()[1:]
    if a and a[0] == "all": return _status_before_mn(c, raw)
    tg(ru_status()[:3900])
MORE_TEXT = MORE_TEXT.replace("/more: этот список", "/menu: кнопки\n/autoproj: ежедневная работа (on|off|now)\n/more: этот список")
CHAT_SYS += " Also real: /menu (buttons) and /autoproj (daily own work: on, off, now)."
EXT_CMDS.update({"/menu": menu_command, "/status": status_command})
@on_log_pre
def _dm_log(kind, kw):
    """Direct messages on Bluesky and Mastodon are private: the public log keeps no text and only a hash of the person."""
    try:
        if kw.get("channel") == "dm":
            for k in ("to", "handle"):
                if k in kw: kw[k] = _h(kw[k])
            for k in ("text", "their", "dm_text", "question"):
                if k in kw: kw[k] = "[private message, not logged]"
    except Exception: pass
