# ---- intuition: a quiet, cheap gut feeling learned from the agent's own history (no model calls, no notifications) ----
# Before it answers, the agent forms a hunch: "will this person come back within 3 days?" (a content-free guess from simple features).
# Three days later the outcome is known from the agent's own inbox. Hits and misses accumulate; once a week one line goes into the report.
# Advisory only: it never blocks, never changes a reply and never touches the safety checks. Switch off: /cfg intuition 0.
CFG_DEFAULT.update(intuition=1)
INTU_WAIT = 72 * 3600
def _intu(): return ST.setdefault("intu", {"open": [], "stats": {}, "glob": [0, 0], "n": 0, "hit": 0, "br": 0.0, "br0": 0.0})
def intu_features(thread, mode, their):
    n = len((their or "").strip())
    return ["pl=" + str(thread).split(":")[0][:12], "mode=" + mode, "len=" + ("s" if n < 60 else "m" if n < 200 else "l"),
            "q=" + ("1" if "?" in (their or "") else "0"), "hr=" + str(now().hour // 6)]
def intu_guess(feats):
    """Smoothed average of the per-feature return rates, pulled toward the overall rate. Returns a probability in (0, 1)."""
    I = _intu(); gp, gn = I["glob"]; g = (gp + 1.0) / (gn + 3.0); ps = []
    for f in feats:
        p_, n_ = I["stats"].get(f, [0, 0]); ps.append((p_ + 4 * g) / (n_ + 4.0))
    return min(0.99, max(0.01, sum(ps) / len(ps))) if ps else g
def intu_resolve(rec, outcome):
    I = _intu(); p = rec["p"]; gp, gn = I["glob"]; g0 = (gp + 1.0) / (gn + 3.0)
    I["n"] += 1; I["hit"] += int((p >= 0.5) == bool(outcome)); I["br"] += (p - outcome) ** 2; I["br0"] += (g0 - outcome) ** 2
    I["glob"] = [gp + outcome, gn + 1]
    for f in rec["f"]:
        s = I["stats"].setdefault(f, [0, 0]); s[0] += outcome; s[1] += 1
def intu_sweep():
    I = _intu(); t = time.time(); keep = []
    for r in I["open"]:
        if t - r["t"] >= INTU_WAIT: intu_resolve(r, 0)
        else: keep.append(r)
    I["open"] = keep
def intu_back(au):
    """The same person wrote to us again while a hunch about them was open: the guess is confirmed."""
    I = _intu(); a = _h(au); keep = []
    for r in I["open"]:
        if r["a"] == a: intu_resolve(r, 1)
        else: keep.append(r)
    I["open"] = keep
_respond_before_intuition = respond
def respond(au, handle, their, thread, uid, send, mode="reply"):
    on = cfg("intuition")
    if on:
        try:
            intu_sweep()
            if mode == "reply": intu_back(au)
            feats = intu_features(thread, mode, their); p = intu_guess(feats)
        except Exception as ex: print("intuition failed:", type(ex).__name__, flush=True); on = 0
    before = ST["replies_today"]
    r_ = _respond_before_intuition(au, handle, their, thread, uid, send, mode)
    if on and ST["replies_today"] > before and LIVE:
        try:
            I = _intu(); I["open"] = (I["open"] + [{"t": time.time(), "a": _h(au), "f": feats, "p": round(p, 3)}])[-300:]
        except Exception as ex: print("intuition failed:", type(ex).__name__, flush=True)
    return r_
def intu_report():
    try: intu_sweep(); I = _intu()
    except Exception: return ""
    if I["n"] < 10: return "Интуиция: пока копится опыт (%d проверенных догадок из 10 нужных)." % I["n"]
    n = I["n"]; g = I["glob"][0] / max(1, I["glob"][1])
    return "Интуиция: проверено %d догадок, вернулись %d%%, угадала %d%%, ошибка %.3f против %.3f у «всегда как в среднем» (меньше значит лучше)." % (n, round(100 * g), round(100 * I["hit"] / n), I["br"] / n, I["br0"] / n)
def intuition_command(c, raw=None):
    I = _intu(); tg(intu_report() + "\nОткрытых догадок: %d. Только наблюдает и ничего не меняет. Выключить: /cfg intuition 0." % len(I["open"]))
try: WEEKLY_EXTRA.append(intu_report)
except Exception: pass
EXT_CMDS["/intuition"] = intuition_command
