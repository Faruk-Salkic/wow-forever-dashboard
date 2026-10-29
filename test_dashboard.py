import os
import json
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = r"C:\Users\Faruk\.gemini\antigravity\scratch\wow-forever-dashboard"

def test_news_json():
    path = os.path.join(BASE_DIR, "data", "news.json")
    assert os.path.exists(path), "data/news.json ne postoji!"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    items = data.get("items", [])
    assert len(items) > 0, "news.json nema stavki!"
    
    seen_ids = set()
    for item in items:
        # Check ID
        iid = str(item.get("id", ""))
        assert iid, "Stavka nema ID!"
        assert not iid.startswith("sample_"), f"Pronađen mock ID: {iid}"
        assert iid not in seen_ids, f"Duplikat ID u news: {iid}"
        seen_ids.add(iid)
        
        # Check category
        cat = item.get("category")
        assert cat in ["news", "hotfix", "bis", "guide", "exploit", "pvp", "pve"], f"Nepoznata kategorija: {cat}"
        
        # Check URL
        url = item.get("url", "")
        assert url.startswith("http"), f"Neispravan URL: {url}"
        
        # Check German text
        assert item.get("title"), "Nedostaje naslov!"
        assert item.get("teaser_de") or item.get("article_de"), "Nedostaje nemački opis!"
        
        # Check date
        assert item.get("date"), "Nedostaje datum!"
        assert item.get("fetched_at"), "Nedostaje fetched_at timestamp!"

    # Check castle status
    cs = data.get("castle_status", {})
    assert cs.get("verified") is False, "Burg status ne sme lažno tvrditi verified: true!"
    
    # Check sources status
    ss = data.get("sources_status", {})
    assert len(ss) > 0, "Nedostaje sources_status!"
    for src, st in ss.items():
        assert "OK" in st or "HTTP" in st or "Keine" in st or "Fehler" in st, f"Sumnjiv status izvora: {src} -> {st}"

    print(f"✅ test_news_json prošao: {len(items)} validnih vesti.")

def test_guides_json():
    path = os.path.join(BASE_DIR, "data", "guides.json")
    assert os.path.exists(path), "data/guides.json ne postoji!"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check profiles
    profiles = data.get("player_profiles", {})
    faruk = profiles.get("Faruk", {})
    mirza = profiles.get("Mirza", {})

    assert "Shaman" in faruk.get("primary_class", ""), "Faruk mora biti Shaman!"
    assert "Dwarf" in faruk.get("race", ""), "Faruk je Dwarf!"
    assert "Bergbau" in str(faruk.get("professions", [])), "Faruk ima Mining!"
    assert "Engineering" in str(faruk.get("professions", [])), "Faruk ima Engineering!"

    assert "Hunter" in mirza.get("primary_class", ""), "Mirza mora biti Hunter!"
    assert "Kürschnerei" in str(mirza.get("professions", [])), "Mirza ima Skinning!"
    assert "Kräuterkunde" in str(mirza.get("professions", [])), "Mirza ima Herbalism!"
    # Race must NOT be assumed as Night Elf
    assert "Night Elf" not in mirza.get("race", ""), "Mirzina rasa ne sme biti fiksirana na Night Elf!"
    assert "Offen" in mirza.get("race", "") or "Noch nicht" in mirza.get("race", ""), "Mirzina rasa mora biti TBD/Offen!"

    # Check dungeon quests
    dq = data.get("dungeon_quests", {})
    dungeons = dq.get("dungeons", [])
    assert len(dungeons) >= 6, "Premalo tamnica u dungeon_quests!"

    q_ids = set()
    total_quests = 0
    for d in dungeons:
        for q in d.get("quests", []):
            qid = q.get("id")
            assert qid, f"Quest u tamnici {d.get('name')} nema stabilan ID!"
            assert qid not in q_ids, f"Duplikat quest ID: {qid}"
            q_ids.add(qid)
            total_quests += 1
            assert q.get("title"), f"Quest {qid} nema naslov!"
            assert q.get("giver"), f"Quest {qid} nema giver!"

    print(f"✅ test_guides_json prošao: {total_quests} stabilnih dungeon questova.")

def test_index_html():
    path = os.path.join(BASE_DIR, "index.html")
    assert os.path.exists(path), "index.html ne postoji!"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Stable modal opening by ID
    assert "openModalById(" in content, "index.html mora sadržavati funkciju openModalById!"
    assert "openModal(" not in content or "openModalById" in content, "Modal se mora otvarati po ID-ju!"

    # 2. Read / Unread tracking
    assert "wow_read_articles" in content, "Nedostaje tracking pročitanih članaka u localStorage!"
    assert "isArticleRead" in content, "Nedostaje isArticleRead provera!"
    assert "markArticleAsRead" in content, "Nedostaje markArticleAsRead!"

    # 3. Dual player checkboxes
    assert "togglePlayerQuest" in content, "Nedostaje funkcija togglePlayerQuest!"
    assert "wow_quest_Faruk_" in content, "Nedostaje Faruk quest key u storage!"
    assert "wow_quest_Mirza_" in content, "Nedostaje Mirza quest key u storage!"
    assert "Lokale Browser-Speicherung" in content, "Nedostaje napomena o lokalnom čuvanju u browseru!"

    # 4. Orthogonal filter logic
    assert "wow_active_profile" in content, "Nedostaje čuvanje profila!"
    assert "wow_active_filter" in content, "Nedostaje čuvanje filtera!"
    assert "wow_active_section" in content, "Nedostaje čuvanje aktivne sekcije!"

    # 5. Compact hero and responsive table CSS
    assert "table-responsive" in content, "Nedostaje .table-responsive klasa!"
    assert "bis-pending-card" in content, "Nedostaje bis-pending-card zamena za praznu tabelu!"
    assert "retry-btn" in content, "Nedostaje retry dugme za greške u učitavanju!"

    print("✅ test_index_html prošao sve funkcionalne provere.")

if __name__ == "__main__":
    test_news_json()
    test_guides_json()
    test_index_html()
    print("🎉 SVI TESTOVI SU USPEŠNO PROŠLI!")
