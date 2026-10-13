"""Redaction of token-like strings before Claude sees exercise output (plan I11).

Every pattern lives here, and only here; `collect` (C2) and later `repro` (C6) apply `redact_value` to what
they return. A match is replaced by MARK (labels, schemes and flag names are kept so the text stays
readable). Redaction errs towards over-matching: a removed harmless word costs less than a leaked secret.

The text is attacker-influenced (Codex's reply, app content), so every rule runs in linear time, and no rule has
a length cap whose excess would let a secret through (exceeding any limit redacts more, never less):
- a match starts only where the preceding character cannot continue the same run (a look-behind on the run's
  own class), so a long run has one start, and every quantifier stops at a character outside its class;
- separators (`=`, `:`, spaces and tabs of any length) and values are read from that one anchored position,
  in Python, once; a span that is redacted is not searched again.

Rules, in the order they are applied:
- URL userinfo: `scheme://user:pass@` and `scheme://token@` -> `scheme://[REDACTED]@` (any length)
- values after secret-bearing flags, of any length: `--password x`, `--token=x`, `-api-key "x y"`,
  `--private-key "-----BEGIN …\n…"`: a flag name with a component password, passwd, passphrase, token, secret,
  key, apikey, accesskey or privatekey, then `=` or spaces, then the value (QUOTED VALUES below, else up to the
  next whitespace)
- bearer and basic credentials: `Bearer <token>`, `Basic <base64>` (8+ characters that look like a secret)
- JSON Web Tokens: `eyJ<header>.<payload>.<signature>`, also right after `-` or `_` (`x-eyJ…`)
- provider keys: `sk-…` (OpenAI style, including `sk-proj-…`), GitHub `ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`/`github_pat_`,
  Slack `xoxa-`/`xoxb-`/`xoxp-`/`xoxo-`/`xoxr-`/`xoxs-`; also right after `-` or `_`, never inside a word
- labelled values: a word followed by an explicit `=` or `:` (spaces and a quote around the word allowed), whose
  name ends with or has a component password, passwd, passphrase, token, secret or key (`DB_PASSWORD=…`,
  `"client_secret": "…"`, `apiKey: …`): the value is redacted whatever its shape (QUOTED VALUES below, else up to
  the next whitespace). Joined by spaces only (`token abc…`), any word holding one of those words: a hex or
  base64 run of 16 or more characters that looks like a secret.

QUOTED VALUES: a value opening with `"` or `'` is redacted up to the matching closing quote, across lines (a
PEM block in quotes); without a closing quote, up to the end of the text (the safer choice: the secret may run
on, and nothing after an unbalanced quote can be shown to be harmless).

A value looks like a secret when it holds a digit, `+`, `/` or `=`, or an upper-case letter after its first
character, so prose ("Basic navigation works", "the token list is empty") is left alone.
"""
import re

MARK = "[REDACTED]"

_WORDS = ("password", "passwd", "passphrase", "token", "secret", "key")
_COMPONENTS = frozenset({*_WORDS, "apikey", "accesskey", "privatekey"})

_URL = re.compile(r"(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://)[^\s/?#@\"'<>]+@")
_FLAG = re.compile(r"(?<![\w-])--?[A-Za-z0-9][A-Za-z0-9_-]*")
_BEARER = re.compile(r"(?<![A-Za-z0-9_-])(?i:bearer|basic)[ \t]+([A-Za-z0-9._~+/-]{8,}=*)")
_JWT_START = re.compile(r"(?<![A-Za-z0-9])eyJ")
_SEGMENT = re.compile(r"[A-Za-z0-9_-]*")
_PROVIDER = re.compile(r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}"
                       r"|github_pat_[A-Za-z0-9_]{20,}|xox[abposr]-[A-Za-z0-9-]{10,})")
