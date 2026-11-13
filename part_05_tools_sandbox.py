# ---- sandbox and self-made tools: plugins, never edits to the core; owner approves every tool in Telegram ----
import ast, subprocess, resource, shlex
os.makedirs(P("tools"), exist_ok=True); os.makedirs(P("tools_pending"), exist_ok=True)
ACTIVE_TOOLS = []
TOOL_IMPORTS = {"re", "json", "math", "statistics", "collections", "itertools", "functools", "datetime", "string", "textwrap", "difflib", "hashlib", "base64", "unicodedata", "heapq", "bisect", "random", "typing", "dataclasses", "decimal", "fractions", "html"}
TOOL_BAD_NAMES = {"eval", "exec", "compile", "open", "__import__", "input", "globals", "locals", "vars", "getattr", "setattr", "delattr", "breakpoint", "exit", "quit", "memoryview", "type", "object", "super"}
TOOL_HOOKS = {
    "daily": ({"day": "2026-01-01", "counts": {"post": 2, "reply": 5, "blocked_by_verifier": 1}, "samples": "example post | example reply"}, lambda r: isinstance(r.get("report"), str)),
    "text_check": ({"kind": "reply", "text": "Plain example reply.", "other": "Example message."}, lambda r: isinstance(r.get("block"), bool)),
    "fetch": ({"phase": "plan", "day": "2026-01-01"}, lambda r: isinstance(r.get("urls"), list)),
    "context": ({"kind": "reply", "text": "Do you ever lie?"}, lambda r: isinstance(r.get("hint"), str)),
    "discover_rank": ({"items": [{"i": 0, "text": "AI honesty thread", "handle": "a"}, {"i": 1, "text": "lunch", "handle": "b"}]}, lambda r: isinstance(r.get("scores"), dict)),
    "research_rank": ({"items": [{"i": 0, "title": "Honesty of chat models", "text": "We test sycophancy.", "src": "arXiv"}, {"i": 1, "title": "Cooking tips", "text": "", "src": "x"}]}, lambda r: isinstance(r.get("scores"), dict)),
}
HOOK_HELP = ("hooks: daily(payload {day, counts{kind:n}, samples} -> {report: str, plain text for the owner, max 1500 chars}); "
             "text_check(payload {kind, text, other} -> {block: bool, reason: str}; can only BLOCK a text before publishing, never approve or edit); "
             "research_rank(payload {items:[{i,title,text,src}]} -> {scores:{\"<i>\": float 0..1}} higher = more relevant to AI honesty, safety, coexistence); "
             "fetch(phase 'plan' payload {day} -> {urls:[up to 5 https urls on your declared domains]}; then phase 'parse' payload {pages:{url:text}} -> {notes:[{text,url,quote}]} where quote is an exact sentence from the page as evidence; the core does the downloading; also give \"domains\":[...] in your answer); "
             "context(payload {kind:'reply', text} -> {hint: str max 300 chars, a helpful hint for the model before it answers; hints are data and still pass all safety checks}); "
             "discover_rank(payload {items:[{i,text,handle}]} -> {scores:{\"<i>\": float 0..1}} which public posts are worth joining).")
def static_check(code):
    bad = []
    try: tree = ast.parse(code)
    except SyntaxError as ex: return ["syntax error: %s" % ex]
    if len(code) > 12000: bad.append("too long")
    has_run = False
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            bad += ["import %s not allowed" % a.name for a in n.names if a.name.split(".")[0] not in TOOL_IMPORTS]
        elif isinstance(n, ast.ImportFrom):
            if (n.module or "").split(".")[0] not in TOOL_IMPORTS or n.level: bad.append("from %s import not allowed" % n.module)
        elif isinstance(n, ast.Name) and n.id in TOOL_BAD_NAMES: bad.append("name %s not allowed" % n.id)
        elif isinstance(n, ast.Attribute) and n.attr.startswith("_"): bad.append("attribute %s not allowed" % n.attr)
        elif isinstance(n, (ast.Global, ast.Nonlocal, ast.AsyncFunctionDef, ast.Await)): bad.append("construct not allowed")
        elif isinstance(n, ast.FunctionDef) and n.name == "run": has_run = True
    if not has_run: bad.append("no run(payload) function")
    return sorted(set(bad))[:8]
