# ---- platform: Mastodon (optional) ----
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
register(Mastodon, ("MASTODON_BASE", "MASTODON_TOKEN"))
