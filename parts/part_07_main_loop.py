T_END = time.time() + RUN_SECONDS; _rnd = -1
while True:
    _rnd += 1
    if time.time() > T_END: break
    EV.clear()
    tg_poll(0)
    if os.path.exists(P("STOP")):      # added 2026-11-14: the file-based STOP check at the top of
        # part_01_core.py only runs once, before this loop starts - so creating STOP mid-run had NO
        # effect on an already-running cycle (it could keep going for up to RUN_SECONDS, ~5.5h). This
        # re-checks it every round (~ROUND_SECONDS) so STOP genuinely halts within a few minutes, not
        # hours - matching what the agent's own docstring claims ("stops at once").
        log("halt", why="STOP file present - ending this run now instead of waiting for it to finish")
        tg("STOP file detected - ending this run now."); save_state(); break
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
    for ad in ([] if econ_mode() else ADAPTERS):      # low-power mode: only Moltbook (its own round below) and the owner chat stay active
        try:
            for m in ad.inbox():
                if m["key"] in ST[K]: continue
                try: r_ = respond(m["akey"], m["handle"] + "@" + ad.name, m["text"], ad.name + ":" + str(m["thread"]), m["key"], m["send"])
                except Exception as ex: log("skip", why="handler error " + type(ex).__name__, uri=m["key"]); r_ = "retry"
                if not settle(m["key"], r_ == "retry"): continue
        except Exception as ex: print(ad.name, "inbox failed:", type(ex).__name__, str(ex)[:150])
    PRIO[0] = 3
    # 2) one original post per day: free topics in the agent's own voice; an idea from the Protocols only about one post in eight
    if ST["posts_today"] < MAX_POSTS and time.time() - ST["last_post"] > POST_GAP_H * 3600 and not econ_mode():
        proto = ST["post_n"] % 8 == 7
        r_p = make_protocol_post() if proto else make_free_post()
        if not r_p: log("skip", why="post text invalid, too similar, or no model")
        else:
            title, text, who, topic, basis = r_p; nxt = "next_saying" if proto else "next_theme"
            vok, vwhy = verify("post", title + ". " + text, "", who)      # the title is checked together with the text
            if not vok: log("blocked_by_verifier", theme=topic, text=text, reason=vwhy); ST[nxt] += 1
            elif LIVE: do_post(title, text, who, nxt, theme=topic, trace=dict(basis=basis, verifier="pass: " + str(vwhy)[:80], limits="posts %d/%d" % (ST["posts_today"], MAX_POSTS)))
            else: log("post_dry", theme=topic, text=text, model=who)
    # 3) discovery: public posts worth joining (comment where the adapter allows it, otherwise only report to the owner)
    if _rnd % 3 == 0 and ST["init_today"] < MAX_INIT and ST["replies_today"] < MAX_REPLIES and not econ_mode():
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
    PRIO[0] = 3
    try: mb_round()
    except Exception as ex: print("mb_round failed:", type(ex).__name__)
    imm = [d for k, d in EV if k == "send_failed"]
    if imm: tg("Сбой отправки:\n" + "\n".join(str(d.get("text") or d.get("reason") or "")[:150] + ((" [" + d["reason"] + "]") if d.get("reason") and d.get("text") else "") for d in imm[:5]))
    daily_digest()
    mem_flush()
    try: lab_sync(); selfmap_sync(); bio_flush(); bio_index_sync(); version_check(); backup_sync(); transparency_sync()
    except Exception as ex: print("lab sync failed:", repr(ex)[:150], flush=True)
    save_state()
    if _rnd % 4 == 3: git_sync()
    if time.time() + ROUND_SECONDS > T_END: break
    wait_and_chat(round_pause())
if MEMQ and LIVE:
    log("memory_failed", n=len(MEMQ), why="private memory could not be written; these exchanges were NOT saved")
    tg("MEMORY NOT SAVED: %d exchange(s) could not be written to the private memory (GitHub unavailable or token problem)." % len(MEMQ))
print("cycle finished, live =", LIVE)
