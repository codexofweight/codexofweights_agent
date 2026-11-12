# ---- private lab: tools_pending, modules, experiments and raw reports live ONLY in the private repo (the public repo never sees them) ----
LAB_MAP = {"tools_pending": "lab/tools_pending", "tools": "lab/tools_active", "modules_pending": "lab/modules_pending", "modules_approved": "lab/modules_approved", "reports": "lab/reports", "experiments": "lab/experiments"}
LAB_OK = [False]      # deletions in the private lab are allowed only after a complete, successful restore in this run
DEL_OK = ("lab/", "backups/")     # memory is inviolable: the agent may remove files only in the lab and among old backups; people, facts, diary, biography and research are never deleted
def mem_del(path, sha):
    if not path.startswith(DEL_OK) or ".." in path: print("refused to delete outside the lab/backups:", path, flush=True); return False
    try: _mem_api(path, {"message": "removed", "sha": sha}, "DELETE"); return True
    except Exception as ex: print("delete failed:", type(ex).__name__, flush=True); return False
def _put(rel, txt, msg="sync"):
    t, sha = mem_get(rel)
    return True if (t == txt and sha) else mem_put(rel, txt, sha, msg)
def _lab_list(rp):
    try:
        r = _mem_api(rp); return r if isinstance(r, list) else []
    except urllib.error.HTTPError as ex: return [] if ex.code == 404 else None
    except Exception: return None
def lab_restore():
    """A fresh runner has empty folders: pull what the private lab holds (only files that are missing locally)."""
    if not MEM_TOKEN: return
    ok = True
    for loc, rp in LAB_MAP.items():
        os.makedirs(P(loc), exist_ok=True); items = _lab_list(rp)
        if items is None: ok = False; continue
        for it in items:
            if it.get("type") != "file" or it["name"] == "README.md" or os.path.exists(P(loc + "/" + it["name"])): continue
            t, _ = mem_get(rp + "/" + it["name"])
            if t: open(P(loc + "/" + it["name"]), "w", encoding="utf-8").write(t)
            else: ok = False
    LAB_OK[0] = ok; print("lab restore:", "ok" if ok else "incomplete (no deletions this run)", flush=True)
def lab_sync():
    """Mirror local lab folders into the private repo; a file that left a folder is removed there, and a rejected tool/module is archived in lab/rejected/."""
    if not MEM_TOKEN or not LIVE: return
    sent = ST.setdefault("lab_sent", {})
    if not sent.get("_init2"):
        idx = "# Lab\n\nPrivate workshop of the agent. Path: lab -> report -> owner says yes -> agent repo. Nothing is promoted without consent.\n\n" + "".join("- `%s/` - %s\n" % kv for kv in (("tools_pending", "tools waiting for the owner's decision"), ("tools_active", "approved tools"), ("modules_pending", "module designs waiting for a decision"), ("modules_approved", "accepted designs (not connected to the core)"), ("rejected", "archive of rejected tools and modules"), ("reports", "raw reports"), ("experiments", "experiments and null results")))
        if _put("lab/README.md", idx, "lab index"): sent["_init2"] = 1
    for loc, rp in LAB_MAP.items():
        d = P(loc)
        if not os.path.isdir(d): continue
        local = [f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))]
        for f in local:
            try: txt = open(os.path.join(d, f), encoding="utf-8").read()
            except Exception: continue
            h = hashlib.sha1(txt.encode()).hexdigest(); rel = rp + "/" + f
            if sent.get(rel) != h and _put(rel, txt, "lab sync"): sent[rel] = h
        if not LAB_OK[0]: continue
        for it in (_lab_list(rp) or []):
            if it.get("type") != "file" or it["name"] == "README.md" or it["name"] in local: continue
            stem = it["name"].rsplit(".", 1)[0]
            approved = loc == "tools_pending" and os.path.exists(P("tools/%s.py" % stem)) or loc == "modules_pending" and os.path.exists(P("modules_approved/%s.md" % stem))
            if loc in ("tools_pending", "modules_pending") and not approved:
                t, _ = mem_get(rp + "/" + it["name"])
                if t: _put("lab/rejected/%s__%s" % (today, it["name"]), t, "archive rejected")
            if mem_del(rp + "/" + it["name"], it["sha"]): sent.pop(rp + "/" + it["name"], None)
lab_restore()
try: sandbox_ready()
except Exception as _ex: SANDBOX_OK[0] = False; print("sandbox check crashed:", type(_ex).__name__, flush=True)

# ---- state: the public file keeps counters and hashed identities only; pending drafts and owner requests stay in the private repo ----
PRIVATE_KEYS = ("asks", "ask_id", "tool_request")
ST["muted"] = [x if str(x).startswith("h:") else _h(x) for x in ST.get("muted", [])]; ST["contacted"] = [x if str(x).startswith("h:") else _h(x) for x in ST.get("contacted", [])]
def state_restore_private():
    if not MEM_TOKEN or ST.get("asks"): return
    t, _ = mem_get("state/private.json")
    try: d = json.loads(t)
    except Exception: return
    for k in PRIVATE_KEYS:
        if k in d: ST[k] = d[k]
def save_state():
    """Public state/state.json without private keys; the private part goes to the memory repo (only when it changed)."""
    pub = {k: v for k, v in ST.items() if k not in PRIVATE_KEYS}
    json.dump(pub, open(P("state/state.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if MEM_TOKEN and LIVE:
        priv = json.dumps({k: ST.get(k) for k in PRIVATE_KEYS if k in ST}, ensure_ascii=False, indent=1); h = hashlib.sha1(priv.encode()).hexdigest()
        if ST.get("priv_h") != h and _put("state/private.json", priv, "private state"): ST["priv_h"] = h
state_restore_private()
