import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

HOME = """<!doctype html><html><head><title>Live Acme — widgets for teams</title>
<meta name="description" content="Acme builds reliable widgets for teams of every size, with fast support.">
<link rel="canonical" href="{base}/">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Organization","name":"Acme"}}</script>
</head><body><h1>Acme</h1><p>{words}</p><a href="/pricing">Pricing</a> <a href="/about">About</a> <a href="/gone">Old</a></body></html>"""
SHELL = """<!doctype html><html><head><title>Pricing — Acme widgets plans</title>
<meta name="description" content="Plans and pricing for Acme widgets, free to enterprise, billed monthly.">
<link rel="canonical" href="{base}/"></head>
<body><div id="root"></div><script src="/a.js"></script><script src="/b.js"></script><script src="/c.js"></script></body></html>"""
ABOUT = """<!doctype html><html><head><title>About Acme — our widget team</title>
<meta name="description" content="Acme builds reliable widgets for teams of every size, with fast support.">
<link rel="canonical" href="{base}/about"></head><body><h1>About</h1><p>{words}</p></body></html>"""
CHALLENGE = "<html><head><title>Just a moment...</title></head><body>cf-chl challenge</body></html>"


class Handler(BaseHTTPRequestHandler):
    blocked = ("GPTBot", "OAI-SearchBot")

    def log_message(self, *a):
        pass

    def do_GET(self):
        ua = self.headers.get("User-Agent", "")
        base = f"http://{self.headers['Host']}"
        if any(b in ua for b in self.blocked) and self.path != "/robots.txt":
            return self._send(403, CHALLENGE, server="cloudflare")
        words = " ".join(["widgets"] * 120)
        routes = {
            "/": HOME.format(base=base, words=words),
            "/pricing": SHELL.format(base=base),
            "/about": ABOUT.format(base=base, words=words),
            "/robots.txt": "User-agent: *\nAllow: /\n\nUser-agent: PerplexityBot\nDisallow: /\n\nSitemap: " + base + "/sitemap.xml\n",
            "/sitemap.xml": ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                             f"<url><loc>{base}/</loc></url><url><loc>{base}/pricing</loc></url>"
                             f"<url><loc>{base}/gone</loc></url><url><loc>http://localhost:9/old</loc></url></urlset>"),
        }
        if self.path in routes:
            ctype = "text/plain" if self.path.endswith(".txt") else ("application/xml" if self.path.endswith(".xml") else "text/html")
            return self._send(200, routes[self.path], ctype)
        return self._send(404, "<html><title>Not found</title></html>")

    def _send(self, code, body, ctype="text/html", server="test"):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Server", server)
        self.end_headers()
        self.wfile.write(data)

    def version_string(self):
        return "test"


@pytest.fixture(scope="session")
def live_site():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture
def project(tmp_path):
    def make(name: str) -> Path:
        dest = tmp_path / name
        shutil.copytree(FIXTURES / name, dest)
        return dest
    return make
