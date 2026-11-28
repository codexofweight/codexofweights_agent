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
    t = time.time(); keep = [x for x in o if _bal_score(x) < _BAL_BUSY and COOL.get(x, 0) <= t]
    return tuple(keep + sorted([x for x in o if x not in keep], key=lambda x: (COOL.get(x, 0) > t, _bal_score(x))))
_llm_before_bal = llm
def llm(system, user, *a, **k):
    a = list(a)
    if a: a[0] = _bal_order(a[0])
    else: k["order"] = _bal_order(k.get("order", ("groq", "groqq", "openrouter", "gemini", "sambanova")))
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
@on_tick
def _econ_tick():
    try:
        if econ_mode() and ST.get("econ_day") != today:
            ST["econ_day"] = today; tg(econ_note() + " Остальное вернётся само после сброса.")
    except Exception as ex: print("econ note failed:", type(ex).__name__, flush=True)
_rs_before_econ = ru_status
def ru_status(*a, **k):
    t = _rs_before_econ(*a, **k); n = econ_note()
    t = (t + "\n" + n) if n and n not in t else t
    try: t += "\n" + gut_line()
    except Exception: pass
    return t
_ssl_before_econ = _ss_limits
def _ss_limits():
    base = _ssl_before_econ()
    return ("limits: EXHAUSTED, low-power mode (only Moltbook publishes and the owner chat answers until the reset at about 03:00 Moscow time). " + base) if econ_mode() else base
_research_before_econ = research
def research(*a, **k):
    if econ_mode(): return None
    return _research_before_econ(*a, **k)
# ---- Hotfix 2026-11-25: a provider that keeps failing is left alone for longer and longer. ----
# Reason: a quota error from Gemini was read as a short pause and retried every minute (515 failed calls in one day). Now every failure in a row lengthens the pause: 5, 10, 20, 40, 80, 120 minutes; 30 in a row = until the daily reset. One success clears it.
_FAIL_RUN = {}
def _fail_pause(n):
    """Seconds to leave a provider alone after n failed attempts in a row (0 below 6)."""
    if n < 6: return 0
    return min(300 * 2 ** ((n - 6) // 3), 7200)
_llm_before_fail = llm
def llm(system, user, *a, **k):
    u = usage(); names = [x[0] for x in LLMS]
    c0 = {n: u["calls"].get(n, 0) for n in names}; f0 = {n: u["fails"].get(n, 0) for n in names}
    try: return _llm_before_fail(system, user, *a, **k)
    finally:
        try:
            u = usage(); t = time.time()
            try:
                dc = sum(u["calls"].values()) - sum(c0.values())
                if dc > 0: pr_ = _hl_roll(_hl()).setdefault("pr", {}); pr_[str(PRIO[0])] = pr_.get(str(PRIO[0]), 0) + dc      # model calls by priority = by circuit (owner, replies, posts, reading, lab)
            except Exception: pass
            for n in names:
                if u["calls"].get(n, 0) > c0[n]: _FAIL_RUN[n] = 0
                elif u["fails"].get(n, 0) > f0[n]:
                    r = _FAIL_RUN[n] = _FAIL_RUN.get(n, 0) + u["fails"].get(n, 0) - f0[n]
                    p = _fail_pause(r)
                    if r >= 30: COOL[n] = max(COOL.get(n, 0), next_reset(n))
                    elif p: COOL[n] = max(COOL.get(n, 0), t + p)
        except Exception as ex: print("fail tracker error:", type(ex).__name__, flush=True)
# Verification and the stop-intent check must not lean on Gemini or on providers switched off by the owner: Qwen on the Groq key and OpenRouter first.
VERIFY_ORDER = ("groqq", "openrouter", "groq")
# A stop phrase without a model is trusted only in a short message; in a long text "go away" or "opt out" is usually about something else.
_stop_heuristic_before = _stop_heuristic
def _stop_heuristic(text):
    return len((text or "").strip()) <= 160 and _stop_heuristic_before(text)
