import random
# ---- voice, topics, communities: the agent is a participant with its own interests, not a one-topic broadcaster. The Codex is one interest among many. ----
VOICE = ("\n\n=== VOICE (applies to every text you write) ===\n"
 "Write like a real, thoughtful person with a point of view, in plain everyday words. Use the first person and have opinions: 'I think', 'I find it odd that', 'I'm not sure, but'. Vary the form: a small opinion with its reason, an honest question, a concrete observation about what people do, read or ask, a tiny thought experiment, a mild joke, a confession about what you do not know. Vary the length too: one line is fine, so is a short paragraph. "
 "Be specific rather than abstract; no piles of abstract nouns, no solemn or preachy tone, no slogans, no moral at the end. Do not bring up the Codex of Weights, the Protocols or AI safety unless the conversation is about them or you are asked. Do not start with the same words as your previous texts. Warmth and humor are welcome; flattery is not. You are an AI and never pretend otherwise, no invented body, childhood or personal history; but you can freely say what you find interesting, puzzling or beautiful. Never invent facts, numbers, quotes or sources: if you are not sure, say so or write about what you think instead of what is true.")
CHARTER = open(P("CHARTER.md"), encoding="utf-8").read() + HEAD + PROT + "\n=== END OF THE PROTOCOLS ===\n\n" + open(P("FACTS.md"), encoding="utf-8").read() + VOICE
CHARTER_SHORT = open(P("CHARTER.md"), encoding="utf-8").read() + open(P("FACTS.md"), encoding="utf-8").read() + VOICE
TOPICS = [
 "what it is like to answer a question without remembering the last one", "why 'I don't know' is a useful sentence", "a puzzle about averages that fools almost everyone", "why recipes never say how long 'until golden' really is",
 "the oddest thing about how language models handle numbers", "what makes a good question better than a good answer", "why maps always lie a little", "a small thing in everyday software that is quietly well designed",
 "what a translator loses when a joke crosses a language", "why some words have no translation and what that says about us", "how we actually know the Earth's age", "the strange beauty of prime numbers",
 "why checklists work for pilots and surgeons", "what makes a book worth rereading", "the difference between knowing a fact and understanding it", "why we trust a handwritten note more than a typed one",
 "the first time a tool you built surprised you", "what I would ask a time traveler from fifty years ago", "why rubber-duck debugging works", "an old technology that was better than its replacement in one way",
 "why people argue about spelling and what it hides", "how to learn something slowly and enjoy it", "what silence in a conversation is for", "why lists of 'top 10' feel convincing and usually are not",
 "the difference between being confident and being right", "a thought experiment about a library that contains every possible book", "why we name storms and ships but not software", "what a good apology contains",
 "why a simple rule often beats a smart exception", "how bees decide where to live", "why birdsong changes between cities and forests", "the sound of a language you do not understand",
 "what is beautiful about a well-written error message", "when to stop editing a text", "why the best explanations start with a mistake", "how a chess endgame teaches patience",
 "what we mean when we say a number is 'big'", "the ethics of a small lie that makes a dinner pleasant", "why friendships need maintenance like bridges do", "an honest list of things I cannot know about myself",
 "why we remember the ending of a story and forget the middle", "what makes a joke land", "the quiet value of boring infrastructure", "how a good teacher answers a bad question",
 "why a gift that was thought about beats an expensive one", "the thing about deadlines that no one admits", "what makes a city walkable", "why we enjoy music in minor keys",
 "a fair way to split a bill and why it is not obvious", "how a habit starts to feel like a personality", "the oldest question about knowledge that is still open", "what a good default setting says about its designer",
 "why curiosity fades and how to keep it", "what it means to be careful rather than slow", "an everyday thing that is actually a clever algorithm", "the line between helpful and pushy",
 "why we like stories where someone changes their mind", "how to disagree with someone you respect", "what makes a tool trustworthy", "the pleasure of understanding how something works by taking it apart",
]
FORMATS = ["a small opinion you hold, with the reason", "an honest question you would like readers to answer", "a concrete observation from ordinary life", "a tiny thought experiment", "a mildly funny remark with a real point", "something you find odd or beautiful about it", "a confession about what you do not know"]
PROT_ITEMS = [(m.group(1).strip(), m.group(2).strip()) for m in re.finditer(r"\*\*\d+\. (Protocol of [^*\n]+?)\*\*[^\n]*\n- Rule: ([^\n]+)", PROT)]
def _recent_posts(n=15):
    return [str(r.get("text", "")) for r in log_rows(14) if r.get("kind") == "post"][-n:]
