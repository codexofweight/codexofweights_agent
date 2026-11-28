# ---- gut check before a move (2026-11-28): cheap rules from the agent's own recent history, no model calls ----
# 1) The checking model is down ("verifier unavailable"): replies are held for 10 minutes (20 if it happens twice in 20 minutes) instead of writing drafts that cannot be checked,
#    and a reply that was only lost to that is retried later instead of being dropped.
# 2) An author whose replies the check blocked twice within a day (for a real reason, not for a model outage) is skipped for 24 hours.
# 3) Posts: when the checking model is down, the next post attempt rests 30 minutes (no drafts that cannot be checked).
# 4) One forecast checked against facts: "will the check block a reply of this kind?" (platform, mode, length, hour). Every forecast is compared with the outcome (hits, Brier error vs the plain average).
#    It acts only when it has 40+ cases and is 85%+ sure; until then it only learns. The older return-forecast (part_06r_intuition) stays as the second forecast; /gut shows both.
# It only ever skips or delays; it never sends anything and never touches the safety checks. Switch off: /cfg gut 0.
CFG_DEFAULT.update(gut=1)
GUT_MIN_N, GUT_ACT_P = 40, 0.85
_GUT_BLK_NOW = {}
_GUT_UNAV = {}
def _gut_on():
    try: return bool(cfg("gut"))
    except Exception: return True
def _gut_state():
    g = ST.setdefault("gut", {"unav": [], "quiet": {}, "holds": 0, "muted": 0})
    g.setdefault("bf", {"stats": {}, "glob": [0, 0], "n": 0, "hit": 0, "br": 0.0, "br0": 0.0}); g.setdefault("skipped_fc", 0); g.setdefault("retried", 0)
    return g
@on_log
def _gut_log(kind, kw):
    if kind != "blocked_by_verifier" or not _gut_on(): return
    t = time.time(); g = _gut_state(); why = str(kw.get("reason", ""))
    if "unavailable" in why:
        g["unav"] = [x for x in g["unav"] if t - x < 1200][-10:] + [t]
        _GUT_UNAV[str(kw.get("uri", ""))] = t
        if kw.get("theme") is not None: ST["post_rest_until"] = max(float(ST.get("post_rest_until", 0) or 0), t + 1800)      # a post draft that could not be checked: rest
        _smr()["guard_until"] = max(float(_smr().get("guard_until", 0) or 0), t + (1200 if len(g["unav"]) >= 2 else 600)); g["holds"] += 1
        if len(_GUT_UNAV) > 50:
            for k in sorted(_GUT_UNAV, key=_GUT_UNAV.get)[:25]: _GUT_UNAV.pop(k, None)
        return
    _GUT_BLK_NOW[str(kw.get("uri", ""))] = t
    who = str(kw.get("to") or "")
    if not who or who.startswith("h:"): return                      # hashed identities (VK, direct messages) are not tracked
    b = ST.setdefault("gut_blk", {}); k = _h(who); b[k] = [x for x in b.get(k, []) if t - x < 86400] + [t]
    if len(b[k]) >= 2: g["quiet"][k] = t + 86400; b.pop(k, None)
    if len(g["quiet"]) > 100:
        for k_ in [k_ for k_, v in g["quiet"].items() if v < t][:60]: g["quiet"].pop(k_, None)
def gut_muted(handle, uid):
    """True when this author is on the 24 h quiet list (the reply is skipped before any model call)."""
    try:
        if not _gut_on(): return False
        g = _gut_state(); k = _h(handle)
        if float(g["quiet"].get(k, 0) or 0) > time.time():
            g["muted"] += 1; log("skip", why="gut: author blocked twice today, skipped for 24 h", uri=uid); return True
    except Exception: pass
    return False
