"""Redaction of token-like strings before Claude sees exercise output (plan I11).

Every pattern lives here, and only here; `collect` (C2) and later `repro` (C6) apply `redact_value` to what
they return. A match is replaced by MARK (labels, schemes and flag names are kept so the text stays
readable). Redaction errs towards over-matching: a removed harmless word costs less than a leaked secret.

Every match is judged on its own. Each rule below is applied to the original text, and every match it finds there (a
scheme, a flag, a keyword, a JWT or key start, a label) is judged as if it were the only one in the text: never
skipped because an earlier match of the same rule covers it (`--token=a/--password x`, `Bearer a/b/basic x`), and
never hidden because another rule redacted its name (`--token=x_password: y`, `Bearer abcd/efgh/password=y`,
`sk-…_password=y`, `--token=Bearer y`). The rules are also applied in order, each to the text the earlier ones left
(as before; a value read up to the next whitespace then runs on past a quoted value an earlier rule replaced). A
character is redacted when any of these redacts it: all spans are unioned and replaced once, so touching spans
become one MARK.

The text is attacker-influenced (Codex's reply, app content), so every rule runs in linear time, and no rule has
a length cap whose excess would let a secret through (exceeding any limit redacts more, never less):
- a match starts only where the preceding character cannot continue the same run (a look-behind on the run's
  own class), so no match starts inside another's name and the names one rule finds are disjoint;
- what a match reads after its start (blanks, the next whitespace, the closing quote, a run's end and its
  secret-like test, a JWT segment's or a key's end) comes from tables built for the whole text in O(n) passes (each
  on first use), so a match costs O(1) plus its own name's length, however many matches lie inside one another's
  values (`--token=--token=…`, `token=key=key=…`, `x_eyJ…_eyJ…`); a bearer keyword reads its own blanks and token
  with the pattern, and no two keywords read the same blanks or token characters;
- the ordered pass keeps, for every character of each intermediate text, the original range it stands for (a MARK
  stands for the whole span it replaced), so its spans map back to the original text in O(n) per rule.

Rules, in the order they are applied:
- URL userinfo: `scheme://user:pass@` and `scheme://token@` -> `scheme://[REDACTED]@` (any length)
- values after secret-bearing flags, of any length: `--password x`, `--token=x`, `-api-key "x y"`,
  `--private-key "-----BEGIN …\n…"`: a flag name with a component password, passwd, passphrase, token, secret,
  key, apikey, accesskey or privatekey, then `=` or spaces, then the value (QUOTED VALUES below, else up to the
  next whitespace); a flag inside another flag's value has its own value redacted too
- bearer and basic credentials: `Bearer <token>`, `Basic <base64>` (8+ characters that look like a secret)
- JSON Web Tokens: `eyJ<header>.<payload>.<signature>`, also right after `-` or `_` (`x-eyJ…`)
- provider keys: `sk-…` (OpenAI style, including `sk-proj-…`), GitHub `ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`/`github_pat_`,
  Slack `xoxa-`/`xoxb-`/`xoxp-`/`xoxo-`/`xoxr-`/`xoxs-`; also right after `-` or `_`, never inside a word
- labelled values: a word followed by an explicit `=` or `:` (spaces and a quote around the word allowed), whose
  name ends with or has a component password, passwd, passphrase, token, secret or key (`DB_PASSWORD=…`,
  `"client_secret": "…"`, `apiKey: …`): the value is redacted whatever its shape (QUOTED VALUES below, else up to
  the next whitespace). Any other word holding one of those words, joined by `=` or `:` (`passwordhash: …`,
  `api_keys=…`, `X-Auth-Tokens: …`) or by spaces only (`token abc…`): a hex or base64 run of 16 or more
  characters that looks like a secret. Words inside any redacted value are read as labels too, so a value that
  ends in a secret's name and a separator (`tokens=AbCd…_password=x`, `keys: /etc/…/server_key=x`,
  `password=abc_token : x`, `token=a_key="x y"`) has that name's value redacted as well.

QUOTED VALUES: a value opening with `"` or `'` is redacted up to the matching closing quote, across lines (a
PEM block in quotes); without a closing quote, up to the end of the text (the safer choice: the secret may run
on, and nothing after an unbalanced quote can be shown to be harmless).

A value looks like a secret when it holds a digit, `+`, `/` or `=`, or an upper-case letter after its first
character, so prose ("Basic navigation works", "the token list is empty") is left alone.
"""
from array import array
from functools import cached_property
from itertools import accumulate
import re