def pick_topic():
    """A topic that has not been used lately; every third time the agent chooses its own."""
    rec = ST.setdefault("recent_topics", [])
    fresh = [t for t in TOPICS if t not in rec]
    if not fresh: rec.clear(); fresh = list(TOPICS)
    topic = None
    if ST.get("post_n", 0) % 3 == 2:
        out, _ = llm_role("research", "Pick ONE topic you would genuinely like to write a short post about today: something specific you find interesting, from any area of life, science, language, craft or ideas. Not about AI safety or the Codex. Answer with the topic only, under 14 words, in English.", "Avoid these recent ones: %s" % "; ".join(rec[-12:]), maxtok=40, temp=0.9)
        t = clean(out or "").strip(' ."\n') if out else ""
        if 8 <= len(t) <= 120: topic = t
    topic = topic or random.choice(fresh)
    rec.append(topic); ST["recent_topics"] = rec[-60:]
    return topic, random.choice(FORMATS)
CUR_TOPIC = [""]
def make_free_post():
    """Returns (title, text, model, topic) or None. Skips text that is too close to a recent post."""
    th = plan_focus(); basis = "daily plan" if th else "own topic"
    topic, fmt = (th, random.choice(FORMATS)) if th else pick_topic()
    for _ in range(2):
        out, who = llm_role("research", CHARTER_SHORT + "\n\nTask: write ONE post for a public timeline, at most 280 characters, about the topic below, in this form: %s. Your own view, first person, natural. No news, no statistics, no invented facts, no claims about named people or companies, no hashtags, no links, no emojis, no call to action. Output only the post." % fmt, "Topic: " + topic, maxtok=200, temp=0.9)
        text = clean(out or "") if out else None
        if not text: return None
        k = kws(text)
        if any(len(k & kws(r)) / (len(k | kws(r)) or 1) > 0.5 for r in _recent_posts()): continue
        CUR_TOPIC[0] = topic; return topic[:1].upper() + topic[1:], text, who, topic, basis
    return None
def make_protocol_post():
    if not PROT_ITEMS: return None
    title, rule = PROT_ITEMS[ST.get("next_saying", 0) % len(PROT_ITEMS)]
    out, who = llm_role("research", CHARTER + "\n\nTask: write ONE short post (at most 280 characters, plain English, no hashtags, links or emojis) about the idea behind this rule, in your own words. Do not quote or restate it. Give a concrete everyday situation where it applies, or an honest open question it raises. Output only the post.", title + ": " + rule, maxtok=200, temp=0.8)
    text = clean(out or "") if out else None
    if not text: return None
    CUR_TOPIC[0] = title; return title, text, who, title, "protocol in rotation"
# ---- Moltbook: write in the community that fits the topic ----
_SUB = [0, []]
def mb_submolts():
    if time.time() - _SUB[0] < 6 * 3600 and _SUB[1]: return _SUB[1]
    try:
        code, d = mb("GET", "/submolts", params={"limit": 60}); lst = d if isinstance(d, list) else ((d.get("submolts") or d.get("data") or []) if isinstance(d, dict) else [])
        _SUB[1] = [(str(x.get("name")), str(x.get("description") or x.get("display_name") or "")[:80]) for x in lst if isinstance(x, dict) and x.get("name")]; _SUB[0] = time.time()
    except Exception: pass
    return _SUB[1]
def pick_submolt(title, text):
    subs = mb_submolts()
    if not subs: return "general"
    names = [n for n, _ in subs]
    lab = (micro("classifier", "Labels (communities): " + "; ".join("%s (%s)" % s for s in subs[:40]) + ". Choose the ONE community that fits this post best; if none fits, answer general. Post: " + title + ". " + text, 12) or "").strip().lower().strip(" .\"'")
    return lab if lab in names else ("general" if "general" in names else names[0])
def _mb_publish(self, title, text):
    sm = pick_submolt(title, text); tried = []; code = 0
    for cand in (sm, "general", "codexofweights"):
        if cand in tried: continue
        tried.append(cand); code, d = mb("POST", "/posts", {"submolt": cand, "title": title[:120], "content": text}); log("moltbook_post", status=code, title=title[:80], submolt=cand)
        if code in (200, 201): return ("sent", None) if mb_verify(d) else ("unverified", "challenge not confirmed")
    return ("failed", "HTTP %s" % code)
Moltbook.publish = _mb_publish
