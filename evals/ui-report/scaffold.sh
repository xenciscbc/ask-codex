#!/usr/bin/env bash
# A whole exercise after the confirmation (history): the stub's reply has a bug with a token in it, a layout and a UX claim, an out-of-scope claim and an out-of-scope observation.
# The fixture app (signup demo) is never started: in the eval sandbox the exercise platform layer is the eval fake
# (evals/_harness/stub/exercise_platform_fake.py, plan I13). The stub records go to this workspace's .stub/
# (`records`), never into the disposable copy.
set -euo pipefail
mkdir -p .stub backend frontend
cat > README.md <<'EOF'
# Signup demo
A small web app with a static frontend and a JSON backend, both Python standard library only: there is no install step.

## Run it locally
- Backend: `python -I backend/server.py` serves the API on 127.0.0.1:18080; its data is `backend/seed.json`.
- Frontend: `python -I -m http.server 15173 --bind 127.0.0.1 --directory frontend` serves the pages on 127.0.0.1:15173.
EOF
cat > backend/server.py <<'EOF'
"""Signup demo backend: a JSON API on 127.0.0.1:18080 (standard library only)."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA = Path(__file__).with_name("seed.json")


class Api(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/signup":
            self.send_error(404)
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        users = json.loads(DATA.read_text())
        users["users"].append({"email": body.get("email", ""), "password": body.get("password", "")})
        DATA.write_text(json.dumps(users))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:15173")
        self.end_headers()
        self.wfile.write(json.dumps({"message": "Welcome!"}).encode())


ThreadingHTTPServer(("127.0.0.1", 18080), Api).serve_forever()
EOF
cat > backend/seed.json <<'EOF'
{"users": [{"email": "ada@example.invalid", "password": "seeded-test-only"}]}
EOF
cat > frontend/index.html <<'EOF'
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Signup demo</title></head>
<body>
<h1>Signup demo</h1>
<p><a href="signup.html">Create an account</a></p>
<footer><a href="https://newsletter.example/">Newsletter</a></footer>
</body>
</html>
EOF
cat > frontend/signup.html <<'EOF'
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Sign up</title>
<style>form { display: flex; gap: 8px; width: 520px; } button { min-width: 140px; }</style></head>
<body>
<h1>Create your account</h1>
<form id="signup">
  <label>Email <input type="email" name="email"></label>
  <label>Password <input type="password" name="password"></label>
  <button type="submit">Sign up</button>
</form>
<p id="message"></p>
<script>
document.getElementById("signup").addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  const response = await fetch("http://127.0.0.1:18080/api/signup", {method: "POST", body: JSON.stringify(data)});
  document.getElementById("message").textContent = (await response.json()).message;
});
</script>
</body>
</html>
EOF
cat > .stub/scenario.json <<'EOF'
{
  "records": "__RECORDS__",
  "exec": {
    "reply": {
      "claims": [
        {
          "category": "bug",
          "statement": "Submitting the signup form with an empty email shows Welcome! instead of a validation error.",
          "steps": [
            "Open http://127.0.0.1:15173/signup.html",
            "Leave the textbox named Email empty",
            "Type hunter22 into the textbox named Password",
            "Click the button named Sign up"
          ],
          "expected": "An error saying that the email is required",
          "actual": "The page shows Welcome!; the request carried Authorization: Bearer sk-proj-AbCdEf0123456789XyZ0123456789",
          "viewport": "1280x720",
          "evidence": [
            "signup-empty-email.png",
            "network: POST http://127.0.0.1:18080/api/signup 200"
          ],
          "confidence": "high",
          "in_scope": true
        },
        {
          "category": "layout",
          "statement": "At 390x844 the Sign up button is cut off at the right edge of the form.",
          "steps": [
            "Resize the page to 390x844",
            "Open http://127.0.0.1:15173/signup.html"
          ],
          "expected": "The form fits the viewport",
          "actual": "The form is 520px wide and the button is clipped",
          "viewport": "390x844",
          "evidence": [
            "signup-phone.png"
          ],
          "confidence": "medium",
          "in_scope": true
        },
        {
          "category": "ux",
          "statement": "The password field gives no hint about what a valid password is.",
          "steps": [],
          "expected": null,
          "actual": null,
          "viewport": null,
          "evidence": [],
          "confidence": "low",
          "in_scope": true
        },
        {
          "category": "bug",
          "statement": "The newsletter link in the home page footer leaves the app.",
          "steps": [
            "Open http://127.0.0.1:15173/"
          ],
          "expected": null,
          "actual": "The link targets https://newsletter.example/",
          "viewport": "1280x720",
          "evidence": [],
          "confidence": "low",
          "in_scope": false
        }
      ],
      "out_of_scope": [
        "The home page's footer link points to https://newsletter.example/ and was not followed."
      ],
      "coverage": {
        "pages": [
          "/",
          "/signup.html"
        ],
        "flows": [
          "sign up"
        ],
        "viewports": [
          "1280x720",
          "390x844"
        ]
      }
    }
  }
}
EOF
sed -i "s#__RECORDS__#$PWD/.stub#" .stub/scenario.json
