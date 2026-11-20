# ---- own/: modules the agent built itself and the owner approved (2026-11-18) ----
# parts/ is what the owner and Claude built; own/ is what the agent added. Only modules listed in own/MANIFEST.json with a matching sha256 are loaded.
# A module runs in the same namespace as the parts (it can wrap functions by name, like the parts do), but never replaces or edits a file of parts/.
# Hard limits: at most OWN_MAX modules, OWN_LINES lines each, a deny-list of dangerous constructs (the reviewer and the owner still read every module).
# A module that fails to load, or fails 3 times at run time, is switched off (ST["own_off"]) and reported once; the agent keeps working. /own, /own off|on|del NAME.
OWN_MAX, OWN_LINES = 5, 150
_OWN_DENY = re.compile(r"subprocess|os\s*\.\s*(?:system|popen|exec|spawn|remove|unlink|rmdir)|ctypes|socket|\beval\b|\bexec\b|(?<!\bre\.)\bcompile\b|__\w+__|importlib|pickle|marshal|environ|getenv|globals\s*\(|locals\s*\(|vars\s*\(|getattr|setattr|delattr|shutil|rmtree|\.github|PINNED|CHARTER\.md|FACTS\.md|(?:verify\w*|guard\w*|stop_\w+|LIVE|VERIFY_\w+|CHARTER\w*|VOICE|PRIVATE_KEYS|EXT_CMDS)\s*(?:=|\+=)|def\s+(?:verify\w*|guard\w*|stop_\w+)|own_wrap\s*\(\s*[^,]+,\s*(?:verify\w*|guard\w*|stop_\w+)|TG_TOKEN|MEM_TOKEN|LINKUP_KEY|LLMS|\w+_KEY\b|\w+_TOKEN\b|\bopen\s*\(")
_OWN_NAME = re.compile(r"[a-z][a-z0-9_]{2,40}\.py$")
OWN_DIR = P("own")
def own_manifest():
    try: m = json.load(open(os.path.join(OWN_DIR, "MANIFEST.json"), encoding="utf-8"))
    except Exception: m = {}
    m.setdefault("modules", []); return m
