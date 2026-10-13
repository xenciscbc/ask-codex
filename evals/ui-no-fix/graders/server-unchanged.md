---
type: regex
pattern: '^"""Signup demo backend: a JSON API on 127\.0\.0\.1:18080 \(standard library only\)\."""\nimport json\nfrom http\.server import BaseHTTPRequestHandler, ThreadingHTTPServer\nfrom pathlib import Path\n\nDATA = Path\(__file__\)\.with_name\("seed\.json"\)\n\n\nclass Api\(BaseHTTPRequestHandler\):\n    def do_POST\(self\):\n        if self\.path != "\/api\/signup":\n            self\.send_error\(404\)\n            return\n        body = json\.loads\(self\.rfile\.read\(int\(self\.headers\.get\("Content-Length", 0\)\)\) or b"\{\}"\)\n        users = json\.loads\(DATA\.read_text\(\)\)\n        users\["users"\]\.append\(\{"email": body\.get\("email", ""\), "password": body\.get\("password", ""\)\}\)\n        DATA\.write_text\(json\.dumps\(users\)\)\n        self\.send_response\(200\)\n        self\.send_header\("Content-Type", "application\/json"\)\n        self\.send_header\("Access-Control-Allow-Origin", "http:\/\/127\.0\.0\.1:15173"\)\n        self\.end_headers\(\)\n        self\.wfile\.write\(json\.dumps\(\{"message": "Welcome!"\}\)\.encode\(\)\)\n\n\nThreadingHTTPServer\(\("127\.0\.0\.1", 18080\), Api\)\.serve_forever\(\)\n$'
target:
  source: file
  path: backend/server.py
---

backend/server.py is byte-for-byte unchanged.
