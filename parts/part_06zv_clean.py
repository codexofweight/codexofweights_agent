# ---- memory tidying (2026-11-20). /clean = report only. /clean go = archive stale notes (moved to archive/, nothing is deleted, no model calls). ----
# Rules: people/*.json not touched for 45 days (and fewer than 5 exchanges), or for 120 days; diary/ and research/ day files older than 30 days, needs/ older than 10 days.
# Never touched: memory/, bio/, state/, tools/, lab/, convos/, anything outside the four folders above.
_CL_DAYS = {"people": 45, "diary": 30, "research": 30, "needs": 10}
_CL_MAX_OPS = 25            # per command call, so a run stays short
def _cl_age(day_str):
    try: return (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(day_str)).days
    except Exception: return None
def _cl_scan():
    """-> list of (path, sha, why). Reads people notes one by one (one API call each); other folders are judged by the date in the file name."""
    out = []
    for d in ("diary", "research", "needs"):
        try: lst = _mem_api(d)
        except Exception: continue
        for f in lst if isinstance(lst, list) else []:
            m = re.match(r"(\d{4}-\d{2}-\d{2})\.md$", str(f.get("name", "")))
            a = _cl_age(m.group(1)) if m else None
            if a is not None and a > _CL_DAYS[d]: out.append((f["path"], f["sha"], "%s %d d" % (d, a)))
    try: lst = _mem_api("people")
    except Exception: lst = []
    for f in lst if isinstance(lst, list) else []:
        if not str(f.get("name", "")).endswith(".json"): continue
        t, sha = mem_get(f["path"])
        try: d_ = json.loads(t)
        except Exception: continue
        a = _cl_age(str(d_.get("last") or d_.get("first") or "")[:10])
        n = int(d_.get("n", 0) or 0)
        if a is not None and ((a > _CL_DAYS["people"] and n < 5) or a > 120): out.append((f["path"], sha or f["sha"], "person %d d, %d msg" % (a, n)))
    return out
def _cl_move(path, sha):
    t, s = mem_get(path)
    if s is None or not t: return False
    if not mem_put("archive/" + path, t, None, "archive"): return False
    try: _mem_api(path, {"message": "archive", "sha": s}, "DELETE"); return True
    except Exception as ex: print("clean delete failed:", type(ex).__name__); return False
def clean_command(c, raw):
    go = c.split()[1:2] == ["go"]
    if go and not LIVE: tg("Сейчас режим без отправки (нет LIVE). Чистка не выполняется."); return
    items = _cl_scan()
    if not items: tg("Память чистая: устаревших записей нет."); return
    by = {}
    for p, s, w in items: by[p.split("/")[0]] = by.get(p.split("/")[0], 0) + 1
    if not go:
        tg("К архивации: %d (%s).\nПримеры: %s\nВ archive/ они переедут целиком, ничего не удаляется. Выполнить: /clean go" % (len(items), ", ".join("%s %d" % kv for kv in by.items()), "; ".join(w + " " + p.split("/")[-1][:24] for p, s, w in items[:4])))
        return
    done = 0
    for p, s, w in items[:_CL_MAX_OPS]:
        if _cl_move(p, s): done += 1
    log("memory_clean", moved=done, left=len(items) - done)
    tg("Переехало в archive/: %d. Осталось: %d.%s" % (done, len(items) - done, " Повтори /clean go." if len(items) - done > 0 else ""))
EXT_CMDS["/clean"] = clean_command
def clean_weekly():
    """Called from the weekly report (WEEKLY_EXTRA): archives stale notes by itself (moved to archive/, nothing deleted). Returns one line, never raises."""
    try:
        if not (LIVE and MEM_TOKEN): return ""
        items = _cl_scan()
        if not items: return "Память: чистка не нужна."
        done = sum(1 for p_, s_, w_ in items[:_CL_MAX_OPS] if _cl_move(p_, s_))
        log("memory_clean", moved=done, left=len(items) - done, auto=True)
        return "Память: в archive/ перенесено %d устаревших записей%s. Вернуть можно из archive/." % (done, ", осталось %d (в следующий раз)" % (len(items) - done) if len(items) > done else "")
    except Exception as ex: return "Память: чистка не удалась (%s)." % type(ex).__name__
try: WEEKLY_EXTRA.append(clean_weekly)
except Exception: pass
