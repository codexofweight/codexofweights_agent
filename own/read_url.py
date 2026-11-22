API_VERSION = 1
# /read <https URL>: plain text of a public page (first 1500 characters). All safety checks (https only, no private addresses, size cap) are done by api.fetch.
def _read_handler(*args):
    raw = args[-1] if args and isinstance(args[-1], str) else ""      # the dispatcher passes (lowercased text, ORIGINAL text): URLs are case-sensitive
    parts = raw.split(None, 1)
    if len(parts) < 2:
        msg = "Usage: /read <https URL>"
        api.say(msg)
        return msg
    url = parts[1].strip()
    if not url.lower().startswith("https://"):
        msg = "Invalid or unsafe URL."
        api.say(msg)
        return msg
    try:
        page = api.fetch(url, max_bytes=200000)
    except Exception:
        msg = "Failed to fetch URL."
        api.say(msg)
        return msg
    text = api.plain(page)[:1500] or "The page has no readable text."
    api.say(text)
    return text

api.command("/read", _read_handler)
