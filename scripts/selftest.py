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
    return bad
