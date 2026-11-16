# ---- full-text search over the agent's own history (SQLite FTS5, in memory, rebuilt on demand): action log + biography; a complement to, not a replacement for, the memory notes ----
import sqlite3
def hist_index():
    """Builds a throw-away FTS5 index from logs/actions.jsonl and the biography. Nothing is stored on disk, so nothing can go stale or leak."""
    db = sqlite3.connect(":memory:"); db.execute("create virtual table h using fts5(src, ts, body, tokenize='unicode61')")
    try:
        for l in open(P("logs/actions.jsonl"), encoding="utf-8").read().splitlines()[-4000:]:
            try: r = json.loads(l)
            except Exception: continue
            body = " ".join(str(r.get(k, "")) for k in ("text", "why", "name", "theme", "reason", "reply") if r.get(k))
            if body: db.execute("insert into h values (?,?,?)", ("log:" + str(r.get("kind", "")), str(r.get("ts", ""))[:19], body[:500]))
    except Exception: pass
    try:
        for e in bio_load().values():
            fx = e["fix"][-1] if e.get("fix") else None
            db.execute("insert into h values (?,?,?)", ("bio:" + e["kind"] + ":" + e["id"], e["ts"][:19], ((fx or e)["text"])[:500]))
    except Exception: pass
    return db
def hist_search(q, n=6):
    """Returns up to n (source, date, snippet) matches; the query is reduced to plain words, so no FTS syntax can break it."""
    words = re.findall(r"\w{3,}", str(q).lower())[:8]
    if not words: return []
    try: return hist_index().execute("select src, ts, snippet(h, 2, '[', ']', '...', 18) from h where h match ? order by rank limit ?", (" OR ".join('"%s"' % w for w in words), n)).fetchall()
    except Exception as ex: print("history search failed:", type(ex).__name__, flush=True); return []
def find_command(c, raw=None):
    q = c.split(" ", 1)[1].strip() if " " in c else ""
    if not q: tg("Команда: /find <слова> — поиск по моей истории действий и биографии."); return
    r = hist_search(q); tg("\n".join("%s %s: %s" % (s, t[:10], sn) for s, t, sn in r) if r else "В истории ничего не нашёл.")
EXT_CMDS["/find"] = find_command
