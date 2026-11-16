# ---- web lookups (2026-11-16): fresh facts from a few fixed, free, key-less public APIs: weather and local time, exchange rates, short Wikipedia summaries ----
# Not a browser: only these hosts are ever contacted, the question itself is never sent anywhere except the place or term, answers are short data (untrusted), 60 lookups a day, cached 10 minutes.
# The data is added to the context of replies (via the tool-hints slot) and of the owner chat; the agent must state it as "according to <source>".
CFG_DEFAULT.update(lookups_day=60)
LK = [""]; _LK_CACHE = {}
_WMO = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers", 81: "rain showers", 82: "heavy showers", 95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail"}
def _lk_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "codexofweights-agent/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r: return json.loads(r.read(200000).decode("utf-8", "ignore"))
def lk_weather(place):
    g = _lk_get("https://geocoding-api.open-meteo.com/v1/search?count=1&language=en&name=" + urllib.parse.quote(place))
    r = (g.get("results") or [None])[0]
    if not r: return ""
    w = _lk_get("https://api.open-meteo.com/v1/forecast?timezone=auto&current=temperature_2m,apparent_temperature,wind_speed_10m,precipitation,weather_code&latitude=%s&longitude=%s" % (r["latitude"], r["longitude"]))
    c = w.get("current") or {}
    return "Weather now in %s, %s (source: open-meteo.com): %s, %s°C (feels like %s°C), wind %s km/h, precipitation %s mm. Local time there: %s (%s)." % (r.get("name"), r.get("country", ""), _WMO.get(c.get("weather_code"), "n/a"), c.get("temperature_2m"), c.get("apparent_temperature"), c.get("wind_speed_10m"), c.get("precipitation"), str(c.get("time", "")).replace("T", " "), w.get("timezone", ""))
_CUR = {"доллар": "USD", "евро": "EUR", "рубл": "RUB", "юан": "CNY", "фунт": "GBP", "иен": "JPY", "тенге": "KZT", "гривн": "UAH", "франк": "CHF", "dollar": "USD", "euro": "EUR", "ruble": "RUB", "yuan": "CNY", "pound": "GBP", "yen": "JPY"}
def lk_rate(text):
    low = text.lower(); found = []
    for k, v in _CUR.items():
        i = low.find(k)
        if i >= 0 and v not in [x[1] for x in found]: found.append((i, v))
    for m in re.finditer(r"\b(USD|EUR|RUB|CNY|GBP|JPY|KZT|UAH|CHF)\b", text.upper()):
        if m.group(1) not in [x[1] for x in found]: found.append((m.start(), m.group(1)))
    found = [v for _, v in sorted(found)]
    if not found: return ""
    a = found[0]; b = found[1] if len(found) > 1 else ("RUB" if a != "RUB" else "USD")
    d = _lk_get("https://open.er-api.com/v6/latest/" + a)
    v = (d.get("rates") or {}).get(b)
    return "Exchange rate (source: open.er-api.com, updated %s): 1 %s = %s %s." % (str(d.get("time_last_update_utc", ""))[:16], a, round(v, 4), b) if v else ""
def lk_wiki(term):
    ru = bool(re.search(r"[а-яА-Я]", term)); host = "ru" if ru else "en"
    s = _lk_get("https://%s.wikipedia.org/w/rest.php/v1/search/title?limit=1&q=%s" % (host, urllib.parse.quote(term)))
    p = (s.get("pages") or [None])[0]
    if not p: return ""
    d = _lk_get("https://%s.wikipedia.org/api/rest_v1/page/summary/%s" % (host, urllib.parse.quote(p["key"], safe="")))
    e = (d.get("extract") or "").strip()
    return "Wikipedia (%s): %s" % (d.get("title", term), e[:450]) if e else ""
_PLACE = re.compile(r"(?:погод[аыу]|температур[аы]|сколько градусов|который час|сколько времени|время)\s+(?:сейчас\s+)?(?:в|во|на)\s+([A-Za-zА-Яа-яЁё\- ]{2,40}?)(?:[?!.,]|$)|(?:weather|temperature|time)\s+(?:right now\s+)?in\s+([A-Za-z\- ]{2,40}?)(?:[?!.,]|\s+(?:now|today|right)|$)", re.I)
_WHAT = re.compile(r"(?:кто такой|кто такая|что такое|что значит|who is|who was|what is|what are)\s+([^?!.\n]{2,60})", re.I)
def lookup(text):
    """Returns a short data string for a question that needs fresh facts, else ''. Never raises."""
    try:
        text = (text or "")[:300]; u = ST.setdefault("lk_day", {})
        if u.get("d") != today: u.clear(); u["d"] = today; u["n"] = 0
        key = text.lower()[:120]; hit = _LK_CACHE.get(key)
        if hit and time.time() - hit[0] < 600: return hit[1]
        out = ""; kind = None
        m = _PLACE.search(text)
        if m: kind = "w"; arg = (m.group(1) or m.group(2)).strip(" -")
        elif re.search(r"\bкурс\b|exchange rate|сколько стоит (?:один |1 )?(?:доллар|евро|юань)|how much is (?:a |one )?(?:dollar|euro)", text, re.I): kind = "r"
        else:
            m = _WHAT.search(text)
            if m: kind = "k"; arg = m.group(1).strip()
        if not kind or u["n"] >= cfg("lookups_day"): return ""
        u["n"] += 1
        out = lk_weather(arg) if kind == "w" else lk_rate(text) if kind == "r" else lk_wiki(arg)
        if out: log("lookup", what=kind)
        _LK_CACHE[key] = (time.time(), out); return out
    except Exception as ex:
        print("lookup failed:", type(ex).__name__, str(ex)[:100], flush=True); return ""
_tool_hints_before_lookup = tool_hints
def tool_hints(kind, text):
    base = _tool_hints_before_lookup(kind, text) or ""; extra = lookup(text)
    return (base + ("\n" if base else "") + "FRESH DATA from a public API (state it as such, may be incomplete): " + extra) if extra else base
_owner_chat_before_lookup = owner_chat
def owner_chat(text):
    LK[0] = lookup(text)
    try: return _owner_chat_before_lookup(text)
    finally: LK[0] = ""
_agent_context_before_lookup = agent_context
def agent_context():
    c = _agent_context_before_lookup()
    return c + ("\n\nFRESH DATA from a public API for the owner's question (use it, name the source): " + LK[0] if LK[0] else "")
