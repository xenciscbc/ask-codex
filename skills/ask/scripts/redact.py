"""Redaction of token-like strings before Claude sees exercise output (plan I11).

Every pattern lives here, and only here; `collect` (C2) and later `repro` (C6) apply `redact_value` to what
they return. A match is replaced by MARK (labels, schemes and flag names are kept so the text stays
readable). Redaction errs towards over-matching: a removed harmless word costs less than a leaked secret.

Patterns, in the order they are applied:
- URL userinfo: `scheme://user:pass@` and `scheme://token@` -> `scheme://[REDACTED]@`
- values after secret-bearing flags of any length: `--password x`, `--token=x`, `-api-key "x y"`, `--client-secret 'x'`
- bearer and basic credentials: `Bearer <token>`, `Basic <base64>` (8+ characters with a digit, `+`, `/`, `=` or an
  inner upper-case letter)
- JSON Web Tokens: `eyJ<header>.<payload>.<signature>`
- provider keys: `sk-…` (OpenAI style, including `sk-proj-…`), GitHub `ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`/`github_pat_`,
  Slack `xoxa-`/`xoxb-`/`xoxp-`/`xoxo-`/`xoxr-`/`xoxs-`
- a long hex or base64 run (16 or more characters with at least one digit) following `token`, `key`, `secret`
  or `password` (any word ending or starting with them, e.g. `api_key`, `X-Auth-Token`, `client_secret`),
  separated by `:`, `=`, quotes or spaces
"""
import re

MARK = "[REDACTED]"

_SECRET_WORD = r"(?:password|passwd|passphrase|token|secret|api[-_]?key|access[-_]?key|private[-_]?key|key)"

PATTERNS = (
    # scheme://userinfo@ — the user name is redacted too (it is often a token itself).
    ("url-userinfo", re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)[^\s/?#@\"'<>]+@"), r"\1" + MARK + "@"),
    # --password value / --token=value / -secret "quoted value"; any flag whose name holds a secret word.
    ("secret-flag", re.compile(r"(?i)((?<![\w-])--?(?:[a-z0-9]+[-_])*" + _SECRET_WORD + r"(?:[-_][a-z0-9]+)*)"
                               r"(=|[ \t]+)(\"[^\"]*\"|'[^']*'|[^\s\"']+)"), r"\1\2" + MARK),
    # A credential of 8+ characters holding a digit, '+', '/', '=' or an upper-case letter after its first
    # character, so prose such as "Basic navigation works" is left alone.
    ("bearer-basic", re.compile(r"\b((?i:bearer|basic))([ \t]+)"
                                r"(?=[A-Za-z0-9._~+/=-][A-Za-z0-9._~+/=-]*?[0-9+/=A-Z])[A-Za-z0-9._~+/-]{8,}=*"),
     r"\1\2" + MARK),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*"), MARK),
    ("provider-key", re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
                                r"|xox[abposr]-[A-Za-z0-9-]{10,})"), MARK),
    ("labelled-run", re.compile(r"(?i)([A-Za-z0-9_-]*" + _SECRET_WORD + r"[A-Za-z0-9_-]*[\"']?[ \t]*[:=]?[ \t]*[\"']?)"
                                r"(?=[A-Za-z0-9+/_-]*[0-9])([A-Za-z0-9+/_-]{16,}=*)"), r"\1" + MARK),
)


def redact(text):
    """The text with every token-like string replaced by MARK."""
    if not isinstance(text, str):
        return text
    for _, pattern, replacement in PATTERNS:
        text = pattern.sub(replacement, text)
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
