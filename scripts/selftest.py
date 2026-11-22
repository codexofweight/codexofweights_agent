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
    check("code_bundle covers own/, scripts and workflows", "own/MANIFEST.json" in cb and any(k.startswith("own/") and k.endswith(".py") for k in cb) and any(k.startswith(".github/workflows/") for k in cb), sorted(cb)[:3])
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
    check("read_url.py and words_counter.py are API-mode modules", all(g["_own_is_api"](open(os.path.join(root_, "own", f), encoding="utf-8").read()) for f in ("read_url.py", "words_counter.py") if f in mods_))
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
        r_ = {"result": [{"update_id": 1, "callback_query": {"id": "x", "data": "c:/status", "message": {"chat": {"id": 123}, "message_id": 5}}},
                         {"update_id": 2, "message": {"chat": {"id": 123}, "text": "Состояние"}},
                         {"update_id": 3, "callback_query": {"id": "y", "data": "c:/stop", "message": {"chat": {"id": 999}, "message_id": 6}}},
                         {"update_id": 4, "message": {"chat": {"id": 999}, "text": "Состояние"}}]}
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
    old_all, old_new, old_room = g["proj_all"], g["proj_new"], g["_ap_room"]; made = []; sent8 = []; old_tg8 = g["tg"]
    g["tg"] = lambda t, *a, **k: sent8.append(t); g["proj_all"] = lambda: []; g["proj_new"] = lambda k, goal, d=None: made.append((k, d)) or "p%07d" % len(made); g["_ap_room"] = lambda: (True, ("x", 1, 10))
    g["ST"].pop("ap", None); g["ST"]["needs_today"] = [{"need": "keep a list of my promises", "kind": "module", "why": "consistency"}]; g["ST"]["plan"] = {"focus": "The underlying logic of everyday household chores"}
    try:
        g["ap_run"]()
        check("daily work starts one module and one scouting, both marked auto", [m[0] for m in made] == ["make", "scout"] and all(m[1] == {"auto": True} for m in made), made)
        g["ap_run"]()
        check("daily work runs once a day", len(made) == 2, made)
        g["ST"]["ap"]["day"] = ""; g["ST"]["ap"]["res"] = ["fail", "rej", "fail"]; g["ap_run"]()
        check("three failures or rejections in a row switch it off and tell the owner", g["ST"]["ap"]["on"] is False and len(made) == 2 and any("выключил сам" in x for x in sent8), (made, sent8[-1:]))
        g["EXT_CMDS"]["/autoproj"]("/autoproj on", "/autoproj on")
        check("/autoproj on switches it back on", g["ST"]["ap"]["on"] is True)
        g["ST"]["ap"]["day"] = ""; g["_ap_room"] = lambda: (False, ("openrouter", 38, 40)); n0 = len(made); g["ap_run"]()
        check("a day with every model more than 60% used is skipped", len(made) == n0 and any("пропускаю" in x for x in sent8), sent8[-1:])
    finally: g["proj_all"], g["proj_new"], g["_ap_room"], g["tg"] = old_all, old_new, old_room, old_tg8; g["ST"].pop("ap", None)
    return bad
