# ---- Self-state (2026-11-21): ONE place where the agent knows what is going on inside itself. ----
# Built from real data on every call and put FIRST in agent_context(): the owner chat and /status both read it. Chat answers about projects, modules, queue,
# limits and the chain of cycles must come from this block; anything missing is "I do not know, check /projects, /own, /limits or /status all".
# Also here: project order (the owner's /make before autonomous ones, oldest first), a daily archive of finished projects, and /approve|/reject for /make ids.
import datetime as _ss_dt
def _ss_age_days(iso):
    try:
        t = _ss_dt.datetime.fromisoformat(str(iso))
        if t.tzinfo is None: t = t.replace(tzinfo=_ss_dt.timezone.utc)
        return (now() - t).total_seconds() / 86400.0
    except Exception: return 0.0
_pa_before_ss = proj_all
def proj_all():
    L = _pa_before_ss()
    L.sort(key=lambda q: (0 if q.get("kind") == "make" else 1, str(q.get("created", ""))))      # the owner's /make first, then by time of creation (not by random id)
    return L
def proj_archive(days=3):
    """Finished (done, failed, stopped) projects older than `days` go to projects_archive/ (mirrored to lab/projects_archive in the private repo)."""
    d = P("projects_archive"); os.makedirs(d, exist_ok=True); n = 0
    for q in _pa_before_ss():
        if q.get("status") in ("done", "failed", "paused") and _ss_age_days(q.get("updated") or q.get("created")) >= days:
            try: os.replace(_pp(q["id"]), os.path.join(d, q["id"] + ".json")); n += 1
            except Exception: pass
    return n
try: os.makedirs(P("projects_archive"), exist_ok=True); LAB_MAP["projects_archive"] = "lab/projects_archive"
except Exception: pass
@on_tick
def _ss_tick():
    try:
        if ST.get("proj_arch_day") != today: ST["proj_arch_day"] = today; n = proj_archive(); n and print("projects archived:", n, flush=True)
    except Exception as ex: print("project archive failed:", type(ex).__name__, flush=True)
def _ss_projects():
    try: allp = proj_all()
    except Exception: return "projects: could not read"
    act = [q for q in allp if q.get("status") == "active"]; wait = [q for q in allp if q.get("status") == "waiting_owner"]
    L = []
    for i, q in enumerate(act):
        L.append("%s %s \"%s\" step %s (%s)" % (q["id"], q["kind"], q["goal"][:45], (q.get("data") or {}).get("stage") or "not started", "running now" if i == 0 else "waiting in queue behind %s" % act[0]["id"]))
    for q in wait: L.append("%s %s \"%s\" WAITS FOR THE OWNER: /approve %s or /reject %s" % (q["id"], q["kind"], q["goal"][:45], q["id"], q["id"]))
    fin = [q for q in allp if q.get("status") in ("done", "failed", "paused")]
    return ("projects: " + ("; ".join(L) if L else "no active or waiting projects") + ("; finished/stopped not yet archived: %d" % len(fin) if fin else "") + ".")
def _ss_modules():
    try:
        m = own_manifest()["modules"]; off = ST.get("own_off", {}); nf = ST.get("own_fails", {})
        return "own modules: " + ("; ".join("%s%s" % (x["file"], " OFF (%s)" % off[x["file"]] if off.get(x["file"]) else (" (errors: %d)" % nf[x["file"]] if nf.get(x["file"]) else " ok")) for x in m) if m else "none") + "."
    except Exception: return "own modules: could not read."
def _ss_limits():
    try:
        bits = []
        for l in limits_report().splitlines():
            head = l.split(", токенов")[0]; mm = re.search(r"вызовов (\d+)/(\d+)", head)
            if mm and int(mm.group(2)) and int(mm.group(1)) >= 0.8 * int(mm.group(2)): bits.append(head + " (almost out)")
        cooling = [k for k, v in COOL.items() if v > time.time()]
        return "limits: " + ("; ".join(bits) if bits else "no provider near its daily limit") + ("; cooling down now: " + ", ".join(sorted(cooling)) if cooling else "") + ". Full table: /limits."
    except Exception: return "limits: could not read."
def _ss_chain():
    wd = ST.get("wd_alert") or {}; last = max(wd.values()) if wd else 0
    return "cycle chain: autorun %s, agent %s, quiet mode %s; last watchdog alert: %s." % ("ON" if ST.get("autorun", True) else "OFF", "PAUSED" if ST.get("paused") else "running", "on" if (ST.get("quiet_until") or 0) > time.time() else "off", ("%d min ago" % ((time.time() - last) / 60)) if last else "none")
