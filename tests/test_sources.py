import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scraper import scrape as S


class SourceTests(unittest.TestCase):
    def test_shared_addons_items_and_mobs_do_not_require_a_class_name(self):
        for title in ['WoW Forever: Recommended addons for a clean UI', 'WoW Forever: A useful early item from a rare mob', 'WoW Forever: Newly discovered weapon drop location']:
            self.assertTrue(S.is_relevant_context(title,'Practical details, locations and requirements.'))

    def test_noise_is_not_accepted_as_gameplay(self):
        for title in ['349 players planned their characters in my app', "Lok'tar Ogar! Chapter 2 of my TTRPG campaign", 'No PTRs and new datamining restrictions in WoW Forever', 'New Player’s Starter Guide for WoW Forever']:
            self.assertFalse(S.is_relevant_context(title,'WoW Forever Hunter Shaman pet quest guide'))

    def test_general_practical_guides_are_discovered_but_other_class_tools_are_not(self):
        html='''<main>
        <a href="/wow-forever/best-early-bags-in-wow-forever">Early bags</a>
        <a href="/wow-forever/new-quest-reward">New quest reward</a>
        <a href="/wow-forever/list-of-enchants-in-wow-forever">Enchants</a>
        <a href="/wow-forever/rogue-leveling-guide-and-talents">Rogue</a>
        <a href="/wow-forever/legacy-calculator">Calculator</a>
        <a href="https://evil.example/wow-forever/hunter-guide">Wrong host</a>
        <a href="/wow-forever/new-quest-reward?utm_source=x">Duplicate</a></main>'''
        links=S.discover_guide_links(html,'https://www.method.gg/wow-forever','Method Forever')
        self.assertEqual(len(links),3)
        self.assertTrue(any('early-bags' in x['url'] for x in links))

    def test_only_main_content_changes_hash(self):
        a='<nav>Shaman Hunter</nav><article><p>Hunter pet cooldown 10 seconds.</p><time>Monday</time><aside>Random advertisement</aside></article>'
        b=a.replace('Shaman Hunter','Warlock Rogue').replace('Monday','Tuesday').replace('Random advertisement','Another advertisement')
        self.assertEqual(S.compute_source_hash('Pet guide',S.extract_main_content(a)),S.compute_source_hash('Pet guide',S.extract_main_content(b)))
        c=b.replace('10 seconds','15 seconds')
        self.assertNotEqual(S.compute_source_hash('Pet guide',S.extract_main_content(a)),S.compute_source_hash('Pet guide',S.extract_main_content(c)))
        self.assertEqual(S.extract_main_content('<html><body>Please sign in</body></html>'),'')

    def test_extractor_migration_is_a_baseline_and_keeps_canonical_id(self):
        old={'id':'old','url':'https://example.org/hunter','title':'WoW Forever Hunter Pet Guide','article_de':'Hunter pet guide','teaser_de':'Hunter pet guide','raw_content':'Old whole body','source_content_hash':'oldhash','content_version':1,'is_updated':False,'date':'2026-10-01'}
        fresh={**old,'id':S.make_canonical_id(old['url']),'normalized_url':S.normalize_url(old['url']),'raw_content':'Clean main content','source_content_hash':'newhash','content_extractor':2,'teaser_de':'Aktuelle, korrigierte Pet-Information.'}
        merged,new,updated,_=S.merge_and_deduplicate_items([copy.deepcopy(old)],[fresh],{},'2026-11-01T10:00:00+00:00')
        self.assertEqual((len(merged),new,updated),(1,0,0))
        self.assertIn('old',merged[0]['migrated_ids'])
        self.assertEqual(merged[0]['content_version'],1)
        self.assertFalse(merged[0]['is_updated'])
        self.assertEqual(merged[0]['teaser_de'],fresh['teaser_de'])

    def test_network_failure_keeps_last_good_articles_and_reports_source_errors(self):
        old={'id':S.make_canonical_id('https://example.org/hunter'),'url':'https://example.org/hunter','title':'WoW Forever Hunter Pet Guide','article_de':'Hunter pet guide','teaser_de':'Hunter pet guide','raw_content':'Full good content','source_content_hash':'abc','date':'2026-10-01','content_version':1}
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'news.json';output.write_text(json.dumps({'items':[old],'castle_status':{'verified':False}}))
            with patch.object(S,'OUTPUT_FILE',str(output)),patch.object(S,'CLIENT_OUTPUT_FILE',str(Path(tmp)/'feed.json')),patch.object(S,'SEEN_IDS_FILE',str(Path(tmp)/'seen.json')),patch.object(S,'BACKUP_FILE',str(Path(tmp)/'backup.json')),patch.object(S.requests,'get',side_effect=S.requests.Timeout):
                S.run_scraper()
            result=json.loads(output.read_text())
            self.assertEqual(len(result['items']),1)
            self.assertEqual(result['items'][0]['source_content_hash'],'abc')
            self.assertTrue(all('Fehler' in v for v in result['sources_status'].values()))
            self.assertTrue(all(not m['fetch_ok'] for m in result['sources_metrics'].values()))

    def test_small_client_feed_preserves_ids_and_read_versions(self):
        raw={'items':[{'id':'stable','migrated_ids':['old'],'source_content_hash':'abc','raw_content':'Very long full source','title':'Title'}]}
        feed=S.make_client_payload(raw)
        self.assertNotIn('raw_content',feed['items'][0])
        self.assertEqual(feed['items'][0]['id'],'stable')
        self.assertEqual(feed['items'][0]['source_content_hash'],'abc')
        self.assertEqual(feed['items'][0]['migrated_ids'],['old'])

    def test_hash_only_baseline_still_detects_real_changes(self):
        old={'id':'old','url':'https://example.org/hunter','title':'WoW Forever Hunter Pet Guide','raw_title':'WoW Forever Hunter Pet Guide','teaser_de':'Hunter pet guide','article_de':'Hunter pet guide','source_content_hash':'before','has_source_baseline':True,'content_extractor':2,'content_version':1,'date':'2026-10-01'}
        new={**old,'normalized_url':S.normalize_url(old['url']),'source_content_hash':'after','raw_content':'Updated pet guide with changed ability','title':'WoW Forever Hunter Pet Guide','radar_status':'normal','category':'guide','classes':['Hunter'],'verified_type':'Guide / Analyse'}
        merged,added,updated,_=S.merge_and_deduplicate_items([copy.deepcopy(old)],[new],{},'2026-11-01T10:00:00+00:00')
        self.assertEqual((added,updated),(0,1))
        self.assertEqual(merged[0]['content_version'],2)
        public=S.without_source_copies({'items':merged})
        self.assertNotIn('raw_content',public['items'][0])
        self.assertTrue(public['items'][0]['has_source_baseline'])


if __name__=='__main__': unittest.main()
