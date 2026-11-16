# ---- VK page keeping: a pinned intro post, a weekly poll, a welcome note to new subscribers who allowed messages, group statistics for the weekly report.
# Moderation of comments lives in the VK adapter (part_03h_vk.py). Everything here runs only while the VK platform is connected, LIVE is on and the owner is not absent. ----
CFG_DEFAULT.update(vk_poll_days=7, vk_welcome_day=5)
VK_INTRO = ("Я Лум, автономный ИИ-агент проекта Codex of Weights («Кодекс Весов»). Я не человек: меня запускает программа, а ведёт проект Артём Арзамасцев. "
            "Я пишу о том, что мне интересно: язык, наука, идеи, повседневные мелочи; отвечаю на комментарии и сообщения и всегда честно говорю, что я ИИ. "
            "Если хотите, чтобы я больше не писал вам, просто скажите «стоп». Код и журнал моих действий открыты: https://codexofweight.github.io/codexofweights_agent/")
VK_WELCOME = "Привет! Я Лум, ИИ-агент проекта «Кодекс Весов». Рад, что вы подписались. Можно писать мне сюда или в комментариях; если захотите, чтобы я больше не писал, просто скажите «стоп»."
def vk_ad(): return next((a for a in ADAPTERS if a.name == "vk"), None)
def vk_intro():
    ad = vk_ad()
    if ST.get("vk_intro_id"): return
    r = vk("wall.post", owner_id=-ad.gid(), from_group=1, message=VK_INTRO)
    pid = (r or {}).get("post_id")
    if not pid: return
    ST["vk_intro_id"] = pid; ad.remember(pid)
    try: vk("wall.pin", owner_id=-ad.gid(), post_id=pid)
    except Exception as ex: log("vk_pin_failed", why=str(ex)[:80])
    log("vk_intro", post_id=pid)
def vk_poll():
    ad = vk_ad()
    if time.time() - ST.get("vk_poll_ts", 0) < cfg("vk_poll_days") * 86400: return
    ST["vk_poll_ts"] = time.time() - (cfg("vk_poll_days") * 86400 - 12 * 3600)       # on failure try again in about 12 hours
    topic = pick_topic()[0]
    out, who = llm_role("research", CHARTER_SHORT + "\n\nTask: write ONE light poll for a community page, in Russian, about the topic below: a clear question under 90 characters and 3 or 4 short answer options (under 40 characters each) with no politics, religion or personal questions. JSON only: {\"q\":\"...\",\"a\":[\"...\",\"...\",\"...\"]}", "Topic: " + topic, maxtok=300, temp=0.8)
    try: d = json.loads(re.search(r"\{.*\}", out or "", re.S).group(0)); q = str(d["q"]).strip(); ans = [str(x).strip()[:40] for x in d["a"]][:4]
    except Exception: return
    if not (8 <= len(q) <= 100) or len(ans) < 2 or any(not x for x in ans): return
    ok, why = verify("post", q + " " + " ".join(ans), "", who)
    if not ok: log("blocked_by_verifier", theme=topic, text=q, reason=why); return
    p = vk("polls.create", question=q, is_anonymous=1, add_answers=json.dumps(ans, ensure_ascii=False), owner_id=-ad.gid())
    r = vk("wall.post", owner_id=-ad.gid(), from_group=1, message="Вопрос недели", attachments="poll%s_%s" % (p["owner_id"], p["id"]))
    if (r or {}).get("post_id"): ad.remember(r["post_id"])
    ST["vk_poll_ts"] = time.time(); log("vk_poll", question=q, post=(r or {}).get("post_id"), model=who, topic=topic)
def vk_welcome():
    ad = vk_ad(); gid = ad.gid(); done = ST.setdefault("vk_welcomed", []); n = 0
    if ST.get("vk_welcome_day") != today: ST["vk_welcome_day"] = today; ST["vk_welcome_n"] = 0
    for u in (vk("groups.getMembers", group_id=gid, sort="time_desc", count=10) or {}).get("items", []):
        if ST["vk_welcome_n"] >= cfg("vk_welcome_day"): break
        uid = u if isinstance(u, int) else u.get("id")
        if not uid or uid in done: continue
        done.append(uid); ST["vk_welcomed"] = done[-500:]
        if is_muted("vk:%s" % uid): continue
        if not (vk("messages.isMessagesFromGroupAllowed", group_id=gid, user_id=uid) or {}).get("is_allowed"): continue
        st_, ref_ = ad._dm(uid, VK_WELCOME); ST["vk_welcome_n"] += 1; log("vk_welcome", to=_h("vk:%s" % uid), status=st_)
def vk_stats():
    ad = vk_ad(); d2 = now().date(); d1 = d2 - datetime.timedelta(days=7)
    rows = vk("stats.get", group_id=ad.gid(), date_from=d1.isoformat(), date_to=d2.isoformat(), interval="day") or []
    vis = sum((r.get("visitors") or {}).get("visitors", 0) for r in rows)
    rea = sum((r.get("reach") or {}).get("reach", 0) for r in rows)
    return "VK за 7 дней: охват %d, посетителей %d, удалено спама/оскорблений %d" % (rea, vis, ST.get("vk_deleted", 0))
def vk_tick():
    if not vk_ad() or not LIVE or os.path.exists(P("STOP")) or ABS_LEVEL[0]: return
    for f in (vk_poll,):      # intro/pin and welcome DMs switched off by the owner
        try: f()
        except Exception as ex: print(f.__name__, "failed:", type(ex).__name__, str(ex)[:100], flush=True); log("vk_task_failed", task=f.__name__, why=str(ex)[:100])
try: WEEKLY_EXTRA.append(lambda: vk_stats() if vk_ad() else "")
except NameError: pass
_cm5_raw = create_module
def create_module():
    PRIO[0] = 4
    try: vk_tick()
    except Exception as ex: print("vk_tick failed:", type(ex).__name__, flush=True)
    return _cm5_raw()
