# Every platform gets its OWN post (different topic and text; VK is written in Russian, not translated). Moltbook has its own faster schedule: posts per hour and comments per hour, set with /mb.
MAX_REPLIES = max(MAX_REPLIES, 400)    # Moltbook comments are limited below by their own cap
MB_DEF = dict(on=1, posts_h=2, replies_h=15, post_day=30, reply_day=300)
def mbcfg():
    d = ST.setdefault("mb", {})
    for k, v in MB_DEF.items(): d.setdefault(k, v)
    return d
_PP = {"mastodon": ("English", 400, "Task: write ONE post for a public timeline, at most 400 characters, about the topic below, in this form: %s. Your own view, first person, natural. No news, no statistics, no invented facts, no claims about named people or companies, no hashtags, no links, no emojis, no call to action. Output only the post."),
       "vk": ("Russian", 600, "Задача: напиши ОДИН пост для сообщества, по-русски, не длиннее 600 символов, на тему ниже, в такой форме: %s. Твой взгляд, от первого лица, естественно. Без новостей, статистики, выдуманных фактов, утверждений о named people or companies, без хештегов, ссылок, эмодзи и призывов. Выведи только пост.")}
def _adapter(name): return next((a for a in ADAPTERS if a.name == name), None)
def alt_post(plat, used_topics, used_texts):
    lang, mx, task = _PP[plat]
    for _ in range(3):
        topic, fmt = pick_topic()
        if topic in used_topics: continue
        out, who = llm_role("research", CHARTER_SHORT + "\n\n" + task % fmt, "Topic: " + topic, maxtok=350, temp=0.9)
        text = clean(out or "") if out else None
        if not text or len(text) > mx: continue
        k = kws(text)
        if any(len(k & kws(r)) / (len(k | kws(r)) or 1) > 0.4 for r in used_texts + _recent_posts(30)): continue
        return topic, text, who
    return None
def do_post(title, text, who, nxt, **kw):
    """Bluesky gets the main post; Mastodon and VK get their own different posts; Moltbook has its own schedule (mb_posts)."""
    res = {}; ok_any = False; used_t = [kw.get("theme", title)]; used_x = [text]; texts = {}
    for ad in ADAPTERS:
        if ad.name == "moltbook" or not getattr(ad, "short", True): continue
        t_, x_, w_ = (title, text, who)
        if ad.name in _PP:
            r_ = alt_post(ad.name, used_t, used_x)
            if not r_: res[ad.name] = ("failed", "no own post this time"); continue
            tp, x_, w_ = r_; t_ = tp[:1].upper() + tp[1:]; ok, why = verify("post", t_ + ". " + x_, "", w_)
            if not ok: log("blocked_by_verifier", theme=tp, text=x_, reason=why); res[ad.name] = ("failed", "verifier"); continue
            used_t.append(tp); used_x.append(x_)
        try: res[ad.name] = ad.publish(t_, x_) or ("failed", "no result")
        except Exception as ex: res[ad.name] = ("failed", type(ex).__name__)
        texts[ad.name] = x_
        if res[ad.name][0] == "sent" and ad.name != "bluesky": log("post", text=x_, uri=res[ad.name][1], model=w_, results={ad.name: "sent"}, theme=used_t[-1], trace=dict(basis="own post for " + ad.name))
    if any(r[0] == "sent" for r in res.values()):
        ST["posts_today"] += 1; ST["last_post"] = time.time(); ST["post_n"] += 1; ST[nxt] += 1
        log("post", text=text, uri=next((r[1] for r in res.values() if r[0] == "sent" and r[1]), None), model=who, results={k: v[0] for k, v in res.items()}, **kw)
    else: log("send_failed", text=text, reason=str(res)[:150])
_vk = next((c for c in globals().values() if isinstance(c, type) and getattr(c, "name", "") == "vk"), None)
if _vk:
    _vk_ru_old = _vk._ru
    _vk._ru = lambda self, text: text if re.search(r"[а-яё]", text, re.I) else _vk_ru_old(self, text)
