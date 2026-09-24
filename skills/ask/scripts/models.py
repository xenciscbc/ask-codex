"""Deterministic model and effort selection from the user's request text and the Codex home."""
import json
import os
from pathlib import Path
import re
import tomllib

LEVELS = ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")
# The only per-model defaults; matched against a slug's -/. parts. Every other model uses its listed default.
DEFAULT_EFFORT = {"sol": "high", "astra": "medium"}
SLUG = re.compile(r"^[A-Za-z0-9._-]+$")
TOKEN = re.compile(r"^[A-Za-z0-9._:-]+( [A-Za-z0-9._-]+)?$")
EFFORT = re.compile(r"^[a-z]+$")
PAIR = re.compile(r"^((?:[^\s,]+\s*,\s*)+[^\s,]+)(?:\s+([\s\S]*))?$")


class Stop(Exception):
    """A request that must stop before any Codex command; carries the structured result."""

    def __init__(self, result):
        super().__init__(result.get("reason", result["state"]))
        self.result = result


def codex_home():
    home = os.environ.get("CODEX_HOME")
    return Path(home) if home else Path.home() / ".codex"


def read_listing(home):
    path = home / "models_cache.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        models = value["models"]
        if not isinstance(models, list) or any(not isinstance(m, dict) for m in models):
            raise ValueError()
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise ValueError(f"Codex model cache is unreadable or malformed: {path}") from None
    listed = []
    for m in models:
        if m.get("visibility") != "list" or not isinstance(m.get("slug"), str) or not SLUG.fullmatch(m["slug"]):
            continue
        levels = [e.get("effort") for e in m.get("supported_reasoning_levels") or [] if isinstance(e, dict)]
        priority = m.get("priority")
        listed.append({"slug": m["slug"], "priority": priority if isinstance(priority, (int, float)) else float("inf"),
                       "default": m.get("default_reasoning_level"), "levels": [e for e in levels if e in LEVELS]})
    return sorted(listed, key=lambda m: m["priority"])


def read_configured_model(home):
    path = home / "config.toml"
    if not path.exists():
        return None
    try:
        value = tomllib.loads(path.read_text(encoding="utf-8-sig")).get("model")
    except (tomllib.TOMLDecodeError, UnicodeError):
        raise ValueError(f"Codex configuration is unreadable or malformed: {path}") from None
    if value is not None and (not isinstance(value, str) or not SLUG.fullmatch(value)):
        raise ValueError(f"Codex configuration names an invalid model: {path}")
    return value


def contiguous(needle, haystack):
    return any(haystack[i:i + len(needle)] == needle for i in range(len(haystack) - len(needle) + 1))


def slug_like(head, slugs):
    head = head.lower()
    return bool(head) and (head in (s.lower() for s in slugs) or
                           any(contiguous(re.split(r"[-.]", head), re.split(r"[-.]", s.lower())) for s in slugs))


def consume(text, count):
    for _ in range(count):
        text = re.sub(r"^\S+(?:\s+|$)", "", text, count=1)
    return text


def read_request(text, slugs):
    """Read a leading model token, `<alias>:<effort>`, `model|use <x>` or `effort <level>`."""
    text = text.strip()
    words = text.split()
    if not words:
        return {"kind": "none", "question": ""}
    head = re.sub(r"[^A-Za-z0-9._-].*", "", words[0], flags=re.S)
    if words[0].lower() in ("model", "use") and len(words) > 1:
        token, used = words[1], 2
    elif words[0].lower() == "effort" and len(words) > 1:
        if not EFFORT.fullmatch(words[1]):
            return {"kind": "invalid", "token": words[1]}
        return {"kind": "effort", "effort": words[1], "question": consume(text, 2)}
    elif ":" in words[0] or slug_like(head, slugs):
        token, used = words[0], 1
        if ":" not in token and len(words) > 1 and SLUG.fullmatch(words[1]) and slug_like(words[1], slugs):
            token, used = f"{token} {words[1]}", 2
    else:
        return {"kind": "none", "question": text}
    alias, _, effort = token.partition(":")
    if not TOKEN.fullmatch(token) or ":" in effort or (":" in token and not EFFORT.fullmatch(effort)):
        return {"kind": "invalid", "token": token}
    return {"kind": "model", "token": token, "alias": alias, "effort": effort or None, "question": consume(text, used)}


def match(alias, slugs):
    exact = [s for s in slugs if s.lower() == alias.lower()]
    if exact:
        return exact
    words = alias.lower().split()
    return [s for s in slugs if all(contiguous(re.split(r"[-.]", w), re.split(r"[-.]", s.lower())) for w in words)]


def rank(level):
    return LEVELS.index(level)


def highest_usable(levels):
    usable = [l for l in levels if l != "ultra" and rank(l) >= rank("medium")]
    return max(usable, key=rank) if usable else None


