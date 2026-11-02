import copy
import unittest
from scraper.check_guides import check_guides


SOURCE = {"id": "shaman-guide", "player": "Faruk", "class": "Shaman", "source": "Method",
          "url": "https://www.method.gg/wow-forever/shaman-leveling", "title": "Shaman · Leveling"}
DOC = {"title": "WoW Forever Shaman Leveling Guide", "text": "Useful leveling talents and spells. " * 150, "date": "2026-10-20"}
FIRST = "2026-11-02T10:00:00+00:00"
LATER = "2026-11-03T10:00:00+00:00"


class GuideChecksTests(unittest.TestCase):
    def baseline(self):
        return check_guides([SOURCE], fetcher=lambda _: copy.deepcopy(DOC), now=FIRST)

    def test_initial_and_identical_checks_do_not_claim_content_updates(self):
        first = self.baseline()
        item = first["items"][0]
        self.assertEqual(item["content_version"], 1)
        self.assertIsNone(item["changed_at"])
        again = check_guides([SOURCE], first, lambda _: DOC, LATER)["items"][0]
        self.assertEqual(again["source_content_hash"], item["source_content_hash"])
        self.assertEqual(again["content_version"], 1)
        self.assertIsNone(again["changed_at"])
        self.assertEqual(again["last_success_at"], LATER)
        self.assertNotIn("text", again)
        self.assertNotIn("raw_content", again)

    def test_changes_at_the_end_of_a_long_guide_increment_once(self):
        first = self.baseline()
        changed = {**DOC, "text": DOC["text"] + " New spell recommendation at the end."}
        result = check_guides([SOURCE], first, lambda _: changed, LATER)
        item = result["items"][0]
        self.assertEqual((item["id"], item["url"]), (SOURCE["id"], SOURCE["url"]))
        self.assertEqual(item["content_version"], 2)
        self.assertEqual(item["changed_at"], LATER)
        again = check_guides([SOURCE], result, lambda _: changed, "2026-11-04T10:00:00+00:00")
        self.assertEqual(again["items"][0]["content_version"], 2)
        self.assertEqual(again["items"][0]["changed_at"], LATER)

    def test_failed_wrong_class_and_incomplete_reads_keep_last_success(self):
        baseline = self.baseline()
        for bad in [{"error": "HTTP 503"}, {**DOC, "title": "Retail Shaman Guide"},
                    {**DOC, "title": "WoW Forever Rogue Leveling"}, {**DOC, "text": "Loading…"}]:
            failed = check_guides([SOURCE], baseline, lambda _: bad, LATER)["items"][0]
            self.assertEqual(failed["status"], "error")
            self.assertEqual(failed["checked_at"], LATER)
            self.assertEqual(failed["last_success_at"], FIRST)
            self.assertEqual(failed["source_content_hash"], baseline["items"][0]["source_content_hash"])
            self.assertEqual(failed["content_version"], 1)
            self.assertIsNone(failed["changed_at"])
        recovered = check_guides([SOURCE], {"items": [failed]}, lambda _: DOC, LATER)["items"][0]
        self.assertEqual(recovered["status"], "ok")
        self.assertEqual(recovered["last_success_at"], LATER)
        self.assertEqual(recovered["content_version"], 1)

    def test_replaced_source_url_gets_a_baseline_not_a_false_update(self):
        source = {**SOURCE, "url": "https://www.method.gg/wow-forever/new-shaman-guide"}
        result = check_guides([source], self.baseline(), lambda _: DOC, LATER)["items"][0]
        self.assertEqual(result["content_version"], 1)
        self.assertIsNone(result["changed_at"])

    def test_talent_allocation_changes_even_when_the_article_text_is_identical(self):
        first = check_guides([SOURCE], fetcher=lambda _: {**DOC, "talent_builds": ["allocation-A"]}, now=FIRST)
        second = check_guides([SOURCE], first, lambda _: {**DOC, "talent_builds": ["allocation-B"]}, LATER)
        self.assertEqual(second["items"][0]["content_version"], 2)
        self.assertEqual(second["items"][0]["changed_at"], LATER)
        self.assertNotIn("talent_builds", second["items"][0])

    def test_build_attributes_are_extracted_but_unrelated_script_versions_are_not(self):
        from unittest.mock import patch
        from scraper import scrape as S
        class Response:
            status_code = 200
            text = ('<main><h1>WoW Forever Shaman Leveling Guide</h1><p>' + DOC["text"] + '</p>'
                    '<div data-talent="method-build"></div>'
                    '<div data-talentcalculator-pointsurl="#tc-icy-build"></div></main>'
                    '<script src="talents.js?v=123"></script>')
        with patch.object(S.requests, 'get', return_value=Response()):
            doc = S.fetch_document(SOURCE["url"])
        self.assertEqual(doc["talent_builds"], ['#tc-icy-build', 'method-build'])
        self.assertNotIn('v=123', str(doc))

    def test_unfinished_level_60_build_is_disclosed_and_cleared_when_completed(self):
        doc = {**DOC, "text": DOC["text"] + "Level 60: This section will be updated in due course!"}
        incomplete = check_guides([SOURCE], self.baseline(), lambda _: doc, LATER)
        self.assertIn("nicht vollständig", incomplete["items"][0]["notice"])
        completed = check_guides([SOURCE], incomplete, lambda _: DOC, LATER)
        self.assertEqual(completed["items"][0]["notice"], "")


if __name__ == "__main__":
    unittest.main()