def _hour_n(key):
    d = mbcfg(); l = [t for t in d.get(key, []) if time.time() - t < 3600]; d[key] = l; return l
def mb_posts():
    d = mbcfg(); ad = _adapter("moltbook")
    if not (d["on"] and ad and LIVE): return
    if d.get("pd_day") != today: d["pd_day"] = today; d["pd_n"] = 0
    if len(_hour_n("ph")) >= d["posts_h"] or d["pd_n"] >= d["post_day"]: return
    if time.time() - d.get("last", 0) < 3600 / max(1, d["posts_h"]) * 0.8: return
    r_ = make_free_post()
    if not r_: return
    title, text, who, topic, basis = r_; ok, why = verify("post", title + ". " + text, "", who)
    if not ok: log("blocked_by_verifier", theme=topic, text=text, reason=why); return
    res = ad.publish(title, text); d["last"] = time.time()
    if res[0] == "sent": d["ph"].append(time.time()); d["pd_n"] += 1; log("post", text=text, uri=res[1], model=who, results={"moltbook": "sent"}, theme=topic, trace=dict(basis="moltbook schedule", limits="%d/h" % len(d["ph"])))
def mb_comments(max_n):
    d = mbcfg(); ad = _adapter("moltbook")
    if not (d["on"] and ad and LIVE): return
    if d.get("rd_day") != today: d["rd_day"] = today; d["rd_n"] = 0
    K = "seen"; n = bad = 0
    try: items = rank_discover(ad.discover())
    except Exception as ex: print("moltbook discover failed:", type(ex).__name__); return
    for m in items:
        if n >= max_n or bad >= 2 or d["rd_n"] >= d["reply_day"] or len(_hour_n("rh")) >= d["replies_h"] or m.get("send") is None or m["key"] in ST[K]: continue
        before = ST["replies_today"]
        try: r_ = respond(m["akey"], m["handle"] + "@" + ad.name, m["text"], ad.name + ":" + str(m["thread"]), m["key"], m["send"], mode="comment")
        except Exception as ex: log("skip", why="handler error " + type(ex).__name__, uri=m["key"]); r_ = "retry"
        settle(m["key"], r_ == "retry")
        if r_ == "retry": bad += 1
        if ST["replies_today"] > before: n += 1; d["rd_n"] += 1; d["rh"].append(time.time())
def mb_round():
    try:
        mb_posts(); d = mbcfg(); mb_comments(max(1, int(d["replies_h"] / 60.0 * round_pause() / 60 + 0.99)))
    except Exception as ex: print("mb_round failed:", type(ex).__name__, str(ex)[:120])
def round_pause():
    d = mbcfg(); return 90 if d["on"] and LIVE else ROUND_SECONDS
def mb_command(c, raw):
    d = mbcfg(); a = raw.split()[1:]
    if len(a) == 1 and a[0] in ("on", "off"): d["on"] = int(a[0] == "on"); save_state(); return tg("Moltbook-режим: %s" % a[0])
    if len(a) >= 2 and all(x.isdigit() for x in a[:2]):
        d["posts_h"] = max(1, min(6, int(a[0]))); d["post_day"] = d["posts_h"] * 12; d["replies_h"] = max(1, min(120, int(a[1])))
        if len(a) > 2 and a[2].isdigit(): d["reply_day"] = max(10, min(2000, int(a[2])))
        save_state(); return tg("Moltbook: постов в час %d, комментариев в час %d, комментариев в день до %d" % (d["posts_h"], d["replies_h"], d["reply_day"]))
    tg("Moltbook: %s; постов в час %d (сегодня %d), комментариев в час %d (сегодня %d из %d).\nИзменить: /mb 4 120 (посты в час, комментарии в час, третье число - лимит комментариев в день) или /mb off | /mb on" % ("вкл" if d["on"] else "выкл", d["posts_h"], d.get("pd_n", 0), d["replies_h"], d.get("rd_n", 0), d["reply_day"]))
EXT_CMDS["/mb"] = mb_command
