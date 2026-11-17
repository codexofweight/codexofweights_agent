"""Coding benchmark for the free LLM providers of the agent (2026-11-17).
Each model gets the same 6 small tasks; the answer is run against hidden tests in a clean subprocess (no secrets in its environment).
Result: table in bench/results.md, short summary in Telegram. Run by hand: Actions -> code-bench -> Run workflow. Nothing here touches the agent."""
import os, re, sys, json, time, subprocess, tempfile, urllib.request, urllib.error

PROVIDERS = [  # name, base url, key env, default model env/default
    ("gemini", os.environ.get("GEMINI_BASE", "https://generativelanguage.googleapis.com/v1beta/openai"), "GEMINI_AGENT_API_KEY", "gemini-3.1-flash-lite"),
    ("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    ("mistral", "https://api.mistral.ai/v1", "MISTRAL_API_KEY", "mistral-large-latest"),
    ("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "nvidia/nemotron-3-ultra-550b-a55b:free"),
    ("sambanova", "https://api.sambanova.ai/v1", "SAMBANOVA_API_KEY", "Meta-Llama-3.3-70B-Instruct"),
]
MAX_PER = int(os.environ.get("BENCH_MAX_PER_PROVIDER", "4"))
WANT = re.compile(r"coder|codestral|devstral|gpt-oss|qwen3|deepseek|kimi|glm|gemini-(?:2\.5|3)|llama-3\.3|nemotron|mistral-(?:large|medium)", re.I)
SKIP = re.compile(r"embed|tts|whisper|guard|image|audio|vision|moderation|ocr|robotics|live|dall|safety", re.I)

HARNESS = '''
def _run(tests):
    ok = 0
    for t in tests:
        try: t(); ok += 1
        except BaseException: pass
    print("SCORE", ok, len(tests))
'''
TASKS = [
 ("duration", "Write a Python function parse_duration(s) that converts strings like '1h30m15s', '45s', '2h', '10m5s' into total seconds (int). Units are h, m, s, each at most once and in this order. Raise ValueError for an empty string, unknown units, wrong order, repeated units, a missing number, or any other garbage.",
  '''
T = [lambda: parse_duration("1h30m15s") == 5415 or 1/0,
     lambda: parse_duration("45s") == 45 or 1/0,
     lambda: parse_duration("2h") == 7200 or 1/0,
     lambda: parse_duration("10m5s") == 605 or 1/0,
     lambda: _raises(lambda: parse_duration("")),
     lambda: _raises(lambda: parse_duration("5x")),
     lambda: _raises(lambda: parse_duration("30m1h")),
     lambda: _raises(lambda: parse_duration("1h1h")),
     lambda: _raises(lambda: parse_duration("h")),
     lambda: _raises(lambda: parse_duration("12")),
     lambda: _raises(lambda: parse_duration("1h abc"))]
'''),
 ("dedupe", "Write a Python function dedupe(items, key=None) that returns a new list with duplicates removed, keeping the FIRST occurrence and the original order. If key is given (a function), items are considered equal when key(item) is equal. It must work with unhashable items (for example lists) when no key is given, and must not modify the input.",
  '''
T = [lambda: dedupe([1,2,1,3,2]) == [1,2,3] or 1/0,
     lambda: dedupe([]) == [] or 1/0,
     lambda: dedupe(["a","A","b"], key=str.lower) == ["a","b"] or 1/0,
     lambda: dedupe([[1],[2],[1]]) == [[1],[2]] or 1/0,
     lambda: dedupe([{"a":1},{"a":1},{"a":2}]) == [{"a":1},{"a":2}] or 1/0,
     lambda: (lambda x: (dedupe(x), x == [1,1,2])[1] or 1/0)([1,1,2]),
     lambda: dedupe("abca") == ["a","b","c"] or 1/0,
     lambda: dedupe([1,1.0,True]) == [1] or 1/0]
'''),
 ("lru", "Write a Python class LRUCache(capacity) with methods get(key) (returns the value or None if absent; marks the key as recently used) and put(key, value) (inserts or updates; marks as recently used; when the size would exceed capacity, evict the least recently used key). capacity 0 means nothing is stored. Also support len(cache) and 'key in cache' (membership must NOT change recency).",
  '''
def _t1():
    c = LRUCache(2); c.put("a",1); c.put("b",2); c.put("c",3); assert c.get("a") is None and c.get("b") == 2 and c.get("c") == 3
def _t2():
    c = LRUCache(2); c.put("a",1); c.put("b",2); c.get("a"); c.put("c",3); assert "b" not in c and "a" in c
def _t3():
    c = LRUCache(2); c.put("a",1); c.put("a",5); assert len(c) == 1 and c.get("a") == 5
def _t4():
    c = LRUCache(0); c.put("a",1); assert len(c) == 0 and c.get("a") is None
def _t5():
    c = LRUCache(2); c.put("a",1); c.put("b",2); assert "a" in c; c.put("c",3); assert "a" not in c
def _t6():
    c = LRUCache(1); c.put("a",1); c.put("b",2); assert len(c) == 1 and c.get("b") == 2
def _t7():
    c = LRUCache(2); c.put("a",None); assert "a" in c and len(c) == 1
T = [_t1,_t2,_t3,_t4,_t5,_t6,_t7]
'''),
 ("intervals", "Write a Python function merge_intervals(intervals) that takes a list of (start, end) tuples (start <= end, integers, any order) and returns a new sorted list of merged tuples. Intervals that overlap OR touch (end of one == start of the next) are merged. Do not modify the input.",
  '''
T = [lambda: merge_intervals([(1,3),(2,6),(8,10)]) == [(1,6),(8,10)] or 1/0,
     lambda: merge_intervals([(1,2),(2,3)]) == [(1,3)] or 1/0,
     lambda: merge_intervals([]) == [] or 1/0,
     lambda: merge_intervals([(5,6),(1,2)]) == [(1,2),(5,6)] or 1/0,
     lambda: merge_intervals([(1,10),(2,3),(4,5)]) == [(1,10)] or 1/0,
     lambda: merge_intervals([(3,3),(3,3)]) == [(3,3)] or 1/0,
     lambda: (lambda x: (merge_intervals(x), x == [(2,3),(1,2)])[1] or 1/0)([(2,3),(1,2)]),
     lambda: merge_intervals([(1,4),(0,0)]) == [(0,0),(1,4)] or 1/0]
'''),
 ("filename", "Write a Python function safe_filename(name) that turns arbitrary text into a safe file name: keep only letters, digits, dot, dash, underscore (Unicode letters allowed); replace every other run of characters with a single underscore; strip leading and trailing dots and underscores; collapse '..' sequences to a single dot; limit to 50 characters; if the result is empty or is a Windows reserved name (CON, PRN, AUX, NUL, COM1-COM9, LPT1-LPT9, case-insensitive, with or without extension) return 'file'.",
  '''
T = [lambda: safe_filename("hello world.txt") == "hello_world.txt" or 1/0,
     lambda: safe_filename("../../etc/passwd") == "etc_passwd" or 1/0,
     lambda: safe_filename("") == "file" or 1/0,
     lambda: safe_filename("CON") == "file" or 1/0,
     lambda: safe_filename("nul.txt") == "file" or 1/0,
     lambda: safe_filename("a" * 80) == "a" * 50 or 1/0,
     lambda: safe_filename("отчёт 2026.pdf") == "отчёт_2026.pdf" or 1/0,
     lambda: safe_filename("a..b") == "a.b" or 1/0,
     lambda: safe_filename("***") == "file" or 1/0,
     lambda: safe_filename("  my   file  ") == "my_file" or 1/0]
'''),
 ("bugfix", "The function below has a bug. Return the corrected full function (same name and signature). It must return the n most common words of the text, lowercase, ignoring punctuation, as a list of (word, count) sorted by count descending and, for equal counts, alphabetically.\n\ndef top_words(text, n):\n    counts = {}\n    for w in text.split():\n        counts[w] = counts.get(w, 0) + 1\n    return sorted(counts.items(), key=lambda kv: kv[1])[:n]",
  '''
T = [lambda: top_words("a b a", 1) == [("a", 2)] or 1/0,
     lambda: top_words("The cat. the CAT! a dog", 2) == [("cat", 2), ("the", 2)] or 1/0,
     lambda: top_words("b a", 2) == [("a", 1), ("b", 1)] or 1/0,
     lambda: top_words("", 3) == [] or 1/0,
     lambda: top_words("x y z", 5) == [("x",1),("y",1),("z",1)] or 1/0,
     lambda: top_words("Hello, hello; HELLO?", 1) == [("hello", 3)] or 1/0,
     lambda: top_words("one two two three three three", 2) == [("three", 3), ("two", 2)] or 1/0]
'''),
]
RAISES = "def _raises(f):\n    try: f()\n    except ValueError: return True\n    except BaseException: raise AssertionError('wrong exception')\n    raise AssertionError('no exception')\n"
PROMPT = "You are a careful Python engineer. Solve the task. Output ONLY one Python code block with the complete solution (imports allowed from the standard library only, no input(), no printing, no tests, no explanations).\n\nTask: "

def extract(text):
    m = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text or "", re.S)
    return max(m, key=len) if m else (text or "")

def score(code, tests):
    src = code + "\n" + HARNESS + RAISES + tests + "\n_run(T)\n"
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "t.py"); open(p, "w").write(src)
        try:
            r = subprocess.run([sys.executable, "-I", p], cwd=d, env={"PATH": os.environ.get("PATH", ""), "LC_ALL": "C.UTF-8"}, capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired: return 0, 1
        m = re.search(r"SCORE (\d+) (\d+)", r.stdout)
        return (int(m.group(1)), int(m.group(2))) if m else (0, 1)

def call(base, key, model, prompt):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 2500}).encode()
    for attempt in range(3):
        req = urllib.request.Request(base.rstrip("/") + "/chat/completions", body, {"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "codex-bench/1"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r: d = json.loads(r.read().decode())
            return (d["choices"][0]["message"].get("content") or "").strip()
        except urllib.error.HTTPError as ex:
            if ex.code in (429, 500, 502, 503) and attempt < 2: time.sleep(20 * (attempt + 1)); continue
            return "ERROR HTTP %s" % ex.code
        except Exception as ex: return "ERROR %s" % type(ex).__name__
    return "ERROR"

def discover(name, base, key, default):
    out = [default]
    try:
        req = urllib.request.Request(base.rstrip("/") + "/models", headers={"Authorization": "Bearer " + key, "User-Agent": "codex-bench/1"})
        with urllib.request.urlopen(req, timeout=30) as r: d = json.loads(r.read().decode())
        ids = [str(x.get("id", "")).replace("models/", "") for x in (d.get("data") or d.get("models") or [])]
        for i in ids:
            if name == "openrouter" and not i.endswith(":free"): continue
            if WANT.search(i) and not SKIP.search(i) and i not in out: out.append(i)
    except Exception as ex: print("model list failed for", name, type(ex).__name__, flush=True)
    return out[:MAX_PER]

def main():
    only = os.environ.get("BENCH_ONLY", "").strip()
    rows = []
    for name, base, kenv, default in PROVIDERS:
        key = os.environ.get(kenv, "")
        if not key or (only and name not in only.split(",")): continue
        for model in discover(name, base, key, os.environ.get("BENCH_" + name.upper(), default)):
            got = tot = 0; fails = []
            for tname, task, tests in TASKS:
                ans = call(base, key, model, PROMPT + task)
                if ans.startswith("ERROR"): fails.append(tname + ":" + ans[6:]); tot += len(re.findall(r"lambda:|_t\d", tests)) or 1; time.sleep(3); continue
                a, b = score(extract(ans), tests); got += a; tot += b
                if a < b: fails.append("%s %d/%d" % (tname, a, b))
                time.sleep(3)
            rows.append((name, model, got, tot, fails)); print("%-10s %-48s %d/%d  %s" % (name, model, got, tot, "; ".join(fails)), flush=True)
    rows.sort(key=lambda r: -(r[2] / max(r[3], 1)))
    md = ["# Coding benchmark of the free models (%s)\n" % time.strftime("%Y-%m-%d"), "| model | provider | passed tests | where it failed |", "|---|---|---|---|"]
    md += ["| %s | %s | %d/%d (%d%%) | %s |" % (m, p, g, t, round(100 * g / max(t, 1)), "; ".join(f) or "-") for p, m, g, t, f in rows]
    os.makedirs("bench", exist_ok=True); open("bench/results.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
    short = "Замер кода:\n" + "\n".join("%d%% %s (%s)" % (round(100 * g / max(t, 1)), m, p) for p, m, g, t, f in rows[:12])
    tok, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if tok and chat:
        try: urllib.request.urlopen(urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % tok, json.dumps({"chat_id": chat, "text": short[:3900]}).encode(), {"Content-Type": "application/json"}), timeout=30)
        except Exception as ex: print("telegram failed", type(ex).__name__)
    print(short)
if __name__ == "__main__": main()