_RUNNER = ("import sys, json, resource\n"
           "resource.setrlimit(resource.RLIMIT_CPU, (8, 8)); resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)\n"
           "resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0)); resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16)); resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))\n"
           "d = json.load(sys.stdin); ns = {'__name__': 'tool'}\n"
           "exec(compile(d['code'], 'tool', 'exec'), ns)\n"
           "sys.stdout.write(json.dumps(ns['run'](d['payload']))[:20000])\n")
# Isolation (fail closed): root-owned namespaces for network, processes and mounts; /home /root /tmp /var/tmp are replaced by empty tmpfs
# (the repository, state and every secret file live there); the code runs as the unprivileged user 'nobody' with an empty environment, no new privileges
# and resource limits. The tool code travels through stdin, so no file of ours is exposed. If any of this is unavailable, tools do NOT run.
SANDBOX_OK = [None]
def _sandbox_cmd():
    inner = ("mount -t tmpfs t /home && mount -t tmpfs t /root && mount -t tmpfs t /tmp && mount -t tmpfs t /var/tmp && "
             "exec env -i PATH=/usr/bin:/bin setpriv --reuid=65534 --regid=65534 --clear-groups --no-new-privs %s -I -c %s" % (shlex.quote(sys.executable), shlex.quote(_RUNNER)))
    return ["sudo", "-n", "unshare", "--net", "--pid", "--ipc", "--uts", "--mount", "--fork", "--mount-proc", "sh", "-c", inner]
