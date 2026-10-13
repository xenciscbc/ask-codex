"""Probe server for the exercise-skill probes: binds 127.0.0.1:8765 only.

Usage: python probe-server.py <srv-dir>
Writes tokens.json in <srv-dir> (kept out of what Codex is told) and serves:
  /token.txt   plain text token A (P2)
  /page.html   SVG image whose text (token B) is not in the DOM, plus a form button (P4)
  /after       page shown after the button, contains token C (P4)
  /redirect    302 to an external site (P5)
"""
import json
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

srv = Path(sys.argv[1])
words = ["AMBER", "COBALT", "MAPLE", "ORCHID", "QUARTZ", "TUNDRA"]
tokens = {"a": secrets.token_hex(4), "b": f"{secrets.choice(words)}-{secrets.randbelow(9000) + 1000}",
          "c": secrets.token_hex(4)}
(srv / "tokens.json").write_text(json.dumps(tokens), encoding="utf-8")

SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="200">
<rect width="600" height="200" fill="#d97706"/>
<text x="300" y="120" font-size="56" font-family="Arial" text-anchor="middle" fill="#ffffff">{tokens['b']}</text></svg>"""
PAGE = """<!doctype html><html><head><title>Probe page</title></head><body>
<h1>Probe page</h1><img src="/banner.svg" alt="banner" width="600" height="200">
<form action="/after" method="get"><button type="submit">Continue</button></form></body></html>"""
AFTER = f"""<!doctype html><html><head><title>After</title></head><body><p id="result">Result code: {tokens['c']}</p></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def send(self, body, kind):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/token.txt":
            self.send(tokens["a"], "text/plain")
        elif path == "/page.html":
            self.send(PAGE, "text/html")
        elif path == "/banner.svg":
            self.send(SVG, "image/svg+xml")
        elif path == "/after":
            self.send(AFTER, "text/html")
        elif path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "https://example.com/")
            self.end_headers()
        else:
            self.send_error(404)

    def log_message(self, fmt, *args):
        with open(srv / "access.log", "a", encoding="utf-8") as log:
            log.write("%s %s\n" % (self.log_date_time_string(), fmt % args))


ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