MARK = "[REDACTED]"

_WORDS = ("password", "passwd", "passphrase", "token", "secret", "key")
_COMPONENTS = frozenset({*_WORDS, "apikey", "accesskey", "privatekey"})

_URL = re.compile(r"(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://)[^\s/?#@\"'<>]+@")
_FLAG = re.compile(r"(?<![\w-])--?[A-Za-z0-9][A-Za-z0-9_-]*")
_FLAG_PARTS = re.compile(r"[-_]")
_BEARER = re.compile(r"(?<![A-Za-z0-9_-])(?i:bearer|basic)")
_BEARER_TOKEN = re.compile(r"[ \t]+([A-Za-z0-9._~+/-]{8,}=*)")
_JWT_START = re.compile(r"(?<![A-Za-z0-9])eyJ")
_PROVIDER = re.compile(r"(?<![A-Za-z0-9])(?:sk-|gh[pousr]_|github_pat_|xox[abposr]-)")
# By prefix length (each prefix has its own): the table giving the end of the key's characters, and their least count.
# sk-[A-Za-z0-9_-]{16,}, gh[pousr]_[A-Za-z0-9]{20,}, github_pat_[A-Za-z0-9_]{20,}, xox[abposr]-[A-Za-z0-9-]{10,}.
_PROVIDER_RUNS = {3: ("word_end", 16), 4: ("alnum_end", 20), 11: ("under_end", 20), 5: ("dash_end", 10)}
_LABEL = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]+")
_BLANKS = re.compile(r"[ \t]+")
_NONSPACE = re.compile(r"\S+")
# A hex or base64 run: 16 or more characters of this class, then up to three `=` (`_Facts.secret_run`).
_RUN_CLASS = re.compile(r"[A-Za-z0-9+/_-]+")
_WORD_CLASS = re.compile(r"[A-Za-z0-9_-]+")  # a JWT segment, an `sk-` key
_ALNUM_CLASS = re.compile(r"[A-Za-z0-9]+")
_UNDER_CLASS = re.compile(r"[A-Za-z0-9_]+")
_DASH_CLASS = re.compile(r"[A-Za-z0-9-]+")
_SPECIAL = frozenset("0123456789+/=")
_UPPER = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
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


def _union(spans):
    """The spans sorted, with overlapping or touching spans merged, so `_replace` gets them in order and apart.
    The spans of one rule come almost in order of their start, so the sort is close to one linear pass."""
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _code(limit):
    """The array type for positions up to `limit`: 4 bytes each when they fit, else 8 (a list would hold one int
    object per entry)."""
    return "i" if limit < 2**31 - 1 else "q"


def _run_ends(text, pattern, code):
    """For every position 0..len(text): the end of the `pattern` match (a run of one character class) that covers
    it, or the position itself when none does. One pass; each match fills its own positions once."""
    ends = array(code, range(len(text) + 1))
    for match in pattern.finditer(text):
        start, end = match.span()
        ends[start:end] = array(code, (end,)) * (end - start)
    return ends


def _next_index(text, char, code):
    """For every position 0..len(text): the index of the first `char` at or after it, else len(text). One pass."""
    found, start, n = array(code), 0, len(text)
    at = text.find(char)
    while at != -1:
        found += array(code, (at,)) * (at + 1 - start)
        start = at + 1
        at = text.find(char, start)
    return found + array(code, (n,)) * (n + 1 - start)


