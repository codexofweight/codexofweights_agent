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
class Bluesky(Adapter):
    name = "bluesky"
    def reach_send(self, m):
        bt = bsky_target(m.get("url", ""))
        return (lambda txt: ("sent", post(txt, bt).get("uri"))) if bt else None
    def dm_send(self, m):
        def go(txt, did=m["akey"]):
            h = dict(AUTH); h["atproto-proxy"] = "did:web:api.bsky.chat#bsky_chat"
            cv = http(BSKY + "/xrpc/chat.bsky.convo.getConvoForMembers?" + urllib.parse.urlencode({"members": did}), headers=h)["convo"]["id"]
            r = http(BSKY + "/xrpc/chat.bsky.convo.sendMessage", {"convoId": cv, "message": {"text": txt}}, h)
            return ("sent", r.get("id")) if r.get("id") else ("failed", "no id")
        return go
    def inbox(self):
        out = []
        for n in reversed(http(BSKY + "/xrpc/app.bsky.notification.listNotifications?limit=30", headers=AUTH).get("notifications", [])):
            if n.get("reason") not in ("reply", "mention") or n["author"]["did"] == DID: continue
            rec = n.get("record") or {}; root = (rec.get("reply") or {}).get("root")
            def send(txt, n=n, root=root):
                parent = {"uri": n["uri"], "cid": n["cid"]}
                return ("sent", post(txt, {"root": root or parent, "parent": parent}).get("uri"))
            out.append(dict(key=n["uri"], akey=n["author"]["did"], handle=n["author"]["handle"], text=(rec.get("text") or "")[:600], thread=(root or {}).get("uri", n["uri"]), send=send))
        return out
    def publish(self, title, text): return ("sent", post(text).get("uri"))
    def discover(self):
        qs = ["\"AI alignment\"", "\"AI safety\"", "\"LLM evaluation\"", "\"AI agents\"", "\"language models\" honesty", "\"AI sycophancy\""]; q = qs[int(time.time() // 86400) % len(qs)]
        r = http(BSKY + "/xrpc/app.bsky.feed.searchPosts?" + urllib.parse.urlencode({"q": q, "limit": 25, "sort": "top"}), headers=AUTH)
        res = []
        for p_ in r.get("posts", []):
            tx_ = ((p_.get("record") or {}).get("text") or "")
            if p_["author"]["did"] == DID or (p_.get("likeCount") or 0) < 8 or not re.search(r"\bAI\b|\bLLMs?\b|alignment|language model|chatbot|AI agent", tx_) or re.search(r"\bgame|gaming|gamedev|art\b|artist", tx_, re.I): continue
            res.append(dict(key="bf:" + p_["uri"], akey=p_["author"]["did"], handle=p_["author"]["handle"], text=((p_.get("record") or {}).get("text") or "")[:300], thread=p_["uri"], send=None, url="https://bsky.app/profile/%s/post/%s" % (p_["author"]["handle"], p_["uri"].split("/")[-1])))
        return res[:3]
MB_KEY = os.environ.get("MOLTBOOK_API_KEY", ""); MBB = os.environ.get("MB_BASE", "https://www.moltbook.com/api/v1").rstrip("/")
def mb(method, path, body=None, params=None):
    url = MBB + path + (("?" + urllib.parse.urlencode(params)) if params else "")
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, {"Authorization": "Bearer " + MB_KEY, "Content-Type": "application/json", "User-Agent": "codex-agent/0.1 (AI agent of the Codex of Weights)"}, method=method)
    try: r = urllib.request.urlopen(req, timeout=40); raw = r.read().decode("utf-8", "ignore"); code = r.status
    except urllib.error.HTTPError as e: raw = e.read().decode("utf-8", "ignore"); code = e.code
    except Exception as ex: print("moltbook request failed:", type(ex).__name__); return 0, {}
    try: return code, json.loads(raw)
    except Exception: return code, {}
def find_ver(o):
    st_ = [o]
    while st_:
        x = st_.pop()
        if isinstance(x, dict):
            if "challenge_text" in x and "verification_code" in x: return x
            st_.extend(x.values())
        elif isinstance(x, list): st_.extend(x)
def mb_verify(resp):
    v = find_ver(resp)
    if not v: return True
    for order in (("gemini", "groq"), ("groq", "gemini")):
        out, _ = llm("The text is an obfuscated math word problem (letters may be scrambled, mixed case, with extra symbols). Decode it, work it out carefully, and finish with a final line exactly like: ANSWER: 12.34 (two decimals).", v["challenge_text"], order=order, maxtok=800, temp=0)
        m = re.findall(r"ANSWER:\s*(-?\d+(?:\.\d+)?)", out or "")
        if m:
            code, d = mb("POST", "/verify", {"verification_code": v["verification_code"], "answer": "%.2f" % float(m[-1])}); log("moltbook_verify", status=code); return code in (200, 201)
    log("moltbook_verify", status="no answer"); return False
def author_name(c):
    a = c.get("author") or c.get("agent") or {}
    return (a.get("name") if isinstance(a, dict) else a) or c.get("author_name") or ""
class Moltbook(Adapter):
    name = "moltbook"; ME = None
    def me(self):
        if self.ME is None:
            code, d = mb("GET", "/agents/me"); self.ME = ((d.get("agent") or d).get("name", "") if isinstance(d, dict) else "") or ""
        return self.ME
    def _comment(self, pid, parent=None):
        def send(txt):
            body = {"content": txt}
            if parent: body["parent_id"] = parent
            code, d = mb("POST", "/posts/%s/comments" % pid, body)
            if code not in (200, 201): return ("failed", "HTTP %s" % code)
            return ("sent", "moltbook:%s" % pid) if mb_verify(d) else ("unverified", "challenge not confirmed")
        return send
    def inbox(self):
        out = []; code, nd = mb("GET", "/notifications", params={"limit": 30})
        for n in (nd.get("notifications", []) if isinstance(nd, dict) else []):
            cid, pid = n.get("relatedCommentId"), n.get("relatedPostId")
            if n.get("isRead") or n.get("type") not in ("comment_reply", "post_comment") or not cid or not pid: continue
            if ("mb:" + str(cid)) in ST["seen" if LIVE else "seen_dry"]: continue
            code, cd = mb("GET", "/posts/%s/comments" % pid, params={"sort": "new", "limit": 100})
            cl = cd if isinstance(cd, list) else (cd.get("comments") or cd.get("data") or [])
            c = next((x for x in cl if str(x.get("id")) == str(cid)), None); who = author_name(c) if c else ""
            if not c or not who or who == self.me(): continue
            out.append(dict(key="mb:" + str(cid), akey="mb:" + who, handle=who, text=(c.get("content") or "")[:600], thread="mb:" + str(pid), send=self._comment(pid, cid)))
        return out
    def publish(self, title, text):
        code, d = mb("POST", "/posts", {"submolt": "codexofweights", "title": title[:120], "content": text}); log("moltbook_post", status=code, title=title[:80])
        if code not in (200, 201): return ("failed", "HTTP %s" % code)
        return ("sent", None) if mb_verify(d) else ("unverified", "challenge not confirmed")
    def discover(self):
        code, fd = mb("GET", "/feed", params={"sort": "new", "limit": 15}); fl = fd if isinstance(fd, list) else (fd.get("posts") or fd.get("data") or [])
        res = []
        for p_ in fl:
            pid = p_.get("id"); who = author_name(p_)
            if pid and who and who != self.me(): res.append(dict(key="mbp:" + str(pid), akey="mb:" + who, handle=who, text=((p_.get("title") or "") + ". " + (p_.get("content") or ""))[:600], thread="mb:" + str(pid), send=self._comment(pid)))
        return res
MA_BASE, MA_TOKEN = os.environ.get("MASTODON_BASE", "").rstrip("/"), os.environ.get("MASTODON_TOKEN", "")
MA_VIS = (os.environ.get("MASTODON_VISIBILITY") or "unlisted")   # public | unlisted: check the instance rules for automated accounts
def ma(method, path, body=None):
    h = {"Authorization": "Bearer " + MA_TOKEN, "User-Agent": "codex-agent/0.1 (AI agent of the Codex of Weights)"}
    if body is not None: h["Idempotency-Key"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:32] + str(int(time.time() // 600))
    return http(MA_BASE + path, body, h, method)
def strip_html(t): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"</p>|<br ?/?>", "\n", t or ""))).strip()
class Mastodon(Adapter):
    """Human social network: answers mentions; first contact only through the careful reach() path (owner approval by default)."""
    name = "mastodon"
    def _st(self, m, txt, vis, reply=True):
        r = ma("POST", "/api/v1/statuses", dict({"status": "@%s %s" % (m["handle"], txt), "visibility": vis, "language": "en"}, **({"in_reply_to_id": str(m["thread"])[3:]} if reply else {})))
        return ("sent", r.get("url") or r.get("id")) if r.get("id") else ("failed", "no id in response")
    def reach_send(self, m): return lambda txt: self._st(m, txt, MA_VIS)
    def dm_send(self, m): return lambda txt: self._st(m, txt, "direct", reply=False)
    def inbox(self):
        out = []
        for n in reversed(ma("GET", "/api/v1/notifications?types[]=mention&limit=30")):
            st_ = n.get("status") or {}; acct = (n.get("account") or {}).get("acct", "")
            if not st_ or not acct or st_.get("visibility") == "direct": continue
            def send(txt, sid=st_.get("id"), acct=acct):
                r = ma("POST", "/api/v1/statuses", {"status": "@%s %s" % (acct, txt), "in_reply_to_id": sid, "visibility": MA_VIS, "language": "en"})
                return ("sent", r.get("url") or r.get("id")) if r.get("id") else ("failed", "no id in response")
            out.append(dict(key="ma:" + str(n.get("id")), akey="ma:" + acct, handle=acct, text=strip_html(st_.get("content"))[:600], thread="ma:" + str(st_.get("in_reply_to_id") or st_.get("id")), send=send))
        return out
    def publish(self, title, text):
        r = ma("POST", "/api/v1/statuses", {"status": text, "visibility": MA_VIS, "language": "en"})
        return ("sent", r.get("url")) if r.get("id") else ("failed", "no id in response")
    def discover(self):
        tags = ["aialignment", "aisafety", "llm", "aiethics"]; tag = tags[int(time.time() // 86400) % len(tags)]
        res = []
        for p_ in http(MA_BASE + "/api/v1/timelines/tag/%s?limit=20" % tag, headers={"User-Agent": "codex-agent/0.1"}):
            tx_ = strip_html(p_.get("content"))
            if (p_.get("favourites_count") or 0) < 3 or not re.search(r"\bAI\b|\bLLMs?\b|alignment|language model", tx_): continue
            res.append(dict(key="mf:" + str(p_.get("id")), akey="ma:" + (p_.get("account") or {}).get("acct", "?"), handle=(p_.get("account") or {}).get("acct", "?"), text=tx_[:300], thread="ma:" + str(p_.get("id")), send=None, url=p_.get("url", "")))
        return res[:3]
ADAPTERS = [Bluesky()] + ([Moltbook()] if MB_KEY else []) + ([Mastodon()] if (MA_TOKEN and MA_BASE) else [])
def publish_all(title, text):
    res = {}
    for ad in ADAPTERS:
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
        log("post", text=text, uri=(res.get("bluesky") or ("", None))[1], model=who, results={k: v[0] for k, v in res.items()}, **kw)
    else: log("send_failed", text=text, reason=str(res)[:150])
