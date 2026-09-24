"""Deterministic model and effort selection from the model tokens Claude read off the request."""
import json
import os
from pathlib import Path
import re
import tomllib

LEVELS = ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")
# The only per-model defaults; matched against a slug's -/. parts. Every other model uses its listed default.
DEFAULT_EFFORT = {"sol": "high", "astra": "medium"}
SLUG = re.compile(r"^[A-Za-z0-9._-]+$")
TOKEN = re.compile(r"^(?P<alias>[A-Za-z0-9._-]+(?: [A-Za-z0-9._-]+)?)(?::(?P<effort>[a-z]+))?$")
EFFORT = re.compile(r"^[a-z]+$")


class Stop(Exception):
    """A request that must stop before any Codex command; carries the structured result."""

    def __init__(self, result):
        super().__init__(result.get("reason", result["state"]))
        self.result = result


def codex_home():
    # The Codex CLI resolves its home from the OS home directory, not from Git Bash's HOME.
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
        levels = [e for e in levels if e in LEVELS]
        priority = m.get("priority")
        listed.append({"slug": m["slug"], "priority": priority if isinstance(priority, (int, float)) else float("inf"),
                       "default": m.get("default_reasoning_level"),
                       # No listed levels means support is unknown, not that nothing is supported.
                       "levels": levels or None})
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


def split_parts(value):
    return re.split(r"[-.]", value.lower())


def contiguous(needle, haystack):
    return any(haystack[i:i + len(needle)] == needle for i in range(len(haystack) - len(needle) + 1))


def match(alias, slugs):
    exact = [s for s in slugs if s.lower() == alias.lower()]
    if exact:
        return exact
    return [s for s in slugs if all(contiguous(split_parts(w), split_parts(s)) for w in alias.split())]


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
            if key in split_parts(slug) and (levels is None or value in levels):
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


def known_effort(value, what):
    if value is not None and (not isinstance(value, str) or not EFFORT.fullmatch(value) or value not in LEVELS):
        raise Stop({"state": "invalid", "reason": f"{what} is not a known effort level: {value!r}"})
    return value


def validate(request):
    if not isinstance(request, dict):
        raise ValueError("A resolve request must be a JSON object")
    tokens = request.get("models") or []
    session = request.get("session") or {}
    if not isinstance(tokens, list) or any(not isinstance(t, str) for t in tokens) or not isinstance(session, dict):
        raise ValueError("A resolve request has a list of model tokens and a session object")
    if session.get("model") is not None and (not isinstance(session["model"], str) or not SLUG.fullmatch(session["model"])):
        raise ValueError("Invalid session model")
    return tokens, request.get("effort"), {"model": session.get("model"), "effort": session.get("effort")}


def resolve(request):
    tokens, effort, session = validate(request)
    home = codex_home()
    listed = read_listing(home) or []
    configured = read_configured_model(home)
    slugs = [m["slug"] for m in listed]
    try:
        known_effort(session["effort"], "The session effort")
        known_effort(effort, "The named effort")
        if len(tokens) > 2:
            raise Stop({"state": "invalid", "reason": "A parallel consultation takes at most two models"})
        named = []
        for index, token in enumerate(tokens or [None]):
            if token is None:
                named.append((None, effort))
                continue
            parsed = TOKEN.fullmatch(token.strip())
            if not parsed:
                raise Stop({"state": "invalid", "reason": f"Invalid model token: {token!r}"})
            alias, token_effort = parsed["alias"], known_effort(parsed["effort"], f"The effort in {token!r}")
            found = match(alias, slugs)
            if len(found) > 1:
                raise Stop({"state": "ambiguous", "member": index, "alias": alias, "effort": token_effort,
                            "candidates": found})
            if not found:
                reason = (f"No listed Codex model matches {alias!r}" if slugs
                          else "No Codex model list is available to resolve a named model")
                raise Stop({"state": "unavailable", "reason": reason, "choices": slugs})
            named.append((found[0], token_effort or effort))
        if len(named) == 2 and named[0][0] == named[1][0]:
            raise Stop({"state": "invalid", "reason": "A parallel consultation needs two different models"})
        choices = [choose(model, level, session, listed, configured) for model, level in named]
    except Stop as stop:
        return stop.result
    try:
        base = choose(None, None, session, listed, configured)
        baseline = {"model": base["model"], "effort": base["effort"]}
    except Stop:
        baseline = None
    for (model, level), choice in zip(named, choices):
        choice["differs_from_baseline"] = bool(model or level) and (
            baseline is None or (choice["model"], choice["effort"]) != (baseline["model"], baseline["effort"]))
    return {"state": "resolved", "models": choices, "baseline": baseline}
