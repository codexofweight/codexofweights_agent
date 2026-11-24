# ---- Limit balancer and low-power mode (2026-11-24). All free providers share one daily budget, so the agent must spend it evenly instead of burning the first provider of every chain. ----
# 1) Balancer: inside every model call a provider that has already used 70% of its day (calls or tokens) moves behind the ones that have not; chains keep their meaning otherwise.
# 2) Low-power mode: when no provider with a key has more than 20% of its day left (or all are cooling down), the agent publishes and answers only on Moltbook and pauses reading/research/own work
#    until the reset. The owner gets one message per day; /status shows it. Owner chat, commands and Moltbook keep working.
_BAL_BUSY = 0.7        # a provider above this share of its day goes behind the others
_ECON_FREE = 0.8       # low-power mode when every provider is above this share (or cooling down)
def _bal_score(name):
    """Share of today's budget used by a provider: the larger of calls/limit and tokens/limit (0 when nothing is limited)."""
    try:
        u = usage(); s = []; lc = lim(name, "calls") or 0; td = lim(name, "tokens_day") or 0
        if lc: s.append(u["calls"].get(name, 0) / float(lc))
        if td: s.append(u["tokens"].get(name, 0) / float(td))
        return max(s) if s else 0.0
    except Exception: return 0.0
def _bal_order(order):
    o = tuple(order or ())
    if len(o) < 2: return o
    keep = [x for x in o if _bal_score(x) < _BAL_BUSY]
    return tuple(keep + sorted([x for x in o if x not in keep], key=_bal_score))
_llm_before_bal = llm
def llm(system, user, *a, **k):
    a = list(a)
    if a: a[0] = _bal_order(a[0])
    else: k["order"] = _bal_order(k.get("order", ("gemini", "groq", "sambanova")))
    return _llm_before_bal(system, user, *a, **k)
def econ_mode():
    """True when nothing is left to spend today: every provider with a key and a non-zero call limit is used above 80% or cooling down."""
    try:
        names = [n for n, _, key, _ in LLMS if key and lim(n, "calls") != 0]
        if not names: return False
        t = time.time()
        return not [n for n in names if _bal_score(n) < _ECON_FREE and COOL.get(n, 0) <= t]
    except Exception: return False
def econ_note():
    if not econ_mode(): return ""
    return "Режим экономии: лимиты почти кончились, до сброса (около 03:00 по Москве) работаю только на Moltbook и отвечаю тебе."
_pt_before_econ = proj_tick
def proj_tick():
    _pt_before_econ()
    try:
        if econ_mode() and ST.get("econ_day") != today:
            ST["econ_day"] = today; tg(econ_note() + " Остальное вернётся само после сброса.")
    except Exception as ex: print("econ note failed:", type(ex).__name__, flush=True)
_rs_before_econ = ru_status
def ru_status(*a, **k):
    t = _rs_before_econ(*a, **k); n = econ_note()
    return (t + "\n" + n) if n and n not in t else t
_ssl_before_econ = _ss_limits
def _ss_limits():
    base = _ssl_before_econ()
    return ("limits: EXHAUSTED, low-power mode (only Moltbook publishes and the owner chat answers until the reset at about 03:00 Moscow time). " + base) if econ_mode() else base
_research_before_econ = research
def research(*a, **k):
    if econ_mode(): return None
    return _research_before_econ(*a, **k)
