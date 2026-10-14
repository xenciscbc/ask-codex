"""TEST ORACLE, not production code: a frozen copy of skills/ask/scripts/redact.py at commit 460de71.

Everything from `from array import array` down to `redact_value` is that revision's module verbatim (only its docstring
is replaced by this one); do not edit it, and never import it from production code. RedactionTest uses it to check
that the current `redact` redacts every original character this pipeline redacts (`covered`), which the current
module guarantees by construction (its phase (2) re-runs this pipeline).

`covered(text)` runs this revision's RULES in order, each on the text the earlier ones left, exactly as its
`redact` does, and records which spans each rule replaced: `_replace`'s argument for the rules that call it, and
`finditer` for the two that use `.sub` (URL userinfo, provider keys); each recorded span list is checked to give that
rule's own output. Each character of every intermediate text carries the original range it stands for (a MARK stands
for the whole range its span covered), so a span maps back to the original characters it removes.
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
_BEARER = re.compile(r"(?<![A-Za-z0-9_-])(?i:bearer|basic)[ \t]+([A-Za-z0-9._~+/-]{8,}=*)")
_JWT_START = re.compile(r"(?<![A-Za-z0-9])eyJ")
_SEGMENT = re.compile(r"[A-Za-z0-9_-]*")
_PROVIDER = re.compile(r"(?<![A-Za-z0-9])(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}"
                       r"|github_pat_[A-Za-z0-9_]{20,}|xox[abposr]-[A-Za-z0-9-]{10,})")
_LABEL = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]+")
_SPACE = re.compile(r"[ \t]*")
_BLANKS = re.compile(r"[ \t]+")
_NONSPACE = re.compile(r"\S+")
# A hex or base64 run: 16 or more characters of this class, then up to three `=` (`_Facts.secret_run`).
_RUN_CLASS = re.compile(r"[A-Za-z0-9+/_-]+")
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


def _positions(values):
    """A table of positions (8 bytes each; a list would hold one int object per entry)."""
    return array("q", values)


def _run_ends(text, pattern):
    """For every position 0..len(text): the end of the `pattern` match (a run of one character class) that covers
    it, or the position itself when none does. One pass; each match fills its own positions once."""
    ends = _positions(range(len(text) + 1))
    for match in pattern.finditer(text):
        start, end = match.span()
        ends[start:end] = _positions((end,)) * (end - start)
    return ends


def _next_index(text, char):
    """For every position 0..len(text): the index of the first `char` at or after it, else len(text). One pass."""
    found, start, n = _positions(()), 0, len(text)
    at = text.find(char)
    while at != -1:
        found += _positions((at,)) * (at + 1 - start)
        start = at + 1
        at = text.find(char, start)
    return found + _positions((n,)) * (n + 1 - start)


class _Facts:
    """The per-position facts a label needs, each computed for the whole text in O(n) passes on first use, so
    judging one label costs O(1) plus the label's own length, whatever any other label did."""

    def __init__(self, text):
        self.text, self.n = text, len(text)

    @cached_property
    def blank_end(self):
        return _run_ends(self.text, _BLANKS)  # what `_skip_space` returns at each position

    @cached_property
    def value_end(self):
        return _run_ends(self.text, _NONSPACE)  # the end of an unquoted value: the next whitespace

    @cached_property
    def class_end(self):
        return _run_ends(self.text, _RUN_CLASS)  # the end of the run-class characters starting there

    @cached_property
    def close(self):
        return {quote: _next_index(self.text, quote) for quote in "\"'"}  # the matching closing quote

    # Prefix counts for `_secret_like` on a run (its characters are ASCII, so `isdigit` is 0-9 there).
    @cached_property
    def special(self):
        return _positions(accumulate(map(_SPECIAL.__contains__, self.text), initial=0))

    @cached_property
    def upper(self):
        return _positions(accumulate(map(_UPPER.__contains__, self.text), initial=0))

    def value(self, k):
        """What `_value(text, k)` returns."""
        text, n = self.text, self.n
        if k >= n:
            return None
        if text[k] in "\"'":
            return (k + 1, self.close[text[k]][k + 1])
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


def _union(spans):
    """The spans sorted, with overlapping or touching spans merged, so `_replace` gets them in order and apart.
    A label's span starts after the label and its separator, which hold no label character, so the spans of
    `_labelled` already come in order of their start and the sort is one linear pass."""
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _labelled(text):
    # Every label holding a secret word is judged on its own, exactly as if it were the only label in the text: a
    # label inside a value another label redacts is read like any other (the value can end in a secret's name whose
    # own value follows: `tokens=AbCd…_password=x`, `token=x_key="a b"`). The spans are unioned, so judging one
    # label never removes what another redacts. Linear time comes from `_Facts`: every scan a label needs (blanks,
    # the next whitespace, the closing quote, the run's end, its secret-like test) is a table lookup, and labels are
    # disjoint, so the per-label work beyond lookups (its name) sums to at most len(text).
    facts = _Facts(text)
    spans = [span for label in _LABEL.finditer(text)
             if any(word in label.group().casefold() for word in _WORDS) and (span := facts.label_span(label))]
    return _replace(text, _union(spans)) if spans else text


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


# ---- Oracle support (not part of the 460de71 module) ----

def _rule_spans(name, rule, view):
    """The rule's output on `view` and the spans (in `view`) it replaced."""
    global _replace
    if name == "url-userinfo":
        spans = [(match.end(1), match.end() - 1) for match in _URL.finditer(view)]
        out = rule(view)
    elif name == "provider-key":
        spans = [match.span() for match in _PROVIDER.finditer(view)]
        out = rule(view)
    else:
        frozen, record = _replace, []

        def recording(text, given):
            record[:] = list(given)
            return frozen(text, given)

        _replace = recording
        try:
            out = rule(view)
        finally:
            _replace = frozen
        spans = record
    assert (_replace(view, spans) if spans else view) == out, (name, view)
    return out, spans


def covered(text):
    """The set of original indices of `text` this revision's pipeline redacts."""
    starts, ends = list(range(len(text))), list(range(1, len(text) + 1))
    result, view = set(), text
    for name, rule in RULES:
        out, spans = _rule_spans(name, rule, view)
        new_starts, new_ends, last = [], [], 0
        for start, end in spans:
            if end > start:
                first, past = starts[start], ends[end - 1]
                result.update(range(first, past))
            else:  # an empty span: MARK inserted, nothing removed
                first = past = starts[start] if start < len(starts) else len(text)
            new_starts += starts[last:start] + [first] * len(MARK)
            new_ends += ends[last:start] + [past] * len(MARK)
            last = end
        starts, ends, view = new_starts + starts[last:], new_ends + ends[last:], out
        assert len(starts) == len(view)
    assert view == redact(text)
    return result
