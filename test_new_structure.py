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
        for kind in ['class','legacy']:
            assert soup.find(id=f'planner-{kind}-{player}')
        assert soup.find(id='discoveries-'+player)
    assert soup.find(id='home-news-list')
    for script in ['planner-core.js','planner-ui.js','news-core.js']:
        assert soup.find('script',src='assets/'+script)
    print('Dashboard views, calculator mounts and unique DOM IDs OK')

if __name__=='__main__': test_new_dashboard_structure()