_LABEL = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]+")
_SPACE = re.compile(r"[ \t]*")
_NONSPACE = re.compile(r"\S+")
_RUN = re.compile(r"[A-Za-z0-9+/_-]{16,}={0,3}")
_PARTS = re.compile(r"[-_]|(?<=[a-z0-9])(?=[A-Z])")


def _secret_like(value):
    return any(c.isdigit() or c in "+/=" for c in value) or any("A" <= c <= "Z" for c in value[1:])


def _components(name):
    return {part.casefold() for part in _PARTS.split(name) if part}


def _replace(text, spans):
    """The text with each (start, end) span, in order and not overlapping, replaced by MARK."""
    out, last = [], 0
    for start, end in spans:
        out += [text[last:start], MARK]
        last = end
    return "".join(out + [text[last:]])


def _skip_space(text, i):
    return _SPACE.match(text, i).end()


def _value(text, i):
    """(start, end) of the value at i, or None: quoted -> to the closing quote, else to the end of the text;
    unquoted -> up to the next whitespace."""
    if i >= len(text):
        return None
    if text[i] in "\"'":
        close = text.find(text[i], i + 1)
        return (i + 1, close if close != -1 else len(text))
    match = _NONSPACE.match(text, i)
    return match.span() if match else None


def _url_userinfo(text):
    return _URL.sub(r"\1" + MARK + "@", text)


def _flags(text):
    spans, last = [], 0
    for flag in _FLAG.finditer(text):
        if flag.start() < last or not _COMPONENTS.intersection(re.split(r"[-_]", flag.group().lstrip("-").casefold())):
            continue
        i = flag.end()
        if i < len(text) and text[i] == "=":
            start = i + 1
        else:
            start = _skip_space(text, i)
            if start == i:
                continue  # no separator: not a flag with a value
        span = _value(text, start)
        if span:
            spans.append(span)
            last = span[1]
    return _replace(text, spans)


def _bearer(text):
    return _replace(text, [m.span(1) for m in _BEARER.finditer(text) if _secret_like(m.group(1))])


def _jwt(text):
    spans, skip, n = [], 0, len(text)
    for candidate in _JWT_START.finditer(text):
        start = candidate.start()
        if start < skip:
            continue
        end1 = _SEGMENT.match(text, start).end()
        skip = end1  # a later candidate in this segment ends at the same place and is shorter
        if end1 - start < 7 or end1 >= n or text[end1] != ".":
            continue
        end2 = _SEGMENT.match(text, end1 + 1).end()
        if end2 - end1 - 1 < 4 or end2 >= n or text[end2] != ".":
            continue
        end3 = _SEGMENT.match(text, end2 + 1).end()
        spans.append((start, end3))
        skip = end3
    return _replace(text, spans)


def _provider(text):
    return _PROVIDER.sub(MARK, text)


def _labelled(text):
    spans, last, n = [], 0, len(text)
    for label in _LABEL.finditer(text):
        if label.start() < last:
            continue
        name = label.group()
        folded = name.casefold()
        if not any(word in folded for word in _WORDS):
            continue
        i = label.end()
        if i < n and text[i] in "\"'":
            i += 1  # the closing quote of a quoted key ("client_secret": …)
        j = _skip_space(text, i)
        if j < n and text[j] in ":=":
            # Explicit separator: the value whatever its shape, when the name is a secret's name.
            if not (_COMPONENTS.intersection(_components(name)) or folded.endswith(_WORDS)):
                continue
            span = _value(text, _skip_space(text, j + 1))
        elif j > i:
            # Joined by spaces only: a long run that looks like a secret.
            k = j + 1 if j < n and text[j] in "\"'" else j
            run = _RUN.match(text, k)
            span = run.span() if run and _secret_like(run.group()) else None
        else:
            continue
        if span:
            spans.append(span)
            last = span[1]
    return _replace(text, spans)


RULES = (("url-userinfo", _url_userinfo), ("secret-flag", _flags), ("bearer-basic", _bearer), ("jwt", _jwt),
         ("provider-key", _provider), ("labelled-value", _labelled))


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
