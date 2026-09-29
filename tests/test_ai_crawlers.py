"""ai_crawlers.py -- the shared AI-crawler registry + RFC 9309 robots evaluator.

Pins: registry shape (four classes, unique tokens, core sets non-empty), RFC 9309
semantics (group merge, specific-over-wildcard, longest match, Allow wins ties,
'*' / '$' wildcards, empty Disallow), the verdict precedence (a blocked classic search
engine outranks everything), the Google-Extended note, the generator round-trip, and
that geo_check + tech_audit now read the SAME registry.

Offline, stdlib-only; runs under unittest and pytest.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "seo", "ai_crawlers.py")
sys.path.insert(0, os.path.join(ROOT, "scripts", "seo"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "workflow"))
import ai_crawlers  # noqa: E402
import geo_check  # noqa: E402
import tech_audit  # noqa: E402


class RegistryTest(unittest.TestCase):
    def test_classes_and_unique_tokens(self):
        toks = [c["token"] for c in ai_crawlers.CRAWLERS]
        self.assertEqual(len(toks), len(set(t.lower() for t in toks)))
        for c in ai_crawlers.CRAWLERS:
            self.assertIn(c["class"], ai_crawlers.CLASSES)
        for cls in ai_crawlers.CLASSES:
            self.assertTrue(ai_crawlers.tokens(cls, core_only=True), cls)

    def test_scripts_share_one_registry(self):
        self.assertIs(geo_check.TRAINING_BOTS, ai_crawlers.TRAINING_BOTS)
        self.assertIs(tech_audit.RETRIEVAL_BOTS, ai_crawlers.RETRIEVAL_BOTS)


class Rfc9309Test(unittest.TestCase):
    def _status(self, text, bot, path="/"):
        groups, _ = ai_crawlers.parse_robots(text)
        return ai_crawlers.bot_status(bot, groups, path)

    def test_specific_group_beats_wildcard(self):
        t = "User-agent: *\nDisallow: /\n\nUser-agent: GPTBot\nAllow: /\n"
        self.assertEqual(self._status(t, "GPTBot"), "allowed")
        self.assertEqual(self._status(t, "ClaudeBot"), "blocked")

    def test_groups_for_same_agent_merge(self):
        t = "User-agent: GPTBot\nAllow: /blog\n\nUser-agent: GPTBot\nDisallow: /\n"
        self.assertEqual(self._status(t, "GPTBot", "/"), "blocked")
        self.assertEqual(self._status(t, "GPTBot", "/blog/post"), "allowed")

    def test_longest_match_and_allow_wins_tie(self):
        t = "User-agent: *\nDisallow: /private\nAllow: /private/public\nAllow: /x\nDisallow: /x\n"
        self.assertEqual(self._status(t, "Bingbot", "/private/a"), "blocked")
        self.assertEqual(self._status(t, "Bingbot", "/private/public/a"), "allowed")
        self.assertEqual(self._status(t, "Bingbot", "/x"), "allowed")

    def test_wildcards(self):
        t = "User-agent: *\nDisallow: /*.pdf$\nDisallow: /*?\n"
        self.assertEqual(self._status(t, "Googlebot", "/a/b.pdf"), "blocked")
        self.assertEqual(self._status(t, "Googlebot", "/a/b.pdf.html"), "allowed")
        self.assertEqual(self._status(t, "Googlebot", "/s?q=1"), "blocked")

    def test_disallow_star_blocks_root(self):
        self.assertEqual(self._status("User-agent: GPTBot\nDisallow: /*\n", "GPTBot"), "blocked")

    def test_empty_disallow_allows(self):
        self.assertEqual(self._status("User-agent: GPTBot\nDisallow:\n", "GPTBot"), "allowed")

    def test_consecutive_agents_share_group_and_case_insensitive(self):
        t = "user-agent: gptbot\nUser-Agent: CCBot\ndisallow: /\n"
        self.assertEqual(self._status(t, "GPTBot"), "blocked")
        self.assertEqual(self._status(t, "CCBot"), "blocked")
        self.assertEqual(self._status(t, "ClaudeBot"), "unmentioned")

    def test_sitemaps_collected_and_junk_tolerated(self):
        groups, maps = ai_crawlers.parse_robots(
            "garbage\nDisallow: /before-any-agent\nSitemap: https://e.test/s.xml\n")
        self.assertEqual(maps, ["https://e.test/s.xml"])
        self.assertEqual(groups, [])


class VerdictTest(unittest.TestCase):
    def test_blocked_search_engine_outranks_everything(self):
        t = "User-agent: Googlebot\nDisallow: /\n\nUser-agent: GPTBot\nDisallow: /\n"
        v = ai_crawlers.verdict(t)
        self.assertEqual(v["verdict"], "search-engine-blocked")
        self.assertIn("AI Overviews", v["note"])

    def test_google_extended_note(self):
        v = ai_crawlers.verdict("User-agent: Google-Extended\nDisallow: /\n")
        self.assertIn("does not remove pages from AI Overviews", v["note"])

    def test_user_fetchers_blocked_are_called_out(self):
        v = ai_crawlers.verdict("User-agent: ChatGPT-User\nDisallow: /\n")
        self.assertEqual(v["classes"]["user"]["stance"], "partial")
        self.assertIn("ChatGPT-User", v["note"])

    def test_non_core_tokens_reported_but_do_not_swing_stance(self):
        v = ai_crawlers.verdict("User-agent: Bytespider\nDisallow: /\n")
        self.assertEqual(v["classes"]["training"]["stance"], "open")
        self.assertIn("Bytespider", v["classes"]["training"]["blocked"])

    def test_geo_scorecard_zeroes_access_when_search_engine_blocked(self):
        pol = geo_check.analyze_robots("User-agent: Bingbot\nDisallow: /\n")
        card = geo_check.build_scorecard({"ai_crawler_policy": pol})
        access = [c for c in card["categories"] if c["name"] == "ai_crawler_access"][0]
        self.assertEqual(access["score"], 0)

    def test_tech_audit_flags_search_engine_block_critical(self):
        notes = tech_audit.analyze_robots("User-agent: *\nDisallow: /\n")
        self.assertEqual(notes[0]["severity"], "critical")


class GeneratorTest(unittest.TestCase):
    def test_citable_no_training_round_trips(self):
        text = ai_crawlers.generate("citable-no-training", "https://e.test/sitemap.xml")
        v = ai_crawlers.verdict(text)
        self.assertEqual(v["verdict"], "citable-training-blocked")
        self.assertEqual(v["classes"]["user"]["stance"], "open")
        self.assertEqual(v["sitemaps"], ["https://e.test/sitemap.xml"])
        # every training token, core or not, is blocked by the generated block
        self.assertEqual(sorted(v["classes"]["training"]["blocked"]),
                         sorted(ai_crawlers.tokens("training")))

    def test_search_only_keeps_search_engines_open(self):
        v = ai_crawlers.verdict(ai_crawlers.generate("search-only"))
        self.assertEqual(v["classes"]["search_engine"]["stance"], "open")
        self.assertEqual(v["verdict"], "retrieval-blocked")

    def test_generate_is_deterministic_and_rejects_unknown(self):
        self.assertEqual(ai_crawlers.generate("fully-open"), ai_crawlers.generate("fully-open"))
        with self.assertRaises(ValueError):
            ai_crawlers.generate("nope")


class CliTest(unittest.TestCase):
    def _run(self, args):
        return subprocess.run([sys.executable, SCRIPT] + args,
                              capture_output=True, encoding="utf-8")

    def test_robots_cli_json(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "robots.txt")
            with open(p, "w", encoding="utf-8") as f:
                f.write("User-agent: GPTBot\nDisallow: /\n")
            r = self._run(["--robots", p])
            self.assertEqual(r.returncode, 0)
            self.assertEqual(json.loads(r.stdout)["verdict"], "citable-training-partial")

    def test_missing_file_is_json_error_nonzero(self):
        r = self._run(["--robots", "/nonexistent/robots.txt"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("error", json.loads(r.stdout))

    def test_list_and_generate(self):
        self.assertEqual(self._run(["--list"]).returncode, 0)
        r = self._run(["--generate", "citable-no-training"])
        self.assertEqual(r.returncode, 0)
        self.assertIn("User-agent: GPTBot", r.stdout)


if __name__ == "__main__":
    unittest.main()
