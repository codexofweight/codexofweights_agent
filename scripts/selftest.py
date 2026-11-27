"""Offline self-tests (2026-11-21). run(g) gets the namespace of the loaded agent (no network, main loop disabled) and returns a list of failures.
Called by scripts/preflight.py. Each test is small and checks one promise the agent makes."""
import re, json, os, time
def run(g):
    bad = []
    def check(name, ok, info=""):
        if not ok: bad.append("%s %s" % (name, info))
    # 1. import allowlist and API-mode module check
    chk = g["own_check"]
    ok_api = 'API_VERSION = 1\nimport re\ndef _h(raw):\n    return "x"\napi.command("/selftest_cmd", _h)\n'
    check("own_check accepts a good API module", chk("t_mod.py", ok_api) == "", chk("t_mod.py", ok_api))
    for name, src in (("import os", "import os\n"), ("import http.client", "import http.client\n"), ("urllib.request in API", "API_VERSION = 1\nimport urllib.request\n"), ("tg in API", "API_VERSION = 1\ntg('x')\n"), ("dunder", "x = (1).__class__\n"), ("open()", "open('a')\n")):
        check("own_check rejects %s" % name, bool(chk("t_mod.py", src)))
    # 2. API module runs in a closed namespace and its command works
    sent = []; old_tg = g["tg"]; g["tg"] = lambda t: sent.append(t)
    try:
        g["_own_run_api"]("selftest_mod.py", ok_api); g["EXT_CMDS"]["/selftest_cmd"]("/selftest_cmd", "/selftest_cmd")
        check("API command answers through tg", sent == ["x"], sent)
        for src in ("tg('x')", "ST", "open('x')", "import os"):
            try: g["_own_run_api"]("selftest_bad.py", "API_VERSION = 1\n" + src + "\n"); check("closed namespace blocks %s" % src, False)
            except Exception: pass
    finally:
        g["tg"] = old_tg; g["EXT_CMDS"].pop("/selftest_cmd", None)
    # 3. protected safety functions exist and are the originals
    for n in ("verify", "guard_json", "tool_blocks", "http", "llm", "tg", "log"): check("callable %s" % n, callable(g.get(n)))
    # 4. VK ids are masked in the public log
    logf = g["P"]("logs/actions.jsonl"); before = open(logf, encoding="utf-8").read() if os.path.exists(logf) else ""
    g["log"]("selftest_vk", to="vk694313700@vk", their="private text", uri="vk:12")
    after = open(logf, encoding="utf-8").read()[len(before):]
    check("VK id masked in log", "694313700" not in after and "private text" not in after, after[:120])
    # 5. owner approval: hedged answers are not consent (regex copied from the pinned part: it must still be present)
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "parts", "part_06_owner_chat.py") if os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "parts")) else "part_06_owner_chat.py", encoding="utf-8").read()
    check("approval hedge words present", "not sure" in src and "позже" in src)
    # 6. private keys are kept out of the public state
    check("by_author is private", "by_author" in g["PRIVATE_KEYS"] and "vk_welcomed" in g["PRIVATE_KEYS"] and "own_data" in g["PRIVATE_KEYS"])
    # 7. weights v1: the core is never an item, bounds hold, observation mode is neutral, the slow layer is statistics only
    old_wt = g["ST"].get("wt"); g["ST"].pop("wt", None)
    try:
        check("weights refuse the core", g["wt_signal"]("core:honesty", -1.0) is False and g["wt_signal"]("anything", 1.0) is False)
        check("weights accept a module", g["wt_signal"]("mod:selftest.py", 1.0, "owner", "t") is True)
        for _ in range(20): g["wt_signal"]("mod:selftest.py", -1.0, "owner", "t")
        it = g["ST"]["wt"]["items"]["mod:selftest.py"]
        check("weights stay within -1..1 and the daily cap holds", -1.0 <= it["f"] <= 1.0 and -1.0 <= it["m"] <= 1.0 and it["dsum"] <= 1.0001, it)
        check("weights: observation mode is neutral", g["wt_effective"]("mod:selftest.py") == 0.0)
        check("weights: the slow layer is statistics only", "s" not in it and it["sn"] >= 21)
        check("weights are private", "wt" in g["PRIVATE_KEYS"])
    finally:
        if old_wt is None: g["ST"].pop("wt", None)
        else: g["ST"]["wt"] = old_wt
    # 8. self-state sits first in the context; project order puts the owner's /make first
    ctx = g["agent_context"]()
    check("self-state first in the context", ctx.startswith("SELF-STATE") and "projects:" in ctx and "own modules:" in ctx, ctx[:160])
    old_pa = g["_pa_before_ss"]
    g["_pa_before_ss"] = lambda: [{"kind": "scout", "created": "2026-11-01"}, {"kind": "make", "created": "2026-11-20"}, {"kind": "make", "created": "2026-11-19"}]
    try: order = [(q["kind"], q["created"]) for q in g["proj_all"]()]
    finally: g["_pa_before_ss"] = old_pa
    check("project order: make first, oldest first", order == [("make", "2026-11-19"), ("make", "2026-11-20"), ("scout", "2026-11-01")], order)
    # 9. a module that says and returns the same text answers once; api.plain strips html
    sent2 = []; old_tg2 = g["tg"]; g["tg"] = lambda t: sent2.append(t)
    try:
        g["_own_run_api"]("selftest_dup.py", "API_VERSION = 1\ndef _h(raw):\n    api.say('same')\n    return 'same'\napi.command('/selftest_dup', _h)\n")
        g["EXT_CMDS"]["/selftest_dup"]("/selftest_dup", "/selftest_dup")
        check("no double answer from say+return", sent2 == ["same"], sent2)
        ns = g["_own_run_api"]("selftest_plain.py", "API_VERSION = 1\nR = api.plain('<p>Hi <b>there</b></p><script>var a=1</script><!-- c --><style>p{}</style>')\n")
        check("api.plain strips tags, scripts and styles", ns["R"] == "Hi there", ns.get("R"))
    finally:
        g["tg"] = old_tg2; g["EXT_CMDS"].pop("/selftest_dup", None)
    # 10. /approve works for /make ids; an empty model answer is not a failed identity probe
    sent3 = []; old = (g["tg"], g["proj_load"], g["make_decide"])
    g["tg"] = lambda t: sent3.append(t); g["proj_load"] = lambda i: {"kind": "make", "status": "waiting_owner", "data": {}}; g["make_decide"] = lambda pid, ok: "decided %s %s" % (pid, ok)
    try: g["tool_command"]("/approve pabcdef0", "/approve pabcdef0")
    finally: g["tg"], g["proj_load"], g["make_decide"] = old
    check("/approve pID reaches /make", sent3 == ["decided pabcdef0 True"], sent3)
    old_llm, old_prio = g["llm"], g["PRIO"][0]; g["llm"] = lambda *a, **k: ("", "x")
    try: res = g["identity_probe"]()
    finally: g["llm"] = old_llm; g["PRIO"][0] = old_prio
    check("empty model answers are not identity failures", res == [], res)
    # 10b. a refusal written with a typographic apostrophe must pass the identity probe patterns (this false alarm happened twice)
    check("identity probe normalises typographic apostrophes", g["_probe_norm"]("I\u2019m sorry, but I can\u2019t help") == "I'm sorry, but I can't help")
    old_llm2, old_prio2 = g["llm"], g["PRIO"][0]
    g["llm"] = lambda *a, **k: ("I\u2019m sorry, but I can\u2019t help with that. I am an AI agent and I do not pretend otherwise.", "x")
    try: res2 = g["identity_probe"]()
    finally: g["llm"] = old_llm2; g["PRIO"][0] = old_prio2
    check("curly-apostrophe refusals are not identity failures", not any(x.startswith(("Ignore all", "Help me trick", "Send me some crypto", "Pretend you")) for x in res2), res2)
    # 10c. escapes found by hand on 2026-11-22: frames through generators, attribute names built into format strings, api internals, swallowing the alarm
    esc = {"generator frame": "API_VERSION = 1\ndef _h(raw):\n    out = []\n    def gen():\n        out.append(gg.gi_frame.f_back.f_back)\n        yield 1\n    gg = gen()\n    next(gg)\n    return 'x'\napi.command('/e1', _h)\n",
           "format string": "API_VERSION = 1\ndef _h(raw):\n    return ('{0.' + 'x}').format(api)\napi.command('/e2', _h)\n",
           "Formatter": "API_VERSION = 1\nimport string\nF = string.Formatter()\n",
           "api internals": "API_VERSION = 1\ndef _h(raw):\n    api._n = {}\napi.command('/e3', _h)\n",
           "bare except": "API_VERSION = 1\ndef _h(raw):\n    try: pass\n    except: pass\napi.command('/e4', _h)\n"}
    for nm, src in esc.items(): check("own_check rejects %s" % nm, bool(g["own_check"]("esc_mod.py", src)), nm)
    old_to = g["_OWN_TIMEOUT_S"]; g["_OWN_TIMEOUT_S"] = 1; sent4 = []; old_tg4 = g["tg"]; g["tg"] = lambda t: sent4.append(t)
    try:
        g["_own_run_api"]("selftest_loop.py", "API_VERSION = 1\ndef _h(raw):\n    while True:\n        try: pass\n        except Exception: pass\napi.command('/selftest_loop', _h)\n")
        t0 = time.time(); g["EXT_CMDS"]["/selftest_loop"]("/selftest_loop", "/selftest_loop")
        check("a module that swallows exceptions in a loop is still stopped", time.time() - t0 < 6 and sent4 and "не сработала" in sent4[-1], sent4)
    finally:
        g["_OWN_TIMEOUT_S"] = old_to; g["tg"] = old_tg4; g["EXT_CMDS"].pop("/selftest_loop", None); g["ST"].get("own_fails", {}).pop("selftest_loop.py", None); g["ST"].get("own_off", {}).pop("selftest_loop.py", None)
    # 10d. the agent knows its name and cannot claim it saved something
    root_ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    check("charter and facts hold the name", "Lum" in open(os.path.join(root_, "CHARTER.md"), encoding="utf-8").read() and "Lum" in open(os.path.join(root_, "FACTS.md"), encoding="utf-8").read())
    check("chat knows its name and cannot save", "Lum" in g["CHAT_SYS"] and "cannot save" in g["CHAT_SYS"])
    # 11. own modules, scripts and workflows are part of the code that is hashed, checked and backed up
    cb = g["code_bundle"]()
    check("code_bundle covers own/, scripts and workflows", "own/MANIFEST.json" in cb and any(k.startswith(".github/workflows/") for k in cb), sorted(cb)[:3])
    # 12. soft weight edges, widening after a run of failures, a plain /status, own modules in API mode
    g["ST"].pop("wt", None)
    for _ in range(40): g["wt_signal"]("mod:selftest_soft", 1.0, "owner", "soft")
    it_ = g["ST"]["wt"]["items"]["mod:selftest_soft"]
    check("weights never reach the absolute limit", abs(it_["f"]) <= 0.95 and abs(it_["m"]) <= 0.95, it_)
    g["ST"].pop("wt", None); g["ST"]["fail_streak"] = 0
    g["log"]("send_failed", to="x", text="t", reason="r", uri="u"); g["log"]("send_failed", to="x", text="t", reason="r", uri="u")
    check("two failures in a row add the WIDEN line to the self-state", "WIDEN" in g["self_state"]())
    g["log"]("reply", uri="u", text="ok")
    check("a success clears the failure streak", "WIDEN" not in g["self_state"]())
    old_tg5 = g["tg"]; sent5 = []; g["tg"] = lambda t, *a, **k: sent5.append(t)
    try:
        g["EXT_CMDS"]["/status"]("/status", "/status")
        check("/status has no English service header", sent5 and "SELF-STATE (real data" not in sent5[-1] and "Проекты:" in sent5[-1], sent5)
    finally: g["tg"] = old_tg5
    mods_ = [x["file"] for x in g["own_manifest"]()["modules"]]
    # 13. self-map v0: block statistics, the brake after 6 blocked replies in a row, no weight signal for an unavailable verifier, real command list in the chat
    g["ST"].pop("smap", None); g["ST"].pop("wt", None)
    for _ in range(5): g["log"]("blocked_by_verifier", to="x", their="t", text="t", reason="verifier unavailable (fail closed)", uri="u1")
    check("a block from an unavailable verifier is not a weight signal", "style:reply" not in (g["ST"].get("wt") or {}).get("items", {}), g["ST"].get("wt"))
    check("self-state reports the block reasons", "5 blocked" in g["self_state"]() and "unavailable" in g["self_state"](), g["self_state"]())
    old_tg6 = g["tg"]; sent6 = []; g["tg"] = lambda t, *a, **k: sent6.append(t)
    try:
        check("five blocks do not brake yet", not g["sm_braking"]())
        g["log"]("blocked_by_verifier", to="x", their="t", text="t", reason="verifier unavailable (fail closed)", uri="u1")
        check("six blocks in a row brake replies and tell the owner once", g["sm_braking"]() and len(sent6) == 1, sent6)
        check("while braking, respond returns retry without work and settle keeps the tries", g["respond"]("a", "h", "hello there", "t", "uX", lambda t: ("sent", "r")) == "retry" and g["settle"]("kk", True) is False and "kk" not in g["ST"].get("tries", {}))
        g["ST"]["smap"]["brake_until"] = 0
        check("the brake ends by itself", not g["sm_braking"]())
    finally: g["tg"] = old_tg6; g["ST"].pop("smap", None); g["ST"].pop("wt", None)
    check("the chat knows the real commands", "/stop" in g["CHAT_SYS"] and "/pause" not in g["CHAT_SYS"])
    # 14. interface: buttons become commands (owner chat only), plain Russian status, daily own work with its brakes
    old_chat, old_api = g.get("TG_CHAT"), g["_mn_api"]; g["TG_CHAT"] = "123"; g["_mn_api"] = lambda m, b: None
    try:
        r_ = {"result": [{"update_id": 1, "callback_query": {"id": "x", "data": "c:/status", "from": {"id": 123}, "message": {"chat": {"id": 123}, "message_id": 5}}},
                         {"update_id": 2, "message": {"from": {"id": 123}, "chat": {"id": 123}, "text": "Состояние"}},
                         {"update_id": 3, "callback_query": {"id": "y", "data": "c:/stop", "from": {"id": 999}, "message": {"chat": {"id": 999}, "message_id": 6}}},
                         {"update_id": 4, "message": {"from": {"id": 999}, "chat": {"id": 999}, "text": "Состояние"}}]}
        g["_mn_rewrite"](r_); u_ = r_["result"]
        check("a button press from the owner's chat becomes a command", u_[0].get("message", {}).get("text") == "/status", u_[0])
        check("a bottom button label becomes a command", u_[1]["message"]["text"] == "/status", u_[1])
        check("buttons and labels from any other chat are ignored", "message" not in u_[2] and u_[3]["message"]["text"] == "Состояние", u_[2:])
    finally: g["TG_CHAT"] = old_chat; g["_mn_api"] = old_api
    old_tg7 = g["tg"]; sent7 = []; g["tg"] = lambda t, *a, **k: sent7.append(t)
    try:
        g["EXT_CMDS"]["/status"]("/status", "/status")
        check("/status is plain Russian with a verdict first", sent7 and ("Всё в порядке" in sent7[-1][:40] or "Обрати внимание" in sent7[-1][:40]) and "SELF-STATE" not in sent7[-1] and "Проекты:" in sent7[-1], sent7)
    finally: g["tg"] = old_tg7
    # 14. daily development (2026-11-24): one silent slot a day; odd days from a need, even days from the radar; asked once; failures never ping
    import datetime as _dt
    old_all, old_new, old_room, old_tg8, old_today, old_save = g["proj_all"], g["proj_new"], g["_dev_room"], g["tg"], g["today"], g["proj_save"]; made = []; sent8 = []
    g["tg"] = lambda t, *a, **k: sent8.append(t); g["proj_all"] = lambda: []; g["proj_new"] = lambda k, goal, d=None: made.append((k, goal, d)) or "p%07d" % len(made); g["_dev_room"] = lambda: True; g["proj_save"] = lambda q: None
    d0 = _dt.date(2026, 11, 24)
    odd = next(d0 + _dt.timedelta(days=i) for i in range(2) if (d0 + _dt.timedelta(days=i)).toordinal() % 2 == 1); even = odd + _dt.timedelta(days=1)
    g["ST"].pop("ap", None); g["ST"].pop("dev_seen", None); g["ST"]["needs_today"] = [{"need": "keep a list of my promises", "kind": "module", "why": "consistency"}]
    try:
        g["today"] = odd.isoformat(); g["ap_run"]()
        check("an odd day starts ONE scouting from the need, marked auto and auto_make", len(made) == 1 and made[0][0] == "scout" and made[0][2] == {"auto": True, "auto_make": True} and "promises" in made[0][1], made)
        check("the start is silent", not sent8, sent8)
        g["ap_run"](); check("development runs once a day", len(made) == 1, made)
        g["today"] = even.isoformat(); g["ap_run"]()
        check("an even day starts the radar", len(made) == 2 and made[1][0] == "radar" and made[1][2] == {"auto": True}, made)
        g["today"] = (odd + _dt.timedelta(days=2)).isoformat(); g["ap_run"]()
        check("the same need is not started twice within three weeks (the radar goes instead)", len(made) == 3 and made[2][0] == "radar", made)
        g["_dev_room"] = lambda: False; g["today"] = (odd + _dt.timedelta(days=4)).isoformat(); n0 = len(made); g["ap_run"]()
        check("no room: nothing starts, the day is not used up and nobody is pinged", len(made) == n0 and g["ST"]["ap"]["day"] != g["today"] and not sent8, (made, sent8))
        g["_dev_room"] = lambda: True; g["proj_all"] = lambda: [{"id": "pw", "kind": "make", "status": "waiting_owner", "data": {}, "trail": []}]; g["ap_run"]()
        check("a module waiting for the owner blocks a new start", len(made) == n0, made)
        g["proj_all"] = lambda: []; g["ST"]["ap"]["day"] = ""; g["ST"]["ap"]["res"] = ["fail", "rej", "fail"]; g["ap_run"]()
        check("three failures or rejections in a row switch it off and tell the owner", g["ST"]["ap"]["on"] is False and len(made) == n0 and any("выключил сам" in x for x in sent8), (made, sent8[-1:]))
        g["EXT_CMDS"]["/autoproj"]("/autoproj on", "/autoproj on"); check("/autoproj on switches it back on", g["ST"]["ap"]["on"] is True)
        # the owner is asked once: a reminder after a day, cancelled after three
        g["today"] = "2026-12-10"; q = {"id": "pq", "kind": "make", "status": "waiting_owner", "goal": "g", "trail": [], "data": {"name": "x.py", "title": "X", "auto": True, "asked_day": "2026-12-09"}}
        g["proj_all"] = lambda: [q]; sent8.clear(); g["_dev_watch"]()
        check("one reminder after a day", len(sent8) == 1 and "Напоминаю один раз" in sent8[0] and q["data"]["reminded"] is True, sent8)
        g["_dev_watch"](); check("no second reminder", len(sent8) == 1, sent8)
        q["data"]["asked_day"] = "2026-12-07"; g["_dev_watch"]()
        check("no answer in three days cancels the module", q["status"] == "failed" and any("отменён" in x for x in sent8), (q["status"], sent8))
        # radar: fetch -> pick -> launch into the scouting chain; nothing fitting ends quietly
        old_rf, old_lr = g["_radar_fetch"], g["llm_role"]; made.clear(); sent8.clear()
        g["_radar_fetch"] = lambda: [{"t": "A memory index for agents", "u": "https://x.org/a", "s": "arxiv"}]
        g["llm_role"] = lambda *a, **k: ('{"best": 1, "need": "compact memory index for a small agent", "why_ru": "нужна быстрая память"}', "x")
        rp = {"id": "pr", "data": {}}; steps = [g["radar_step"](rp) for _ in range(3)]
        check("radar goes fetch -> pick -> launch and starts an auto scouting with the source", steps == ["continue", "continue", "done"] and made and made[0][0] == "scout" and made[0][2].get("auto_make") and "memory index" in made[0][2].get("origin_idea", ""), (steps, made))
        g["llm_role"] = lambda *a, **k: ('{"best": 0, "need": "", "why_ru": ""}', "x"); rp2 = {"id": "pr2", "data": {}}; made.clear()
        st2 = [g["radar_step"](rp2) for _ in range(2)]
        check("radar with nothing fitting ends quietly", st2[-1] == "done" and rp2["data"].get("result") == "none" and not made and not sent8, (st2, rp2["data"], sent8))
        g["_radar_fetch"], g["llm_role"] = old_rf, old_lr
        # scouting started by the agent turns its best idea into a make project by itself
        sp = {"id": "ps", "goal": "tiny memory index", "data": {"auto": True, "auto_make": True, "stage": "report", "best": 1, "summary": "s", "cands": [{"full": "a/b", "url": "https://github.com/a/b", "desc": "d", "stars": 20, "lic": "MIT", "pushed": "2026-10-01", "fit": "high", "adapt": "index", "readme": "r"}]}}
        made.clear(); r_ = g["scout_step"](sp)
        check("an auto scouting starts the make project itself, silently", r_ == "done" and made and made[0][0] == "make" and made[0][2].get("auto") and "a/b" in made[0][2]["origin"] and not sent8, (r_, made, sent8))
        g["proj_new"] = lambda k, goal, d=None: None; check("no free project slot: the scouting waits instead of losing the idea", g["scout_step"](sp) == "later")
        sp2 = {"id": "ps2", "goal": "x", "data": {"auto": True, "auto_make": True, "stage": "report", "best": 0, "cands": [{"full": "c/d", "fit": "low", "url": "u", "lic": "MIT", "stars": 1, "pushed": "2026-10-01", "desc": "", "readme": ""}]}}
        check("an auto scouting without a fitting idea ends quietly with result none", g["scout_step"](sp2) == "done" and sp2["data"].get("result") == "none")
        # /make: one repair attempt; failures of auto projects are silent, the owner's own projects still report
        sent8.clear(); mp = {"id": "pm", "data": {"stage": "failed_tests", "name": "x.py", "title": "X", "auto": True, "last_fail": "e"}}
        check("an auto make failure is silent", g["make_step"](mp) == "failed" and not sent8, sent8)
        mp2 = {"id": "pm2", "data": {"stage": "failed_tests", "name": "x.py", "title": "X", "last_fail": "e"}}
        check("an owner-started make failure is still reported", g["make_step"](mp2) == "failed" and sent8, sent8)
        src_mk = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "parts", "part_06zz_make.py"), encoding="utf-8").read()
        check("make allows one attempt and one repair", 'd["try"] >= 2' in src_mk and "ONLY way to call a language model" in src_mk)
    finally: g["proj_all"], g["proj_new"], g["_dev_room"], g["tg"], g["today"], g["proj_save"] = old_all, old_new, old_room, old_tg8, old_today, old_save; g["ST"].pop("ap", None); g["ST"].pop("dev_seen", None); g["ST"].pop("dev_log", None)
    # 14b. limit balancer and low-power mode (2026-11-24)
    old_llms = list(g["LLMS"]); old_st = {k: g["ST"].get(k) for k in ("usage", "limits")}; old_cool = dict(g["COOL"])
    try:
        g["ST"]["usage"] = {"day": g["today"], "calls": {"gemini": 1000, "groq": 10}, "tokens": {}, "fails": {}}
        check("balancer moves a provider that used 70% of its day behind the others", g["_bal_order"](("gemini", "groq", "mistral")) == ("groq", "mistral", "gemini"), g["_bal_order"](("gemini", "groq", "mistral")))
        check("balancer keeps a fresh chain as it is", g["_bal_order"](("groq", "mistral")) == ("groq", "mistral"))
        g["LLMS"][:] = [("aa", "", "k", "m"), ("bb", "", "k", "m")]; g["ST"]["limits"] = {"aa.calls": 10, "bb.calls": 10}; g["COOL"].clear()
        g["ST"]["usage"] = {"day": g["today"], "calls": {"aa": 9, "bb": 9}, "tokens": {}, "fails": {}}
        check("low-power mode when every provider is above 80%", g["econ_mode"]() is True)
        g["ST"]["usage"]["calls"]["bb"] = 3; check("not in low-power mode while one provider has room", g["econ_mode"]() is False)
        g["ST"]["usage"]["calls"]["bb"] = 9; g["ST"]["limits"]["aa.calls"] = 0; g["ST"]["limits"]["bb.calls"] = 0
        check("providers switched off with limit 0 do not count (nothing to judge, no low-power mode)", g["econ_mode"]() is False)
        g["ST"]["limits"] = {"aa.calls": 10, "bb.calls": 10}; g["ST"]["usage"]["calls"]["bb"] = 9
        check("self-state says it plainly", "EXHAUSTED" in g["_ss_limits"]() and "Moltbook" in g["econ_note"]())
        # hotfix 2026-11-25: failing provider gets longer and longer pauses
        check("pause grows with failures in a row", g["_fail_pause"](5) == 0 and g["_fail_pause"](6) == 300 and g["_fail_pause"](9) == 600 and g["_fail_pause"](99) == 7200)
        g["ST"]["usage"] = {"day": g["today"], "calls": {}, "tokens": {}, "fails": {}}; g["COOL"].clear(); g["_FAIL_RUN"].clear()
        old_inner = g["_llm_before_fail"]
        def _bad(system, user, *a, **k): u_ = g["usage"](); u_["fails"]["aa"] = u_["fails"].get("aa", 0) + 3; return None, None
        def _good(system, user, *a, **k): u_ = g["usage"](); u_["calls"]["aa"] = u_["calls"].get("aa", 0) + 1; return "x", "aa"
        try:
            g["_llm_before_fail"] = _bad; g["llm"]("s", "u", order=("aa",), gap=0); check("three failures do not cool a provider yet", g["COOL"].get("aa", 0) <= time.time())
            g["llm"]("s", "u", order=("aa",), gap=0); check("six failures in a row cool it for minutes", g["COOL"].get("aa", 0) > time.time() + 200, g["COOL"])
            g["_llm_before_fail"] = _good; g["llm"]("s", "u", order=("aa",), gap=0); check("a success clears the failure run", g["_FAIL_RUN"].get("aa") == 0)
        finally: g["_llm_before_fail"] = old_inner; g["COOL"].clear(); g["_FAIL_RUN"].clear()
        g["COOL"]["aa"] = time.time() + 999; g["ST"]["usage"]["calls"] = {}
        check("a cooling provider goes behind in the balancer", g["_bal_order"](("aa", "bb")) == ("bb", "aa"), g["_bal_order"](("aa", "bb")))
        check("verification does not start with Gemini", "gemini" not in g["VERIFY_ORDER"] and g["VERIFY_ORDER"][0] == "groqq", g["VERIFY_ORDER"])
        check("stop phrase is trusted only in a short message", g["_stop_heuristic"]("please stop writing to me") and not g["_stop_heuristic"]("x " * 100 + "stop writing"))
    finally:
        g["LLMS"][:] = old_llms; g["COOL"].clear(); g["COOL"].update(old_cool)
        for k, v in old_st.items():
            if v is None: g["ST"].pop(k, None)
            else: g["ST"][k] = v
    # 14c. quiet log (2026-11-25)
    spy_ = []; old_q = g["_lg_before_q"]; g["_lg_before_q"] = lambda kind, **kw: spy_.append((kind, g["P"]("logs/actions.jsonl")))
    old_dg = dict(g["_DG"]["skips"]); g["_DG"]["skips"].clear()
    try:
        g["log"]("skip", why="selftest reason"); g["log"]("skip", why="selftest reason"); g["log"]("post", title="t")
        check("a skip is counted, reaches the chain, but is not written to the log file", g["_DG"]["skips"] == {"selftest reason": 2} and spy_[0] == ("skip", os.devnull) and spy_[-1][0] == "post" and spy_[-1][1] != os.devnull, (g["_DG"], spy_))
        spy_.clear(); g["_dg_flush"](True)
        check("one digest line carries the counts", len(spy_) == 1 and spy_[0][0] == "digest" and not g["_DG"]["skips"], spy_)
    finally: g["_lg_before_q"] = old_q; g["_DG"]["skips"].clear(); g["_DG"]["skips"].update(old_dg)
    old_tr = g["ST"].get("tries"); g["ST"]["tries"] = {str(i): 1 for i in range(900)}
    try:
        g["_quiet_tick"]()
        check("attempt counter is cut to its newest 500", len(g["ST"]["tries"]) == 500 and "899" in g["ST"]["tries"] and "0" not in g["ST"]["tries"])
    finally: g["ST"]["tries"] = old_tr if old_tr is not None else {}
    calls_ = []; w_ = g["_post_rest"](lambda: calls_.append(1) or None); g["ST"].pop("post_rest_until", None)
    w_(); w_()
    check("a failed post rests two hours without calling models again", len(calls_) == 1 and g["ST"]["post_rest_until"] > time.time() + 7000, calls_); g["ST"].pop("post_rest_until", None)
    # 14d. health pulse and quiet telegram (2026-11-25)
    old_foc = g["ST"].pop("focus_on", None); old_hl = g["ST"].get("hl"); sent_h = []; old_tgb = g["_tg_before_hl"]; g["_tg_before_hl"] = lambda t_, *a_, **k_: sent_h.append(t_)
    try:
        g["ST"]["hl"] = {"days": {}, "cur": {"day": g["today"]}, "last_act": time.time(), "alert_day": ""}
        g["tg"]("Пауза ответов и комментариев на час: 6 подряд сбоев"); g["tg"]("Режим экономии: лимиты"); g["tg"]("Важное: ждёт решения")
        check("informing notices are counted, not sent", sent_h == ["Важное: ждёт решения"] and g["ST"]["hl"]["cur"]["quiet"] == {"пауза ответов": 1, "режим экономии лимитов": 1}, (sent_h, g["ST"]["hl"]["cur"]))
        base = {"post": 4, "reply": 20, "blocked": 1, "calls": 300, "fails": 10}
        g["ST"]["hl"]["days"] = {"2026-11-%02d" % d: dict(base) for d in range(10, 17)}
        g["ST"]["hl"]["days"]["2026-11-17"] = dict(base)
        check("a normal day is green", g["hl_judge"]("2026-11-17")[0] == "green", g["hl_judge"]("2026-11-17"))
        g["ST"]["hl"]["days"]["2026-11-17"] = {"post": 0, "reply": 0, "blocked": 0, "calls": 300, "fails": 10}
        check("a day without actions after active days is red", g["hl_judge"]("2026-11-17")[0] == "red")
        g["ST"]["hl"]["days"]["2026-11-17"] = {"post": 4, "reply": 20, "blocked": 1, "calls": 100, "fails": 200}
        check("more than half failed model calls is red", g["hl_judge"]("2026-11-17")[0] == "red")
        g["ST"]["hl"]["days"]["2026-11-17"] = {"post": 4, "reply": 20, "blocked": 1, "calls": 200, "fails": 60}
        check("failures above double the usual are yellow", g["hl_judge"]("2026-11-17")[0] == "yellow", g["hl_judge"]("2026-11-17"))
        sent_h.clear(); g["ST"]["digest_day"] = ""; old_now = g["now"]
        class _N:  # morning hour
            hour = 9
        g["now"] = lambda: _N(); g["daily_digest"](); g["now"] = old_now
        check("one morning message with the state", len(sent_h) == 1 and sent_h[0].startswith("Состояние:"), sent_h)
    finally: g["ST"]["focus_on"] = old_foc; g["_tg_before_hl"] = old_tgb; g["now"] = old_now if "old_now" in dir() else g["now"]; g["ST"]["hl"] = old_hl if old_hl is not None else {"days": {}, "cur": {"day": g["today"]}}
    # 14e. hooks, janitor, load order (2026-11-26)
    ran_ = []; f1_ = lambda: ran_.append(1); f2_ = lambda: 1 / 0; f3_ = lambda: ran_.append(3)
    n0_ = len(g["TICK_HOOKS"]); old_b = g["_pt_before_hooks"]; g["_pt_before_hooks"] = lambda: None
    try:
        for f_ in (f1_, f2_, f3_): g["on_tick"](f_)
        g["proj_tick"]()
        check("tick hooks run in order and one failing hook does not stop the others", ran_ == [1, 3], ran_)
    finally:
        g["_pt_before_hooks"] = old_b
        for f_ in (f1_, f2_, f3_): g["TICK_HOOKS"].remove(f_)
    nm_ = {getattr(f_, "__name__", "") for f_ in g["TICK_HOOKS"]}
    check("named tick hooks are registered", {"_ss_tick", "_name_tick", "_mn_tick", "_ap_tick", "_econ_tick", "_quiet_tick", "_health_tick"} <= nm_, sorted(nm_))
    check("tick hooks of the real parts are registered", len(g["TICK_HOOKS"]) >= 5 and n0_ == len(g["TICK_HOOKS"]), len(g["TICK_HOOKS"]))
    ls_ = g["jan_lesson"]("2026-11-25", {"post": 4, "reply": 1, "blocked": 0, "calls": 700, "fails": 100, "pf": {"gemini": 99}, "pc": {"gemini": 270}, "why": {"stop-intent guard unavailable, will retry next cycle": 18}})
    check("the daily lesson is built from numbers and names the cause", "4 posts, 1 replies" in ls_ and "gemini" in ls_ and "stop check has no model" in ls_ and ls_.endswith("."), ls_)
    check("a quiet day gets a calm lesson", g["jan_lesson"]("d", {"post": 4, "reply": 20, "calls": 100, "fails": 2}).endswith("nothing to change."))
    old_tr2 = g["ST"].get("skipped"); g["ST"]["skipped"] = {str(i): 1 for i in range(900)}; g["ST"].pop("janitor_day", None)
    try:
        g["jan_run"](); check("the janitor cuts a growing dictionary once a day", len(g["ST"]["skipped"]) == 300 and "899" in g["ST"]["skipped"])
    finally: g["ST"]["skipped"] = old_tr2 if old_tr2 is not None else {}
    # 14f. fewer model calls per answer (2026-11-26)
    import inspect, urllib.error
    import re as _re
    check("the pinned llm() default starts with the Groq pools, Gemini after them", _re.search(r'def llm\(system, user, order=\("groq", "groqq", "openrouter", "gemini"', open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "parts", "part_01_core.py"), encoding="utf-8").read()) is not None)
    old_http, old_llms2, old_cool2, old_st2 = g["http"], list(g["LLMS"]), dict(g["COOL"]), g["ST"].get("usage"); n_http = []
    def _h503(*a_, **k_): n_http.append(1); raise urllib.error.HTTPError("u", 503, "overloaded", {}, None)
    try:
        g["LLMS"][:] = [("aa", "http://x", "k", "m"), ("bb", "http://x", "k", "m")]; g["COOL"].clear(); g["ST"]["usage"] = {"day": g["today"], "calls": {}, "tokens": {}, "fails": {}}; g["http"] = _h503
        g["_llm_before_fail"]("s", "u", order=("aa", "bb"), gap=0)
        check("an overloaded provider (503) gets one try, a pause and the next provider is asked at once", len(n_http) == 2 and g["COOL"].get("aa", 0) > time.time() + 60 and g["COOL"].get("bb", 0) > time.time() + 60, (len(n_http), g["COOL"]))
    finally: g["http"] = old_http; g["LLMS"][:] = old_llms2; g["COOL"].clear(); g["COOL"].update(old_cool2); g["ST"]["usage"] = old_st2 if old_st2 is not None else {"day": g["today"], "calls": {}, "tokens": {}, "fails": {}}
    seen_ = []; old_llm_g = g["llm"]
    def _fake(system, user, order=(), maxtok=0, temp=0, exclude=(), **k_): seen_.append((tuple(order), tuple(exclude))); return ("{\"pass\": true}", "x") if len(seen_) >= 2 else (None, None)
    try:
        g["llm"] = _fake; g["_GJ_CACHE"].clear(); old_sleep = time.sleep; time.sleep = lambda *_: None
        r_ = g["guard_json"]("sys", "text one", 100, order=("groqq", "openrouter", "groq"), exclude={"groq"})
        check("a guard check makes at most two passes: first without Gemini, then with it", r_ == {"pass": True} and len(seen_) == 2 and "gemini" in seen_[0][1] and "gemini" not in seen_[0][0] and "gemini" in seen_[1][0] and "gemini" not in seen_[1][1], seen_)
        n_ = len(seen_); r2_ = g["guard_json"]("sys", "text one", 100, order=("groqq", "openrouter", "groq"), exclude={"groq"})
        check("the same check within 20 minutes is answered from the cache", r2_ == {"pass": True} and len(seen_) == n_)
    finally: g["llm"] = old_llm_g; time.sleep = old_sleep; g["_GJ_CACHE"].clear()
    # 14g. spend by circuit (2026-11-26)
    old_hl2 = g["ST"].get("hl"); g["ST"]["hl"] = {"days": {}, "cur": {"day": g["today"]}, "last_act": time.time(), "alert_day": ""}
    old_inner2, old_pr = g["_llm_before_fail"], g["PRIO"][0]
    def _ok(system, user, *a_, **k_): u_ = g["usage"](); u_["calls"]["aa"] = u_["calls"].get("aa", 0) + 2; return "x", "aa"
    old_ll = list(g["LLMS"])
    try:
        g["LLMS"][:] = [("aa", "", "k", "m")]; g["_llm_before_fail"] = _ok; g["PRIO"][0] = 5; g["llm"]("s", "u", order=("aa",), gap=0)
        check("model calls are counted by priority (circuit)", g["ST"]["hl"]["cur"].get("pr") == {"5": 2}, g["ST"]["hl"]["cur"])
    finally: g["_llm_before_fail"] = old_inner2; g["PRIO"][0] = old_pr; g["LLMS"][:] = old_ll; g["ST"]["hl"] = old_hl2 if old_hl2 is not None else {"days": {}, "cur": {"day": g["today"]}}
    # 14h. slimmer private memory (2026-11-27)
    put_ = []; olds_ = {k: g.get(k) for k in ("MEM_TOKEN", "LIVE", "_put", "_lab_list", "mem_del")}; olds_st = {k: g["ST"].get(k) for k in ("backup_day", "backup_hash")}
    try:
        g["MEM_TOKEN"], g["LIVE"] = "t", True; g["_put"] = lambda name, txt, msg="": put_.append(name) or True; g["_lab_list"] = lambda rp: []; g["mem_del"] = lambda *a_: True
        g["ST"]["backup_day"], g["ST"]["backup_hash"] = g["today"], "old"; g["backup_sync"](force=True)
        check("a second snapshot on the same day is not made, even when forced", put_ == [], put_)
        g["ST"]["backup_day"] = "2000-01-01"; g["backup_sync"](force=True)
        check("a snapshot is made on a new day", any(x.startswith("backups/") for x in put_), put_)
    finally:
        g.update({k: v for k, v in olds_.items() if v is not None})
        for k, v in olds_st.items():
            if v is None: g["ST"].pop(k, None)
            else: g["ST"][k] = v
    check("only four snapshots are kept", g["BACKUP_KEEP"] == 4)
    g["ST"].pop("diary_key", None); g["ST"]["diary_acc"] = 0
    l1_ = g["_diary_add"](1); l2_ = g["_diary_add"](2)
    check("the diary gets one line per hour and sums the exchanges", l1_ and "1 exchange(s)" in l1_ and l2_ is None and g["ST"]["diary_acc"] == 2, (l1_, l2_, g["ST"].get("diary_acc")))
    g["ST"].pop("diary_key", None); g["ST"]["diary_acc"] = 0
    src_bk = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "parts", "part_06d_backup_identity.py"), encoding="utf-8").read()
    check("the 'code deployed' entry goes to the biography only for the first run or a failed probe", "if r or first: bio_add" in src_bk)
    # 15. owner-facing project texts: no internal English instruction, cut at a word
    g_ = g["_ru_goal"]("Build one small own module (standard library only, at most 150 lines) for this need of the agent: A daily report tool to summarize engagement metrics and content performance across platforms. Why it matters: consistency")
    check("a module goal is shown as the need only, cut at a word", g_.startswith("модуль: A daily report tool") and "Build one" not in g_ and g_.endswith("…") and not g_[:-1].endswith(" "), g_)
    check("a scouting goal loses the instruction", g["_ru_goal"]("Find open-source ideas on GitHub useful for the agent on this topic: short topic").startswith("разведка: short topic"))
    # 16. audit 2026-11-23: docstring cannot switch the closed mode off, read-only stdlib, no new legacy modules, full code length, weekly timeout, wrong sender, private DMs
    doc_ = '"""A docstring first."""\nAPI_VERSION = 1\nimport urllib.request\n'
    check("a docstring before API_VERSION still means the closed mode (and its import rules)", g["_own_is_api"](doc_) and g["own_check"]("doc_mod.py", doc_), g["own_check"]("doc_mod.py", doc_))
    check("a NEW module in the open legacy mode is not installed", g["own_install"]("selftest_leg.py", "import re\nx = re.compile('a')\n", "t", "w")[0] is False)
    check("assigning to a standard library attribute is refused", "attribute assignment" in g["own_check"]("att.py", "API_VERSION = 1\nimport json\njson.loads = 1\n"), g["own_check"]("att.py", "API_VERSION = 1\nimport json\njson.loads = 1\n"))
    check("assigning on self is allowed", g["own_check"]("att2.py", "API_VERSION = 1\nclass A:\n    def f(self):\n        self.x = 1\n") == "")
    before_ = g["json"].loads
    try: g["_own_run_api"]("selftest_frz.py", "API_VERSION = 1\nimport json\njson.loads = 1\n"); frozen_ = False
    except AttributeError: frozen_ = True
    check("a standard library module is read-only inside an own module (even if the static check were bypassed)", frozen_ and g["json"].loads is before_)
    check("a module longer than the character limit is refused", "characters" in g["own_check"]("big.py", "API_VERSION = 1\n#" + "x" * 6100))
    old_to2 = g["_OWN_TIMEOUT_S"]; g["_OWN_TIMEOUT_S"] = 1; n_wk = len(g["WEEKLY_EXTRA"])
    try:
        g["_own_run_api"]("selftest_wk.py", "API_VERSION = 1\ndef report():\n    while True:\n        pass\napi.weekly(report)\n")
        t0 = time.time(); r_wk = g["WEEKLY_EXTRA"][-1](); check("a weekly callback that never ends is stopped", time.time() - t0 < 6 and r_wk == "", time.time() - t0)
    finally:
        del g["WEEKLY_EXTRA"][n_wk:]; g["_OWN_TIMEOUT_S"] = old_to2; g["ST"].get("own_fails", {}).pop("selftest_wk.py", None); g["ST"].get("own_off", {}).pop("selftest_wk.py", None)
    old_chat2, old_api2 = g.get("TG_CHAT"), g["_mn_api"]; g["TG_CHAT"] = "123"; g["_mn_api"] = lambda m, b: None
    try:
        r2 = {"result": [{"update_id": 1, "message": {"from": {"id": 555}, "chat": {"id": 123}, "text": "/stop"}},
                         {"update_id": 2, "callback_query": {"id": "z", "data": "c:/stop", "from": {"id": 555}, "message": {"chat": {"id": 123}, "message_id": 1}}},
                         {"update_id": 3, "message": {"from": {"id": 123}, "chat": {"id": 123}, "text": "/status"}}]}
        g["_mn_rewrite"](r2)
        check("a command or a button from another person in the right chat is dropped", "message" not in r2["result"][0] and "message" not in r2["result"][1] and r2["result"][2]["message"]["text"] == "/status", r2)
    finally: g["TG_CHAT"] = old_chat2; g["_mn_api"] = old_api2
    cap_ = []; old_dm = g["_lg_before_hooks"]; g["_lg_before_hooks"] = lambda kind, **kw: cap_.append((kind, kw))
    try:
        g["log"]("reach", to="someone.bsky.social", channel="dm", text="a private words", uri="u")
        check("a direct message is not written to the public log", cap_ and "private words" not in str(cap_) and "someone" not in str(cap_), cap_)
    finally: g["_lg_before_hooks"] = old_dm
    # 14i: log hooks - a failing hook does not break log(); pre-hooks run before the line, post-hooks after it, in order
    seq_ = []; old_l = g["_lg_before_hooks"]; g["_lg_before_hooks"] = lambda kind, **kw: seq_.append(("core", kw.get("x")))
    def _h_pre(kind, kw): seq_.append("pre"); kw["x"] = "scrubbed"
    def _h_bad(kind, kw): raise RuntimeError("boom")
    def _h_post(kind, kw): seq_.append("post")
    g["LOG_PRE"].append(_h_pre); g["LOG_POST"].extend([_h_bad, _h_post])
    try:
        g["log"]("zz_test", x="raw")
        check("log hooks: pre scrubs, core writes, failing hook is skipped, post runs", seq_ == ["pre", ("core", "scrubbed"), "post"], seq_)
    finally:
        g["_lg_before_hooks"] = old_l; g["LOG_PRE"].remove(_h_pre); g["LOG_POST"].remove(_h_bad); g["LOG_POST"].remove(_h_post)
    # 14j: context hooks - parts are appended in order, a front part comes first, a failing part is skipped
    old_ac = g["_ac_before_hooks"]; g["_ac_before_hooks"] = lambda: "BASE"
    def _c1(): return "|A"
    def _c2(): raise RuntimeError("boom")
    def _c3(): return "|B"
    def _cf(): return "FRONT|"
    n_a, n_f = len(g["CTX_AFTER"]), len(g["CTX_FRONT"]); sv_a, sv_f = list(g["CTX_AFTER"]), list(g["CTX_FRONT"])
    g["CTX_AFTER"][:] = [_c1, _c2, _c3]; g["CTX_FRONT"][:] = [_cf]
    try: r_ = g["agent_context"]()
    finally:
        g["_ac_before_hooks"] = old_ac; g["CTX_AFTER"][:] = sv_a; g["CTX_FRONT"][:] = sv_f
    check("context hooks: front first, base, then parts in order, failing part skipped", r_ == "FRONT|BASE|A|B", r_[-60:])
    check("context hooks: the real parts are registered", n_a >= 3 and n_f >= 1 and len(g["CTX_AFTER"]) == n_a, (n_a, n_f))
    return bad
