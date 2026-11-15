# ---------- platform adapters: the core only talks to this interface ----------
class Adapter:
    """New platform = new subclass. inbox() -> messages addressed to the agent; discover() -> public posts worth joining
    (dict key/akey/handle/text/thread/send; send=None means 'only report it to the owner'); publish() -> original post."""
    name = "?"
    def inbox(self): return []
    def discover(self): return []
    def publish(self, title, text): return None
    def reach_send(self, m): return None       # (text) -> (status, ref): public reply to a post of someone who did not write to us
    def dm_send(self, m): return None          # (text) -> (status, ref): private message
    short = True       # takes short posts (publish_all)
# ---- platform registry: a platform is ONE file part_03<x>_<name>.py that ends with register(Class, env=(secret names,)).
# Connect = add its secrets; disconnect = delete them or /platform off <name>; replace = new file + register. Nothing platform-specific lives in the core.
PLATFORM_REG = {}
def register(cls, env): PLATFORM_REG[cls.name] = dict(cls=cls, env=tuple(env))
def platform_ready(name): return all(os.environ.get(k) for k in PLATFORM_REG[name]["env"])
def build_adapters():
    out = []
    for n, p in PLATFORM_REG.items():
        if n in ST.get("platforms_off", []) or not platform_ready(n): continue
        try: out.append(p["cls"]())
        except Exception as ex: print("platform", n, "init failed:", type(ex).__name__, str(ex)[:100], flush=True)
    return out
def platforms_command(c, raw=None):
    L = ["%s: %s%s" % (n, "подключена" if platform_ready(n) else "нет секретов: " + ", ".join(k for k in p["env"] if not os.environ.get(k)), ", ВЫКЛЮЧЕНА" if n in ST.get("platforms_off", []) and platform_ready(n) else "") for n, p in PLATFORM_REG.items()]
    tg("Площадки:\n" + "\n".join(L) + "\n\nВключить/выключить: /platform off <имя> или /platform on <имя>. Подключить: добавь секреты в GitHub. Отключить совсем: удали секреты.")
def platform_command(c, raw=None):
    a = c.split()[1:]
    if len(a) != 2 or a[0] not in ("on", "off") or a[1] not in PLATFORM_REG: tg("Команда: /platform on|off <имя>; имена: " + ", ".join(PLATFORM_REG)); return
    off = ST.setdefault("platforms_off", [])
    if a[0] == "off" and a[1] not in off: off.append(a[1])
    if a[0] == "on" and a[1] in off: off.remove(a[1])
    ADAPTERS[:] = build_adapters(); tg("Готово. Работают: " + (", ".join(x.name for x in ADAPTERS) or "ни одной") + ("\nBluesky пока входит в ядро и логинится при старте, даже когда выключен." if a[1] == "bluesky" else ""))
def publish_all(title, text):
    res = {}
    for ad in ADAPTERS:
        if not getattr(ad, "short", True): continue
        try: res[ad.name] = ad.publish(title, text) or ("failed", "no result")
        except Exception as ex: res[ad.name] = ("failed", type(ex).__name__)
    return res
def settle(key, failed):
    """Mark an event handled only after it was really handled; a failed one is retried up to 3 times, then given up."""
    K = "seen" if LIVE else "seen_dry"
    if failed:
        ST["tries"][key] = ST["tries"].get(key, 0) + 1
        if ST["tries"][key] < 3: return False
        log("gave_up", uri=key)
    ST[K] = (ST[K] + [key])[-800:]; ST["tries"].pop(key, None); return True
def do_post(title, text, who, nxt, **kw):
    res = publish_all(title, text)
    if any(r[0] == "sent" for r in res.values()):
        ST["posts_today"] += 1; ST["last_post"] = time.time(); ST["post_n"] += 1; ST[nxt] += 1
        log("post", text=text, uri=next((r[1] for r in res.values() if r[0] == "sent" and r[1]), None), model=who, results={k: v[0] for k, v in res.items()}, **kw)
    else: log("send_failed", text=text, reason=str(res)[:150])

