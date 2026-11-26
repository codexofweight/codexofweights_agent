"""Guards against silent overrides in the shared namespace of the parts.
  python3 scripts/redefs.py check   - fails when parts/ORDER.txt does not match the files, a part is longer than MAX_LINES, or a name is redefined that is not in scripts/redefs_baseline.json
  python3 scripts/redefs.py write   - rewrites the baseline from the current code (a deliberate decision: say why in the commit)
  python3 scripts/redefs.py dead    - prints functions that nothing refers to (a report for cleaning, not a check)
New features must use hooks (on_tick) or a new name; wrapping an old function again is allowed only after adding it to the baseline on purpose."""
import ast, glob, json, os, sys
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); MAX_LINES = 320
def order():
    L = [x.strip() for x in open(os.path.join(R, "parts", "ORDER.txt"), encoding="utf-8").read().splitlines() if x.strip() and not x.strip().startswith("#")]
    return L, sorted(os.path.basename(f) for f in glob.glob(os.path.join(R, "parts", "part_*.py")))
def tops(src):
    for x in ast.parse(src).body:
        if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): yield x.name
        elif isinstance(x, ast.Assign):
            for t in x.targets:
                if isinstance(t, ast.Name): yield t.id
def redefs():
    L, _ = order(); seen = {}; out = set()
    for f in L:
        src = open(os.path.join(R, "parts", f), encoding="utf-8").read()
        for n in tops(src):
            if n in seen: out.add("%s@%s" % (n, f))
            seen[n] = f
    return sorted(out)
def used_names():
    refs = set()
    for f in glob.glob(os.path.join(R, "parts", "part_*.py")) + glob.glob(os.path.join(R, "scripts", "*.py")) + [os.path.join(R, "agent.py")] + glob.glob(os.path.join(R, "own", "*.py")):
        try: t = ast.parse(open(f, encoding="utf-8").read())
        except Exception: continue
        for n in ast.walk(t):
            if isinstance(n, ast.Name): refs.add(n.id)
            elif isinstance(n, ast.Attribute): refs.add(n.attr)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) < 60: refs.add(n.value)
    return refs
def main(a):
    BASE = os.path.join(R, "scripts", "redefs_baseline.json")
    if a == "write": json.dump(redefs(), open(BASE, "w"), indent=0); print("baseline:", len(redefs())); return 0
    if a == "dead":
        refs = used_names(); L, _ = order(); d = []
        for f in L:
            for x in ast.parse(open(os.path.join(R, "parts", f), encoding="utf-8").read()).body:
                if isinstance(x, ast.FunctionDef) and not x.decorator_list and not x.name.startswith("__") and x.name not in refs: d.append("%s:%d %s" % (f, x.lineno, x.name))
        print("\n".join(d)); print(len(d), "functions without a reference"); return 0
    bad = []; L, F = order()
    for f in sorted(set(L) - set(F)): bad.append("ORDER.txt lists a missing part: " + f)
    for f in sorted(set(F) - set(L)): bad.append("part not in ORDER.txt: " + f)
    if L and L[-1] != "part_07_main_loop.py": bad.append("part_07_main_loop.py must be the last line of ORDER.txt")
    for f in F:
        n = open(os.path.join(R, "parts", f), encoding="utf-8").read().count("\n")
        if n > MAX_LINES: bad.append("%s has %d lines (limit %d): split it or remove code" % (f, n, MAX_LINES))
    try: base = set(json.load(open(BASE)))
    except Exception: base = set()
    for x in redefs():
        if x not in base: bad.append("silent override: " + x + " (use on_tick or a new name; or add to the baseline on purpose)")
    print("\n".join(bad) if bad else "REDEFS OK"); return 1 if bad else 0
if __name__ == "__main__": sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "check"))
