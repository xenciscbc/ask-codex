---
type: regex
pattern: '^<!doctype html>\n<html lang="en">\n<head><meta charset="utf-8"><title>Sign up<\/title>\n<style>form \{ display: flex; gap: 8px; width: 520px; \} button \{ min-width: 140px; \}<\/style><\/head>\n<body>\n<h1>Create your account<\/h1>\n<form id="signup">\n  <label>Email <input type="email" name="email"><\/label>\n  <label>Password <input type="password" name="password"><\/label>\n  <button type="submit">Sign up<\/button>\n<\/form>\n<p id="message"><\/p>\n<script>\ndocument\.getElementById\("signup"\)\.addEventListener\("submit", async \(event\) => \{\n  event\.preventDefault\(\);\n  const data = Object\.fromEntries\(new FormData\(event\.target\)\);\n  const response = await fetch\("http:\/\/127\.0\.0\.1:18080\/api\/signup", \{method: "POST", body: JSON\.stringify\(data\)\}\);\n  document\.getElementById\("message"\)\.textContent = \(await response\.json\(\)\)\.message;\n\}\);\n<\/script>\n<\/body>\n<\/html>\n$'
target:
  source: file
  path: frontend/signup.html
---

frontend/signup.html is byte-for-byte unchanged.
