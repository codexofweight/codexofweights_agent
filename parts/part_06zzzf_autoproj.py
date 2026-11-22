# ---- Daily own work (2026-11-23): once a day, right after the limits reset, the agent starts ONE own module (/make) from its own needs and ONE scouting (/scout) from the topic of its plan. ----
# Owner decisions: ON from the start; reports in plain Russian. What stays with the owner: installing a module (/approve) and choosing a scouting result. Brakes: it skips the day when every model is
# already more than 60% used; it switches itself OFF after 3 failed or rejected results in a row (and says so). Commands: /autoproj, /autoproj on|off|now.
def _apr():
    w = ST.setdefault("ap", {}); w.setdefault("on", True); w.setdefault("day", ""); w.setdefault("off_why", ""); w.setdefault("res", []); w.setdefault("last", "")
    return w
def _ap_room():
    lim = _ru_limits(); free = [x for x in lim if x[2] and x[1] < 0.6 * x[2]]
    return (bool(free) or not lim), (max(lim, key=lambda x: x[1] / float(x[2] or 1)) if lim else ("", 0, 1))
def _ap_res(x): w = _apr(); w["res"] = (w["res"] + [x])[-10:]
def _ap_check_off():
    w = _apr(); r = w["res"][-3:]
    if w["on"] and len(r) == 3 and all(x in ("fail", "rej") for x in r):
        w["on"] = False; w["off_why"] = "3 подряд неудачи или отказа"; tg("Ежедневную работу я выключил сам: три результата подряд были неудачными или ты их отклонял. Включить снова: /autoproj on")
def ap_run(force=False):
    w = _apr()
    if not force and (not w["on"] or w["day"] == today): return
    _ap_check_off()
    if not w["on"] and not force: return
    w["day"] = today; ok, worst = _ap_room()
    if not ok: w["last"] = "пропустил: лимиты почти исчерпаны"; tg("Сегодняшнюю работу пропускаю: все модели уже заняты больше чем на 60%% (самая загруженная: %s, %d из %d). Попробую завтра." % worst); return
    allp = proj_all()
    if any(q.get("status") in ("active", "waiting_owner") for q in allp):
        w["last"] = "пропустил: есть незавершённое"; tg("Сегодня новую работу не начинаю: есть незавершённый проект. Посмотри /projects."); return
    done = []; ns = ST.get("needs_today") or []
    if ns:
        n = ns[0]; i = proj_new("make", ("Build one small own module (standard library only, at most 150 lines) for this need of the agent: %s. Why it matters: %s" % (str(n.get("need", ""))[:150], str(n.get("why", ""))[:80]))[:300], {"auto": True})
        if i: done.append("Модуль: делаю по своей нужде «%s» (проект %s)." % (str(n.get("need", ""))[:80], i))
    focus = str((ST.get("plan") or {}).get("focus") or "")
    if len(focus) >= 15:
        i = proj_new("scout", "Find open-source ideas on GitHub useful for the agent on this topic: " + focus[:200], {"auto": True})
        if i: done.append("Разведка: ищу на GitHub по теме «%s» (проект %s)." % (focus[:80], i))
    w["last"] = "начал: %d" % len(done) if done else "нечего делать"
    tg(("Сегодняшняя работа началась.\n" + "\n".join("— " + x for x in done) + "\nКогда будет готово, напишу. Устанавливать модуль буду только после твоего «да».") if done else "Сегодня заняться нечем: нет ни новой нужды, ни темы плана. Попробую завтра.")
def ap_line():
    w = _apr()
    return "Ежедневная работа: %s%s." % ("включена" if w["on"] else "выключена (%s)" % (w["off_why"] or "тобой"), (", сегодня: " + w["last"]) if w["last"] and w["day"] == today else "")
_pt_before_ap = proj_tick
def proj_tick():
    _pt_before_ap()
    try:
        for q in proj_all():
            d = q.setdefault("data", {})
            if d.get("auto") and q.get("status") == "failed" and not d.get("ap_seen"): d["ap_seen"] = True; proj_save(q); _ap_res("fail")
        ap_run()
    except Exception as ex: print("daily work failed:", type(ex).__name__, flush=True)
_md_before_ap = make_decide
def make_decide(pid, ok):
    auto = bool(((proj_load(pid) or {}).get("data") or {}).get("auto"))
    r = _md_before_ap(pid, ok)
    try:
        if auto: _ap_res("ok" if ok else "rej"); ok or _ap_check_off()
    except Exception: pass
    return r
def autoproj_command(c, raw=None):
    a = (raw or c).split()[1:]; w = _apr(); sub = a[0].lower() if a else ""
    if sub == "on": w["on"] = True; w["off_why"] = ""; w["res"] = []; tg("Ежедневная работа включена. Первая начнётся после сброса лимитов (около 03:00 по Москве) или сразу: /autoproj now")
    elif sub == "off": w["on"] = False; w["off_why"] = ""; tg("Ежедневная работа выключена. Включить: /autoproj on")
    elif sub == "now": ap_run(force=True)
    else: tg(ap_line() + "\n\nРаз в день после сброса лимитов (около 03:00 по Москве) я сам делаю один модуль по своей нужде и одну разведку на GitHub по теме плана. Модуль ставлю только с твоего «да». Если все модели заняты больше чем на 60%, день пропускаю. После трёх неудач или отказов подряд выключаюсь сам.\n\n/autoproj on, /autoproj off, /autoproj now (начать сейчас)")
EXT_CMDS["/autoproj"] = autoproj_command
