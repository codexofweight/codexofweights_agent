# ---- platform: Moltbook ----
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
register(Moltbook, ("MOLTBOOK_API_KEY",))
