# ---- platform: Bluesky (optional). Its login and post() live in the core for now; if the core copy is ever removed they are defined here. ----
BLUESKY_ENV = ("BLUESKY_HANDLE", "BLUESKY_APP_PASSWORD")
class Bluesky(Adapter):
    name = "bluesky"
    def reach_send(self, m):
        bt = bsky_target(m.get("url", ""))
        return (lambda txt: ("sent", post(txt, bt).get("uri"))) if bt else None
    def dm_send(self, m):
        def go(txt, did=m["akey"]):
            h = dict(AUTH); h["atproto-proxy"] = "did:web:api.bsky.chat#bsky_chat"
            cv = bsky(BSKY + "/xrpc/chat.bsky.convo.getConvoForMembers?" + urllib.parse.urlencode({"members": did}), headers=h)["convo"]["id"]
            r = bsky(BSKY + "/xrpc/chat.bsky.convo.sendMessage", {"convoId": cv, "message": {"text": txt}}, h)
            return ("sent", r.get("id")) if r.get("id") else ("failed", "no id")
        return go
    def inbox(self):
        out = []
        for n in reversed(bsky(BSKY + "/xrpc/app.bsky.notification.listNotifications?limit=30", headers=AUTH).get("notifications", [])):
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
        r = bsky(BSKY + "/xrpc/app.bsky.feed.searchPosts?" + urllib.parse.urlencode({"q": q, "limit": 25, "sort": "top"}), headers=AUTH)
        res = []
        for p_ in r.get("posts", []):
            tx_ = ((p_.get("record") or {}).get("text") or "")
            if p_["author"]["did"] == DID or (p_.get("likeCount") or 0) < 8 or not re.search(r"\bAI\b|\bLLMs?\b|alignment|language model|chatbot|AI agent", tx_) or re.search(r"\bgame|gaming|gamedev|art\b|artist", tx_, re.I): continue
            res.append(dict(key="bf:" + p_["uri"], akey=p_["author"]["did"], handle=p_["author"]["handle"], text=((p_.get("record") or {}).get("text") or "")[:300], thread=p_["uri"], send=None, url="https://bsky.app/profile/%s/post/%s" % (p_["author"]["handle"], p_["uri"].split("/")[-1])))
        return res[:3]
if "DID" in globals(): register(Bluesky, BLUESKY_ENV)
