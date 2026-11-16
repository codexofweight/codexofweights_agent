# ---- biographical memory: a verifiable history (decisions, promises, mistakes, extensions, episodes) with source, confidence and a trail of corrections ----
BIO_KINDS = ("decision", "promise", "mistake", "extension", "episode")
BIOQ = []; _BIOC = [0, {}]
def bio_add(kind, text, source, conf=0.8, status="active"):
    """One line per meaningful event. Same kind+text is never recorded twice. Entries are never edited: a correction is a new line that points to the old one."""
    if kind not in BIO_KINDS or not text: return None
    i = "b" + hashlib.sha1((kind + "|" + text).encode()).hexdigest()[:8]
    if any(q.get("id") == i for q in BIOQ): return i
    BIOQ.append({"id": i, "ts": now().isoformat(timespec="seconds"), "kind": kind, "text": str(text)[:400], "source": str(source)[:160], "conf": conf, "status": status}); return i
def bio_correct(i, text, source, conf=0.9, status=None):
    BIOQ.append({"op": "correct", "id": i, "ts": now().isoformat(timespec="seconds"), "text": str(text)[:400], "source": str(source)[:160], "conf": conf, "status": status})
BIO_MAP = {"send_failed": ("mistake", lambda k: "A message could not be delivered: %s" % (k.get("reason") or k.get("text") or "")[:150], "log", 1.0),
           "gave_up": ("mistake", lambda k: "Gave up on an event after retries: %s" % str(k.get("why") or k.get("uri") or "")[:150], "log", 1.0),
           "memory_failed": ("mistake", lambda k: "Memory write failed: %s" % str(k.get("why") or "")[:150], "log", 1.0),
           "tool_proposed": ("extension", lambda k: "Proposed tool %s (%s)" % (k.get("name"), str(k.get("hook") or "")), "log", 1.0),
           "module_proposed": ("extension", lambda k: "Proposed module design %s" % k.get("name"), "log", 1.0),
           "tool_rejected": ("decision", lambda k: "Tool %s not offered: %s" % (k.get("name") or "?", str(k.get("why") or "")[:120]), "log", 0.9),
           "module_rejected": ("decision", lambda k: "Module idea dropped: %s" % str(k.get("why") or "")[:120], "log", 0.9),
           "reach": ("episode", lambda k: "First contact (%s) with %s, approved by %s" % (k.get("channel"), k.get("to"), (k.get("trace") or {}).get("approved_by", "?")), "log", 1.0),
           "mute": ("episode", lambda k: "Stopped contact with %s: asked to stop" % k.get("author"), "log", 1.0)}
_log_plain = log
def log(kind, **kw):
    r = _log_plain(kind, **kw)
    try:
        if kind in BIO_MAP:
            bk, fn, src, cf = BIO_MAP[kind]; bio_add(bk, fn(kw), "%s:%s@%s" % (src, kind, now().isoformat(timespec="minutes")), cf)
    except Exception: pass
    return r
def _bio_month(ym):
    t, sha = mem_get("bio/%s.jsonl" % ym); return t, sha
def bio_flush():
    if not (MEM_TOKEN and LIVE and BIOQ): return
    ym = today[:7]; t, sha = _bio_month(ym)
    have = set(); 
    for l in t.splitlines():
        try: d = json.loads(l); have.add((d.get("id"), d.get("op"), d.get("ts")))
        except Exception: pass
    new = [q for q in BIOQ if (q.get("id"), q.get("op"), q.get("ts")) not in have and not (q.get("op") is None and any(h[0] == q["id"] and h[1] is None for h in have))]
    if new and not mem_put("bio/%s.jsonl" % ym, t + ("\n" if t and not t.endswith("\n") else "") + "\n".join(json.dumps(q, ensure_ascii=False) for q in new) + "\n", sha, "bio"): return
    BIOQ.clear(); _BIOC[0] = 0
def bio_load():
    if time.time() - _BIOC[0] < 600 and _BIOC[1]: return _BIOC[1]
    ents = {}; prev = (now().replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
    for ym in (prev, today[:7]):
        t, _ = _bio_month(ym) if MEM_TOKEN else ("", None)
        for q in [q for q in BIOQ] + [json.loads(l) for l in t.splitlines() if l.strip().startswith("{")]:
            e = ents.setdefault(q["id"], {"fix": []}) if q.get("op") else ents.setdefault(q["id"], {"fix": []})
            if q.get("op") == "correct": e["fix"].append(q)
            else: e.update(q)
    _BIOC[0] = time.time(); _BIOC[1] = {k: v for k, v in ents.items() if v.get("kind")}; return _BIOC[1]
def bio_digest(n=8):
    """Compact view for the owner chat: open promises first, then the latest items per kind, each with source, confidence and corrections."""
    try: ents = bio_load()
    except Exception: return ""
    def line(e):
        fx = e["fix"][-1] if e["fix"] else None; st = (fx or {}).get("status") or e.get("status")
        return "- [%s %s%s] %s (источник: %s, уверенность %.1f)%s" % (e["kind"], e["ts"][:10], ", " + st if st not in (None, "active") else "", (fx or e)["text"][:140], e.get("source", "?")[:40], e.get("conf", 0), " [исправлено %d раз]" % len(e["fix"]) if e["fix"] else "")
    L = ["Открытые обещания:"] + [line(e) for e in ents.values() if e["kind"] == "promise" and ((e["fix"] or [{}])[-1].get("status") or e.get("status")) == "active"][:5]
    L += ["Последнее важное:"] + [line(e) for e in sorted((e for e in ents.values() if e["kind"] != "promise"), key=lambda e: e["ts"], reverse=True)[:n]]
    return "\n".join(L) if len(L) > 2 else ""
def bio_index_sync():
    if not (MEM_TOKEN and LIVE) or ST.get("bio_idx_day") == today: return
    try: ents = bio_load()
    except Exception: return
    cnt = {k: sum(1 for e in ents.values() if e["kind"] == k) for k in BIO_KINDS}
    txt = "# Biography index (%s)\n\nEntries are append-only: a correction is a new line pointing to the old one (see bio/YYYY-MM.jsonl).\n\nCounts (last 2 months): %s\n\n%s\n" % (today, json.dumps(cnt), bio_digest(15))
    if _put("bio/INDEX.md", txt, "bio index"): ST["bio_idx_day"] = today
def bio_command(c, raw):
    """Owner: /bio (view) | /promise <text> | /done <id> | /correct <id> <text>"""
    arg = raw.split(" ", 1)[1].strip() if " " in raw else ""
    if c == "/bio": tg(bio_digest(12) or "История пока пуста.")
    elif c.startswith("/promise "): tg("Записал обещание %s." % bio_add("promise", arg, "owner chat", 1.0))
    elif c.startswith("/done "): bio_correct(arg.split()[0], "Выполнено", "owner chat", 1.0, "fulfilled"); tg("Отметил выполненным.")
    elif c.startswith("/correct ") and " " in arg: i, tx = arg.split(" ", 1); bio_correct(i, tx, "owner chat", 1.0); tg("Исправление записано (старая запись сохранена).")
