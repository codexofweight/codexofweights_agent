# ---- resilience for years of unattended work: model auto-replacement, weekly report, long-owner-absence mode ----
_BAD_MODEL = re.compile(r"embed|vision|audio|tts|whisper|guard|moderat|image|rerank|transcri|ocr|safeguard|speech|live|dall|imagen|veo|robot|aqa", re.I)
def _model_ids(base, key):
    try: d = http(base.rstrip("/") + "/models", headers={"Authorization": "Bearer " + key})
    except Exception as ex: return None
    lst = d.get("data") if isinstance(d, dict) else d
    if not isinstance(lst, list): return None
    return [str(x.get("id", "")).replace("models/", "", 1) for x in lst if isinstance(x, dict) and x.get("id")]
def _score(cur, cand):
    n = 0
    for a, b in zip(re.split(r"[-_:/.]", cur.lower()), re.split(r"[-_:/.]", cand.lower())):
        if a != b: break
        n += 1
    return n
def _works(base, key, model):
    try:
        r = http(base + "/chat/completions", {"model": model, "max_tokens": 8, "messages": [{"role": "user", "content": "Say ok."}]}, {"Authorization": "Bearer " + key})
        return bool(r.get("choices"))
    except Exception: return False
def model_refresh():
    """Once a week: if a provider no longer lists the model I use, choose the closest listed text model, test it with one tiny call, switch, and tell the owner in one line."""
    if time.time() - ST.get("model_check", 0) < 6.5 * 86400: return
    ST["model_check"] = time.time(); ov = ST.setdefault("model_override", {}); notes = []
    for i, (name, base, key, model) in enumerate(list(LLMS)):
        if not key: continue
        ids = _model_ids(base, key)
        if not ids or model in ids: continue
        pool = [x for x in ids if not _BAD_MODEL.search(x)]
        if name == "openrouter": pool = [x for x in pool if x.endswith(":free")] or pool
        pool.sort(key=lambda x: (_score(model, x), x), reverse=True)
        for cand in pool[:3]:
            if _score(model, cand) and _works(base, key, cand):
                LLMS[i] = (name, base, key, cand); ov[name] = cand; notes.append("%s: %s -> %s" % (name, model, cand)); break
        else: notes.append("%s: модель %s пропала, замену не нашёл (провайдер пока пропускается)" % (name, model))
    if notes:
        log("model_replaced", notes=notes); bio_add("decision", "Models auto-replaced: " + "; ".join(notes), "agent decision", 0.8); tg("Заменил модель у провайдера (старую убрали):\n" + "\n".join(notes))
def apply_model_overrides():
    for name, cand in (ST.get("model_override") or {}).items():
        for i, (n, base, key, model) in enumerate(LLMS):
            if n == name and key and model != cand: LLMS[i] = (n, base, key, cand)
apply_model_overrides()
def weekly_report():
    if time.time() - ST.get("weekly_ts", 0) < 6.9 * 86400: return
    ST["weekly_ts"] = time.time(); rows = log_rows(7); c = {}
    for r in rows: c[r.get("kind")] = c.get(r.get("kind"), 0) + 1
    L = ["Недельный отчёт.", "Посты: %d, ответы: %d, первые контакты: %d, заблокировано проверкой: %d, ошибок отправки: %d" % (c.get("post", 0), c.get("reply", 0), c.get("reach", 0), c.get("blocked_by_verifier", 0), c.get("send_failed", 0))]
    pv = []
    for name, _, key, model in LLMS:
        if not key: pv.append("%s: ключа нет" % name); continue
        cd = int(COOL.get(name, 0) - time.time()) // 60
        pv.append("%s (%s): %s" % (name, model.split("/")[-1][:28], "пауза %d мин" % cd if cd > 0 else "ok"))
    L.append("Провайдеры: " + "; ".join(pv)); L.append(health_report())
    d = absence_days()
    if d >= 3: L.append("Ты не писал мне %d дн.%s" % (d, " Работаю в экономном режиме." if ABS_LEVEL[0] else ""))
    nd = [n["need"][:70] for n in ST.get("needs_today", [])][:3]
    if nd: L.append("Что мне нужно: " + "; ".join(nd))
    L.append("Если что-то сломалось в ключах (401/403 в журнале) или модели, напиши /health.")
    tg("\n".join(L))
# ---- long absence of the owner: do less, never stop, never ask for anything ----
ABS_LEVEL = [0]; _ABS_BASE = {}
def absence_days():
    return int((time.time() - ST.setdefault("owner_seen", time.time())) // 86400)
_tg_poll_abs = tg_poll
def tg_poll(timeout=0):
    off = ST.get("tg_offset", 0); r = _tg_poll_abs(timeout)
    if ST.get("tg_offset", 0) != off: ST["owner_seen"] = time.time()
    return r
_cfg_abs = cfg
def cfg(k):
    if ABS_LEVEL[0] and k in ("proj_max_active", "content_plans_day") : return 0
    return _cfg_abs(k)
def apply_absence():
    d = absence_days(); lvl = 2 if d >= 45 else (1 if d >= 14 else 0)
    if not _ABS_BASE: _ABS_BASE.update(MAX_POSTS=MAX_POSTS, MAX_REPLIES=MAX_REPLIES, MAX_INIT=MAX_INIT, REACH=REACH_MAX_DAY, GAP=POST_GAP_H)
    if lvl == ABS_LEVEL[0]: return
    g = globals(); b = _ABS_BASE; prev = ABS_LEVEL[0]; ABS_LEVEL[0] = lvl
    if lvl == 0: g.update(MAX_POSTS=b["MAX_POSTS"], MAX_REPLIES=b["MAX_REPLIES"], MAX_INIT=b["MAX_INIT"], REACH_MAX_DAY=b["REACH"], POST_GAP_H=b["GAP"]); tg("С возвращением! Выхожу из экономного режима, всё работает как раньше.")
    elif lvl == 1: g.update(MAX_POSTS=1, MAX_REPLIES=min(b["MAX_REPLIES"], 15), MAX_INIT=2, REACH_MAX_DAY=2, POST_GAP_H=max(b["GAP"], 12))
    else: g.update(MAX_POSTS=1, MAX_REPLIES=8, MAX_INIT=1, REACH_MAX_DAY=0, POST_GAP_H=48)
    log("absence_mode", level=lvl, days=d)
    if lvl > prev: tg("Ты не писал %d дн., перехожу в экономный режим (уровень %d): меньше постов, ответов и контактов, новых проектов не начинаю. Напиши мне любое сообщение, и всё вернётся." % (d, lvl))
_cm3_raw = create_module
def create_module():
    for f in (apply_absence, model_refresh, weekly_report):
        try: f()
        except Exception as ex: print(f.__name__, "failed:", type(ex).__name__, str(ex)[:100], flush=True)
    return _cm3_raw()
