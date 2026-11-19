# Focus: while an owner's project (/make, /scout) is active, the agent puts it first: no original posts, no reading/research, no Moltbook initiative; replies to people and the owner's chat go on. The project gets up to 3 steps per round and rounds are shorter. /focus shows or changes it.
def focus_on():
    if ST.get("focus", "auto") == "off": return False
    try: return any(q["status"] == "active" and q["kind"] in ("make", "scout") for q in proj_all())
    except Exception: return False
_research_old = research
def research():
    on = focus_on()
    if on != bool(ST.get("focus_on")):
        ST["focus_on"] = on; tg("Режим проекта %s: %s" % ("включён" if on else "выключен", "посты, чтение и инициатива на Moltbook на паузе, ресурсы идут на проект" if on else "всё снова в обычном режиме"))
    if on: ST["last_post"] = time.time(); return          # holds the next original post back; replies to people continue
    return _research_old()
_rank_old = rank_discover
def rank_discover(ms): return [] if focus_on() else _rank_old(ms)
_mbr_old = mb_round
def mb_round():
    if not focus_on(): return _mbr_old()
_rp_old = round_pause
def round_pause(): return min(_rp_old(), 120) if focus_on() else _rp_old()
def _snap(): return json.dumps([(q["id"], q["data"].get("stage"), q["data"].get("try"), q["errors"]) for q in proj_all() if q["status"] == "active"])
_pt_old = proj_tick
def proj_tick():
    prev = _snap(); _pt_old()
    for _ in range(3):
        cur = _snap()
        if cur == prev or not focus_on(): break              # no progress (limits or waiting) -> do not push
        prev = cur; _pt_old()
def focus_command(c, raw):
    a = raw.split()[1:]
    if a and a[0] in ("auto", "off"): ST["focus"] = a[0]; save_state(); return tg("Режим проекта: %s" % ("автоматически (включается, пока идёт проект)" if a[0] == "auto" else "выключен"))
    tg("Режим проекта: %s, сейчас %s.\nПорядок приоритетов: 1 чат владельца, 2 ответы людям, 3 проект, 4 посты, 5 чтение и поиск. Пока идёт проект, 4 и 5 на паузе.\nИзменить: /focus auto | /focus off" % (ST.get("focus", "auto"), "включён" if focus_on() else "выключен"))
EXT_CMDS["/focus"] = focus_command
