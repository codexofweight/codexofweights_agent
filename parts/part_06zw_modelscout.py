# ---- model scout (2026-11-18): once a week the agent looks for NEW free models at its providers, tests the newest with the same benchmarks as bench/ and proposes the good ones to the owner ----
# The first run only records what exists (no proposals). A model is proposed only if it passes >=90% of the code tests AND >=80% of the review checks. /model add PROVIDER MODEL_ID installs it under an alias (only
# for the roles the owner puts it on with /route; it never touches the owner chat or private memory by itself), /model del ALIAS removes it. At most 2 candidates are tested per week.
for _e in list(ST.get("extra_llms", [])):
    try:
        _p = [x for x in LLMS if x[0] == _e["provider"]]
        if _p and _p[0][2] and not any(x[0] == _e["alias"] for x in LLMS):
            LLMS.append((_e["alias"], _p[0][1], _p[0][2], _e["model"])); BUDGET[_e["alias"]] = 60; TOK_DAY[_e["alias"]] = 60000; TOK_MIN[_e["alias"]] = 4000; ROUTE_MODELS = ROUTE_MODELS + (_e["alias"],)
    except Exception: pass
def _bench_mods():
    sys.path.insert(0, P("bench"))
    try:
        import code_bench as B, review_bench as R
        return B, R
    except Exception as ex: print("model scout: bench not available:", type(ex).__name__, flush=True); return None, None
    finally:
        try: sys.path.remove(P("bench"))
        except ValueError: pass
def bench_model(B, R, base, key, model):
    """Returns (code_percent, review_percent). Same tasks and scoring as bench/code_bench.py and bench/review_bench.py."""
    got = tot = 0
    for tname, task, tests in B.TASKS:
        ans = B.call(base, key, model, B.PROMPT + task); a, b = B.score(B.extract(ans), tests) if not ans.startswith("ERROR") else (0, 1); got += a; tot += b; time.sleep(3)
    ok = 0
    for sid, rx, code in R.S:
        ans = B.call(base, key, model, R.PROMPT % code); j = R.judge(ans, rx) if not ans.startswith("ERROR") else "error"; ok += j in ("located", "ok"); time.sleep(3)
    return round(100 * got / max(tot, 1)), round(100 * ok / len(R.S))
def model_scout():
    """Weekly (WEEKLY_EXTRA). Returns '' or one line for the report. Never raises."""
    try:
        B, R = _bench_mods()
        if not B: return ""
        seen = ST.setdefault("models_seen", {}); first = not seen; B.MAX_PER = 60; fresh = []
        for name, base, kenv, default in B.PROVIDERS:
            key = os.environ.get(kenv, "")
            if not key: continue
            ids = B.discover(name, base, key, default)
            new = [i for i in ids if i not in seen.get(name, [])]
            if not first: fresh += [(name, base, key, i) for i in new]
            seen[name] = sorted(set(seen.get(name, [])) | set(ids))[-80:]
        if first or not fresh: return "Модели: новых бесплатных нет." if not first else ""
        done = []
        for name, base, key, mid in fresh[:2]:
            c, r = bench_model(B, R, base, key, mid); done.append("%s %s: код %d%%, проверка %d%%" % (name, mid, c, r)); log("model_scout", provider=name, model=mid, code=c, review=r)
            if c >= 90 and r >= 80: tg("Нашёл новую бесплатную модель, которая прошла наши замеры:\n%s (%s)\nКод: %d%%, поиск дыр: %d%%.\nПоставить: /model add %s %s\nПотом назначить роль: /route code|review %s,...\nВ чат с тобой и к личным данным она сама не попадёт." % (mid, name, c, r, name, mid, "<псевдоним>"))
        return "Модели: проверил %s." % "; ".join(done)
    except Exception as ex: print("model_scout failed:", type(ex).__name__, str(ex)[:80], flush=True); return ""
def model_command(c, raw=None):
    a = (raw or c).split(" ")[1:]; ex = ST.setdefault("extra_llms", [])
    if not a:
        tg("Модели провайдеров:\n" + "\n".join("%s: %s%s" % (n, m, "" if k else " (нет ключа)") for n, b, k, m in LLMS) + "\n\nДобавить: /model add провайдер модель · убрать: /model del псевдоним"); return
    if a[0] == "add" and len(a) == 3 and re.fullmatch(r"[A-Za-z0-9_./:\-]{3,80}", a[2]):
        pv = [x for x in LLMS if x[0] == a[1] and x[2]]
        if not pv or a[1] not in ("gemini", "groq", "sambanova", "cohere", "mistral", "openrouter"): tg("Нет такого провайдера с ключом."); return
        n = 1
        while any(x["alias"] == "%s%d" % (a[1][:4], n) for x in ex) or any(x[0] == "%s%d" % (a[1][:4], n) for x in LLMS): n += 1
        al = "%s%d" % (a[1][:4], n); ex.append(dict(alias=al, provider=a[1], model=a[2])); LLMS.append((al, pv[0][1], pv[0][2], a[2])); BUDGET[al] = 60; TOK_DAY[al] = 60000; TOK_MIN[al] = 4000
        globals()["ROUTE_MODELS"] = ROUTE_MODELS + (al,); tg("Добавил %s (%s, %s). Назначить роль: /route code %s,groq,gemini" % (al, a[1], a[2], al)); return
    if a[0] == "del" and len(a) == 2:
        ST["extra_llms"] = [x for x in ex if x["alias"] != a[1]]; LLMS[:] = [x for x in LLMS if x[0] != a[1]]
        for r_, v_ in list(ST.get("route", {}).items()): ST["route"][r_] = [x for x in v_ if x != a[1]] or None
        tg("Убрал %s (маршруты очищены)." % a[1]); return
    tg("Команды: /model, /model add провайдер модель, /model del псевдоним")
EXT_CMDS["/model"] = model_command
try: WEEKLY_EXTRA.append(model_scout)
except Exception: pass
