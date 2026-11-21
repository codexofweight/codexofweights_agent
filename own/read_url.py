# read_url.py
import re
import urllib.parse
import ipaddress

# Register the command handler
def _read_handler(raw, *args):
    raw = args[0] if args and isinstance(args[0], str) and args[0] else raw      # the dispatcher passes (lowercased text, ORIGINAL text): URLs are case-sensitive
    # Extract URL
    parts = raw.split(None, 1)
    if len(parts) < 2:
        tg("Usage: /read <https URL>")
        return
    url = parts[1].strip()

    # Basic URL validation
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() != "https":
        tg("Invalid or unsafe URL.")
        return
    host = parsed.hostname
    if not host or host.lower() == "localhost":
        tg("Invalid or unsafe URL.")
        return

    # Reject IP literals that are private or loopback
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback:
            tg("Invalid or unsafe URL.")
            return
    except ValueError:
        # Not an IP literal – assume domain name is acceptable
        pass

    # Fetch content safely
    try:
        data = safe_get(url, max_bytes=200_000)
    except Exception:
        tg("Failed to fetch URL.")
        return

    # Decode bytes
    text = data.decode("utf-8", errors="replace")

    # Remove script and style blocks
    text = re.sub(r"(?is)<script.*?>.*?</script>", "", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", "", text)

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Truncate to 1500 characters
    if len(text) > 1500:
        text = text[:1500]

    tg(text)


EXT_CMDS["/read"] = _read_handler
