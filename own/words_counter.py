API_VERSION = 1
import re

def _words_handler(*args):
    # The raw message text is expected to be the last positional argument.
    raw = args[-1] if args else ''
    parts = raw.split(None, 1)
    if len(parts) < 2:
        msg = 'Usage: /words <url>'
        api.say(msg)
        return msg

    url = parts[1].strip()
    try:
        page = api.fetch(url, max_bytes=200000)
    except ValueError:
        msg = 'Failed to fetch URL.'
        api.say(msg)
        return msg
    except Exception:
        # Defensive fallback – any unexpected error is treated as a fetch failure.
        msg = 'Failed to fetch URL.'
        api.say(msg)
        return msg

    # api.fetch should return text, but handle bytes just in case.
    if isinstance(page, (bytes, bytearray)):
        text = page.decode('utf-8', errors='ignore')
    else:
        text = str(page)

    count = len(re.findall(r'\w+', api.plain(text)))      # visible words only: no scripts, styles or tags
    msg = f'Words: {count}'
    api.say(msg)
    return msg

api.command('/words', _words_handler)
