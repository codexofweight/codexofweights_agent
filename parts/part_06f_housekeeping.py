# ---- housekeeping: memory of rejected ideas, stale questions, a 14-day trash, tool cooldown, and the architect's exception (/quiet) ----
EXT_CMDS = {}      # owner commands added by later parts: {"/name": handler(c, raw)}
def _toks(s): return set(re.findall(r"[a-z]{4,}", str(s).lower()))
def TOOL_COOLDOWN_ACTIVE():
    d = ST.get("tool_try_day")
    try: return bool(d) and (now().date() - datetime.date.fromisoformat(d)).days < cfg("tool_cooldown_days")
    except Exception: return False
def was_rejected(name, desc=""):
    """True if the owner already rejected this name, or an idea whose description is close to a rejected one (word overlap)."""
    rj = ST.get("rejected", {})
    if name in rj: return True
    a = _toks(desc)
    for v in rj.values():
        b = _toks(v.get("desc", ""))
        if a and b and len(a & b) / len(a | b) >= 0.5: return True
    return False
def _pending_now():
    out = {}
    for f in os.listdir(P("tools_pending")):
        if f.endswith(".json"):
            try: out[f[:-5]] = ("tool", str(json.load(open(P("tools_pending/" + f), encoding="utf-8")).get("description", ""))[:200])
            except Exception: out[f[:-5]] = ("tool", "")
    for f in os.listdir(P("modules_pending")):
        if f.endswith(".md"): out[f[:-3]] = ("module", f[:-3].replace("_", " "))
    return out
def sweep_pending():
    """Whatever left the pending folders without being approved counts as rejected: remember it (so it is not proposed again) and drop its open question."""
    cur = _pending_now(); seen = ST.setdefault("pend_seen", {}); rj = ST.setdefault("rejected", {})
    for n, v in list(seen.items()):
        if n in cur: continue
        if not (os.path.exists(P("tools/%s.json" % n)) or os.path.exists(P("modules_approved/%s.md" % n))):
            rj[n] = {"desc": v.get("desc", "")[:200], "day": today}
            bio_add("decision", "Idea %s rejected by the owner; not proposed again" % n, "owner decision", 1.0)
        seen.pop(n, None)
    for n, v in cur.items(): seen[n] = {"kind": v[0], "desc": v[1]}
    if len(rj) > 80:
        for k in sorted(rj, key=lambda k: rj[k]["day"])[:len(rj) - 80]: rj.pop(k)
    ST["asks"] = [a for a in ST.get("asks", []) if a["kind"] not in ("tool", "module") or a.get("name") in cur]
def purge_trash():
    """lab/rejected/ is a bin: files older than TRASH_DAYS are removed for good (once a day, only after a complete restore)."""
    if not LAB_OK[0] or ST.get("trash_day") == today: return
    ST["trash_day"] = today; n = 0
    for it in (_lab_list("lab/rejected") or []):
        m = re.match(r"(\d{4}-\d{2}-\d{2})__", it.get("name", ""))
        if it.get("type") != "file" or not m: continue
        try: old = (now().date() - datetime.date.fromisoformat(m.group(1))).days >= cfg("trash_days")
        except Exception: continue
        if old and mem_del("lab/rejected/" + it["name"], it["sha"]): n += 1
    if n: print("trash emptied:", n, flush=True)
# the architect is never muted: a STOP from the owner means "quiet for a while", never "forever". Critical alerts still pass.
_tg_raw = tg; _OWNER_TURN = [False]
CRITICAL = re.compile(r"песочниц|sandbox|identity|идентичн|ключ|token|ошибк", re.I)
def tg(text):
    if ST.get("quiet_until", 0) > time.time() and not _OWNER_TURN[0] and not CRITICAL.search(str(text)[:200]): return
    return _tg_raw(text)
_tg_poll_raw = tg_poll
def tg_poll(timeout=0):
    _OWNER_TURN[0] = True
    try: return _tg_poll_raw(timeout)
    finally: _OWNER_TURN[0] = False
_tool_command_raw = tool_command
def tool_command(c, raw):
    _tool_command_raw(c, raw); sweep_pending()
_assess_raw = assess_needs
def assess_needs():
    sweep_pending(); purge_trash()
    r = _assess_raw(); track_needs(); return r
def track_needs():
    """A TOOL need counts only after it was named on tool_need_days different days (documented, repeated need); modules and one-off wishes are not filtered here."""
    hist = ST.setdefault("need_hist", {}); keep = []
    for n in ST.get("needs_today", []):
        t = _toks(n["need"]); key = next((k for k, v in hist.items() if len(t & set(v["t"])) / (len(t | set(v["t"])) or 1) >= 0.4), None)
        if key is None: key = n["need"][:60]; hist[key] = {"t": sorted(t), "days": []}
        if today not in hist[key]["days"]: hist[key]["days"].append(today)
        if n["kind"] != "tool" or len(hist[key]["days"]) >= cfg("tool_need_days"): keep.append(n)
    ST["needs_today"] = keep
    for k in sorted(hist, key=lambda k: hist[k]["days"][-1])[:max(0, len(hist) - 60)]: hist.pop(k)
def quiet_command(c, raw=None):
    """/quiet <hours 1..168> or /quiet off: a temporary pause of proactive messages to the owner. Replies to the owner's own messages always go through."""
    a = c.split(" ", 1)[1].strip() if " " in c else ""
    if a == "off": ST["quiet_until"] = 0; tg("Тихий режим выключен."); return
    try: h = max(1, min(cfg("quiet_max_h"), int(a)))
    except Exception: tg("Команда: /quiet <часы, 1-168> или /quiet off. Я не молчу навсегда: ты для меня исключение. Важные тревоги (песочница, ошибки, идентичность) всё равно придут."); return
    ST["quiet_until"] = time.time() + h * 3600; bio_add("decision", "Owner asked for quiet for %d h (temporary; the owner is never muted for good)" % h, "owner decision", 1.0); tg("Хорошо, молчу %d ч. На твои сообщения отвечаю, критичные тревоги придут." % h)
EXT_CMDS["/quiet"] = quiet_command
