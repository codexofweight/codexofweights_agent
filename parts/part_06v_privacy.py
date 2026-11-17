# ---- privacy of third parties in the PUBLIC logs (2026-11-17): logs/actions.jsonl and the Actions run log are public ----
# VK users are identified by a numeric id that opens their profile, and VK messages are private: so for VK the log keeps a hash of the handle and no text of the other person.
_log_before_privacy = log
def log(kind, **kw):
    try:
        to = str(kw.get("to") or kw.get("handle") or "")
        if re.match(r"vk\d+$", to) or str(kw.get("uri") or "").startswith(("vkm:", "vk:dm")):
            for k in ("to", "handle"):
                if k in kw: kw[k] = _h(kw[k])
            for k in ("their", "dm_text", "question"):
                if k in kw: kw[k] = "[not logged]"
            if str(kw.get("uri") or "").startswith("vkm:"): kw["text"] = "[private message reply, not logged]"
    except Exception: pass
    return _log_before_privacy(kind, **kw)