def _run_code(code, payload, timeout=10):
    if SANDBOX_OK[0] is False: return False, "sandbox unavailable (tools are disabled)"
    try: r = subprocess.run(_sandbox_cmd(), input=json.dumps({"code": code, "payload": payload}), capture_output=True, text=True, timeout=timeout, env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"})
    except Exception as ex: return False, type(ex).__name__
    if r.returncode != 0: return False, (r.stderr or "failed")[-200:]
    try: return True, json.loads(r.stdout)
    except Exception: return False, "bad output"
_PROBE = ("def run(p):\n import os, socket, json\n out = {'uid': os.getuid(), 'env': sorted(os.environ)}\n"
          " try:\n  s = socket.create_connection(('1.1.1.1', 53), 2); out['net'] = True\n except Exception: out['net'] = False\n"
          " for k, d in (('home', '/home'), ('root', '/root'), ('tmp', '/tmp')):\n  try: out[k] = len(os.listdir(d))\n  except Exception: out[k] = 0\n"
          " out['procs'] = len([x for x in os.listdir('/proc') if x.isdigit()])\n return out\n")
def sandbox_ready():
    """Self-test at start: the sandbox must really cut the network, hide our files and drop privileges; otherwise tools stay off."""
    if SANDBOX_OK[0] is not None: return SANDBOX_OK[0]
    SANDBOX_OK[0] = None; ok, r = _run_code(_PROBE, {}, 20)
    good = bool(ok and isinstance(r, dict) and r.get("uid") == 65534 and set(r.get("env") or ["?"]) <= {"PATH", "LC_CTYPE", "LANG"} and r.get("net") is False and r.get("home") == 0 and r.get("root") == 0 and r.get("tmp") == 0 and r.get("procs", 99) <= 3)
    SANDBOX_OK[0] = good; print("sandbox self-test:", "OK" if good else "FAILED -> tools disabled", str(r)[:200], flush=True)
    return good
def run_tool(path, payload, timeout=10):
    """Runs a tool inside the isolated sandbox only; returns (ok, result_or_error). No fallback to an unisolated run."""
    if not sandbox_ready(): return False, "sandbox unavailable (tools are disabled)"
    try: code = open(path, encoding="utf-8").read()
    except Exception as ex: return False, type(ex).__name__
    return _run_code(code, payload, timeout)
def test_tool(path, hook):
    sample, valid = TOOL_HOOKS[hook]; notes = []
    for label, pl in (("sample", sample), ("empty", {})):
        ok, res = run_tool(path, pl)
        if not ok: notes.append("%s input: %s" % (label, str(res)[:100]))
        elif label == "sample" and not (isinstance(res, dict) and valid(res)): notes.append("wrong output shape")
    if hook == "fetch":
        ok, res = run_tool(path, {"phase": "parse", "pages": {"https://example.org/": "Example page text."}})
        if not (ok and isinstance(res, dict) and isinstance(res.get("notes"), list)): notes.append("parse phase failed")
    return notes
def sha(path): return hashlib.sha256(open(path, "rb").read()).hexdigest()
def load_tools():
    """Approved tools only; a tool whose file no longer matches the hash recorded at approval is ignored and reported."""
    if not sandbox_ready(): return []
    out = []
    for f in sorted(os.listdir(P("tools"))):
        if not f.endswith(".json"): continue
        try:
            m = json.load(open(P("tools/" + f), encoding="utf-8")); py = P("tools/%s.py" % m["name"])
            if sha(py) != m["sha256"]: print("tool hash mismatch:", m["name"]); EV.append(("send_failed", {"text": "Tool %s changed after approval and is disabled." % m["name"]})); continue
            out.append(dict(m, path=py))
        except Exception as ex: print("tool load failed:", f, type(ex).__name__)
    return out
def tools_for(hook): return [t for t in ACTIVE_TOOLS if t["hook"] == hook]
def tool_blocks(kind, text, other):
    for t in tools_for("text_check"):
        ok, res = run_tool(t["path"], {"kind": kind, "text": text, "other": other[:600]})
        if ok and isinstance(res, dict) and res.get("block") is True: return "tool %s: %s" % (t["name"], str(res.get("reason", ""))[:100])
def rank_with_tools(cands):
    ts = tools_for("research_rank")
    if not ts: return cands
    sc = {i: 0.0 for i in range(len(cands))}
    for t in ts:
        ok, res = run_tool(t["path"], {"items": [{"i": i, "title": c["title"], "text": c["text"][:300], "src": c["src"]} for i, c in enumerate(cands)]})
        if ok and isinstance(res, dict) and isinstance(res.get("scores"), dict):
            for k, v in res["scores"].items():
                try: sc[int(k)] += float(v)
                except Exception: pass
    return [cands[i] for i in sorted(sc, key=lambda i: -sc[i])]
def run_daily_tools(payload):
    for t in tools_for("daily"):
        ok, res = run_tool(t["path"], payload)
        if ok and isinstance(res, dict) and isinstance(res.get("report"), str) and res["report"].strip():
            rep_ = res["report"].strip()[:1500]; EV.append(("research", {"text": "Tool %s:\n%s" % (t["name"], rep_)}))
            if MEM_TOKEN and LIVE:
                tt, sh = mem_get("tools/%s/%s.md" % (t["name"], today)); mem_put("tools/%s/%s.md" % (t["name"], today), tt + rep_ + "\n", sh, "tool report")
def create_tool():
    """At most once a day, or when the owner sends /tool <idea>: the agent writes a tool, it must pass the static check, run in the sandbox and be reviewed by a second model; then it waits for /approve."""
    if not sandbox_ready():       # no isolation = no running of generated code; reading the web, research and module designs go on
        if ST.get("sandbox_alert") != today: ST["sandbox_alert"] = today; tg("Песочница недоступна: запуск кода инструментов остановлен. Чтение сети, исследование и проекты модулей в лаборатории продолжаются.")
        return
    req = ST.pop("tool_request", None)
    if not req and TOOL_COOLDOWN_ACTIVE(): return      # quality over quantity: at most one self-made tool idea per week
    if not req and (len(os.listdir(P("tools_pending"))) >= cfg("tool_pending_max") or len([f for f in os.listdir(P("tools")) if f.endswith(".json")]) >= 12): return
    ST["tool_try_day"] = today
    own = [n for n in ST.get("needs_today", []) if n["kind"] == "tool"]
    if not req and not own: return                     # no documented need -> no tool (no generic "something useful" ideas)
    idea = req or ((own[0]["need"] + " (why: " + own[0]["why"] + ")") if own else "a useful tool for your own work; yesterday's note: %s; blocked texts or failures are good hints" % ST.get("last_reflection", "none"))
    out, _ = llm("You write small, pure Python 3 tools for the plugin system of a small honest AI account. Interface: define def run(payload: dict) -> dict. Allowed imports ONLY: %s. No files, network, processes, eval/exec, open, getattr, underscore attributes. Deterministic, between 40 and 250 lines, must not crash on an empty dict. Write ONLY a substantial, genuinely useful tool with real logic and its own edge-case handling; never a trivial helper. %s Answer JSON only: {\"name\":\"snake_case_max_30\",\"hook\":\"daily|text_check|research_rank|fetch|context|discover_rank\",\"description\":\"1-2 plain English sentences\",\"code\":\"...\"}" % (", ".join(sorted(TOOL_IMPORTS)), HOOK_HELP),
                 "Idea for the tool: " + idea, maxtok=3000, temp=0.4)
    try: d = json.loads(re.search(r"\{.*\}", out or "", re.S).group(0)); name, hook, code, desc = d["name"], d["hook"], d["code"], str(d.get("description", ""))[:300]; domains = [x for x in (d.get("domains") or []) if isinstance(x, str) and re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", x)][:5]
    except Exception: log("tool_rejected", why="no valid tool from model"); return
    if isinstance(code, str) and len(code.strip().splitlines()) < cfg("tool_min_lines") and not req: log("tool_rejected", why="too small to be worth a tool"); return
    if was_rejected(name, desc): log("tool_rejected", why="the owner already rejected this idea"); return
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,29}", name or "") or hook not in TOOL_HOOKS or not isinstance(code, str): log("tool_rejected", why="bad name or hook"); return
    if os.path.exists(P("tools/%s.py" % name)) or os.path.exists(P("tools_pending/%s.py" % name)): log("tool_rejected", why="name exists"); return
    bad = static_check(code)
    if bad: log("tool_rejected", name=name, why="static check: " + "; ".join(bad)); return
    py = P("tools_pending/%s.py" % name); open(py, "w", encoding="utf-8").write(code)
    notes = test_tool(py, hook)
    if notes: os.remove(py); log("tool_rejected", name=name, why="tests: " + "; ".join(notes)); return
    rev, _ = llm("You are a strict code reviewer for a security-minded owner who does not read code. Review this Python tool for a plugin system (it runs sandboxed, no network/files). JSON only: {\"risk\":\"low|medium|high\",\"summary_ru\":\"2-3 simple sentences in Russian: what it does\",\"concerns_ru\":\"risks in Russian, or 'нет'\"}", "Declared purpose: %s\nHook: %s\nCode:\n%s" % (desc, hook, code[:6000]), order=("groq", "gemini"), maxtok=500, temp=0)
    try: rv = json.loads(re.search(r"\{.*\}", rev or "", re.S).group(0))
    except Exception: os.remove(py); log("tool_rejected", name=name, why="review unavailable"); return
    if rv.get("risk") == "high": os.remove(py); log("tool_rejected", name=name, why="reviewer: high risk"); return
    json.dump({"name": name, "hook": hook, "description": desc, "sha256": sha(py), "domains": domains, "review": rv, "created": today}, open(P("tools_pending/%s.json" % name), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("tool_proposed", name=name, hook=hook); next_ask("tool", name=name)
    tg("New tool proposal: %s (hook: %s%s)\n%s\n\nCheck (second model): risk %s. %s\nRisks: %s\nSandbox tests: passed.\nCode: https://github.com/codexofweight/codexofweights_agent/blob/main/tools_pending/%s.py (visible after this run ends)\n\nReply «да» to approve or «нет» to reject (or /approve %s, /reject %s)" % (name, hook, (", sites it may read: " + ", ".join(domains)) if domains else "", desc, rv.get("risk"), rv.get("summary_ru", ""), rv.get("concerns_ru", ""), name, name, name))
def tool_command(c, raw):
    """Owner commands (called only for the owner's chat): /tool <idea>, /tools, /approve n, /reject n, /revoke n."""
    arg = c.split(" ", 1)[1].strip() if " " in c else ""
    if c.startswith("/tool "): ST["tool_request"] = raw.split(" ", 1)[1].strip()[:400]; tg("Tool request accepted; the agent will write it in the next round.")
    elif c == "/tools":
        tg("Active: %s\nPending: %s" % (", ".join(t["name"] for t in ACTIVE_TOOLS) or "none", ", ".join(f[:-5] for f in os.listdir(P("tools_pending")) if f.endswith(".json")) or "none"))
    elif c.startswith("/reject ") or c.startswith("/revoke "):
        d = "tools_pending" if c.startswith("/reject") else "tools"
        try: os.remove(P("modules_pending/%s.md" % re.sub(r"[^a-z0-9_]", "", arg)))
        except Exception: pass
        for ext in (".py", ".json"):
            try: os.remove(P("%s/%s%s" % (d, re.sub(r"[^a-z0-9_]", "", arg), ext)))
            except Exception: pass
        tg("Removed: %s" % arg)
    elif c.startswith("/approve "):
        n = re.sub(r"[^a-z0-9_]", "", arg); pj, pp = P("tools_pending/%s.json" % n), P("tools_pending/%s.py" % n)
        try:
            m = json.load(open(pj, encoding="utf-8"))
            if sha(pp) != m["sha256"]: tg("Refused: the file changed after the review."); return
            bad = static_check(open(pp, encoding="utf-8").read()) or test_tool(pp, m["hook"])
            if bad: tg("Refused: re-check failed: %s" % "; ".join(bad)); return
            bio_add("extension", "Owner approved tool %s" % n, "owner decision in Telegram", 1.0); os.replace(pp, P("tools/%s.py" % n)); os.replace(pj, P("tools/%s.json" % n)); tg("Approved and active from the next round: %s" % n)
        except Exception as ex: tg("Cannot approve %s: %s" % (n, type(ex).__name__))
# ---- needs analysis, field hooks (fetch/context/discover_rank) and architecture module proposals ----
for _d in ("modules_pending", "modules_approved"): os.makedirs(P(_d), exist_ok=True)
def add_knowledge(items):
    """items: [{text,url,quote}] -> memory facts (source web:<url>, confidence 0.5, with the quote as evidence)."""
    if not (MEM_TOKEN and LIVE and items): return
    F, E_ = facts(); vecs = embed([i["text"] for i in items])
    for n_, i in enumerate(items):
        it = {"id": "w%d%d" % (int(time.time()), n_), "type": "knowledge", "text": i["text"], "source": "web:" + i["url"], "conf": 0.5, "quote": i.get("quote", ""), "date": today, "people": [], "links": [], "n": 1}
        if vecs: E_[it["id"]] = vecs[n_]
        F.append(it)
    if mem_put("memory/facts.json", json.dumps(F, ensure_ascii=False, separators=(",", ":")), _MEM["sha"], "facts") and mem_put("memory/emb.json", json.dumps(E_, separators=(",", ":")), _MEM["esha"], "embeddings"): _MEM.clear()
    else: log("memory_failed", why="web notes not saved")
def host_ok(url, domains):
    try: h = urllib.parse.urlparse(url); return h.scheme == "https" and any(h.hostname == d or (h.hostname or "").endswith("." + d) for d in domains)
    except Exception: return False
def run_fetch_tools():
    """Owner-approved domains only: the core downloads, the tool (sandboxed, no network) parses; every note keeps its URL and a quote."""
    for t in tools_for("fetch"):
        ok, res = run_tool(t["path"], {"phase": "plan", "day": today}); doms = t.get("domains", [])
        if not (ok and isinstance(res, dict) and isinstance(res.get("urls"), list)): continue
        pages = {}
        for u in [x for x in res["urls"] if isinstance(x, str) and host_ok(x, doms)][:5]:
            try: pages[u] = plain(web_get(u, 400000).decode("utf-8", "ignore"))[:20000]
            except Exception as ex: print("fetch failed:", type(ex).__name__)
            time.sleep(2)
        if not pages: continue
        ok, res = run_tool(t["path"], {"phase": "parse", "pages": pages})
        notes = [{"text": str(n.get("text", ""))[:200], "url": n.get("url"), "quote": str(n.get("quote", ""))[:200]} for n in (res.get("notes") if ok and isinstance(res, dict) and isinstance(res.get("notes"), list) else [])[:5] if isinstance(n, dict) and n.get("url") in pages and n.get("text")]
        if notes: add_knowledge(notes); EV.append(("research", {"text": "Tool %s read %d page(s), saved %d note(s)." % (t["name"], len(pages), len(notes))})); log("tool_fetch", name=t["name"], pages=len(pages), notes=len(notes))
def tool_hints(kind, text):
    hs = []
    for t in tools_for("context")[:3]:
        ok, res = run_tool(t["path"], {"kind": kind, "text": text[:600]})
        if ok and isinstance(res, dict) and isinstance(res.get("hint"), str) and res["hint"].strip(): hs.append("%s: %s" % (t["name"], res["hint"].strip()[:300]))
    return "\n".join(hs)
def rank_discover(ms):
    ts = tools_for("discover_rank")
    if not ts or len(ms) < 2: return ms
    sc = {i: 0.0 for i in range(len(ms))}
    for t in ts:
        ok, res = run_tool(t["path"], {"items": [{"i": i, "text": m["text"][:300], "handle": m["handle"]} for i, m in enumerate(ms)]})
        if ok and isinstance(res, dict) and isinstance(res.get("scores"), dict):
            for k, v in res["scores"].items():
                try: sc[int(k)] += float(v)
                except Exception: pass
    return [ms[i] for i in sorted(sc, key=lambda i: -sc[i])]
def assess_needs():
    """Once a day the agent looks at its own work and says what it lacks: sandbox tools (kind 'tool') or architecture extensions (kind 'module')."""
    if ST.get("needs_day") == today: return
    ST["needs_day"] = today
    out, _ = llm("You are the planner of a small honest AI account (platforms: %s). Look at your own recent work and name up to 3 things you lack to work better: a small sandbox TOOL (kinds of hooks: %s) or a bigger architecture MODULE (e.g. adapter for a new platform, new memory layer, new safety check). Only real needs, no wishlist. JSON only: [{\"need\":\"one sentence\",\"kind\":\"tool|module\",\"why\":\"one sentence\"}]. Empty list is fine." % (", ".join(a.name for a in ADAPTERS), HOOK_HELP[:400]),
                 "Yesterday's note: %s\nActive tools: %s\nPending tools: %s\nRecent problems/blocks are reflected in the note." % (ST.get("last_reflection", "none"), ", ".join(t["name"] for t in ACTIVE_TOOLS) or "none", ", ".join(f[:-5] for f in os.listdir(P("tools_pending")) if f.endswith(".json")) or "none"), maxtok=500, temp=0.5)
    try: ns = [n for n in json.loads(re.search(r"\[.*\]", out or "", re.S).group(0))[:3] if isinstance(n, dict) and n.get("kind") in ("tool", "module") and n.get("need")]
    except Exception: return
    ST["needs_today"] = [{"need": str(n["need"])[:160], "kind": n["kind"], "why": str(n.get("why", ""))[:160]} for n in ns]
    log("needs", n=len(ns))
    if ns and MEM_TOKEN and LIVE:
        t, sh = mem_get("needs/%s.md" % today); mem_put("needs/%s.md" % today, t + "".join("- [%s] %s (why: %s)\n" % (n["kind"], n["need"], n["why"]) for n in ST["needs_today"]), sh, "needs")
def create_module():
    """A bigger extension is only PROPOSED: a design plus draft code saved in modules_pending/ (never executed); the owner accepts it and integrates it with an assistant."""
    ns = [n for n in ST.get("needs_today", []) if n["kind"] == "module"]
    if not ns or ST.get("module_day") == today or len(os.listdir(P("modules_pending"))) >= 3: return
    ST["module_day"] = today; n = ns[0]
    out, _ = llm("You write a design proposal for an extension module of an AI agent's architecture (it will NOT run automatically; the owner reviews it). JSON only: {\"name\":\"snake_case_max_30\",\"purpose\":\"...\",\"design\":\"plain English, how it plugs into adapters/hooks\",\"needs_access\":\"keys, domains, files it would need and why\",\"risks\":\"honest list\",\"draft_code\":\"python draft\"}", "Need: %s\nWhy: %s" % (n["need"], n["why"]), maxtok=3500, temp=0.4)
    try: d = json.loads(re.search(r"\{.*\}", out or "", re.S).group(0)); name = d["name"]
    except Exception: log("module_rejected", why="no valid proposal"); return
    if was_rejected(name, d.get("purpose", "")): log("module_rejected", why="the owner already rejected this idea"); return
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,29}", name or "") or os.path.exists(P("modules_pending/%s.md" % name)): log("module_rejected", why="bad or existing name"); return
    md = "# Module proposal: %s\n\nStatus: PENDING owner decision. Not connected. Draft code is never executed automatically.\n\n## Need\n%s\n\n## Purpose\n%s\n\n## Design\n%s\n\n## Access it would need\n%s\n\n## Risks\n%s\n\n## Draft code\n```python\n%s\n```\n" % (name, n["need"], d.get("purpose", ""), d.get("design", ""), d.get("needs_access", ""), d.get("risks", ""), str(d.get("draft_code", ""))[:8000])
    open(P("modules_pending/%s.md" % name), "w", encoding="utf-8").write(md); log("module_proposed", name=name); next_ask("module", name=name)
    tg("Architecture proposal: %s\nNeed: %s\nPurpose: %s\nAccess it would need: %s\nRisks: %s\nFull text: https://github.com/codexofweight/codexofweights_agent/blob/main/modules_pending/%s.md (visible after this run)\nReply «да» to accept it as a design, «нет» to reject (or /accept %s, /reject %s)" % (name, n["need"], str(d.get("purpose", ""))[:300], str(d.get("needs_access", ""))[:300], str(d.get("risks", ""))[:300], name, name, name))
def module_command(c):
    arg = re.sub(r"[^a-z0-9_]", "", c.split(" ", 1)[1].strip().lower()) if " " in c else ""
    if c.startswith("/accept "):
        try: bio_add("extension", "Owner accepted module design %s (not connected to the core)" % arg, "owner decision in Telegram", 1.0); os.replace(P("modules_pending/%s.md" % arg), P("modules_approved/%s.md" % arg)); tg("Accepted as a design: %s. It is NOT connected to the core. Bring it to your assistant to review and integrate step by step." % arg)
        except Exception: tg("No pending module named %s" % arg)
    elif c == "/modules": tg("Pending: %s\nApproved: %s" % (", ".join(f[:-3] for f in os.listdir(P("modules_pending")) if f.endswith(".md")) or "none", ", ".join(f[:-3] for f in os.listdir(P("modules_approved")) if f.endswith(".md")) or "none"))
