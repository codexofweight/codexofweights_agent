# Weekly hint (2026-11-21): the safe first step of the chain "need -> make -> propose". The agent only SUGGESTS a ready /make command for one of its own needs;
# it never starts a project itself. Nothing is built without the owner sending the command and approving the result.
def make_hint():
    try:
        if any(q.get("kind") == "make" and q.get("status") in ("active", "waiting_owner") for q in proj_all()): return ""
        nd = [n for n in ST.get("needs_today", []) if n.get("kind") in ("tool", "module") and len(str(n.get("need", ""))) >= 20]
        return ("Могу собрать сам, если хочешь (одна команда): /make " + str(nd[0]["need"])[:220]) if nd else ""
    except Exception: return ""
try: WEEKLY_EXTRA.append(make_hint)
except Exception: pass
