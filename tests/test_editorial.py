import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scraper import publish_editorial as E


class EditorialTests(unittest.TestCase):
    def test_dungeon_changes_publish_once_and_keep_the_actual_change_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            (root/'data/editorial_updates.json').write_text(json.dumps({'items':[]}))
            guides={'dungeon_quests':{'status':'ok','source_url':'https://www.wowhead.com/forever/guide/dungeons/every-dungeon-quest-location',
                    'latest_change':{'checked_at':'2026-11-04T14:00:00Z','entries':[
                        {'dungeon':'The Stockades','title':'Example quest','description':'Annahme ab: 16 → 15',
                         'url':'https://www.wowhead.com/forever/quest=123'}]}}}
            path=root/'data/guides.json';path.write_text(json.dumps(guides))
            with patch.object(E,'ROOT',root):
                E.publish();E.publish()
                first=json.loads((root/'data/news.json').read_text())
                self.assertEqual((first['total_count'],first['new_count'],first['updated_count']),(1,1,0))
                self.assertEqual(first['items'][0]['date'],'2026-11-04')
                self.assertIn('Annahme ab: 16 → 15',first['items'][0]['article_de'])
                self.assertEqual(first['items'][0]['internal_action'],'dungeons')
                guides['dungeon_quests'].update(status='error',checked_at='2026-11-05T12:00:00Z')
                path.write_text(json.dumps(guides));E.publish()
                after=json.loads((root/'data/news.json').read_text())
                for field in ['id','date','article_de','content_version','source_content_hash']:
                    self.assertEqual(after['items'][0].get(field),first['items'][0].get(field))
                self.assertEqual(after['new_count'],1)
                self.assertEqual(after['updated_count'],0)
                guides['dungeon_quests']['latest_change']['entries'][0]['description']='Abholort: Stormwind'
                guides['dungeon_quests']['latest_change']['checked_at']='2026-11-05T14:00:00Z'
                path.write_text(json.dumps(guides));E.publish();E.publish()
                changed=json.loads((root/'data/news.json').read_text())
                self.assertEqual(changed['total_count'],1)
                self.assertEqual(changed['updated_count'],1)
                self.assertEqual(changed['items'][0]['id'],first['items'][0]['id'])

    def test_publishing_preserves_other_sources_and_updates_one_note_idempotently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            note={'url':'https://example.org/?focus=dungeons','title':'Dungeon-Quests vorbereiten','article_de':'WoW Forever: Vorbereitung und Vorquests.','teaser_de':'Quests für uns.','date':'2026-11-04','classes':[],'category':'guide','references':[],'internal_action':'dungeons'}
            other={'id':'keep','url':'https://reddit.com/r/wowforever/comments/example','title':'ShotRange','date':'2026-11-04','custom':'preserved'}
            (root/'data/news.json').write_text(json.dumps({'items':[other],'new_count':0,'updated_count':0}))
            source=root/'data/editorial_updates.json';source.write_text(json.dumps({'items':[note]}))
            with patch.object(E,'ROOT',root):
                E.publish();E.publish()
                result=json.loads((root/'data/news.json').read_text())
                self.assertIn(other,result['items'])
                self.assertEqual((len(result['items']),result['new_count'],result['updated_count']),(2,1,0))
                original=next(i for i in result['items'] if i['id']!='keep')
                note['article_de']+=' Neue Abholstelle.';source.write_text(json.dumps({'items':[note]}))
                E.publish();E.publish()
                changed=json.loads((root/'data/news.json').read_text())
                self.assertIn(other,changed['items'])
                updated=next(i for i in changed['items'] if i['id']!='keep')
                self.assertEqual(updated['id'],original['id'])
                self.assertEqual(updated['content_version'],2)
                self.assertEqual(changed['updated_count'],1)


if __name__=='__main__':unittest.main()
