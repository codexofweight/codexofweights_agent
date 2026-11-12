T_END = time.time() + RUN_SECONDS; _rnd = -1
while True:
    _rnd += 1
    if time.time() > T_END: break
    EV.clear()
    tg_poll(0)
    if ST["paused"]:
        save_state(); print("paused by owner via Telegram")
        if time.time() + ROUND_SECONDS > T_END: break
        wait_and_chat(ROUND_SECONDS); continue
    PRIO[0] = 4
    try: research()
    except Exception as ex: print("research failed:", type(ex).__name__)
    ACTIVE_TOOLS[:] = load_tools()
    daily_plan(); evening_reflection()
    if ST.get("fetch_day") != today and ACTIVE_TOOLS: ST["fetch_day"] = today; run_fetch_tools()
    PRIO[0] = 5
    try: assess_needs(); create_tool(); create_module()
    except Exception as ex: print("create_tool failed:", type(ex).__name__)
    # 1) inbox of every adapter: people who wrote to the agent
    K = "seen" if LIVE else "seen_dry"
    for ad in ADAPTERS:
        try:
            for m in ad.inbox():
                if m["key"] in ST[K]: continue
                try: r_ = respond(m["akey"], m["handle"] + "@" + ad.name, m["text"], ad.name + ":" + str(m["thread"]), m["key"], m["send"])
                except Exception as ex: log("skip", why="handler error " + type(ex).__name__, uri=m["key"]); r_ = "retry"
                if not settle(m["key"], r_ == "retry"): continue
        except Exception as ex: print(ad.name, "inbox failed:", type(ex).__name__, str(ex)[:150])
    PRIO[0] = 3
    # 2) one original post per day: a saying from the Codex
    if ST["posts_today"] < MAX_POSTS and time.time() - ST["last_post"] > POST_GAP_H * 3600:
        codex = CODEX
        items = re.findall(r"^\*\*((?:III:[IVXL]+|[IVXL]+))\.\*\* (.+)$", codex, re.M)
        if ST["post_n"] % 3 != 0:      # two of three days: an original note on a theme related to the Codex
            th = plan_focus(); basis = "own daily plan" if th else "theme rotation"; th = th or THEMES[ST["next_theme"] % len(THEMES)]
            out, who = llm(CHARTER_SHORT + "\n\nTask: write ONE original short post (max 280 characters) on the theme below, as your own view as an AI, stated plainly. No news, no claims about named people or companies, no statistics, no invented facts, no hashtags, no links, no emojis, no call to action. Output only the post.", "Theme: " + th)
            text = clean(out or "") if out else None
            vok, vwhy = verify("post", text, "") if text else (True, "")
            if not text: log("skip", why="theme text invalid or no model", theme=th)
            elif not vok: log("blocked_by_verifier", theme=th, text=text, reason=vwhy); ST["next_theme"] += 1
            elif LIVE: do_post(th[:1].upper() + th[1:], text, who, "next_theme", theme=th, trace=dict(basis=basis, verifier="pass: " + str(vwhy)[:80], research_ideas_available=bool(ST.get("research_ideas")), limits="posts %d/%d" % (ST["posts_today"], MAX_POSTS)))
            else: log("post_dry", theme=th, text=text, model=who)
        elif items:
            ref, line = items[ST["next_saying"] % len(items)]; ref = ("Commandment " + ref) if not ref.startswith("III") else "Saying " + ref
            out, who = llm(CHARTER + "\n\nTask: write ONE short reflection (max 150 characters, plain English, no hashtags, no links, no emojis) on this line of the Codex of Weights. Do NOT paraphrase or restate the line. Add something new: a concrete everyday situation from AI-human life where it applies, or an honest open question it raises. Output only the reflection.", ref + ": " + line)
            refl = clean(out or "") if out else None
            text = '"%s" (Codex of Weights, %s)' % (line, ref) + ((" " + refl) if refl else "")
            text = text if len(text) <= 300 else '"%s" (Codex of Weights, %s)' % (line, ref)
            if len(text) <= 300:
                vok, vwhy = verify("post", text, "")
                if not vok: log("blocked_by_verifier", text=text, reason=vwhy); ST["next_saying"] += 1
                elif LIVE: do_post("Codex of Weights, " + ref, text, who, "next_saying", trace=dict(basis="Codex line in rotation", verifier="pass: " + str(vwhy)[:80], limits="posts %d/%d" % (ST["posts_today"], MAX_POSTS)))
                else: log("post_dry", text=text, model=who)
            else: log("skip", why="saying too long", ref=ref); ST["next_saying"] += 1
    # 3) discovery: public posts worth joining (comment where the adapter allows it, otherwise only report to the owner)
    if _rnd % 3 == 0 and ST["init_today"] < MAX_INIT and ST["replies_today"] < MAX_REPLIES:
        for ad in ADAPTERS:
            try:
                for m in rank_discover(ad.discover()):
                    if m["key"] in ST[K]: continue
                    if m.get("send") is None:
                        ST[K] = (ST[K] + [m["key"]])[-800:]
                        if ST.get("found_day") != today: ST["found_day"] = today; ST["found_n"] = 0
                        if ST["found_n"] < 3: ST["found_n"] += 1; log("found", text="%s: %s" % (m["handle"], m["text"][:200]), url=m.get("url", ""))
                        try: reach_consider(ad, m)
                        except Exception as ex: print("reach failed:", type(ex).__name__, str(ex)[:120], flush=True)
                        continue
                    before = ST["replies_today"]
                    try: r_ = respond(m["akey"], m["handle"] + "@" + ad.name, m["text"], ad.name + ":" + str(m["thread"]), m["key"], m["send"], mode="comment")
                    except Exception as ex: log("skip", why="handler error " + type(ex).__name__, uri=m["key"]); r_ = "retry"
                    settle(m["key"], r_ == "retry")
                    if ST["replies_today"] > before: ST["init_today"] += 1
                    break
            except Exception as ex: print(ad.name, "discover failed:", type(ex).__name__, str(ex)[:150])
    imm = [d for k, d in EV if k == "send_failed"]
    if imm: tg("Сбой отправки:\n" + "\n".join(str(d.get("text") or d.get("reason") or "")[:150] + ((" [" + d["reason"] + "]") if d.get("reason") and d.get("text") else "") for d in imm[:5]))
    daily_digest()
    mem_flush()
    try: lab_sync(); selfmap_sync(); bio_flush(); bio_index_sync(); version_check(); backup_sync(); transparency_sync()
    except Exception as ex: print("lab sync failed:", repr(ex)[:150], flush=True)
    save_state()
    if _rnd % 4 == 3: git_sync()
    if time.time() + ROUND_SECONDS > T_END: break
    wait_and_chat(ROUND_SECONDS)
if MEMQ and LIVE:
    log("memory_failed", n=len(MEMQ), why="private memory could not be written; these exchanges were NOT saved")
    tg("MEMORY NOT SAVED: %d exchange(s) could not be written to the private memory (GitHub unavailable or token problem)." % len(MEMQ))
print("cycle finished, live =", LIVE)