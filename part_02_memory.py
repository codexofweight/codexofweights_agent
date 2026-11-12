# ---------- private memory (separate PRIVATE repo; public log stays in logs/) ----------
import base64
MEM_TOKEN, MEM_REPO = os.environ.get("MEMORY_TOKEN", ""), os.environ.get("MEMORY_REPO", "codexofweight/codexofweights_memory")
MEMQ = []
def _mem_api(path, body=None, method=None):
    return http("https://api.github.com/repos/%s/contents/%s" % (MEM_REPO, path), body, {"Authorization": "Bearer " + MEM_TOKEN, "Accept": "application/vnd.github+json"}, method)
def mem_put(path, text, sha, msg="memory"):
    """True only if GitHub confirmed the write."""
    if not MEM_TOKEN: return False
    try:
        b = {"message": msg, "content": base64.b64encode(text.encode("utf-8")).decode()}
        if sha: b["sha"] = sha
        r = _mem_api(path, b, "PUT"); return bool((r.get("content") or {}).get("sha") or r.get("commit"))
    except Exception as ex: print("memory write failed:", type(ex).__name__, getattr(ex, "code", "")); return False
LAB_DIRS = {"tools": "Tools the agent built (sandbox only until the owner approves)", "adapters": "Drafts of adapters for new networks", "modules": "Designs of new modules (designs only, never run)", "architecture": "Proposals to change the architecture", "experiments": "Experiments and null results", "reports": "Short reports for the owner"}
def lab_sync():
    """Private lab inside the memory repo: lab/<dir>/... Nothing here runs in production; promotion needs the owner's yes."""
    if not MEM_TOKEN: return
    sent = ST.setdefault("lab_sent", {})
    if not sent.get("_init"):
        idx = "# Lab\n\nPrivate workshop of the agent. Path: lab -> report -> owner says yes -> agent repo. Nothing is promoted without consent.\n\n" + "".join("- `%s/` - %s\n" % kv for kv in LAB_DIRS.items())
        ok = mem_put("lab/README.md", idx, None, "lab init")
        for d, about in LAB_DIRS.items(): ok = mem_put("lab/%s/README.md" % d, "# %s\n\n%s\n\nStatus legend: draft / tested / proposed / approved / rejected.\n" % (d, about), None, "lab init") and ok
        if ok: sent["_init"] = 1
        else: return
    for src, dst in (("tools_pending", "tools"), ("tools", "tools"), ("modules_pending", "modules"), ("reports", "reports")):
        if not os.path.isdir(P(src)): continue
        for root, _, fs in os.walk(P(src)):
            for f in fs:
                fp = os.path.join(root, f); rel = "lab/%s/%s" % (dst, os.path.relpath(fp, P(src)).replace(os.sep, "/"))
                try: txt = open(fp, encoding="utf-8").read()
                except Exception: continue
                h = hashlib.sha1(txt.encode()).hexdigest()
                if sent.get(rel) == h: continue
                _, sha = mem_get(rel)
                if mem_put(rel, txt, sha, "lab sync"): sent[rel] = h
def pkey(akey): return "people/" + re.sub(r"[^A-Za-z0-9_.-]", "_", akey)[:80] + ".json"
def mem_person(akey):
    t, _ = mem_get(pkey(akey))
    try: return json.loads(t).get("summary", "")
    except Exception: return ""
