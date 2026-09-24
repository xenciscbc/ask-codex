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
Q = "Why does fetchUser in src/user.js return an empty object when the API times out?"
ALL = ["low", "medium", "high", "xhigh", "max", "ultra"]


def model(slug, priority, default="medium", levels=ALL, visibility="list"):
    return {"slug": slug, "display_name": slug, "priority": priority, "visibility": visibility,
            "default_reasoning_level": default, "supported_reasoning_levels": [{"effort": e} for e in levels]}


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

    def resolve(self, text, session=None):
        request = self.root / "resolve.json"
        request.write_text(json.dumps({"text": text, "session": session or {}}), encoding="utf-8")
        result = subprocess.run([sys.executable, str(CLI), "resolve", str(request)], env=self.env,
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return json.loads(result.stdout)

    def single(self, text, session=None):
        result = self.resolve(text, session)
        self.assertEqual(result["state"], "resolved", result)
        self.assertEqual(len(result["models"]), 1, result)
        return result, result["models"][0]

    # Model tokens and aliases (the slice-03 readings of model-token-rule.mjs).

    def test_alias_resolves_to_listed_slug_and_leaves_the_question(self):
        result, choice = self.single(f"sol {Q}")
        self.assertEqual((choice["model"], result["question"]), ("gpt-6-sol", Q))

    def test_two_word_alias_joins(self):
        _, choice = self.single(f"6 sol {Q}")
        self.assertEqual(choice["model"], "gpt-6-sol")

    def test_model_and_use_prefixes_name_a_model(self):
        self.assertEqual(self.single(f"model astra {Q}")[1]["model"], "gpt-6-astra")
        self.assertEqual(self.single(f"use gpt-5.5 {Q}")[1]["model"], "gpt-5.5")

    def test_exact_slug_wins_case_insensitively(self):
        self.assertEqual(self.single(f"GPT-5.5 {Q}")[1]["model"], "gpt-5.5")

    def test_ambiguous_alias_returns_listed_candidates_only(self):
        result = self.resolve(f"6 {Q}")
        self.assertEqual(result["state"], "ambiguous", result)
        self.assertEqual(sorted(result["candidates"]), ["gpt-5.6-terra", "gpt-6-astra", "gpt-6-luna", "gpt-6-sol"])

    def test_unknown_alias_is_unavailable_with_the_listed_choices(self):
        result = self.resolve(f"model nova {Q}")
        self.assertEqual(result["state"], "unavailable", result)
        self.assertEqual(result["choices"], ["gpt-6-astra", "gpt-6-sol", "gpt-5.6-terra", "gpt-6-luna", "gpt-5.5"])

    def test_hidden_models_are_not_aliases(self):
        result, choice = self.single(f"reserve {Q}")
        self.assertEqual((choice["model"], result["question"]), ("gpt-5.6-terra", f"reserve {Q}"))

    def test_metacharacter_token_is_invalid(self):
        self.assertEqual(self.resolve("sol;touch${IFS}pwned " + Q)["state"], "invalid")

    def test_uppercase_effort_is_invalid(self):
        self.assertEqual(self.resolve(f"sol:HIGH {Q}")["state"], "invalid")

    def test_plain_question_names_nothing(self):
        result, choice = self.single("src/user.js is slow")
        self.assertEqual((choice["model"], result["question"]), ("gpt-5.6-terra", "src/user.js is slow"))

    # Effort rules.

    def test_per_model_defaults_sol_high_astra_medium(self):
        self.assertEqual(self.single(f"sol {Q}")[1]["effort"], "high")
        self.assertEqual(self.single(f"astra {Q}")[1]["effort"], "medium")

    def test_low_is_raised_to_medium_with_a_note(self):
        _, choice = self.single(f"sol:low {Q}")
        self.assertEqual(choice["effort"], "medium")
        self.assertTrue(choice["notes"], choice)

    def test_unsupported_level_uses_highest_supported_non_ultra_with_a_note(self):
        _, choice = self.single(f"gpt-5.5:max {Q}")
        self.assertEqual(choice["effort"], "xhigh")
        self.assertTrue(choice["notes"], choice)

    def test_unsupported_ultra_is_lowered(self):
        _, choice = self.single(f"luna:ultra {Q}")
        self.assertEqual(choice["effort"], "max")
        self.assertFalse(choice.get("explicit_ultra"))

    def test_explicit_supported_ultra_is_marked(self):
        _, choice = self.single(f"use astra:ultra {Q}")
        self.assertEqual((choice["effort"], choice["explicit_ultra"]), ("ultra", True))

    def test_leading_effort_selects_effort_without_a_model(self):
        result, choice = self.single(f"effort high {Q}")
        self.assertEqual((choice["model"], choice["effort"], result["question"]), ("gpt-5.6-terra", "high", Q))

    def test_configured_effort_is_never_inherited(self):
        _, choice = self.single(Q)
        self.assertEqual((choice["model"], choice["effort"]), ("gpt-5.6-terra", "medium"))

    def test_listed_default_below_medium_is_raised_without_a_named_model(self):
        self.write_config('model = "gpt-6-luna"\n')
        self.write_cache({"models": [model("gpt-6-luna", 1, default="low", levels=ALL[:-1])]})
        self.assertEqual(self.single(Q)[1]["effort"], "medium")

    def test_listed_default_above_medium_is_used(self):
        self.write_cache({"models": [model("gpt-6-luna", 1, default="xhigh", levels=ALL[:-1])]})
        self.write_config("")
        self.assertEqual(self.single(Q)[1]["effort"], "xhigh")

    def test_listed_default_ultra_is_never_used_by_default(self):
        self.write_cache({"models": [model("gpt-6-luna", 1, default="ultra")]})
        self.write_config("")
        self.assertEqual(self.single(Q)[1]["effort"], "max")

    def test_no_supported_level_at_or_above_medium_stops(self):
        self.write_cache({"models": [model("gpt-tiny", 1, default="low", levels=["low"])]})
        self.write_config("")
        self.assertEqual(self.resolve(Q)["state"], "unavailable")

    # Default order: session choice, configured model, lowest priority number, none.

    def test_session_choice_comes_first(self):
        _, choice = self.single(Q, {"model": "gpt-6-astra", "effort": "high"})
        self.assertEqual((choice["model"], choice["effort"]), ("gpt-6-astra", "high"))

    def test_session_effort_is_used_for_a_named_model(self):
        self.assertEqual(self.single(f"astra {Q}", {"effort": "xhigh"})[1]["effort"], "xhigh")

    def test_without_config_the_lowest_priority_number_is_used(self):
        (self.codex / "config.toml").unlink()
        self.assertEqual(self.single(Q)[1]["model"], "gpt-6-astra")

    def test_without_cache_or_config_no_model_is_named(self):
        (self.codex / "config.toml").unlink()
        (self.codex / "models_cache.json").unlink()
        _, choice = self.single(Q)
        self.assertEqual((choice["model"], choice["effort"]), (None, "medium"))

    def test_without_cache_a_named_model_is_unavailable(self):
        # Without a listing a bare word is not a model token; a colon token still names one.
        (self.codex / "models_cache.json").unlink()
        self.assertEqual(self.resolve(f"sol:high {Q}")["state"], "unavailable")
        self.assertEqual(self.single(f"sol {Q}")[0]["question"], f"sol {Q}")

    def test_malformed_configuration_is_reported(self):
        self.write_config("model = [unterminated\n")
        self.assertEqual(self.resolve(Q)["state"], "failed")
        self.write_config(CONFIG)
        self.write_cache("{not json")
        self.assertEqual(self.resolve(Q)["state"], "failed")

    def test_invalid_request_file_is_reported(self):
        request = self.root / "bad.json"
        request.write_text(json.dumps({"text": 3}), encoding="utf-8")
        result = subprocess.run([sys.executable, str(CLI), "resolve", str(request)], env=self.env,
                                capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(json.loads(result.stdout)["state"], "failed")

    # Parallel pairs (ticket 11).

    def test_pair_resolves_each_member_with_its_own_effort(self):
        result = self.resolve(f"astra:high, sol {Q}")
        self.assertEqual(result["state"], "resolved", result)
        self.assertEqual([(m["model"], m["effort"]) for m in result["models"]],
                         [("gpt-6-astra", "high"), ("gpt-6-sol", "high")])
        self.assertEqual(result["question"], Q)

    def test_three_models_stop(self):
        self.assertEqual(self.resolve(f"astra, sol, terra {Q}")["state"], "invalid")

    def test_duplicate_resolved_models_stop(self):
        self.assertEqual(self.resolve(f"sol, 6-sol {Q}")["state"], "invalid")

    def test_invalid_member_stops(self):
        self.assertEqual(self.resolve(f"astra, sol;touch {Q}")["state"], "invalid")

    def test_commas_in_a_question_are_not_a_pair(self):
        text = "Why, exactly, does fetchUser return an empty object?"
        result, _ = self.single(text)
        self.assertEqual(result["question"], text)

    def test_ambiguous_member_returns_its_candidates(self):
        result = self.resolve(f"6, sol {Q}")
        self.assertEqual((result["state"], result["member"]), ("ambiguous", 0), result)
        self.assertIn("gpt-6-astra", result["candidates"])

    # Baseline difference (ticket 11): does the named choice differ from the choice without it?

    def test_nothing_named_does_not_differ(self):
        self.assertFalse(self.single(Q)[1]["differs_from_baseline"])

    def test_naming_the_baseline_does_not_differ(self):
        self.assertFalse(self.single(f"terra {Q}")[1]["differs_from_baseline"])
        self.assertFalse(self.single(f"effort medium {Q}")[1]["differs_from_baseline"])

    def test_naming_another_model_or_effort_differs(self):
        self.assertTrue(self.single(f"sol {Q}")[1]["differs_from_baseline"])
        self.assertTrue(self.single(f"effort high {Q}")[1]["differs_from_baseline"])
        self.assertTrue(self.single(f"terra:xhigh {Q}")[1]["differs_from_baseline"])

    def test_session_setting_is_part_of_the_baseline(self):
        session = {"model": "gpt-6-astra", "effort": "medium"}
        self.assertFalse(self.single(f"astra {Q}", session)[1]["differs_from_baseline"])
        self.assertTrue(self.single(f"terra {Q}", session)[1]["differs_from_baseline"])

    def test_baseline_is_reported(self):
        result, _ = self.single(f"sol {Q}")
        self.assertEqual(result["baseline"], {"model": "gpt-5.6-terra", "effort": "medium"})

    def test_pair_members_report_their_own_difference(self):
        result = self.resolve(f"terra, sol {Q}")
        self.assertEqual([m["differs_from_baseline"] for m in result["models"]], [False, True])


if __name__ == "__main__":
    unittest.main()