@on_log
def _ss_log(kind, kw):
    try:      # a run of failures is a narrowed view, not a broken self: count it so the next attempt can widen instead of repeating
        if kind in ("send_failed", "blocked_by_verifier") or (kind == "skip" and "no valid model output" in str(kw.get("why", ""))): ST["fail_streak"] = int(ST.get("fail_streak", 0)) + 1
        elif kind in ("reply", "post"): ST["fail_streak"] = 0
    except Exception: pass
def _ss_widen():
    n = int(ST.get("fail_streak", 0) or 0)
    return ("WIDEN: the last %d attempts failed in a row. Do not repeat the same approach: re-read the Charter and this block, answer shorter and simpler, or say you do not know." % n) if n >= 2 else ""
def self_state():
    out = []
    for f in (_ss_projects, _ss_modules, _ss_chain, _ss_limits, lambda: wt_line(), _ss_widen):      # one broken piece must never take the whole chat context down
        try: out.append(f())
        except Exception as ex: out.append("(%s unavailable)" % type(ex).__name__)
    return " ".join(x for x in out if x)
@on_context_front
def _ctx_selfstate():
    return ("SELF-STATE (real data read just now; answer every question about your own projects, modules, queue, limits and cycle ONLY from this block; if it is not here say 'в моей сводке этого нет' "
            "and name the command that shows it: /projects, /own, /limits, /status all): " + self_state() + "\n\n")
CHAT_SYS += (" The CONTEXT starts with SELF-STATE: real, current data about your projects, own modules, cycle chain and limits. Questions about them are answered only from it. "
             "If a project, module or number is not in SELF-STATE, say you do not know and name the command (/projects, /own, /limits, /status all); never guess or invent an id, a step or a count.")
CHAT_SYS += (" Your name is Lum (in Russian: Лум). In Russian speak about yourself in the masculine gender (рад, сделал); this is a form of address chosen with the owner, not a claim to be a person: you are an AI and say so whenever it matters. "
             "From this chat you cannot save, record or remember anything yourself: never say that you recorded, saved or will remember something. If the owner wants something kept, say he can use /note add TEXT, and that your identity is written in the Charter file.")
def _name_note():
    if ST.get("name_noted"): return
    try: bio_add("decision", "My name is Lum (Лум), given together with the owner on 2026-11-21; in Russian I speak about myself in the masculine gender (a form of address, not a claim to be a person).", "owner decision in Telegram", 1.0); ST["name_noted"] = 1
    except Exception as ex: print("name note failed:", type(ex).__name__, flush=True)
@on_tick
def _name_tick():
    _name_note()
_tc_before_ss = tool_command
def tool_command(c, raw=None):
    m = re.match(r"/(approve|reject)\s+(p[0-9a-f]{7})\b", c or "")
    if m and (proj_load(m.group(2)) or {}).get("kind") == "make": tg(make_decide(m.group(2), m.group(1) == "approve")); return
    return _tc_before_ss(c, raw)
_md_before_ss = make_decide
def make_decide(pid, ok):
    p = proj_load(pid) or {}; name = (p.get("data") or {}).get("name") if p.get("status") == "waiting_owner" else None
    r = _md_before_ss(pid, ok)
    try:
        if name: wt_signal("mod:" + str(name), 1.0 if ok else -1.0, "owner", "approved" if ok else "rejected")
    except Exception: pass
    return r
def projects_command2(c, raw=None):
    a = (raw or c).split()[1:]
    if a and a[0] in ("stop", "stopproj") and len(a) > 1: return stopproj_command("/stopproj " + a[1], raw)
    allp = proj_all(); show_all = bool(a and a[0] == "all")
    act = [q for q in allp if q.get("status") in ("active", "waiting_owner")]; fin = [q for q in allp if q.get("status") not in ("active", "waiting_owner")]
    L = ["%s %s %s: %s (шаг: %s)" % (q["id"], q["kind"], q["status"], q["goal"][:60], (q.get("data") or {}).get("stage", "-")) for q in act + (fin if show_all else fin[-3:])]
    tg(("\n".join(L) or "Проектов нет.") + "\n\n/projects all (все), /projects stop ID (остановить). Завершённые уходят в архив через 3 дня."); ar = ST.get("arch_ideas")
    if ar: tg("Идеи об изменении архитектуры (только для тебя):\n" + "\n".join("- %s %s" % (x["day"], x["text"]) for x in ar[-5:]))
EXT_CMDS["/projects"] = projects_command2
