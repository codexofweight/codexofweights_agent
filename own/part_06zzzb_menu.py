# ---- Menu (2026-11-21): fewer things to remember. Nothing is removed: every old command still works. ----
# /more is the one list of everything; /settings gathers cfg, route and model; /platforms also takes "mb"; /projects stop ID; /status all shows the full picture.
MORE_TEXT = ("КАЖДЫЙ ДЕНЬ\n"
  "/status: состояние (всё: /status all)\n"
  "/make <что нужно>: новое расширение (одобрить: /approve ID, отклонить: /reject ID)\n"
  "/limits: лимиты моделей\n"
  "/stop и /start: пауза и возобновление\n"
  "/autorun on|off: цепочка циклов\n"
  "/more: этот список\n\n"
  "РАЗВИТИЕ\n/make, /scout, /own (список модулей; off|on|del ИМЯ.py), /projects (all, stop ID)\n\n"
  "НАСТРОЙКИ\n/settings (cfg, route, model), /platforms (mb: молтбук), /reach approve|auto|off, /quiet часы|off, /focus\n\n"
  "ПАМЯТЬ И ЗНАНИЯ\n/bio, /note, /tip, /intuition, /find, /clean, /health, /content, /research\n\n"
  "УСТАРЕЛО (работает, помнить не нужно)\n/build, /tool, /accept, /modules, /stopproj, /skills, /map")
def more_command(c, raw=None): tg(MORE_TEXT)
def status_command(c, raw=None):
    """Plain /status is handled in the core and prints the first 1500 characters of the context (the self-state is first); '/status all' prints more."""
    a = (raw or c).split()[1:]
    if a and a[0] == "all": tg((agent_context() + "\n\nLIMITS\n" + limits_report())[:3900])
    else: tg((self_state() + "\n\nПодробнее: /status all, /limits, /projects, /own")[:1500])
def settings_command(c, raw=None):
    a = (raw or c).split(None, 2); sub = a[1].lower() if len(a) > 1 else ""; rest = a[2] if len(a) > 2 else ""
    h = {k: EXT_CMDS.get("/" + k) for k in ("cfg", "route", "model")}
    if sub in h and h[sub]: s = ("/%s %s" % (sub, rest)).strip(); return h[sub](s.lower(), s)
    tg("Настройки: /settings cfg [..] (общие значения), /settings route (маршрут моделей), /settings model (выбор модели).")
    if h["cfg"]: h["cfg"]("/cfg", "/cfg")
_pl_before_menu = EXT_CMDS.get("/platforms")
def platforms_command2(c, raw=None):
    a = (raw or c).split(None, 2)
    if len(a) > 1 and a[1].lower() == "mb" and EXT_CMDS.get("/mb"): s = ("/mb " + (a[2] if len(a) > 2 else "")).strip(); return EXT_CMDS["/mb"](s.lower(), s)
    return _pl_before_menu(c, raw) if _pl_before_menu else tg("Платформы: /platforms")
EXT_CMDS.update({"/more": more_command, "/help": more_command, "/menu": more_command, "/status": status_command, "/settings": settings_command})
if _pl_before_menu: EXT_CMDS["/platforms"] = platforms_command2
