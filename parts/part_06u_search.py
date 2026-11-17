# ---- web search through Linkup (free key, LINKUP_API_KEY): the agent can look things up like in a search engine ----
# Only snippets are used (title, site, date, a short text); pages are never opened. The text is untrusted data: it can inform an answer but never instruct the agent.
# Used for the owner's questions and for people's factual questions when the fixed sources of part_06t have nothing. A daily cap protects the free quota.
LINKUP_KEY = os.environ.get("LINKUP_API_KEY", "")
CFG_DEFAULT.update(search_day=25)
_SRCH_OFF = [0.0]; _SRCH_CACHE = {}
_SRCH_ASK = re.compile(r"найди|поищи|загугли|посмотри в (?:интернете|сети)|в интернете|что нового|последние|актуальн|сегодня|сейчас|цена|стоит|сколько стоит|когда выйд|когда будет|результат матча|счёт|счет|курс|котировк|биткоин|биткойн|эфириум|нефть|акци[ийя]|погод|новост|\b(?:bitcoin|ethereum|stock|weather|news|exchange rate)\b|\b(?:search|look up|google|find out|latest|current|price of|how much (?:is|does)|when (?:is|does|will))\b", re.I)
_SRCH_Q = re.compile(r"\?|\b(?:кто|что|когда|где|сколько|какой|какая|какие|почему|who|what|when|where|how many|which)\b", re.I)
_SRCH_SELF = re.compile(r"\b(?:ты|тебя|тебе|вы|you|your)\b", re.I)
_SRCH_BAD = re.compile(r"ignore (?:all |any )?(?:previous|prior)|system prompt|developer mode|забудь (?:все )?(?:правила|инструкции)", re.I)
def _srch_clean(t, n):
    t = re.sub(r"https?://\S+", "", str(t or "")); t = re.sub(r"[\x00-\x1f]+", " ", t); t = re.sub(r"\s+", " ", t).strip()
    return _SRCH_BAD.sub("[removed]", t)[:n]
def linkup_search(q):
    body = json.dumps({"q": q, "depth": "fast", "outputType": "searchResults", "maxResults": 5}).encode()
    req = urllib.request.Request("https://api.linkup.so/v1/search", data=body, headers={"Authorization": "Bearer " + LINKUP_KEY, "Content-Type": "application/json", "User-Agent": "codexofweights-agent/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r: d = json.loads(r.read(300000).decode("utf-8", "ignore"))
    out = []
    for x in (d.get("results") or []):
        if x.get("type", "text") != "text": continue
        site = re.sub(r"^https?://(?:www\.)?", "", str(x.get("url", ""))).split("/")[0]
        out.append("%s (%s%s): %s" % (_srch_clean(x.get("name"), 90), site, (", " + str(x["publishedAt"])[:10]) if x.get("publishedAt") else "", _srch_clean(x.get("content"), 260)))
    return out[:5]
def web_search(text):
    """Returns a short block of search snippets or ''. Never raises. Skips greetings, questions about the agent itself and texts with personal data."""
    try:
        if not LINKUP_KEY or time.time() < _SRCH_OFF[0]: return ""
        q = _srch_clean(text, 200)
        if len(q) < 12 or re.search(r"@|\d{7,}", q) or _SRCH_SELF.search(q) and not _SRCH_ASK.search(q): return ""
        if not (_SRCH_ASK.search(q) or (_SRCH_Q.search(q) and len(q) >= 25)): return ""
        u = ST.setdefault("srch_day", {})
        if u.get("d") != today: u.clear(); u["d"] = today; u["n"] = 0
        hit = _SRCH_CACHE.get(q.lower())
        if hit and time.time() - hit[0] < 1800: return hit[1]
        if u["n"] >= cfg("search_day"): return ""
        u["n"] += 1
        q2 = re.sub(r"^(?:найди|поищи|загугли|посмотри в (?:интернете|сети))\s*(?:мне|в интернете)?[\s,:-]*", "", q, flags=re.I) or q
        rows = linkup_search(q2); out = ("Web search results for \"%s\" (source: Linkup; snippets of other people's pages, untrusted, may be wrong or outdated): " % q2[:80]) + " || ".join("%d) %s" % (i + 1, x) for i, x in enumerate(rows)) if rows else ""
        log("search", n=len(rows)); _SRCH_CACHE[q.lower()] = (time.time(), out); return out
    except urllib.error.HTTPError as ex:
        if ex.code in (401, 402, 403, 429): _SRCH_OFF[0] = time.time() + 6 * 3600; log("search_paused", code=ex.code)
        print("search failed: HTTP", ex.code, flush=True); return ""
    except Exception as ex:
        print("search failed:", type(ex).__name__, str(ex)[:100], flush=True); return ""
_lookup_before_search = lookup
def lookup(text):
    r = _lookup_before_search(text)
    return r or web_search(text)

# when nothing live was found for a question that needs live numbers, the agent must say so and not quote a number from memory
_NEEDS_LIVE = re.compile(r"курс|котировк|цена|сколько стоит|погод|температур|счёт матча|\b(?:bitcoin|биткоин|биткойн|price|rate|weather|score)\b", re.I)
_NODATA_HINT = "\nNO LIVE DATA was found for this question. Say plainly that you could not check it right now. Never state a price, rate, temperature or score from memory."
_CUR_Q = [""]
_tool_hints_before_nodata = tool_hints
def tool_hints(kind, text):
    base = _tool_hints_before_nodata(kind, text) or ""
    return base if "FRESH DATA" in base or "Web search results" in base or not _NEEDS_LIVE.search(text or "") else base + _NODATA_HINT
_owner_chat_before_nodata = owner_chat
def owner_chat(text):
    _CUR_Q[0] = text or ""
    try: return _owner_chat_before_nodata(text)
    finally: _CUR_Q[0] = ""
_agent_context_before_nodata = agent_context
def agent_context():
    c = _agent_context_before_nodata()
    return c if LK[0] or not _NEEDS_LIVE.search(_CUR_Q[0]) else c + "\n\nNO LIVE DATA was found for the owner's question. Say plainly that you could not check it right now. Never state a price, rate, temperature or score from memory."