def settle_requested(requested, slug, levels):
    notes = []
    effort = requested
    if effort in ("none", "minimal", "low"):
        notes.append(f"Effort {effort} was raised to medium: consultations run at medium or above.")
        effort = "medium"
    if levels is None:
        if effort == "ultra":
            notes.append("ultra needs confirmed model support, which is unknown here; using max.")
            return "max", False, notes
        if effort not in LEVELS:
            raise Stop({"state": "unavailable", "reason": f"Effort {effort} is not a known level", "choices": []})
        return effort, False, notes
    if effort in levels:
        return effort, effort == "ultra", notes
    best = highest_usable(levels)
    if best is None:
        raise Stop({"state": "unavailable", "reason": f"{slug} supports no effort at or above medium", "choices": []})
    notes.append(f"{slug} does not support effort {effort}; using {best}, its highest supported level other than ultra.")
    return best, False, notes


def settle_default(slug, entry):
    levels = entry["levels"] if entry else None
    if slug:
        for key, value in DEFAULT_EFFORT.items():
            if key in re.split(r"[-.]", slug.lower()) and (levels is None or value in levels):
                return value
    if levels is None:
        return "medium"
    listed = entry["default"] if entry["default"] in LEVELS else "medium"
    target = min(max(rank(listed), rank("medium")), rank("max"))
    above = [l for l in levels if l != "ultra" and rank(l) >= target]
    if above:
        return min(above, key=rank)
    best = highest_usable(levels)
    if best is None:
        raise Stop({"state": "unavailable", "reason": f"{slug} supports no effort at or above medium", "choices": []})
    return best


def choose(named_model, named_effort, session, listed, configured):
    fallback = listed[0]["slug"] if listed else None
    slug = named_model or session.get("model") or configured or fallback
    entry = next((m for m in listed if m["slug"] == slug), None)
    requested = named_effort or session.get("effort")
    if requested:
        effort, ultra, notes = settle_requested(requested, slug, entry["levels"] if entry else None)
    else:
        effort, ultra, notes = settle_default(slug, entry), False, []
    return {"model": slug, "effort": effort, "explicit_ultra": ultra, "notes": notes}


def validate(request):
    if not isinstance(request, dict) or not isinstance(request.get("text"), str):
        raise ValueError("A resolve request needs the request text")
    session = request.get("session") or {}
    if not isinstance(session, dict):
        raise ValueError("The session choice must be an object")
    if session.get("model") is not None and (not isinstance(session["model"], str) or not SLUG.fullmatch(session["model"])):
        raise ValueError("Invalid session model")
    if session.get("effort") is not None and (not isinstance(session["effort"], str) or not EFFORT.fullmatch(session["effort"])):
        raise ValueError("Invalid session effort")
    return request["text"], {k: session.get(k) for k in ("model", "effort")}


def readings_of(text, slugs):
    pair = PAIR.match(text.strip())
    if pair:
        items = re.split(r"\s*,\s*", pair.group(1))
        readings = [read_request(f"{item} x", slugs) for item in items]
        if all(r["kind"] in ("model", "invalid") for r in readings):
            if len(items) > 2:
                raise Stop({"state": "invalid", "reason": "A parallel consultation takes at most two models"})
            return readings, pair.group(2) or ""
    reading = read_request(text, slugs)
    return [reading], reading.get("question", "")


def resolve(request):
    text, session = validate(request)
    home = codex_home()
    listed = read_listing(home) or []
    configured = read_configured_model(home)
    slugs = [m["slug"] for m in listed]
    try:
        readings, question = readings_of(text, slugs)
        named = []
        for index, reading in enumerate(readings):
            if reading["kind"] == "invalid":
                raise Stop({"state": "invalid", "reason": f"Invalid model or effort token: {reading['token']!r}"})
            if reading["kind"] == "model":
                found = match(reading["alias"], slugs)
                if len(found) > 1:
                    raise Stop({"state": "ambiguous", "member": index, "token": reading["token"], "candidates": found})
                if not found:
                    reason = (f"No listed Codex model matches {reading['alias']!r}" if slugs
                              else "No Codex model list is available to resolve a named model")
                    raise Stop({"state": "unavailable", "reason": reason, "choices": slugs})
                named.append((found[0], reading["effort"]))
            else:
                named.append((None, reading.get("effort")))
        if len(named) == 2 and named[0][0] == named[1][0]:
            raise Stop({"state": "invalid", "reason": "A parallel consultation needs two different models"})
        choices = [choose(model, effort, session, listed, configured) for model, effort in named]
    except Stop as stop:
        return stop.result
    try:
        base = choose(None, None, session, listed, configured)
        baseline = {"model": base["model"], "effort": base["effort"]}
    except Stop:
        baseline = None
    for (model, effort), choice in zip(named, choices):
        choice["differs_from_baseline"] = bool(model or effort) and (
            baseline is None or (choice["model"], choice["effort"]) != (baseline["model"], baseline["effort"]))
    return {"state": "resolved", "question": question, "models": choices, "baseline": baseline}
