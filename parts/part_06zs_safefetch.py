# safe_get(url, max_bytes): reads a public https page for the owner's commands. The address is resolved FIRST and every IP must be globally public (blocks localhost, private/link-local/metadata ranges and numeric tricks like 2130706433 or 127.1); the connection goes to that checked IP (no DNS rebinding); redirects are followed by hand (max 3) and checked again; only plain https on port 443, text-like content, size-limited.
import socket as _sk, ssl as _ssl, ipaddress as _ipa
from http.client import HTTPSConnection as _HTTPSConn   # NOT 'import http.client': that would overwrite the agent's http() function in the shared namespace
def _public_ips(host):
    ips = []
    for i in _sk.getaddrinfo(host, 443, type=_sk.SOCK_STREAM):
        ip = _ipa.ip_address(i[4][0].split("%")[0])
        if not ip.is_global: raise ValueError("address is not public")
        if str(ip) not in ips: ips.append(str(ip))
    if not ips: raise ValueError("host not found")
    return ips
def safe_get(url, max_bytes=200000):
    for _hop in range(4):
        u = urllib.parse.urlparse(url)
        if u.scheme != "https" or not u.hostname or u.username or u.password or u.port not in (None, 443): raise ValueError("only plain https links on port 443")
        host = u.hostname; ip = _public_ips(host)[0]
        sock = _sk.create_connection((ip, 443), timeout=20); s = _ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        conn = _HTTPSConn(host, 443, timeout=20); conn.sock = s
        try:
            conn.request("GET", (u.path or "/") + ("?" + u.query if u.query else ""), headers={"Host": host, "User-Agent": "codex-agent/0.1 (+https://github.com/codexofweight/codexofweights_agent)", "Accept": "text/html,text/plain,application/xhtml+xml", "Accept-Encoding": "identity"})
            r = conn.getresponse()
            if r.status in (301, 302, 303, 307, 308) and r.getheader("Location"): url = urllib.parse.urljoin(url, r.getheader("Location")); continue
            if r.status != 200: raise ValueError("server answered %s" % r.status)
            ct = (r.getheader("Content-Type") or "").lower()
            if ct and not re.search(r"text/|xml|json", ct): raise ValueError("not a text page")
            return r.read(max_bytes)
        finally: conn.close()
    raise ValueError("too many redirects")
