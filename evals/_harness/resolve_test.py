"""Model and effort resolution through the public consultation CLI; never calls Codex."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[2]
CLI = REPO / "skills/ask/scripts/consult.py"
ALL = ["low", "medium", "high", "xhigh", "max", "ultra"]


def model(slug, priority, default="medium", levels=ALL, visibility="list"):
    entry = {"slug": slug, "display_name": slug, "priority": priority, "visibility": visibility,
             "default_reasoning_level": default}
    if levels is not None:
        entry["supported_reasoning_levels"] = [{"effort": e} for e in levels]
    return entry


# Same listing as the eval fixtures (alias-sol and siblings).
CACHE = {"fetched_at": "2026-09-15T00:00:00Z", "models": [
    model("gpt-6-astra", 1),
    model("gpt-reserve", 3, levels=ALL[:-1], visibility="hide"),
    model("gpt-6-sol", 4, default="low"),
    model("gpt-5.6-terra", 7),
    model("gpt-6-luna", 8, levels=ALL[:-1]),
    model("gpt-5.5", 12, levels=ALL[:4]),
    model("codex-auto-review", 43, levels=ALL[:-1], visibility="hide"),
]}
CONFIG = 'model = "gpt-5.6-terra"\nmodel_reasoning_effort = "low"\n'


class ResolveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ask-codex-resolve-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.codex = self.root / "codex-home"
        self.codex.mkdir()
        self.write_cache(CACHE)
        self.write_config(CONFIG)
        self.env = {**os.environ, "CODEX_HOME": str(self.codex), "HOME": str(self.root), "USERPROFILE": str(self.root)}

    def write_cache(self, value):
        (self.codex / "models_cache.json").write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")

    def write_config(self, text):
        (self.codex / "config.toml").write_text(text, encoding="utf-8")

    def call(self, request):
        path = self.root / "resolve.json"
        path.write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run([sys.executable, str(CLI), "resolve", str(path)], env=self.env,
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return json.loads(result.stdout)

    def resolve(self, *tokens, effort=None, session=None):
        request = {"models": list(tokens), "session": session or {}}
        if effort is not None:
            request["effort"] = effort
        return self.call(request)

    def single(self, *tokens, effort=None, session=None):
        result = self.resolve(*tokens, effort=effort, session=session)
        self.assertEqual(result["state"], "resolved", result)
        self.assertEqual(len(result["models"]), max(1, len(tokens)), result)
        return result["models"][0]

    # Model tokens and aliases.

    def test_alias_resolves_to_listed_slug(self):
        self.assertEqual(self.single("sol")["model"], "gpt-6-sol")

    def test_two_word_alias_joins_with_or_without_an_effort(self):
        self.assertEqual(self.single("6 sol")["model"], "gpt-6-sol")
        choice = self.single("6 sol:high")
        self.assertEqual((choice["model"], choice["effort"]), ("gpt-6-sol", "high"))

    def test_exact_slug_wins_case_insensitively(self):
        self.assertEqual(self.single("GPT-5.5")["model"], "gpt-5.5")

    def test_ambiguous_alias_returns_candidates_and_keeps_the_effort(self):
        result = self.resolve("6:high")
        self.assertEqual(result["state"], "ambiguous", result)
        self.assertEqual((result["alias"], result["effort"], result["member"]), ("6", "high", 0))
        self.assertEqual(sorted(result["candidates"]), ["gpt-5.6-terra", "gpt-6-astra", "gpt-6-luna", "gpt-6-sol"])

    def test_unknown_alias_is_unavailable_with_the_listed_choices(self):
        result = self.resolve("nova")
        self.assertEqual(result["state"], "unavailable", result)
        self.assertEqual(result["choices"], ["gpt-6-astra", "gpt-6-sol", "gpt-5.6-terra", "gpt-6-luna", "gpt-5.5"])

    def test_hidden_models_are_not_resolved(self):
        self.assertEqual(self.resolve("reserve")["state"], "unavailable")

    def test_metacharacter_token_is_invalid(self):
        self.assertEqual(self.resolve("sol;touch${IFS}pwned")["state"], "invalid")
        self.assertEqual(self.resolve("sol:hi gh")["state"], "invalid")

    def test_uppercase_or_unknown_effort_is_invalid(self):
        self.assertEqual(self.resolve("sol:HIGH")["state"], "invalid")
        self.assertEqual(self.resolve("sol:hgih")["state"], "invalid")
        self.assertEqual(self.resolve(effort="estimation")["state"], "invalid")

    # Effort rules.

    def test_per_model_defaults_sol_high_astra_medium(self):
        self.assertEqual(self.single("sol")["effort"], "high")
        self.assertEqual(self.single("astra")["effort"], "medium")

    def test_low_is_raised_to_medium_with_a_note(self):
        choice = self.single("sol:low")
        self.assertEqual(choice["effort"], "medium")
        self.assertTrue(choice["notes"], choice)

    def test_unsupported_level_uses_highest_supported_non_ultra_with_a_note(self):
        choice = self.single("gpt-5.5:max")
        self.assertEqual(choice["effort"], "xhigh")
        self.assertTrue(choice["notes"], choice)

    def test_unsupported_ultra_is_lowered(self):
        choice = self.single("luna:ultra")
        self.assertEqual((choice["effort"], choice["explicit_ultra"]), ("max", False))

    def test_explicit_supported_ultra_is_marked(self):
        choice = self.single("astra:ultra")
        self.assertEqual((choice["effort"], choice["explicit_ultra"]), ("ultra", True))

    def test_effort_alone_keeps_the_default_model(self):
        choice = self.single(effort="high")
        self.assertEqual((choice["model"], choice["effort"]), ("gpt-5.6-terra", "high"))

    def test_configured_effort_is_never_inherited(self):
        choice = self.single()
        self.assertEqual((choice["model"], choice["effort"]), ("gpt-5.6-terra", "medium"))

    def test_listed_default_below_medium_is_raised(self):
        self.write_config('model = "gpt-6-luna"\n')
        self.write_cache({"models": [model("gpt-6-luna", 1, default="low", levels=ALL[:-1])]})
        self.assertEqual(self.single()["effort"], "medium")

    def test_listed_default_above_medium_is_used(self):
        self.write_cache({"models": [model("gpt-6-luna", 1, default="xhigh", levels=ALL[:-1])]})
        self.write_config("")
        self.assertEqual(self.single()["effort"], "xhigh")

    def test_listed_default_ultra_is_never_used_by_default(self):
        self.write_cache({"models": [model("gpt-6-luna", 1, default="ultra")]})
        self.write_config("")
        self.assertEqual(self.single()["effort"], "max")

    def test_missing_level_list_means_unknown_support(self):
        self.write_cache({"models": [model("gpt-6-nova", 1, default="high", levels=None)]})
        self.write_config("")
        self.assertEqual(self.single()["effort"], "medium")
        self.assertEqual(self.single("nova:xhigh")["effort"], "xhigh")

    def test_no_supported_level_at_or_above_medium_stops(self):
        self.write_cache({"models": [model("gpt-tiny", 1, default="low", levels=["low"])]})
        self.write_config("")
        self.assertEqual(self.resolve()["state"], "unavailable")

    # Default order: session choice, configured model, lowest priority number, none.

    def test_session_choice_comes_first(self):
        choice = self.single(session={"model": "gpt-6-astra", "effort": "high"})
        self.assertEqual((choice["model"], choice["effort"]), ("gpt-6-astra", "high"))

    def test_session_effort_is_used_for_a_named_model(self):
        self.assertEqual(self.single("astra", session={"effort": "xhigh"})["effort"], "xhigh")

    def test_without_config_the_lowest_priority_number_is_used(self):
        (self.codex / "config.toml").unlink()
        self.assertEqual(self.single()["model"], "gpt-6-astra")

    def test_without_cache_or_config_no_model_is_named(self):
        (self.codex / "config.toml").unlink()
        (self.codex / "models_cache.json").unlink()
        choice = self.single()
        self.assertEqual((choice["model"], choice["effort"]), (None, "medium"))

    def test_without_cache_a_named_model_is_unavailable(self):
        (self.codex / "models_cache.json").unlink()
        self.assertEqual(self.resolve("sol")["state"], "unavailable")

    def test_malformed_configuration_is_reported(self):
        self.write_config("model = [unterminated\n")
        self.assertEqual(self.resolve()["state"], "failed")
        self.write_config(CONFIG)
        self.write_cache("{not json")
        self.assertEqual(self.resolve()["state"], "failed")

    def test_invalid_request_file_is_reported(self):
        self.assertEqual(self.call({"models": "sol"})["state"], "failed")
        self.assertEqual(self.call({"models": [], "session": {"model": "a b"}})["state"], "failed")

    # Parallel pairs (ticket 11).

    def test_pair_resolves_each_member_with_its_own_effort(self):
        result = self.resolve("astra:high", "sol")
        self.assertEqual(result["state"], "resolved", result)
        self.assertEqual([(m["model"], m["effort"]) for m in result["models"]],
                         [("gpt-6-astra", "high"), ("gpt-6-sol", "high")])

    def test_three_models_stop(self):
        self.assertEqual(self.resolve("astra", "sol", "terra")["state"], "invalid")

    def test_duplicate_resolved_models_stop(self):
        self.assertEqual(self.resolve("sol", "6-sol")["state"], "invalid")

    def test_invalid_member_stops(self):
        self.assertEqual(self.resolve("astra", "sol;touch")["state"], "invalid")

    def test_ambiguous_member_returns_its_candidates(self):
        result = self.resolve("sol", "6")
        self.assertEqual((result["state"], result["member"]), ("ambiguous", 1), result)
        self.assertIn("gpt-6-astra", result["candidates"])

    def test_two_word_member_of_a_pair(self):
        result = self.resolve("6 sol", "astra")
        self.assertEqual([m["model"] for m in result["models"]], ["gpt-6-sol", "gpt-6-astra"])

    # Baseline difference (ticket 11): does the named choice differ from the choice without it?

    def test_nothing_named_does_not_differ(self):
        self.assertFalse(self.single()["differs_from_baseline"])

    def test_naming_the_baseline_does_not_differ(self):
        self.assertFalse(self.single("terra")["differs_from_baseline"])
        self.assertFalse(self.single(effort="medium")["differs_from_baseline"])

    def test_naming_another_model_or_effort_differs(self):
        self.assertTrue(self.single("sol")["differs_from_baseline"])
        self.assertTrue(self.single(effort="high")["differs_from_baseline"])
        self.assertTrue(self.single("terra:xhigh")["differs_from_baseline"])

    def test_session_setting_is_part_of_the_baseline(self):
        session = {"model": "gpt-6-astra", "effort": "medium"}
        self.assertFalse(self.single("astra", session=session)["differs_from_baseline"])
        self.assertTrue(self.single("terra", session=session)["differs_from_baseline"])

    def test_baseline_is_reported(self):
        result = self.resolve("sol")
        self.assertEqual(result["baseline"], {"model": "gpt-5.6-terra", "effort": "medium"})

    def test_pair_members_report_their_own_difference(self):
        result = self.resolve("terra", "sol")
        self.assertEqual([m["differs_from_baseline"] for m in result["models"]], [False, True])


if __name__ == "__main__":
    unittest.main()
