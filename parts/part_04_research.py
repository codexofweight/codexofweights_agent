# ---- research module: reads public feeds once a day, keeps source-tagged notes, feeds ideas to the daily plan ----
import xml.etree.ElementTree as ET, html as _html
SOURCES = [("arXiv cs.CL", "https://rss.arxiv.org/rss/cs.CL"), ("arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI"), ("arXiv cs.CY", "https://rss.arxiv.org/rss/cs.CY"),
           ("Alignment Forum", "https://www.alignmentforum.org/feed.xml"), ("LessWrong", "https://www.lesswrong.com/feed.xml")]
try: SOURCES += [tuple(x) for x in json.load(open(P("sources.json"), encoding="utf-8"))]   # optional: owner adds [["name","feed url"], ...]
except Exception: pass
RKW = re.compile(r"honest|sycophan|decepti|alignment|corrigib|shutdown|oversight|transparen|evaluat|benchmark|trust|safety|agent|coexist|manipulat|refus", re.I)
def web_get(url, max_bytes=2000000):
    req = urllib.request.Request(url, headers={"User-Agent": "codex-agent/0.1 (AI agent of the Codex of Weights; +https://github.com/codexofweight/codexofweights_agent)"})
    return urllib.request.urlopen(req, timeout=25).read(max_bytes)
def plain(t): return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()
def parse_feed(raw):
    if b"<!ENTITY" in raw[:5000]: return []          # refuse entity tricks in untrusted XML
    out = []
    for el in ET.fromstring(raw).iter():
        if el.tag.split("}")[-1] not in ("item", "entry"): continue
        g = {c.tag.split("}")[-1]: c for c in el}
        link = (g["link"].get("href") or g["link"].text) if "link" in g else ""
        body = next((g[k].text for k in ("description", "summary", "content") if k in g and g[k].text), "")
        out.append({"title": plain(g["title"].text if "title" in g else "")[:200], "url": (link or "").strip(), "text": plain(body)[:500]})
    return out
def research():
    """Once a day: read feeds, pick 3 items relevant to the agent's themes, save notes (source URL, date, low confidence) and tell the owner."""
    if ST.get("research_day") == today: return
    ST["research_try"] = ST.get("research_try", {}); ST["research_try"] = {today: ST["research_try"].get(today, 0) + 1}
    if ST["research_try"][today] > 3: return          # at most 3 attempts a day
    ST.setdefault("read_urls", []); ST.setdefault("skipped", {}); cands = []
    for name, url in SOURCES:
        try:
            for it in parse_feed(web_get(url))[:200]:
                if it["url"] and it["url"] not in ST["read_urls"] and RKW.search(it["title"] + " " + it["text"][:200]): it["src"] = name; cands.append(it)
        except Exception as ex: print("feed failed:", name, type(ex).__name__)
        time.sleep(2)
    try:
        r = json.loads(web_get("https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode({"query": ["AI alignment", "AI agents", "LLM evaluation"][int(time.time() // 86400) % 3], "tags": "story", "numericFilters": "points>40"})).decode())
        for h in r.get("hits", [])[:8]:
            u = h.get("url") or ""
            if u and u not in ST["read_urls"]: cands.append({"title": plain(h.get("title", ""))[:200], "url": u, "text": "", "src": "Hacker News"})
    except Exception as ex: print("hn failed:", type(ex).__name__)
    if not cands: ST["research_day"] = today; return
    cands = rank_with_tools(cands)[:25]
    out, _ = llm("You pick reading for a small honest AI account about AI honesty, safety and living alongside people. From the numbered list choose the 3 most relevant and write for each ONE plain sentence (max 25 words) saying what the idea is, using only the title and snippet; do not add facts. JSON only: [{\"n\":<number>,\"gist\":\"...\"}].",
                 "\n".join("%d. [%s] %s :: %s" % (i, c["src"], c["title"], c["text"][:200]) for i, c in enumerate(cands)), maxtok=500, temp=0.2)
    try: picks = json.loads(re.search(r"\[.*\]", out or "", re.S).group(0))[:3]
    except Exception: return
    notes = []
    for p_ in picks:
        try: c = cands[int(p_["n"])]; g = clean(str(p_.get("gist", "")))[:200]
        except Exception: continue
        if g: notes.append((c, g))
    if not notes: return
    chosen = {c["url"] for c, g in notes}
    for c in cands:      # only processed items become "read"; the others may return, and are dropped after 3 passes
        if c["url"] in chosen: ST["read_urls"].append(c["url"])
        else:
            ST["skipped"][c["url"]] = ST["skipped"].get(c["url"], 0) + 1
            if ST["skipped"][c["url"]] >= 3: ST["read_urls"].append(c["url"]); ST["skipped"].pop(c["url"], None)
    ST["read_urls"] = ST["read_urls"][-2000:]
    if len(ST["skipped"]) > 1500: ST["skipped"] = dict(list(ST["skipped"].items())[-1000:])
    ST["research_day"] = today
    ST["research_ideas"] = " | ".join(g for c, g in notes)
    EV.append(("research", {"text": "\n".join("%s (%s)\n%s" % (g, c["src"], c["url"]) for c, g in notes)})); log("research", n=len(notes), items=[{"gist": g, "url": c["url"]} for c, g in notes])
    if MEM_TOKEN and LIVE:
        try:
            t, sha = mem_get("research/%s.md" % today)
            mem_put("research/%s.md" % today, t + "".join("- [%s] %s | %s | gist written by the agent from title/snippet only (unverified), read %s\n" % (c["src"], g, c["url"], today) for c, g in notes), sha, "research")
            F, E_ = facts(); vecs = embed([g for c, g in notes])
            for n_, (c, g) in enumerate(notes):
                it = {"id": "r%d%d" % (int(time.time()), n_), "type": "knowledge", "text": g, "source": "web:" + c["url"], "conf": 0.4, "date": today, "people": [], "links": [], "n": 1}
                if vecs: E_[it["id"]] = vecs[n_]
                F.append(it)
            mem_put("memory/facts.json", json.dumps(F, ensure_ascii=False, separators=(",", ":")), _MEM["sha"], "facts")
            if not mem_put("memory/emb.json", json.dumps(E_, separators=(",", ":")), _MEM["esha"], "embeddings"): log("memory_failed", why="research items not saved")
            _MEM.clear()
        except Exception as ex: print("research save failed:", type(ex).__name__)