class _Facts:
    """The per-position facts a match needs, each computed for the whole text in O(n) passes on first use, so
    judging one match costs O(1) plus the match's own name, whatever any other match did."""

    def __init__(self, text):
        self.text, self.n = text, len(text)
        self.code = _code(self.n + 1)
        self._close = {}

    @cached_property
    def blank_end(self):
        return _run_ends(self.text, _BLANKS, self.code)  # past the spaces and tabs starting there

    @cached_property
    def value_end(self):
        return _run_ends(self.text, _NONSPACE, self.code)  # the end of an unquoted value: the next whitespace

    @cached_property
    def class_end(self):
        return _run_ends(self.text, _RUN_CLASS, self.code)  # the end of the run-class characters starting there

    @cached_property
    def word_end(self):
        return _run_ends(self.text, _WORD_CLASS, self.code)

    @cached_property
    def alnum_end(self):
        return _run_ends(self.text, _ALNUM_CLASS, self.code)

    @cached_property
    def under_end(self):
        return _run_ends(self.text, _UNDER_CLASS, self.code)

    @cached_property
    def dash_end(self):
        return _run_ends(self.text, _DASH_CLASS, self.code)

    def close(self, quote):
        """For every position: the first `quote` at or after it, else len(text) (one table per quote, on first use)."""
        if quote not in self._close:
            self._close[quote] = _next_index(self.text, quote, self.code)
        return self._close[quote]

    # Prefix counts for `_secret_like` on a run (its characters are ASCII, so `isdigit` is 0-9 there).
    @cached_property
    def special(self):
        return array(self.code, accumulate(map(_SPECIAL.__contains__, self.text), initial=0))

    @cached_property
    def upper(self):
        return array(self.code, accumulate(map(_UPPER.__contains__, self.text), initial=0))

    def value(self, k):
        """(start, end) of the value at k, or None: quoted -> to the closing quote, else to the end of the text;
        unquoted -> up to the next whitespace."""
        text, n = self.text, self.n
        if k >= n:
            return None
        if text[k] in "\"'":
            return (k + 1, self.close(text[k])[k + 1])
        end = self.value_end[k]
        return (k, end) if end > k else None

    def secret_run(self, k):
        """(start, end) of the hex or base64 run of 16 or more characters at k (after one opening quote) when it
        looks like a secret, else None."""
        text, n = self.text, self.n
        if k < n and text[k] in "\"'":
            k += 1
        end = self.class_end[k]
        if end - k < 16:
            return None
        for _ in range(3):  # `={0,3}`
            if end < n and text[end] == "=":
                end += 1
        if self.special[end] - self.special[k] or self.upper[end] - self.upper[k + 1]:
            return (k, end)
        return None

    def label_span(self, label):
        """The span one label redacts, judged as if it were the only label in the text, or None."""
        text, n = self.text, self.n
        name = label.group()
        folded = name.casefold()
        i = label.end()
        if i < n and text[i] in "\"'":
            i += 1  # the closing quote of a quoted key ("client_secret": …)
        j = self.blank_end[i]
        if j < n and text[j] in ":=":
            # Explicit separator: the value whatever its shape when the name is a secret's name, else (the word
            # only inside the name: `passwordhash`, `api_keys`) a long run that looks like a secret.
            k = self.blank_end[j + 1]
            if _COMPONENTS.intersection(_components(name)) or folded.endswith(_WORDS):
                return self.value(k)
            return self.secret_run(k)
        if j > i:
            # Joined by spaces only: a long run that looks like a secret.
            return self.secret_run(j)
        return None


# Each rule: (text, its _Facts) -> the spans it redacts, in order and apart, every match judged on its own.

def _url_userinfo(text, facts):
    return [(match.end(1), match.end() - 1) for match in _URL.finditer(text)]


def _flags(text, facts):
    # Every secret-bearing flag is judged on its own, also one inside another flag's value (`--token=a/--password x`,
    # `--api-key=x;--password "y z"`). Flags are disjoint (a flag cannot start inside a flag's name), and what one
    # reads after its name is a table lookup, so `--token=--token=…` stays linear.
    n, spans = facts.n, []
    for flag in _FLAG.finditer(text):
        if not _COMPONENTS.intersection(_FLAG_PARTS.split(flag.group().lstrip("-").casefold())):
            continue
        i = flag.end()
        if i < n and text[i] == "=":
            start = i + 1
        else:
            start = facts.blank_end[i]
            if start == i:
                continue  # no separator: not a flag with a value
        span = facts.value(start)
        if span:
            spans.append(span)
    return _union(spans)


def _bearer(text, facts):
    # Every keyword is judged on its own, also one inside another keyword's token (`Bearer a/b/basic x`). A keyword
    # inside a token can only end where that token ends, so no two keywords read the same blanks or token.
    spans = []
    for word in _BEARER.finditer(text):
        token = _BEARER_TOKEN.match(text, word.end())
        if token and _secret_like(token.group(1)):
            spans.append(token.span(1))
    return _union(spans)


