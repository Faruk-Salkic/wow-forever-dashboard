import copy
import json
import unittest
from scraper import check_quest_rewards as Q
from scraper import scrape as S

NOW = "2026-11-02T14:00:00+00:00"
LATER = "2026-11-03T14:00:00+00:00"
QUEST = {"id": 123, "name": "A useful new quest", "level": 16, "reqlevel": 9, "side": 1,
         "reqclass": 0, "type": 81, "itemchoices": [[456, 1]], "itemrewards": [],
         "envChange": {"status": "new", "labels": []}}
ITEMS = {"456": {"name_enus": "A real quest reward", "quality": 3, "jsonequip": {"dps": 9.57, "sta": 3}}}


class QuestRewardTests(unittest.TestCase):
    def test_embedded_json_is_parsed_without_executing_page_scripts(self):
        html = "WH.Gatherer.addData(3, 16, " + json.dumps(ITEMS) + ");new Listview({template: 'quest',id:'quests',data:" + json.dumps([QUEST]) + "});"
        quests, items = Q.parse_catalog(html)
        self.assertEqual(quests, [QUEST])
        self.assertEqual(items, ITEMS)
        for bad in ["<html>Sign in</html>", "new Listview({template: 'quest',data:[]});"]:
            with self.assertRaises(ValueError):
                Q.parse_catalog(bad)

    def test_alliance_class_and_reward_filters_and_exact_source_facts(self):
        variants = [QUEST, {**QUEST, "id": 124, "side": 2}, {**QUEST, "id": 125, "side": 0},
                    {**QUEST, "id": 126, "reqclass": 16}, {**QUEST, "id": 127, "reqclass": 64},
                    {**QUEST, "id": 128, "envChange": {"status": "unchanged"}}]
        payload, _ = Q.build_snapshot(variants, ITEMS, now=NOW)
        self.assertEqual({q["id"] for q in payload["items"]}, {123, 127})
        item = next(q for q in payload["items"] if q["id"] == 123)
        self.assertEqual((item["level"], item["min_level"]), (16, 9))
        self.assertEqual(item["rewards"][0]["stats"]["dps"], 9.57)
        self.assertEqual(item["rewards"][0]["name"], ITEMS["456"]["name_enus"])
        self.assertEqual(Q.reward_items(QUEST, {}), [])

    def test_initial_baseline_popularity_changes_and_new_discoveries(self):
        first, state = Q.build_snapshot([QUEST], ITEMS, now=NOW)
        self.assertEqual((first["discovered_count"], first["updated_count"]), (0, 0))
        self.assertIsNone(first["items"][0]["changed_at"])
        same, state = Q.build_snapshot([{**QUEST, "popularity": 999}], ITEMS, state, LATER)
        self.assertEqual((same["discovered_count"], same["updated_count"]), (0, 0))
        newer, _ = Q.build_snapshot([QUEST, {**QUEST, "id": 999}], ITEMS, state, LATER)
        self.assertEqual(newer["discovered_count"], 1)
        self.assertEqual(next(q for q in newer["items"] if q["id"] == 999)["change_kind"], "discovered")

    def test_reward_stat_changes_are_detected_without_duplicate_quests(self):
        _, state = Q.build_snapshot([QUEST], ITEMS, now=NOW)
        changed_items = copy.deepcopy(ITEMS)
        changed_items["456"]["jsonequip"]["dps"] = 12.5
        result, _ = Q.build_snapshot([QUEST], changed_items, state, LATER)
        self.assertEqual((len(result["items"]), result["updated_count"], result["discovered_count"]), (1, 1, 0))
        self.assertEqual(result["items"][0]["change_kind"], "updated")

    def test_duplicate_source_rows_cannot_duplicate_a_quest_card(self):
        result, _ = Q.build_snapshot([QUEST, QUEST], ITEMS, now=NOW)
        self.assertEqual(len(result["items"]), 1)

    def test_a_popular_weapon_reward_is_not_crowded_out_by_low_level_generic_rewards(self):
        rows = [{**QUEST, "id": i, "itemchoices": [[457, 1]], "popularity": 1} for i in range(10)]
        rows.append({**QUEST, "popularity": 100})
        items = {**ITEMS, "457": {"name_enus": "A generic green item", "quality": 2, "jsonequip": {}}}
        payload, _ = Q.build_snapshot(rows, items, now=NOW)
        self.assertEqual(len(payload["items"]), 8)
        self.assertEqual(payload["items"][0]["id"], QUEST["id"])

    def test_failed_fetch_and_incomplete_html_preserve_last_success_and_baseline(self):
        first, state = Q.build_snapshot([QUEST], ITEMS, now=NOW)
        for fetcher in [lambda: "<main>Temporarily unavailable</main>", lambda: (_ for _ in ()).throw(TimeoutError("network"))]:
            result, unchanged = Q.refresh(first, state, fetcher, LATER)
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["last_success_at"], NOW)
            self.assertEqual(result["items"], first["items"])
            self.assertEqual(unchanged, state)

    def test_dedicated_reddit_context_does_not_need_forever_in_each_title(self):
        post = {"title": "New quest reward shield worth picking up", "summary": "Useful early weapon reward.", "source": "Reddit r/wowforever"}
        self.assertTrue(S.relevant_feed_item(post))
        self.assertFalse(S.relevant_feed_item({**post, "source": "Reddit r/woweconomy"}))
        self.assertTrue(S.relevant_feed_item({**post, "source": "Reddit r/classicwow", "forever_link": True}))
        self.assertFalse(S.relevant_feed_item({**post, "title": "TBC quest reward for Shaman"}))
        self.assertFalse(S.relevant_feed_item({**post, "title": "Rogue leveling quest guide", "summary": "Hunter is mentioned once."}))


if __name__ == "__main__":
    unittest.main()
