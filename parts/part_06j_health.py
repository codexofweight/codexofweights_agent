# ---- long-life health: size caps, log rotation, memory audit (archive stale, flag conflicts, never delete), daily health report ----
def trim_state():
    n = 0; mx = cfg("state_list_max")
    for k, v in list(ST.items()):
        if isinstance(v, list) and len(v) > mx: ST[k] = v[-int(mx * 0.6):]; n += 1
    try:
        L = open(P("logs/actions.jsonl"), encoding="utf-8").read().splitlines(); keep = cfg("log_keep_lines")
        if len(L) > keep * 2: open(P("logs/actions.jsonl"), "w", encoding="utf-8").write("\n".join(L[-keep:]) + "\n"); n += 1
    except Exception: pass
    return n
def memory_audit():
    """Weekly. Facts that are unverified, single-mention, low-confidence and old move to memory/archive_facts.json (kept, not deleted). The closest fact pairs are checked for conflict; conflicts are only FLAGGED for the owner."""
    if not MEM_TOKEN or not LIVE: return None
    if ST.get("audit_day") and (now().date() - datetime.date.fromisoformat(ST["audit_day"])).days < cfg("audit_days"): return None
    ST["audit_day"] = today; F, E_ = facts(); old = []; keep = []
    for it in F:
        age = (now().date() - datetime.date.fromisoformat(it.get("date", today))).days if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(it.get("date", ""))) else 0
        (old if (it.get("source") != "own_statement" and it.get("n", 1) == 1 and it.get("conf", 0.5) < 0.5 and age > cfg("stale_days")) else keep).append(it)
    if old:
        t, sh = mem_get("memory/archive_facts.json")
        try: A = json.loads(t)
        except Exception: A = []
        if mem_put("memory/archive_facts.json", json.dumps(A + [dict(x, archived=today) for x in old], ensure_ascii=False)[:900000], sh, "archive stale facts"):
            ids = {x["id"] for x in old}; F[:] = keep
            for i in ids: E_.pop(i, None)
            _MEM["dirty"] = True
    pairs = []
    for a in F[-60:]:
        for b in F:
            if a["id"] < b["id"] and a["id"] in E_ and b["id"] in E_ and cos(E_[a["id"]], E_[b["id"]]) > 0.8 and "conflict" not in a: pairs.append((a, b))
    flagged = []
    for a, b in pairs[:3]:
        v = (micro("classifier", "Labels: conflict, same, unrelated. Do these two statements contradict each other? A: %s | B: %s" % (a["text"], b["text"]), 10) or "").lower()
        if "conflict" in v: a["conflict"] = b["id"]; b["conflict"] = a["id"]; flagged.append((a["text"][:80], b["text"][:80])); _MEM["dirty"] = True
    if old or flagged: bio_add("episode", "Memory audit: archived %d stale facts, flagged %d conflicts" % (len(old), len(flagged)), "memory audit", 1.0)
    if flagged: tg("Проверка памяти: нашёл возможные противоречия (ничего не менял):\n" + "\n".join("- «%s» против «%s»" % x for x in flagged))
    return len(old), len(flagged)
def health_report():
    L = []; sz = os.path.getsize(P("state/state.json")) // 1024 if os.path.exists(P("state/state.json")) else 0
    L.append("state: %d КБ%s" % (sz, " (много)" if sz > 400 else ""))
    try: L.append("журнал: %d строк" % len(open(P("logs/actions.jsonl"), encoding="utf-8").read().splitlines()))
    except Exception: L.append("журнал: нет")
    try: L.append("факты: %d" % len(facts()[0]))
    except Exception: pass
    pr = proj_all(); L.append("проекты: активных %d, ждут тебя %d, остановлено %d" % (sum(q["status"] == "active" for q in pr), sum(q["status"] == "waiting_owner" for q in pr), sum(q["status"] == "failed" for q in pr)))
    L.append("песочница: %s, отклонённых идей помню: %d, навыков: %d" % ("ok" if SANDBOX_OK[0] else "ВЫКЛ", len(ST.get("rejected", {})), len(os.listdir(P("skills")))))
    L.append("ошибок доставки за 14 дней логов: %d" % sum(1 for l in open(P("logs/actions.jsonl"), encoding="utf-8").read().splitlines()[-1500:] if '"send_failed"' in l) if os.path.exists(P("logs/actions.jsonl")) else "")
    return "\n".join(x for x in L if x)
def health_daily():
    if ST.get("health_day") == today: return
    ST["health_day"] = today; trim_state(); r = memory_audit(); ST["health"] = health_report()
def health_command(c, raw=None): tg("Здоровье агента:\n" + health_report())
EXT_CMDS["/health"] = health_command
_cm2_raw = create_module
def create_module():
    r = _cm2_raw()
    try: health_daily()
    except Exception as ex: print("health failed:", type(ex).__name__, flush=True)
    return r
