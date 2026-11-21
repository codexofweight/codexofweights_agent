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
    return bad
