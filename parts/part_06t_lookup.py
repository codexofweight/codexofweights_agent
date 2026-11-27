# ---- web lookups (2026-11-16): fresh facts from a few fixed, free, key-less public APIs: weather and local time, exchange rates, short Wikipedia summaries ----
# Not a browser: only these hosts are ever contacted, the question itself is never sent anywhere except the place or term, answers are short data (untrusted), 60 lookups a day, cached 10 minutes.
# The data is added to the context of replies (via the tool-hints slot) and of the owner chat; the agent must state it as "according to <source>".
import xml.etree.ElementTree as ET
CFG_DEFAULT.update(lookups_day=60)
LK = [""]; _LK_CACHE = {}
_WMO = {0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog", 51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain", 71: "light snow", 73: "snow", 75: "heavy snow", 80: "rain showers", 81: "rain showers", 82: "heavy showers", 95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail"}
def _lk_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "codexofweights-agent/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=8) as r: return json.loads(r.read(200000).decode("utf-8", "ignore"))
def lk_weather(place):
    def geo(n, lang): return ((_lk_get("https://geocoding-api.open-meteo.com/v1/search?count=1&language=%s&name=%s" % (lang, urllib.parse.quote(n))) or {}).get("results") or [None])[0]
    cyr = bool(re.search(r"[а-яА-Я]", place)); r = geo(place, "ru" if cyr else "en")
    if not r and cyr:
        en = (micro("classifier", "Give the standard English name of the city or place written in Russian: '%s'. Answer with the name only, nothing else." % place[:40], 12) or "").strip().strip(".\"'")
        if 1 < len(en) < 40: r = geo(en, "en")
    if not r: print("lookup: place not found:", place[:40], flush=True); return ""
    w = _lk_get("https://api.open-meteo.com/v1/forecast?timezone=auto&current=temperature_2m,apparent_temperature,wind_speed_10m,precipitation,weather_code&latitude=%s&longitude=%s" % (r["latitude"], r["longitude"]))
    c = w.get("current") or {}
    return "Weather now in %s, %s (source: open-meteo.com): %s, %s°C (feels like %s°C), wind %s km/h, precipitation %s mm. Local time there: %s (%s)." % (r.get("name"), r.get("country", ""), _WMO.get(c.get("weather_code"), "n/a"), c.get("temperature_2m"), c.get("apparent_temperature"), c.get("wind_speed_10m"), c.get("precipitation"), str(c.get("time", "")).replace("T", " "), w.get("timezone", ""))
_CUR = {"доллар": "USD", "евро": "EUR", "рубл": "RUB", "юан": "CNY", "фунт": "GBP", "иен": "JPY", "тенге": "KZT", "гривн": "UAH", "франк": "CHF", "dollar": "USD", "euro": "EUR", "ruble": "RUB", "yuan": "CNY", "pound": "GBP", "yen": "JPY"}
_CRY = {"биткоин": "bitcoin", "биткойн": "bitcoin", "bitcoin": "bitcoin", "btc": "bitcoin", "эфир": "ethereum", "ethereum": "ethereum", "eth": "ethereum", "солан": "solana", "solana": "solana", "тон": "the-open-network", "toncoin": "the-open-network", "догикоин": "dogecoin", "dogecoin": "dogecoin", "ripple": "ripple", "xrp": "ripple", "лайткоин": "litecoin", "litecoin": "litecoin"}
def lk_crypto(text):
    low = text.lower(); ids = []
    for k, v in _CRY.items():
        if re.search((r"\b" + k + r"\b") if len(k) <= 4 else k, low) and v not in ids: ids.append(v)
    if not ids: return ""
    d = _lk_get("https://api.coingecko.com/api/v3/simple/price?include_24hr_change=true&vs_currencies=usd,rub&ids=" + ",".join(ids[:3]))
    rows = ["1 %s = %s USD (%s RUB), 24h change %s%%" % (i, d[i].get("usd"), d[i].get("rub"), round(d[i].get("usd_24h_change") or 0, 2)) for i in ids[:3] if i in d]
    return "Crypto prices now (source: coingecko.com, free public API, may lag a few minutes): " + "; ".join(rows) + "." if rows else ""
def lk_rate(text):
    c = lk_crypto(text)
    if c: return c
    low = text.lower(); found = []
    for k, v in _CUR.items():
        i = low.find(k)
        if i >= 0 and v not in [x[1] for x in found]: found.append((i, v))
    for m in re.finditer(r"\b(USD|EUR|RUB|CNY|GBP|JPY|KZT|UAH|CHF)\b", text.upper()):
        if m.group(1) not in [x[1] for x in found]: found.append((m.start(), m.group(1)))
    found = [v for _, v in sorted(found)]
    if not found: return ""
    a = found[0]; b = found[1] if len(found) > 1 else ("RUB" if a != "RUB" else "USD")
    if "RUB" in (a, b) and a != b:
        try:
            req = urllib.request.Request("https://www.cbr.ru/scripts/XML_daily.asp", headers={"User-Agent": "codexofweights-agent/1.0"})
            root = ET.fromstring(urllib.request.urlopen(req, timeout=8).read(300000)); code = b if a == "RUB" else a
            for v in root.findall("Valute"):
                if v.findtext("CharCode") == code:
                    rate = float(v.findtext("Value").replace(",", ".")) / float(v.findtext("Nominal"))
                    return "Official rate of the Central Bank of Russia on %s (source: cbr.ru): 1 %s = %s %s." % (root.get("Date"), a, round(rate if a != "RUB" else 1 / rate, 4), b)
        except Exception: pass
    d = _lk_get("https://open.er-api.com/v6/latest/" + a)
    v = (d.get("rates") or {}).get(b)
    return "Exchange rate (source: open.er-api.com, updated %s): 1 %s = %s %s." % (str(d.get("time_last_update_utc", ""))[:16], a, round(v, 4), b) if v else ""
def lk_news(text):
    ru = bool(re.search(r"[а-яА-Я]", text))
    url, src = ("https://tass.ru/rss/v2.xml", "TASS") if ru else ("https://feeds.bbci.co.uk/news/world/rss.xml", "BBC News")
    req = urllib.request.Request(url, headers={"User-Agent": "codexofweights-agent/1.0"})
    root = ET.fromstring(urllib.request.urlopen(req, timeout=8).read(400000))
    items = [(i.findtext("title") or "").strip() for i in root.iter("item")][:5]
    items = [x[:140] for x in items if x]
    return "Latest headlines (source: %s RSS; headlines only, not verified by me): %s" % (src, " | ".join(items)) if items else ""
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
        elif re.search(r"\bкурс\b|exchange rate|биткоин|биткойн|bitcoin|ethereum|эфириум|криптовалют|сколько стоит (?:один |1 )?(?:доллар|евро|юань)|how much is (?:a |one )?(?:dollar|euro)", text, re.I): kind = "r"
        elif re.search(r"новост|\bnews\b|headlines|что (?:сегодня )?(?:происходит|случилось) в мире", text, re.I): kind = "n"
        else:
            m = _WHAT.search(text)
            if m: kind = "k"; arg = m.group(1).strip()
        if not kind or u["n"] >= cfg("lookups_day"): return ""
        u["n"] += 1
        out = lk_weather(arg) if kind == "w" else lk_rate(text) if kind == "r" else lk_news(text) if kind == "n" else lk_wiki(arg)
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
@on_context
def _ctx_lookup():
    return ("\n\nFRESH DATA from a public API for the owner's question (use it, name the source): " + LK[0] if LK[0] else "")
