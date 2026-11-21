# Watchdog (2026-11-20). Runs after all other parts, before the main loop.
# 1) tells the owner in Telegram if the loader had to skip/repair a part (see _PART_FAILS in agent.py);
# 2) checks that critical functions are still callable; 3) alerts when the language models fail many times in a row.
import time as _wt
_CRIT = ("http", "llm", "tg", "log", "verify", "guard_json", "wait_and_chat", "do_post", "research", "tg_poll")
def _wd_alert(key, text, every=6 * 3600):
    try:
        al = ST.setdefault("wd_alert", {})
        if _wt.time() - al.get(key, 0) < every: return
        al[key] = _wt.time(); tg("⚠️ Сторож: " + text)
    except Exception: pass
try:
    for _n, _why in list(globals().get("_PART_FAILS", [])):
        log("part_guard", part=_n, why=_why)
        _wd_alert("part:" + _n + _why[:40], "файл %s не загрузился или сломал другие функции (%s). Я его пропустил и всё откатил, агент работает без него. Исправь или удали файл." % (_n, _why[:150]), every=24 * 3600)
    _missing = [n for n in _CRIT if not callable(globals().get(n))]
    if _missing: _wd_alert("crit", "сломаны функции: %s. Нужен откат последней загрузки." % ", ".join(_missing))
except Exception as _e: print("watchdog init failed:", repr(_e)[:100], flush=True)
_wd_llm_orig = llm
_wd_streak = [0]
def llm(*a, **k):
    _pr = PRIO[0]      # background tasks (priority 4-5) are limited to a share of the budget on purpose; their refusals are not an outage
    try: r = _wd_llm_orig(*a, **k)
    except Exception:
        if _pr > 3: raise
        _wd_streak[0] += 1
        if _wd_streak[0] >= 8: _wd_alert("llm", "модели не отвечают %d раз подряд (лимиты или ошибка сервиса). Агент ждёт, ничего не ломается." % _wd_streak[0], every=8 * 3600)
        raise
    if _pr > 3: return r
    if r and r[0]: _wd_streak[0] = 0
    else:
        _wd_streak[0] += 1
        if _wd_streak[0] >= 8: _wd_alert("llm", "модели не отвечают %d раз подряд (лимиты или ошибка сервиса). Агент ждёт, ничего не ломается." % _wd_streak[0], every=8 * 3600)
    return r
