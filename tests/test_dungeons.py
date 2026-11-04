import copy
import json
import unittest
from unittest.mock import patch
from scraper import check_dungeons as D


def fixture():
    metadata, parts = {}, []
    for group in range(10):
        name = 'The Deadmines' if group == 0 else 'Ruins of Lordaeron' if group == 1 else f'Example {group}'
        parts.append(f'<h2>{name} Dungeon Quests</h2><p>At Level: Level 19</p><table>')
        for i in range(5):
            qid = group*100+i+1000
            title = 'Underground Assault' if (group,i)==(0,0) else f'Quest {qid}'
            metadata[str(qid)] = {'name_enus':title, '_side':1, 'reqclass':4 if i==1 else 64 if i==2 else 0}
            notes = ('<br>Complete <a href="/forever/quest=888">Earlier Quest</a> first.' if i==3
                     else '<br>Leads to <a href="/forever/quest=889">Later Quest</a>.' if i==4 else '')
            flags = 'Pre' if i==3 else 'Drop' if i==4 else ''
            parts.append(f'<tr><td><a href="/forever/quest={qid}">{title}</a></td><td>16</td><td>19</td><td>Alliance</td><td>{flags}</td><td>Stormwind - <a href="/forever/npc=123">Example NPC</a> /way 46.6 56.8{notes}</td></tr>')
        # Keep one orphan row; the source also has rows outside its table.
        parts.append('</table>')
        if group==0:
            for qid, side, cls in [(7000,2,0),(7001,1,8),(7002,1,0)]:
                metadata[str(qid)]={'name_enus':f'Quest {qid}','_side':side,'reqclass':cls}
                parts.append(f'<tr><td><a href="/forever/quest={qid}">Quest {qid}</a></td><td>10</td><td>19</td><td></td><td></td><td>Ironforge - NPC</td></tr>')
    # Same actual quest may appear in another dungeon; DOM IDs must still be unique.
    parts.append('<tr><td><a href="/forever/quest=1000">Underground Assault</a></td><td>16</td><td>19</td><td></td><td></td><td>Stormwind - NPC</td></tr>')
    return '<script>WH.Gatherer.addData(5,16,'+json.dumps(metadata)+');</script>'+''.join(parts)


class DungeonTests(unittest.TestCase):
    def test_faction_class_minimum_and_prerequisite_direction(self):
        data=D.parse_guide(fixture(), '2026-11-04T10:00:00Z')
        quests=[q for d in data['dungeons'] for q in d['quests']]
        self.assertEqual(len(quests),52)
        self.assertFalse({7000,7001}&{q['game_id'] for q in quests})
        q=quests[0]
        self.assertEqual(q['id'],'dm_underground_assault')
        self.assertEqual(q['min_lvl'],16)
        self.assertEqual(data['dungeons'][0]['recommended_level'],19)
        self.assertEqual(q['coordinates'],[46.6,56.8])
        self.assertEqual(quests[1]['classes'],['Hunter'])
        self.assertEqual(quests[2]['classes'],['Shaman'])
        self.assertEqual(quests[3]['prerequisites'],['Earlier Quest'])
        self.assertEqual(quests[4]['prerequisites'],[])
        self.assertEqual(quests[4]['followups'],['Later Quest'])
        self.assertEqual(quests[4]['phase'],'inside')
        ids=[q['id'] for q in quests]
        self.assertEqual(len(ids),len(set(ids)))
        same=[q for q in quests if q['game_id']==1000]
        self.assertEqual(same[0]['progress_id'],same[1]['progress_id'])

    def test_rechecks_are_quiet_and_source_failure_preserves_facts(self):
        with patch.object(D,'load_json',return_value={}):
            first=D.refresh({},fixture(),'2026-11-04T10:00:00Z')
            again=D.refresh(first,fixture(),'2026-11-04T12:00:00Z')
            self.assertEqual(first['source_hash'],again['source_hash'])
            self.assertIsNone(again['changed_at'])
            changed=D.refresh(first,fixture().replace('/way 46.6 56.8','/way 47.6 56.8'),'2026-11-04T14:00:00Z')
            self.assertEqual(changed['changed_at'],'2026-11-04T14:00:00Z')
        snapshot=copy.deepcopy(first)
        with patch.object(D.requests,'get',side_effect=D.requests.Timeout):
            failed=D.refresh(first,now='2026-11-04T16:00:00Z')
        self.assertEqual(failed['status'],'error')
        self.assertEqual(failed['dungeons'],snapshot['dungeons'])
        self.assertEqual(failed['last_success_at'],snapshot['last_success_at'])
        self.assertEqual(first,snapshot)
        self.assertRaises(ValueError,D.parse_guide,'<h2>Broken guide</h2>')

    def test_individual_quest_requirement_overrides_aggregate_guide(self):
        raw='$.extend(g_quests[92753], {"id":92753,"reqlevel":9,"level":18});'
        self.assertEqual(D.detail_level(raw,92753),9)
        self.assertRaises(ValueError,D.detail_level,raw,92742)
        overrides={'quests':{'1000':{'min_lvl':9,'prepare_from_level':9}},
                   'dungeons':{'ruins_of_lordaeron':{'replace_minimum':{'16':15},'notice':'Official correction'}}}
        parsed=D.parse_guide(fixture(),overrides=overrides)
        self.assertEqual(parsed['dungeons'][0]['quests'][0]['min_lvl'],9)
        self.assertEqual(parsed['dungeons'][1]['quests'][0]['min_lvl'],15)
        self.assertEqual(parsed['dungeons'][1]['notice'],'Official correction')


if __name__=='__main__': unittest.main()
