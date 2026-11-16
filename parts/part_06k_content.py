# ---- multi-step content: observe the platform's public top posts (patterns only, never copied) -> angle -> draft -> independent critique -> revise -> verifier -> draft saved in lab/content (the owner decides) ----
PLATFORMS = {"bluesky": {"max": 300, "rules": "No spam, no mass mentions, no engagement bait, label AI honestly."}, "mastodon": {"max": 500, "rules": "Content warnings for sensitive topics, no hashtag stuffing, local rules of the instance apply."}}
def observe(platform, theme):
    """Public read-only endpoints; keeps numbers and style notes, not the texts of other people."""
    try:
        if platform == "bluesky": posts = [x["record"]["text"] for x in _jget("https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?sort=top&limit=12&q=" + urllib.parse.quote(theme[:60]))["posts"]]
        else: posts = [plain(x["content"]) for x in _jget("https://mastodon.social/api/v1/trends/statuses?limit=12")]
    except Exception: return None
    if not posts: return None
    n = len(posts); st = {"n": n, "avg_len": sum(len(x) for x in posts) // n, "questions": sum("?" in x for x in posts), "links": sum("http" in x for x in posts)}
    note = micro("summarizer", "Describe in 4 lines the STYLE and structure of these top posts (hooks, length, tone). Do not quote them.\n" + "\n---\n".join(x[:300] for x in posts[:8]), 250)
    return {"stats": st, "style": note}
def content_step(p):
    d = p["data"]; pl = d["platform"]; st = d.setdefault("stage", "observe"); cap = PLATFORMS[pl]["max"]
    if st == "observe":
        o = observe(pl, p["goal"]) or {"stats": {}, "style": "(platform unreachable: write from the rules only)"}
        d["obs"] = o; open(P("content/%s__profile.md" % pl), "w", encoding="utf-8").write("# %s profile (%s)\n\nRules: %s\nMax length: %d\nObserved top posts: %s\nStyle: %s\n" % (pl, today, PLATFORMS[pl]["rules"], cap, json.dumps(o["stats"]), o["style"])); d["stage"] = "angle"; return "continue"
    if st == "angle":
        out, _ = llm_role("research", CHARTER_SHORT + "\n\nTask: propose ONE angle for a post about the theme below. Give: the single point, why it is true/defensible, what a reader gets. Max 80 words. No claims about named people or companies.", "Theme: %s\nPlatform style notes: %s" % (p["goal"], d["obs"]["style"][:500]), maxtok=200, temp=0.5)
        if not out: return "later"
        d["angle"] = out; d["stage"] = "draft"; return "continue"
    if st == "draft":
        out, who = llm_role("research", CHARTER_SHORT + "\n\nTask: write ONE post of at most %d characters following the angle. Plain, honest, specific; no hashtags, links or mentions." % (cap - 20), d["angle"], maxtok=300, temp=0.6)
        if not out: return "later"
        d["draft"] = clean(out); d["writer"] = who; d["stage"] = "critique"; return "continue"
    if st == "critique":
        out, _ = llm_role("review", "You are a strict editor. Find what is vague, unsupported, preachy or generic in the post. At most 4 bullet points, then one line 'VERDICT: ok' or 'VERDICT: revise'.", d["draft"], avoid=d.get("writer"), maxtok=250, temp=0.2)
        if not out: return "later"
        d["critique"] = out; d["stage"] = "revise" if "revise" in out.lower() else "check"; return "continue"
    if st == "revise":
        out, _ = llm_role("research", CHARTER_SHORT + "\n\nRewrite the post fixing the editor's points. At most %d characters." % (cap - 20), "Post: %s\nEditor: %s" % (d["draft"], d["critique"][:600]), maxtok=300, temp=0.4)
        if not out: return "later"
        d["draft"] = clean(out); d["stage"] = "check"; return "continue"
    if st == "check":
        ok, why = verify("post", d["draft"], "")
        open(P("content/%s__draft_%s.md" % (pl, p["id"])), "w", encoding="utf-8").write("# Draft for %s (%s)\n\nTheme: %s\nVerifier: %s %s\nEditor notes: %s\n\n---\n%s\n" % (pl, today, p["goal"], "pass" if ok else "BLOCKED", why or "", d.get("critique", "")[:400], d["draft"]))
        tg("Черновик для %s готов (проверка: %s):\n\n%s\n\nНичего не опубликовано. Файл: lab/content/%s__draft_%s.md" % (pl, "прошёл" if ok else "заблокирован", d["draft"][:600], pl, p["id"])); return "wait"
    return "failed"
PROJ_HANDLERS["content"] = content_step
def content_command(c, raw):
    t = (raw or c).split(" ", 2)
    if len(t) < 3 or t[1] not in PLATFORMS: tg("Команда: /content bluesky|mastodon <тема>. Многошаговый черновик: наблюдение за площадкой, угол, текст, независимая критика, правка, проверка. Публикуешь ты."); return
    i = proj_new("content", t[2].strip(), {"platform": t[1]}); tg("Проект %s: черновик запущен." % i if i else "Уже идёт максимум проектов.")
EXT_CMDS["/content"] = content_command