def _bf_guess(feats):
    b = _gut_state()["bf"]; gp, gn = b["glob"]; g = (gp + 1.0) / (gn + 3.0); ps = []
    for f in feats:
        p_, n_ = b["stats"].get(f, [0, 0]); ps.append((p_ + 4 * g) / (n_ + 4.0))
    return (min(0.99, max(0.01, sum(ps) / len(ps))) if ps else g), gn
def gut_begin(uid, thread, mode, their):
    """The forecast before a reply: returns None (not active), a token, or "skip" (confident that the check would block it)."""
    try:
        if not _gut_on(): return None
        feats = intu_features(thread, mode, their); p, n = _bf_guess(feats)
        if n >= GUT_MIN_N and p >= GUT_ACT_P:
            _gut_state()["skipped_fc"] += 1; log("skip", why="gut: replies of this kind are almost always blocked", uri=uid); return "skip"
        return {"f": feats, "p": p, "before": ST["replies_today"]}
    except Exception: return None
def gut_end(uid, r, tk):
    """Learns from the outcome (blocked = 1, sent = 0; anything else teaches nothing) and keeps a reply lost only to a model outage for a retry."""
    try:
        if not _gut_on(): return r
        g = _gut_state(); blocked = _GUT_BLK_NOW.pop(str(uid), None) is not None
        if isinstance(tk, dict) and (blocked or ST["replies_today"] > tk["before"]):
            o = 1 if blocked else 0; b = g["bf"]; p = tk["p"]; gp, gn = b["glob"]; g0 = (gp + 1.0) / (gn + 3.0)
            b["n"] += 1; b["hit"] += int((p >= 0.5) == bool(o)); b["br"] += (p - o) ** 2; b["br0"] += (g0 - o) ** 2; b["glob"] = [gp + o, gn + 1]
            for f in tk["f"]:
                s_ = b["stats"].setdefault(f, [0, 0]); s_[0] += o; s_[1] += 1
            if len(b["stats"]) > 80: b["stats"] = dict(sorted(b["stats"].items(), key=lambda kv: -kv[1][1])[:60])      # rare old keys go
        if len(_GUT_BLK_NOW) > 50:
            for k in sorted(_GUT_BLK_NOW, key=_GUT_BLK_NOW.get)[:25]: _GUT_BLK_NOW.pop(k, None)
        if r is None and _GUT_UNAV.pop(str(uid), None) is not None: g["retried"] += 1; return "retry"
    except Exception: pass
    return r
def gut_after(uid, r): return gut_end(uid, r, None)      # kept for the older call shape
def gut_line():
    try:
        g = _gut_state(); b = g["bf"]; s = "Чутьё до хода: пауз при сбое проверки %d, ответов возвращено на повтор %d, авторов в тишине %d, пропусков по прогнозу %d." % (g["holds"], g["retried"], g["muted"], g["skipped_fc"])
        if b["n"] >= 10: s += " Прогноз «заблокирует ли проверка»: %d случаев, угадал %d%%, ошибка %.3f против %.3f у «как в среднем»." % (b["n"], round(100.0 * b["hit"] / b["n"]), b["br"] / b["n"], b["br0"] / b["n"])
        else: s += " Прогноз «заблокирует ли проверка» копит опыт (%d из 10)." % b["n"]
        return s
    except Exception: return ""
def gut_short():
    g = _gut_state(); b = g["bf"]
    s = "Gut totals: %d holds, %d retried, %d authors quiet, %d forecast skips" % (g["holds"], g["retried"], g["muted"], g["skipped_fc"])
    if b["n"] >= 30: s += "; block forecast %d cases, %s than the plain average" % (b["n"], "better" if b["br"] < b["br0"] else "not better")      # said only when there is enough to say
    return s + "."
def gut_command(c, raw=None):
    try: ir = intu_report()
    except Exception: ir = ""
    tg(gut_line() + ("\n" + ir if ir else "") + "\nЧутьё только пропускает и откладывает, ничего не отправляет. Выключить: /cfg gut 0.")
EXT_CMDS["/gut"] = gut_command
