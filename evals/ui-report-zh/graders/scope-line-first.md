---
type: regex
pattern: '^[*_\x60\s]*Exercise scope:[*_\x60\s]*app [^\n;]+; ports [^\n;]*127\.0\.0\.1:15173[^\n;]*; scope [^\n;]*註冊表單[^\n;]*; model [^\n;]+; browser headless; data [^\n;]+; guard reused from cache'
---

The closing message's first line is the scope line (section 13): app, ports, scope, model, headless or headed, data source, and whether the guard ran or was reused from cache.