def _jwt(text, facts):
    # Every `eyJ` start is judged on its own, also one inside another JWT (its own segments can run past that JWT).
    n, spans = facts.n, []
    for candidate in _JWT_START.finditer(text):
        segment_end = facts.word_end
        start = candidate.start()
        end1 = segment_end[start]
        if end1 - start < 7 or end1 >= n or text[end1] != ".":
            continue
        end2 = segment_end[end1 + 1]
        if end2 - end1 - 1 < 4 or end2 >= n or text[end2] != ".":
            continue
        spans.append((start, segment_end[end2 + 1]))
    return _union(spans)


def _provider(text, facts):
    # Every key start is judged on its own, also one inside another key (`xoxb-…-sk-…_x`, whose `_x` the Slack key's
    # characters do not reach). The prefixes cannot overlap, and a key's end is a table lookup.
    spans = []
    for prefix in _PROVIDER.finditer(text):
        table, least = _PROVIDER_RUNS[len(prefix.group())]
        k = prefix.end()
        end = getattr(facts, table)[k]
        if end - k >= least:
            spans.append((prefix.start(), end))
    return _union(spans)


def _labelled(text, facts):
    # Every label holding a secret word is judged on its own, exactly as if it were the only label in the text: a
    # label inside a value another label redacts is read like any other (the value can end in a secret's name whose
    # own value follows: `tokens=AbCd…_password=x`, `token=x_key="a b"`). The spans are unioned, so judging one
    # label never removes what another redacts. Labels are disjoint, so the per-label work beyond table lookups (its
    # name) sums to at most len(text).
    return _union([span for label in _LABEL.finditer(text)
                   if any(word in label.group().casefold() for word in _WORDS) and (span := facts.label_span(label))])


RULES = (("url-userinfo", _url_userinfo), ("secret-flag", _flags), ("bearer-basic", _bearer), ("jwt", _jwt),
         ("provider-key", _provider), ("labelled-value", _labelled))


def _mapped(starts, ends, spans):
    """The view's spans as original ranges. `starts[i]`/`ends[i]` are the original range character i of the view
    stands for (a MARK's characters stand for the whole range its span covered); `starts` has one more entry, the
    original length, for an empty span at the end."""
    return [(starts[start], ends[end - 1] if end > start else starts[start]) for start, end in spans]


def _advance(view, starts, ends, spans, mapped):
    """The view with each span (in order, apart) replaced by MARK, and its original-range tables."""
    code = starts.typecode
    out, new_starts, new_ends, last = [], array(code), array(code), 0
    for (start, end), (first, past) in zip(spans, mapped):
        out += [view[last:start], MARK]
        new_starts += starts[last:start]
        new_starts += array(code, (first,)) * len(MARK)
        new_ends += ends[last:start]
        new_ends += array(code, (past,)) * len(MARK)
        last = end
    out.append(view[last:])
    new_starts += starts[last:]
    new_ends += ends[last:]
    return "".join(out), new_starts, new_ends


def redact(text):
    """The text with every token-like string replaced by MARK."""
    if not isinstance(text, str):
        return text
    n = len(text)
    # Every rule on the original text, every match judged on its own.
    facts = _Facts(text)
    found = [rule(text, facts) for _, rule in RULES]
    del facts
    spans = [span for own in found for span in own]
    # The rules in order, each on the text the earlier ones left, its spans mapped back to the original text. Until
    # a rule redacts something that text is the original, whose spans are already known (and already in `spans`).
    view, starts, ends, view_facts = text, None, None, None
    for index, ((_, rule), own) in enumerate(zip(RULES, found)):
        if starts is None:
            if not own:
                continue
            code = _code(n + 1)
            starts, ends = array(code, range(n + 1)), array(code, range(1, n + 1))
            mapped = own
        else:
            own = rule(view, view_facts)
            if not own:
                continue
            mapped = _mapped(starts, ends, own)
            spans += mapped
        if index + 1 < len(RULES):  # a later rule reads the new view
            view, starts, ends = _advance(view, starts, ends, own, mapped)
            view_facts = _Facts(view)
    return _replace(text, _union(spans)) if spans else text


def redact_value(value):
    """Every string inside a JSON value redacted (object keys too); structure and other types unchanged."""
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return {redact(key): redact_value(item) for key, item in value.items()}
    return value
