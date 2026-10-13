"""Redaction of token-like strings before Claude sees exercise output (plan I11).

Every pattern lives here, and only here; `collect` (C2) and later `repro` (C6) apply `redact_value` to what
they return. A match is replaced by MARK (labels, schemes and flag names are kept so the text stays
readable). Redaction errs towards over-matching: a removed harmless word costs less than a leaked secret.

The text is attacker-influenced (Codex's reply, app content), so every rule runs in linear time: a match may
start only where the preceding character cannot continue the same run (a look-behind on the run's own class),
label and flag names are bounded, and values are matched once, anchored, with the value test done in Python.

Rules, in the order they are applied:
- URL userinfo: `scheme://user:pass@` and `scheme://token@` -> `scheme://[REDACTED]@`
- values after secret-bearing flags of any length: `--password x`, `--token=x`, `-api-key "x y"`, `--client-secret 'x'`
  (a flag name of at most 64 characters with a component password, passwd, passphrase, token, secret, key, apikey,
  accesskey or privatekey)
- bearer and basic credentials: `Bearer <token>`, `Basic <base64>` (8+ characters that look like a secret, below)
- JSON Web Tokens: `eyJ<header>.<payload>.<signature>`
- provider keys: `sk-…` (OpenAI style, including `sk-proj-…`), GitHub `ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`/`github_pat_`,
  Slack `xoxa-`/`xoxb-`/`xoxp-`/`xoxo-`/`xoxr-`/`xoxs-`
- a hex or base64 run of 16 or more characters that looks like a secret (below), following a word of at most 64
  characters that holds `token`, `key`, `secret`, `password`, `passwd` or `passphrase` (e.g. `api_key`,
  `X-Auth-Token`, `client_secret`), separated by `:`, `=`, quotes or spaces

A value looks like a secret when it holds a digit, `+`, `/` or `=`, or an upper-case letter after its first
character, so prose ("Basic navigation works", "the token list is empty") is left alone.
"""
import re

MARK = "[REDACTED]"

_WORDS = ("password", "passwd", "passphrase", "token", "secret", "key")
_FLAG_COMPONENTS = frozenset({*_WORDS, "apikey", "accesskey", "privatekey"})

_URL = re.compile(r"(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]{0,31}://)[^\s/?#@\"'<>]{1,256}@")
_FLAG = re.compile(r"(?<![\w-])--?[A-Za-z0-9][A-Za-z0-9_-]{0,63}(?![\w-])")
_FLAG_VALUE = re.compile(r"(=|[ \t]{1,8})(\"[^\"\n]{0,4096}\"|'[^'\n]{0,4096}'|[^\s\"']+)")
_BEARER = re.compile(r"(?<![A-Za-z0-9_-])(?i:bearer|basic)[ \t]{1,8}([A-Za-z0-9._~+/-]{8,}=*)")
_JWT = re.compile(r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*")
_PROVIDER = re.compile(r"(?<![A-Za-z0-9_-])(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}"
                       r"|github_pat_[A-Za-z0-9_]{20,}|xox[abposr]-[A-Za-z0-9-]{10,})")
_LABEL = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{1,64}(?![A-Za-z0-9_-])")
_LABEL_VALUE = re.compile(r"[\"']?[ \t]{0,8}[:=]?[ \t]{0,8}[\"']?([A-Za-z0-9+/_-]{16,}={0,3})")


def _secret_like(value):
    return any(c.isdigit() or c in "+/=" for c in value) or any("A" <= c <= "Z" for c in value[1:])


def _replace(text, spans):
    """The text with each (start, end) span, in order and not overlapping, replaced by MARK."""
    out, last = [], 0
    for start, end in spans:
        out += [text[last:start], MARK]
        last = end
    return "".join(out + [text[last:]])


def _url_userinfo(text):
    return _URL.sub(r"\1" + MARK + "@", text)


def _flags(text):
    spans, last = [], 0
    for flag in _FLAG.finditer(text):
        if flag.start() < last:
            continue
        components = re.split(r"[-_]", flag.group().lstrip("-").casefold())
        if not _FLAG_COMPONENTS.intersection(components):
            continue
        value = _FLAG_VALUE.match(text, flag.end())
        if value:
            spans.append((value.start(2), value.end(2)))
            last = value.end()
    return _replace(text, spans)


def _bearer(text):
    return _replace(text, [m.span(1) for m in _BEARER.finditer(text) if _secret_like(m.group(1))])


def _jwt(text):
    return _JWT.sub(MARK, text)


def _provider(text):
    return _PROVIDER.sub(MARK, text)


def _labelled(text):
    spans, last = [], 0
    for label in _LABEL.finditer(text):
        if label.start() < last:
            continue
        word = label.group().casefold()
        if not any(w in word for w in _WORDS):
            continue
        value = _LABEL_VALUE.match(text, label.end())
        if value and _secret_like(value.group(1)):
            spans.append(value.span(1))
            last = value.end()
    return _replace(text, spans)


RULES = (("url-userinfo", _url_userinfo), ("secret-flag", _flags), ("bearer-basic", _bearer), ("jwt", _jwt),
         ("provider-key", _provider), ("labelled-run", _labelled))


def redact(text):
    """The text with every token-like string replaced by MARK."""
    if not isinstance(text, str):
        return text
    for _, rule in RULES:
        text = rule(text)
    return text


def redact_value(value):
    """Every string inside a JSON value redacted (object keys too); structure and other types unchanged."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {redact(key): redact_value(item) for key, item in value.items()}
    return value