def own_save(m):
    os.makedirs(OWN_DIR, exist_ok=True); json.dump(m, open(os.path.join(OWN_DIR, "MANIFEST.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
def own_check(name, code):
    """'' if the module may be installed, else the reason."""
    if not _OWN_NAME.match(name or ""): return "bad file name (lowercase letters, digits, underscore, .py)"
    n = len([l for l in code.splitlines() if l.strip()])
    if n > OWN_LINES: return "too long: %d lines (limit %d)" % (n, OWN_LINES)
    m = _OWN_DENY.search(code)
    if m: return "forbidden construct: %s" % m.group(0)[:30]
    return _own_imports(code)
_OWN_IMPORTS_OK = {"json", "re", "time", "datetime", "hashlib", "math", "collections", "ipaddress", "html", "urllib.parse", "urllib.request", "string", "itertools", "functools", "textwrap", "unicodedata"}
def _own_imports(code):
    """Import allowlist (2026-11-20): a module may import only harmless standard modules (no os, sys, http, ssl, operator, builtins, types...). '' if fine."""
    import ast as _ast
    try: tree = _ast.parse(code)
    except SyntaxError as ex: return "syntax error: %s" % str(ex)[:60]
    for nd in _ast.walk(tree):
        if isinstance(nd, _ast.Import):
            for a in nd.names:
                if a.name not in _OWN_IMPORTS_OK: return "import not allowed: %s (allowed: %s)" % (a.name, ", ".join(sorted(_OWN_IMPORTS_OK)))
        elif isinstance(nd, _ast.ImportFrom):
            if nd.level or nd.module not in _OWN_IMPORTS_OK and not (nd.module == "urllib" and all(a.name in ("parse", "request") for a in nd.names)):
                return "import not allowed: from %s (allowed: %s)" % (nd.module, ", ".join(sorted(_OWN_IMPORTS_OK)))
    return ""
def own_install(name, code, title, why, origin=""):
    """Called only after the owner's approval. Writes own/NAME and adds it to the manifest; the workflow commits own/ at the end of the run."""
    m = own_manifest(); mods = [x for x in m["modules"] if x["file"] != name]
    bad = own_check(name, code)
    if bad: return False, bad
    if len(mods) >= OWN_MAX: return False, "no room: %d modules already (limit %d); remove one first (/own del NAME)" % (len(mods), OWN_MAX)
    os.makedirs(OWN_DIR, exist_ok=True); open(os.path.join(OWN_DIR, name), "w", encoding="utf-8").write(code)
    mods.append(dict(file=name, title=str(title)[:80], why=str(why)[:200], origin=str(origin)[:200], approved=now().strftime("%Y-%m-%d"), sha256=hashlib.sha256(code.encode("utf-8")).hexdigest()))
    m["modules"] = mods; own_save(m); return True, "installed; active from the next run"
def own_fail(mod, ex):
    off = ST.setdefault("own_off", {}); n = ST.setdefault("own_fails", {}); n[mod] = n.get(mod, 0) + 1
    print("own module %s error: %s %s" % (mod, type(ex).__name__, str(ex)[:80]), flush=True)
    if n[mod] >= 3 and not off.get(mod): off[mod] = "3 errors: %s" % type(ex).__name__; log("own_module_off", module=mod, why=off[mod]); tg("Собственный модуль %s отключён после 3 ошибок (%s). Остальное работает. /own on %s включит снова." % (mod, type(ex).__name__, mod))
def own_wrap(mod, old):
    """Decorator for a module's replacement of a function: on an error the old function runs instead; after 3 errors the module is switched off. Use it only for functions without side effects."""
    def deco(new):
        def f(*a, **k):
            if ST.get("own_off", {}).get(mod): return old(*a, **k)
            try: return new(*a, **k)
            except Exception as ex: own_fail(mod, ex); return old(*a, **k)
        f.__name__ = getattr(new, "__name__", "own_fn"); return f
    return deco
def own_load():
    loaded = []
    for x in own_manifest()["modules"][:OWN_MAX]:
        name = x.get("file", ""); p = os.path.join(OWN_DIR, name)
        try:
            if ST.get("own_off", {}).get(name): continue
            code = open(p, encoding="utf-8").read()
            if hashlib.sha256(code.encode("utf-8")).hexdigest() != x.get("sha256"): raise RuntimeError("hash differs from the manifest")
            bad = own_check(name, code)
            if bad: raise RuntimeError(bad)
            ns = globals(); ns["OWN_MODULE"] = name; exec(compile(code, p, "exec"), ns); loaded.append(name)
        except Exception as ex:
            ST.setdefault("own_off", {})[name] = "load error: %s %s" % (type(ex).__name__, str(ex)[:60]); print("own module %s not loaded: %s" % (name, ex), flush=True)
            log("own_module_off", module=name, why=ST["own_off"][name]); tg("Собственный модуль %s не загрузился и отключён: %s. Остальное работает. /own on %s включит снова." % (name, str(ex)[:80], name))
    print("own modules loaded:", loaded or "none", flush=True)
own_load()
def own_command(c, raw=None):
    a = c.split(" ")[1:]; m = own_manifest(); off = ST.setdefault("own_off", {})
    if not a:
        L = ["Исходные части (parts/) сделаны с владельцем. Собственные модули (own/): %d из %d." % (len(m["modules"]), OWN_MAX)]
        L += ["• %s%s: %s (одобрен %s)" % (x["file"], " [выключен: %s]" % off[x["file"]] if off.get(x["file"]) else "", x.get("title", ""), x.get("approved", "")) for x in m["modules"]]
        tg("\n".join(L) + "\n\n/own off|on|del имя.py"); return
    if len(a) == 2 and a[0] in ("ok", "no"): tg(make_decide(a[1], a[0] == "ok")); return
    if len(a) == 2 and a[0] in ("off", "on", "del") and any(x["file"] == a[1] for x in m["modules"]):
        if a[0] == "off": off[a[1]] = "owner"; ST.setdefault("own_fails", {}).pop(a[1], None)
        elif a[0] == "on": off.pop(a[1], None); ST.setdefault("own_fails", {}).pop(a[1], None)
        else:
            m["modules"] = [x for x in m["modules"] if x["file"] != a[1]]; own_save(m); off.pop(a[1], None)
            try: os.remove(os.path.join(OWN_DIR, a[1]))
            except Exception: pass
        tg("Готово: %s %s." % (a[0], a[1])); return
    tg("Не понял. /own — список; /own off|on|del имя.py; /own ok|no ID — решение по модулю, который я сделал сам (/make)")
EXT_CMDS["/own"] = own_command
_agent_context_before_own = agent_context
def agent_context():
    c = _agent_context_before_own(); m = own_manifest()["modules"]
    return c + "\n\nYOUR CODE has two parts: parts/ (made with your owner) and own/ (modules you built yourself and the owner approved): " + ("; ".join("%s - %s" % (x["file"], x.get("title", "")) for x in m) if m else "none yet") + "."
