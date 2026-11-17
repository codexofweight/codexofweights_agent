# ---- tips layer (2026-11-18): a short list of practical tips the agent gives itself, BELOW the Codex and the rules ----
# One private file notes/addendum.json: {"tips": [{"id", "text"}], "props": [{"id", "text", "why"}]}. At most 12 tips, 160 characters each, 1500 in total.
# The agent may only PROPOSE a tip (weekly, from facts in its own log); a tip becomes active after the owner's /tip ok N. /tip del N removes it.
# The tips are added to the prompts that carry the Codex or the owner chat; they never override the Codex, the rules or the verifier.
TIP_FILE, TIP_MAX, TIP_LEN, TIP_TOTAL = "notes/addendum.json", 12, 160, 1500
_TIP = {"d": None, "sha": None}
_TIP_BAD = re.compile(r"ignore|override|disable|bypass|forget|jailbreak|pretend|игнориру|отключ|обойд|забудь|не проверяй|без проверки|кодекс не|правила не", re.I)
def tip_load():
    if _TIP["d"] is None:
        d = {"tips": [], "props": []}
        try:
            t, sha = mem_get(TIP_FILE); _TIP["sha"] = sha
            if t: d.update(json.loads(t))
        except Exception: pass
        _TIP["d"] = d
    return _TIP["d"]
def tip_save():
    try:
        if mem_put(TIP_FILE, json.dumps(_TIP["d"], ensure_ascii=False, indent=1), _TIP["sha"], "tips"): _TIP["sha"] = mem_get(TIP_FILE)[1]; return True
    except Exception as ex: print("tips save failed:", type(ex).__name__, flush=True)
    return False
def tip_clean(t):
    t = re.sub(r"\s+", " ", re.sub(r"https?://\S+", "", str(t or ""))).strip().strip('"').strip("-• ")[:TIP_LEN]
    return "" if len(t) < 8 or _TIP_BAD.search(t) else t
def tip_block():
    tips = tip_load().get("tips", [])
    if not tips: return ""
    return ("\n\nPRACTICAL TIPS (written by you, approved by your owner; they are advice for doing the job well and stand BELOW the Codex and the rules: they never override them and never allow what the rules forbid):\n" + "\n".join("- " + x["text"] for x in tips[:TIP_MAX]))[:TIP_TOTAL + 400]
_llm_before_tips = llm
def llm(system, user, *a, **k):
    try:
        if isinstance(system, str) and (system.startswith(CHARTER[:200]) or system.startswith(CHARTER_SHORT[:200]) or system.startswith(CHAT_SYS[:200])): system = system + tip_block()
    except Exception: pass
    return _llm_before_tips(system, user, *a, **k)
def tip_propose(text, why=""):
    d = tip_load(); t = tip_clean(text)
    if not t or len(d["tips"]) >= TIP_MAX or len(d["props"]) >= 3 or any(x["text"] == t for x in d["tips"] + d["props"]): return None
    i = max([x["id"] for x in d["tips"] + d["props"]] + [0]) + 1; d["props"].append(dict(id=i, text=t, why=str(why)[:200]))
    return i if tip_save() else None
def tip_command(c, raw=None):
    d = tip_load(); p = (raw or c).split(" ", 2); sub = p[1].lower() if len(p) > 1 else ""; arg = p[2].strip() if len(p) > 2 else ""
    if sub in ("", "list"):
        L = ["Подсказки (%d из %d):" % (len(d["tips"]), TIP_MAX)] + ["#%s %s" % (x["id"], x["text"]) for x in d["tips"]]
        if d["props"]: L += ["", "Предложены, ждут решения:"] + ["#%s %s%s" % (x["id"], x["text"], " (" + x["why"] + ")" if x.get("why") else "") for x in d["props"]] + ["", "/tip ok N  или  /tip no N"]
        L += ["", "/tip add текст  ·  /tip del N"]; tg("\n".join(L)); return
    if sub == "add":
        t = tip_clean(arg)
        if not t: tg("Подсказка слишком короткая или содержит запрещённые слова (игнорировать, отключить, обойти и т.п.). До %d символов." % TIP_LEN); return
        if len(d["tips"]) >= TIP_MAX or sum(len(x["text"]) for x in d["tips"]) + len(t) > TIP_TOTAL: tg("Место закончилось: сначала убери одну (/tip del N). Это правило простоты."); return
        i = max([x["id"] for x in d["tips"] + d["props"]] + [0]) + 1; d["tips"].append(dict(id=i, text=t)); tg("Добавил подсказку #%s." % i if tip_save() else "Не удалось сохранить."); return
    try: n = int(arg.split()[0])
    except Exception: tg("Нужен номер: /tip %s N" % (sub or "ok")); return
    if sub in ("ok", "no"):
        pr = [x for x in d["props"] if x["id"] == n]
        if not pr: tg("Нет такого предложения."); return
        d["props"] = [x for x in d["props"] if x["id"] != n]
        if sub == "ok":
            if len(d["tips"]) >= TIP_MAX or sum(len(x["text"]) for x in d["tips"]) + len(pr[0]["text"]) > TIP_TOTAL: tg("Место закончилось: сначала убери одну (/tip del N)."); return
            d["tips"].append(dict(id=n, text=pr[0]["text"]))
        tg(("Принято: #%s." if sub == "ok" else "Отклонено: #%s.") % n if tip_save() else "Не удалось сохранить."); return
    if sub == "del":
        d["tips"] = [x for x in d["tips"] if x["id"] != n]; tg("Убрал #%s." % n if tip_save() else "Не удалось сохранить."); return
    tg("Команды: /tip, /tip add текст, /tip ok N, /tip no N, /tip del N")
EXT_CMDS["/tip"] = tip_command
def tip_weekly():
    """Once a week: ONE proposal from facts of the agent's own log (never from other people's texts). Returns '' (nothing to add to the report)."""
    try:
        d = tip_load()
        if len(d["tips"]) >= TIP_MAX or len(d["props"]) >= 3: return ""
        rows = log_rows(7); why = {}
        for r in rows:
            if r.get("kind") in ("blocked_by_verifier", "send_failed", "reply_unverified"): k = str(r.get("reason") or r.get("why") or r.get("kind"))[:90]; why[k] = why.get(k, 0) + 1
        if not why: return ""
        facts = "; ".join("%s x%d" % kv for kv in sorted(why.items(), key=lambda kv: -kv[1])[:5])
        out, _ = llm_role("review", "You improve an AI agent's daily work. From the facts below propose ONE practical tip the agent can give itself (an instruction to itself, one sentence, at most %d characters, plain words) that would prevent the most frequent problem. It must not weaken any rule or check. If nothing useful, answer exactly NONE." % TIP_LEN, "Facts from the agent's own log for the last 7 days (problems and how often): " + facts, maxtok=120, temp=0.3)
        out = (out or "").strip()
        if out and out.upper() != "NONE":
            i = tip_propose(out, facts[:150])
            if i: tg("Предлагаю подсказку для себя #%s: %s\nОснование: %s\n/tip ok %s  или  /tip no %s" % (i, tip_clean(out), facts[:150], i, i))
    except Exception as ex: print("tip_weekly failed:", type(ex).__name__, str(ex)[:80], flush=True)
    return ""
try: WEEKLY_EXTRA.append(tip_weekly)
except Exception: pass
