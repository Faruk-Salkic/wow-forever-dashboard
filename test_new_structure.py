"""Small layout contract; behavior is covered by the Node and source tests."""
from pathlib import Path
from bs4 import BeautifulSoup

def test_new_dashboard_structure():
    root=Path(__file__).resolve().parent
    soup=BeautifulSoup((root/'index.html').read_text(encoding='utf-8'),'html.parser')
    ids=[x['id'] for x in soup.select('[id]')]
    assert len(ids)==len(set(ids)), 'Duplicate DOM IDs'
    for view in ['home','faruk','mirza','news']:
        assert soup.find(id='view-'+view), view
    for player in ['faruk','mirza']:
        assert soup.find(id='class-news-'+player)
        assert soup.find(id='discoveries-'+player)
        assert soup.find(id='all-quests-'+player)
    for element in ['home-news-list','discoveries-home','shared-addons','f-items-list','m-items-list']:
        assert soup.find(id=element)
    assert soup.find('script',src='assets/news-core.js')
    assert not soup.select('[id^="planner-"], [id*="talent-milestones"]')
    assert not soup.find('script',src='assets/planner-core.js')
    assert not soup.find('script',src='assets/planner-ui.js')
    assert not (root/'data/planner.json').exists()
    links=soup.select('a.resource-link')
    assert {a['href'] for a in links}=={
        'https://www.wowhead.com/forever/talent-calc/hunter',
        'https://www.wowhead.com/forever/talent-calc/shaman'}
    print('Separate news feeds, shared guidance and no bundled calculators OK')

if __name__=='__main__': test_new_dashboard_structure()
