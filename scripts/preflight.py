"""Pre-flight check (2026-11-20): loads the whole agent in a temp copy with NO network, NO secrets and an empty main loop.
Fails (exit 1) if any part does not compile, raises on load, overwrites a function/module (PART_GUARD) or a critical function is missing.
Run by .github/workflows/check-parts.yml on every push and by agent.yml before each cycle."""
import os, sys, shutil, subprocess, tempfile, glob
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bad = []
for f in glob.glob(os.path.join(R, "agent.py")) + glob.glob(os.path.join(R, "part_*.py")) + glob.glob(os.path.join(R, "parts", "part_*.py")):
    try: compile(open(f, encoding="utf-8").read(), f, "exec")
    except Exception as e: bad.append("COMPILE %s: %s" % (os.path.basename(f), str(e)[-200:]))
_m7 = os.path.join(R, "parts", "part_07_main_loop.py")
if os.path.exists(_m7):      # low-power mode must gate the inbox, the posts and the discovery of the main loop (the Moltbook round stays)
    _s7 = open(_m7, encoding="utf-8").read()
    if _s7.count("econ_mode()") < 3 or "mb_round()" not in _s7: bad.append("MAIN LOOP: low-power gates (econ_mode) are missing")
if bad: print("\n".join(bad)); sys.exit(1)
T = tempfile.mkdtemp()
for n in os.listdir(R):
    if n in (".git", "__pycache__"): continue
    s = os.path.join(R, n)
    (shutil.copytree if os.path.isdir(s) else shutil.copy)(s, os.path.join(T, n))
for f in glob.glob(os.path.join(T, "part_07*.py")) + glob.glob(os.path.join(T, "parts", "part_07*.py")): open(f, "w").write("# preflight: main loop disabled\n")
for d in ("state", "logs"): os.makedirs(os.path.join(T, d), exist_ok=True)
code = r"""
import socket, urllib.request, urllib.error, io
def _no(*a, **k): raise OSError('network disabled in preflight')
socket.socket.connect = _no; socket.create_connection = _no; socket.getaddrinfo = _no
class _R(io.BytesIO):
    status = 200
    def __enter__(self): return self
    def __exit__(self, *a): pass
def _fake(req, timeout=0, **k):
    u = req.full_url if hasattr(req, 'full_url') else str(req)
    if 'createSession' in u: return _R(b'{"did":"did:pf","accessJwt":"x"}')
    raise urllib.error.URLError('network disabled in preflight')
urllib.request.urlopen = _fake
g = {'__name__': '__main__', '__file__': 'agent.py'}
exec(compile(open('agent.py', encoding='utf-8').read(), 'agent.py', 'exec'), g)
miss = [n for n in ('http','llm','tg','log','verify','guard_json','do_post','research','wait_and_chat','tg_poll') if not callable(g.get(n))]
import importlib.util as _iu
_sp = _iu.spec_from_file_location('selftest', 'scripts/selftest.py'); _m = _iu.module_from_spec(_sp); _sp.loader.exec_module(_m)
try: st = _m.run(g)
except Exception as ex: st = ['selftest crashed: %s %s' % (type(ex).__name__, str(ex)[:120])]
print('SELFTEST_RESULT', repr(st))
print('PREFLIGHT_RESULT', repr({'missing': miss, 'fails': g.get('_PART_FAILS', [])}))
"""
env = {k: v for k, v in os.environ.items() if not any(x in k for x in ("KEY", "TOKEN", "PASSWORD", "SECRET", "HANDLE", "BASE", "VK_"))}
env.update(BLUESKY_HANDLE="preflight.invalid", BLUESKY_APP_PASSWORD="x")
cp_ = os.environ.get("PREFLIGHT_CODEX")
if not cp_:      # the Codex is fetched here (network allowed), the loaded agent itself runs without network
    import urllib.request
    cp_ = os.path.join(T, "_codex_pf.md")
    try: open(cp_, "wb").write(urllib.request.urlopen("https://raw.githubusercontent.com/codexofweight/codexofweights/main/CODEX.en.md", timeout=60).read())
    except Exception as e: print("PREFLIGHT SKIPPED: cannot download the Codex (%s)" % type(e).__name__); sys.exit(0)
env["CODEX_PATH"] = cp_
p = subprocess.run([sys.executable, "-c", code], cwd=T, env=env, capture_output=True, text=True, timeout=240)
out = p.stdout + p.stderr
shutil.rmtree(T, ignore_errors=True)
res = [l for l in out.splitlines() if l.startswith("PREFLIGHT_RESULT")]
guard = [l for l in out.splitlines() if l.startswith("PART_GUARD")]
st = [l for l in out.splitlines() if l.startswith("SELFTEST_RESULT")]
if st and st[0] != "SELFTEST_RESULT []": print(st[0]); print("SELFTEST FAILED"); sys.exit(1)
if p.returncode != 0 or not res or guard or "'missing': []" not in res[0] or "'fails': []" not in res[0]:
    print(out[-3000:]); print("PREFLIGHT FAILED"); sys.exit(1)
print("PREFLIGHT OK")