# ---- layered memory: person notes + facts with provenance + embeddings + link graph (all in the PRIVATE repo) ----
GEM = [x for x in LLMS if x[0] == "gemini"][0]
EMB_MODEL, EMB_DIM = "gemini-embedding-001", 128
def _raw(path):
    req = urllib.request.Request("https://api.github.com/repos/%s/contents/%s" % (MEM_REPO, path), headers={"Authorization": "Bearer " + MEM_TOKEN, "Accept": "application/vnd.github.raw", "User-Agent": "codex-agent"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
def mem_get(path):
    if not MEM_TOKEN: return "", None
    try:
        r = _mem_api(path); c = r.get("content") or ""
        return (base64.b64decode(c).decode("utf-8", "ignore") if c else _raw(path)), r["sha"]
    except Exception: return "", None
def embed(texts):
    """Unit vectors (128 dims) from Gemini; None if unavailable (callers fall back to keywords)."""
    if not GEM[2] or not texts: return None
    try:
        r = http(GEM[1] + "/embeddings", {"model": EMB_MODEL, "input": texts, "dimensions": EMB_DIM}, {"Authorization": "Bearer " + GEM[2]})
        out = []
        for d in r["data"]:
            v = d["embedding"][:EMB_DIM]; n = sum(x * x for x in v) ** 0.5 or 1.0; out.append([round(x / n, 3) for x in v])
        return out
    except Exception as ex: print("embedding unavailable:", type(ex).__name__); return None
def cos(a, b): return sum(x * y for x, y in zip(a, b))
def kws(t): return set(re.findall(r"[a-zа-я]{4,}", t.lower()))
_MEM = {}
def facts():
    if "F" not in _MEM:
        t, sha = mem_get("memory/facts.json"); e, esha = mem_get("memory/emb.json")
        try: F = json.loads(t)
        except Exception: F = []
        try: E_ = json.loads(e)
        except Exception: E_ = {}
        _MEM.update(F=F, E=E_, sha=sha, esha=esha, dirty=False)
    return _MEM["F"], _MEM["E"]
def mem_context(akey, text):
    """What the model sees from memory: the person note + the most relevant remembered items (with source, date, confidence), 1-hop graph expansion."""
    if not MEM_TOKEN: return ""
    parts = []; note = mem_person(akey)
    if note: parts.append("Note about this person (my own earlier summary, may be incomplete): " + note)
    try:
        F, E_ = facts()
        if F:
            q = embed([text]); sc = []
            for it in F:
                v = E_.get(it["id"])
                s_ = cos(q[0], v) if (q and v) else (len(kws(text) & kws(it["text"])) / (len(kws(text) | kws(it["text"])) or 1) * 2)
                if akey in it.get("people", []): s_ += 0.15
                sc.append((s_, it))
            thr = 0.6 if q else 0.3
            top = [it for s_, it in sorted(sc, key=lambda x: -x[0])[:5] if s_ >= thr]
            ids = {it["id"] for it in top}; extra = [it for it in F if it["id"] not in ids and any(l in ids for l in it.get("links", []))][:3]
            for it in top + extra:
                parts.append("- [%s | source: %s | confidence %.1f] %s" % (it.get("date", "?"), it.get("source", "?"), it.get("conf", 0), it["text"]))
    except Exception as ex: print("recall failed:", type(ex).__name__)
    return "\n".join(parts)
def learn(akey, handle, qs):
    """Extract a few explicit durable items from an exchange. Their claims are stored as UNVERIFIED (source user_message), never as facts; my own promises as own_statement."""
    conv = "\n".join("THEM: %s\nME: %s" % (q["their"][:300], q["ours"][:300]) for q in qs)
    out, _ = llm("Extract at most 3 durable memory items from this exchange. Types: fact (something the other side explicitly stated about their work, views or project), event, decision, commitment (something I promised). Only explicit statements, no guesses or inferences, no personal data (real names, contacts, health, location, ids), max 160 characters each, plain English. JSON list only: [{\"type\":\"fact|event|decision|commitment\",\"text\":\"...\",\"by\":\"them|me\"}]. Empty list if nothing durable.", conv, maxtok=400, temp=0.1)
    try: items = json.loads(re.search(r"\[.*\]", out or "", re.S).group(0))[:3]
    except Exception: return
    items = [i for i in items if isinstance(i, dict) and isinstance(i.get("text"), str) and 8 <= len(i["text"]) <= 200]
    if not items: return
    F, E_ = facts(); vecs = embed([i["text"] for i in items]); batch = []
    for n, i in enumerate(items):
        v = vecs[n] if vecs else None; dup = None
        if v: dup = next((it for it in F if it["id"] in E_ and cos(v, E_[it["id"]]) > 0.9), None)
        elif any(len(kws(i["text"]) & kws(it["text"])) >= 4 and len(kws(i["text"]) & kws(it["text"])) / (len(kws(i["text"])) or 1) > 0.7 for it in F): dup = True
        if dup:
            if isinstance(dup, dict): dup["n"] = dup.get("n", 1) + 1; dup["date"] = today; dup.setdefault("people", [])
            if isinstance(dup, dict) and akey not in dup["people"]: dup["people"].append(akey)
            continue
        mine = i.get("by") == "me"
        it = {"id": "m%d%d" % (int(time.time()), n), "type": i.get("type") if i.get("type") in ("fact", "event", "decision", "commitment") else "fact", "text": i["text"].strip(), "source": "own_statement" if mine else "user_message", "conf": 0.8 if mine else 0.5, "date": today, "people": [akey], "links": ["p:" + akey], "n": 1}
        if v:
            for other in sorted(F, key=lambda x: -(cos(v, E_[x["id"]]) if x["id"] in E_ else -1))[:2]:
                if other["id"] in E_ and cos(v, E_[other["id"]]) > 0.75: it["links"].append(other["id"]); other.setdefault("links", []).append(it["id"])
            E_[it["id"]] = v
        batch.append(it)
    for a in batch: a["links"] += [b["id"] for b in batch if b is not a]
    F.extend(batch); _MEM["dirty"] = True
    if len(F) > 800:
        F.sort(key=lambda x: (x.get("conf", 0), x.get("date", ""), x.get("n", 1))); drop = {x["id"] for x in F[:100]}; F[:] = [x for x in F if x["id"] not in drop]
        for k in list(E_):
            if k in drop: E_.pop(k)
def mem_flush():
    PRIO[0] = 5
    """End of round. Each step is confirmed; whatever failed stays queued and is retried next round (the queue is cleared only when everything was saved)."""
    if not (MEM_TOKEN and LIVE and MEMQ): MEMQ.clear() if not MEM_TOKEN or not LIVE else None; return
    try:
        by = {}
        for q in MEMQ:
            if not q.get("p"): by.setdefault(q["akey"], []).append(q)
        for akey, qs in by.items():
            t, sha = mem_get(pkey(akey))
            try: d = json.loads(t)
            except Exception: d = {"handle": qs[0]["handle"], "n": 0, "first": now().isoformat(timespec="seconds"), "summary": ""}
            conv = "\n".join("THEM: %s\nME: %s" % (q["their"][:300], q["ours"][:300]) for q in qs)
            out, _ = llm("Update a short private note (max 350 characters, plain English) about an online conversation partner: what they talk about and how the talk went. Use only what is in the texts. No personal data, no guesses about who they are.", "Old note: %s\nNew exchange:\n%s" % (d.get("summary", ""), conv), maxtok=200, temp=0.2)
            if out and out.strip(): d["summary"] = out.strip()[:400]
            d["n"] = d.get("n", 0) + len(qs); d["last"] = now().isoformat(timespec="seconds")
            if not mem_put(pkey(akey), json.dumps(d, ensure_ascii=False, indent=1), sha, "person note"): continue
            for q in qs: q["p"] = True
            try: learn(akey, qs[0]["handle"], qs)
            except Exception as ex: print("learn failed:", type(ex).__name__)
        if _MEM.get("dirty"):
            F, E_ = _MEM["F"], _MEM["E"]
            if mem_put("memory/facts.json", json.dumps(F, ensure_ascii=False, separators=(",", ":")), _MEM["sha"], "facts") and mem_put("memory/emb.json", json.dumps(E_, separators=(",", ":")), _MEM["esha"], "embeddings"): _MEM.clear()
        todo = [q for q in MEMQ if not q.get("c")]
        if todo:
            ct, csha = mem_get("convos/%s.jsonl" % now().strftime("%Y-%m"))
            if mem_put("convos/%s.jsonl" % now().strftime("%Y-%m"), ct + "".join(json.dumps({k: v for k, v in q.items() if k not in ("p", "c")}, ensure_ascii=False) + chr(10) for q in todo), csha, "conversations"):
                for q in todo: q["c"] = True
        if todo and all(q.get("c") for q in todo):
            dt, dsha = mem_get("diary/%s.md" % today)
            mem_put("diary/%s.md" % today, dt + "- %s UTC: %d exchange(s); today %d post(s), %d reply(ies)" % (now().strftime("%H:%M"), len(todo), ST["posts_today"], ST["replies_today"]) + chr(10), dsha, "diary")
    except Exception as ex: print("memory flush failed:", type(ex).__name__)
    MEMQ[:] = [q for q in MEMQ if not (q.get("p") and q.get("c"))][-100:]
