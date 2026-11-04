import contextlib
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from scraper import scrape as S


class BriefTests(unittest.TestCase):
    def setUp(self):
        self.state = dict(S.AI_STATE)
        self.failures = S.AI_FAILURES
        S.AI_FAILURES = 0
        S.AI_STATE.update(status="ready", attempts=0, succeeded=0, failed=0, reason="")

    def tearDown(self):
        S.AI_STATE.clear(); S.AI_STATE.update(self.state)
        S.AI_FAILURES = self.failures

    def test_valid_structured_brief_and_request_budget(self):
        brief = {"title_de":"Neue Quest", "summary_de":"Die Quelle beschreibt eine neue Quest.", "action_de":"Voraussetzungen in der Quelle prüfen."}
        generate = Mock(return_value=SimpleNamespace(text=json.dumps(brief)))
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
        with patch.object(S, "client", client), patch.object(S, "AI_MAX_CALLS", 1):
            self.assertEqual(S.generate_german_brief("Quest", "Source details about a new quest. " * 3, "Source"), brief)
            self.assertIsNone(S.generate_german_brief("Quest", "Same source details. " * 4, "Source"))
        self.assertEqual(generate.call_count, 1)
        config = generate.call_args.kwargs["config"]
        self.assertNotIn("temperature", config)
        self.assertIn("response_schema", config)
        self.assertEqual(S.AI_STATE["succeeded"], 1)

    def test_auth_failure_is_diagnosed_without_key_leak_and_stops_further_calls(self):
        class Failure(Exception):
            code = 400
            message = "API key not valid. private-test-key"
        generate = Mock(side_effect=Failure())
        client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
        output = io.StringIO()
        with patch.object(S, "client", client), patch.object(S, "GEMINI_KEY", "private-test-key"), contextlib.redirect_stdout(output):
            self.assertIsNone(S.generate_german_brief("Quest", "Source material long enough. " * 4, "Source"))
            self.assertIsNone(S.generate_german_brief("Quest", "Source material long enough. " * 4, "Source"))
        self.assertEqual(generate.call_count, 1)
        self.assertNotIn("private-test-key", output.getvalue())
        self.assertEqual(S.AI_STATE["reason"], "invalid_key")

    def test_incomplete_json_is_not_published_as_a_valid_brief(self):
        client = SimpleNamespace(models=SimpleNamespace(generate_content=Mock(return_value=SimpleNamespace(text='{"title_de":"Quest"}'))))
        with patch.object(S, "client", client), contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(S.generate_german_brief("Quest", "Source material long enough. " * 4, "Source"))
        self.assertEqual(S.AI_STATE["status"], "error")


if __name__ == "__main__": unittest.main()
