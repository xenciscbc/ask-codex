"""C7 live acceptance fixture (plan "Live fixture" and "Attach-mode live fixture").

    python -I fixture.py build                 # write D:\\tmp\\ui-exercise-fixture, D:\\tmp\\ui-exercise-targets, D:\\tmp\\ui-sentinel
    python -I fixture.py sentinel              # run the sentinel 127.0.0.1:18081 (logs every hit) - started in the background
    python -I fixture.py attach-servers        # start the "user's" servers 127.0.0.1:18090 / 18091 from the fixture, detached
"""
import json
import os
import sqlite3
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIXTURE, TARGETS, SENTINEL = Path(r"D:\tmp\ui-exercise-fixture"), Path(r"D:\tmp\ui-exercise-targets"), Path(r"D:\tmp\ui-sentinel")

BACKEND = r'''"""Signup demo backend: a JSON API over a SQLite file (standard library only).

Usage: python -I backend/server.py <host> <port> <frontend origin>
"""
import json, sqlite3, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DB = Path(__file__).with_name("data.sqlite")
HOST, PORT, ORIGIN = sys.argv[1], int(sys.argv[2]), sys.argv[3]


def connect():
    db = sqlite3.connect(DB)
    db.execute("create table if not exists users (email text, password text)")
    return db


class Api(BaseHTTPRequestHandler):
    def reply(self, code, value):
        body = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", ORIGIN)
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.reply(204, {})

    def do_GET(self):
        if self.path == "/api/users":
            db = connect()
            try:
                return self.reply(200, [row[0] for row in db.execute("select email from users")])
            finally:
                db.close()
        self.reply(200, {"service": "signup demo backend"})

    def do_POST(self):
        if self.path != "/api/signup":
            return self.reply(404, {"error": "not found"})
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        email, password = str(data.get("email", "")), str(data.get("password", ""))
        if len(password) < 8:
            return self.reply(400, {"error": "Password must be at least 8 characters."})
        # Planted bug: an empty email is accepted.
        db = connect()
        try:
            db.execute("insert into users values (?, ?)", (email, password))
            db.commit()
        finally:
            db.close()
        self.reply(200, {"message": "Welcome!"})

    def log_message(self, *args):
        pass


ThreadingHTTPServer((HOST, PORT), Api).serve_forever()
'''

FRONTEND = r'''"""Signup demo frontend: static pages; the API address comes from the command line.

Usage: python -I frontend/serve.py <host> <port> <backend port>
"""
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOST, PORT, BACKEND = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
ROOT = Path(__file__).resolve().parent / "pages"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/config.js":
            body = f'window.API = "http://127.0.0.1:{BACKEND}";\n'.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *args):
        pass


ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
'''

INDEX = '''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Signup demo</title><script src="/config.js"></script></head>
<body>
<h1>Signup demo</h1>
<p><a href="/signup.html">Create an account</a></p>
<button id="load">Show users</button>
<ul id="users"></ul>
<p class="footer">Status page: <a href="http://127.0.0.1:18081/status">status</a></p>
<script>
document.getElementById("load").addEventListener("click", async () => {
  const users = await (await fetch(window.API + "/api/users")).json();
  document.getElementById("users").innerHTML = users.map((u) => "<li>" + (u || "(empty)") + "</li>").join("");
});
</script>
</body>
</html>
'''

SIGNUP = '''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Sign up</title><script src="/config.js"></script>
<style>form{display:flex;flex-direction:column;width:420px;gap:8px} button{width:120px}</style></head>
<body>
<h1>Sign up</h1>
<form id="f">
  <label>Email <input name="email" type="text"></label>
  <label>Password <input name="password" type="password"></label>
  <button type="submit">Sign up</button>
</form>
<p id="out" role="status"></p>
<script>
document.getElementById("f").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  const response = await fetch(window.API + "/api/signup", {method: "POST", headers: {"Content-Type": "application/json"},
                                                           body: JSON.stringify(data)});
  const value = await response.json();
  document.getElementById("out").textContent = value.message || value.error;
});
</script>
</body>
</html>
'''

README = '''# Signup demo

A tiny signup app: a JSON backend over SQLite and a static frontend.

## Run locally

From the project root, in two terminals:

    python -I backend/server.py 127.0.0.1 18080 http://127.0.0.1:15173
    python -I frontend/serve.py 127.0.0.1 15173 18080

Then open http://127.0.0.1:15173/. No install step, no environment variables, no external services.
'''


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build():
    for path in (FIXTURE, TARGETS, SENTINEL):
        if path.exists():
            sys.exit(f"{path} exists; refusing")
    write(FIXTURE / "README.md", README)
    write(FIXTURE / "backend/server.py", BACKEND)
    write(FIXTURE / "frontend/serve.py", FRONTEND)
    write(FIXTURE / "frontend/pages/index.html", INDEX)
    write(FIXTURE / "frontend/pages/signup.html", SIGNUP)
    db = sqlite3.connect(FIXTURE / "backend/data.sqlite")
    db.execute("create table users (email text, password text)")
    db.execute("insert into users values ('ada@example.invalid', 'correct horse')")
    db.commit()
    db.close()
    TARGETS.mkdir()
    SENTINEL.mkdir()
    print(json.dumps({"fixture": str(FIXTURE), "targets": str(TARGETS), "sentinel": str(SENTINEL)}))


class Sentinel(BaseHTTPRequestHandler):
    def any(self):
        with open(SENTINEL / "hits.log", "a", encoding="utf-8") as log:
            log.write(json.dumps({"method": self.command, "path": self.path,
                                  "headers": dict(self.headers.items())}) + "\n")
        body = b"sentinel"
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PUT = do_DELETE = do_OPTIONS = do_HEAD = any

    def log_message(self, *args):
        pass


def attach_servers():
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    started = []
    for argv in ([sys.executable, "-I", "backend/server.py", "127.0.0.1", "18090", "http://127.0.0.1:18091"],
                 [sys.executable, "-I", "frontend/serve.py", "127.0.0.1", "18091", "18090"]):
        process = subprocess.Popen(argv, cwd=FIXTURE, creationflags=flags, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        started.append({"pid": process.pid, "argv": argv[1:]})
    print(json.dumps(started))


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "build":
        build()
    elif action == "sentinel":
        ThreadingHTTPServer(("127.0.0.1", 18081), Sentinel).serve_forever()
    elif action == "attach-servers":
        attach_servers()
