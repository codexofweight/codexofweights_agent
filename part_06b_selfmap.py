# ---- self map: an up-to-date description of the agent's own components, abilities and limits (names and numbers only; no code, no secrets) ----
import glob
def self_map():
    L = ["COMPONENTS (files, rebuilt from the code on every start):"]
    for f in sorted(glob.glob(os.path.join(ROOT, "part_*.py"))):
        try:
            src = open(f, encoding="utf-8").read(); first = src.split("\n", 1)[0].lstrip("#-\" ").rstrip("-\" "); n = sum(1 for x in ast.parse(src).body if isinstance(x, ast.FunctionDef))
        except Exception: first, n = "unreadable", 0
        L.append("- %s: %s (%d functions)" % (os.path.basename(f)[:-3], first[:110], n))
    act = ", ".join("%s(%s)" % (t["name"], t["hook"]) for t in ACTIVE_TOOLS) or "none"
    L += ["ABILITIES: platforms: %s; live mode: %s; memory repo: %s; models: %s" % (", ".join(a.name for a in ADAPTERS), LIVE, "connected" if MEM_TOKEN else "off", ", ".join(x[0] for x in LLMS if x[2])),
          "Active tools: %s; sandbox: %s; first contacts: mode %s" % (act, {True: "verified", False: "FAILED (tools disabled)", None: "not tested yet"}[SANDBOX_OK[0]], ST.get("reach_mode", "approve")),
          "LIMITS: posts/day %d, replies/day %d, first contacts/day %d; model quotas today:\n%s" % (MAX_POSTS, MAX_REPLIES, REACH_MAX_DAY, limits_report()),
          "CANNOT (by design): edit the core files, the Protocols or the charter; read secrets or raw code of other files; run a tool or module the owner has not approved; publish without the checks; contact someone who asked to stop; register on platforms by itself."]
    return "\n".join(L)
def selfmap_sync():
    if not (MEM_TOKEN and LIVE): return
    txt = "# Self map (auto-generated %s)\n\n%s\n" % (today, self_map()); h = hashlib.sha1(txt.encode()).hexdigest()
    if ST.get("selfmap_h") != h and _put("memory/self_map.md", txt, "self map"): ST["selfmap_h"] = h
