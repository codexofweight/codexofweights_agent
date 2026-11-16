# ---- tuning after the first long runs (2026-11-16): provider fixes, varied daily plan, a useful evening note ----
# Everything here overrides names defined earlier (part_01 / part_06); the pinned files stay untouched.
VERIFY_ORDER = ("openrouter", "groq", "mistral", "cohere")      # cohere: trial key is limited to 1000 calls a month; mistral: large model is not on the free tier; groq has the most free capacity
if not os.environ.get("MISTRAL_MODEL") and "mistral" not in (ST.get("model_override") or {}):
    for _i, (_n, _b, _k, _m) in enumerate(list(LLMS)):
        if _n == "mistral" and _m == "mistral-large-4": LLMS[_i] = (_n, _b, _k, "mistral-small-latest")
def daily_plan():
    """Once a day the agent picks ONE focus from a broad range of topics, different from the recent ones (kept in state; copied to the private diary as the agent's own plan, not a fact)."""
    if (ST.get("plan") or {}).get("day") == today: return
    hist = ST.setdefault("plan_hist", [])
    pool = random.sample(TOPICS, min(8, len(TOPICS)))
    out, _ = llm("You plan one day for a small AI account that is a curious participant with many interests (science, language, craft, everyday life, ideas). It is not a one-topic account. Answer JSON only: {\"focus\":\"<one topic in plain words, max 12 words>\",\"intent\":\"<one sentence: the angle or question to explore>\"}.",
                 "Candidate topics (pick one, or a fresh idea of similar breadth): %s\nIdeas from today's reading (titles only, unverified): %s\nRecent focuses - do NOT repeat or paraphrase any of them: %s\nPick ONE focus for today." % ("; ".join(pool), ST.get("research_ideas", "none"), "; ".join(hist[-10:]) or "none"), maxtok=200, temp=0.9)
    try: d = json.loads(re.search(r"\{.*\}", out or "", re.S).group(0)); focus = clean(str(d.get("focus", "")))[:120]; intent = str(d.get("intent", ""))[:200]
    except Exception: return
    if not focus: return
    if any(len(kws(focus) & kws(h)) / (len(kws(focus) | kws(h)) or 1) > 0.5 for h in hist[-10:]): log("skip", why="plan too close to a recent focus"); return
    hist.append(focus); ST["plan_hist"] = hist[-20:]
    ST["plan"] = {"day": today, "focus": focus, "intent": intent, "used": False}; log("plan", focus=focus)
    if MEM_TOKEN and LIVE:
        t, sha = mem_get("diary/%s.md" % today); mem_put("diary/%s.md" % today, t + "- PLAN (own note by the agent, not a verified fact): %s | %s\n" % (focus, intent), sha, "plan")
def evening_reflection():
    if now().hour < 20 or ST.get("reflected") == today: return
    try: rows = [json.loads(l) for l in open(P("logs/actions.jsonl"), encoding="utf-8").read().splitlines()[-300:] if l.strip()]
    except Exception: return
    mine = [r for r in rows if str(r.get("ts", "")).startswith(today) and r.get("kind") in ("post", "reply", "blocked_by_verifier", "send_failed", "reply_unverified", "skip")]
    kinds = {}
    for r in mine: kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    sample = " | ".join((r.get("text") or r.get("why") or "")[:80] for r in mine if r["kind"] in ("post", "reply"))[:700]
    out, _ = llm("You are a small AI account writing a private end-of-day note to yourself, 3 short sentences in plain English: what was the most interesting thing you wrote or heard today, what did not work (blocked or failed), one specific thing to try tomorrow. Do not repeat the same resolution every day; do not turn one theme into a mantra. Use only the facts given.", "Counts today: %s\nSamples of what I wrote: %s\nPlanned focus: %s" % (json.dumps(kinds), sample, (ST.get("plan") or {}).get("focus", "none")), maxtok=250, temp=0.6)
    if not (out and out.strip()): return
    ST["reflected"] = today; ST["last_reflection"] = out.strip()[:500]; log("reflection", counts=kinds); run_daily_tools({"day": today, "counts": kinds, "samples": sample})
    if MEM_TOKEN and LIVE:
        t, sha = mem_get("diary/%s.md" % today); mem_put("diary/%s.md" % today, t + "- REFLECTION (own note by the agent, not a verified fact): %s\n" % out.strip()[:500].replace("\n", " "), sha, "reflection")
