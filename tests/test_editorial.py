import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scraper import publish_editorial as E


class EditorialTests(unittest.TestCase):
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
