import os
import json
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. Obavezna dinamička putanja: radi i na Windows-u i na Linux runneru
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Importuj funkcije iz scrapera
sys.path.insert(0, BASE_DIR)
from scraper.scrape import is_relevant_context, detect_classes, detect_category, normalize_url, CLASSES

def test_news_json():
    path = os.path.join(BASE_DIR, "data", "news.json")
    assert os.path.exists(path), "data/news.json ne postoji!"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    items = data.get("items", [])
    assert len(items) > 0, "news.json nema stavki!"
    
    seen_ids = set()
    seen_urls = set()
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
        
        # Check URL & deduplication by normalized URL
        url = item.get("url", "")
        assert url.startswith("http"), f"Neispravan URL: {url}"
        norm_url = normalize_url(url)
        assert norm_url not in seen_urls, f"Pronađen duplikat normalizovanog URL-a: {norm_url}"
        seen_urls.add(norm_url)
        
        # Check German text
        assert item.get("title"), "Nedostaje naslov!"
        assert item.get("teaser_de") or item.get("article_de"), "Nedostaje nemački opis!"
        
        # Check date
        assert item.get("date"), "Nedostaje datum!"
        assert item.get("fetched_at"), "Nedostaje fetched_at timestamp!"

        # Fokus samo na Huntera i Shamana (bez Rogue i Priest)
        for cls in item.get("classes", []):
            assert cls in ["Hunter", "Shaman"], f"Zabranjena klasa u vestima: {cls}"

    # Check castle status
    cs = data.get("castle_status", {})
    assert cs.get("verified") is False, "Burg status ne sme lažno tvrditi verified: true!"
    
    # Check sources status
    ss = data.get("sources_status", {})
    assert len(ss) > 0, "Nedostaje sources_status!"
    for src, st in ss.items():
        assert "OK" in st or "HTTP" in st or "Keine" in st or "Fehler" in st, f"Sumnjiv status izvora: {src} -> {st}"

    print(f"✅ test_news_json prošao: {len(items)} validnih vesti (fokus Shaman & Hunter).")

def test_guides_and_bis_json():
    # 1. Guides JSON
    path = os.path.join(BASE_DIR, "data", "guides.json")
    assert os.path.exists(path), "data/guides.json ne postoji!"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check profiles
    profiles = data.get("player_profiles", {})
    assert "Priest" not in profiles and "Rogue" not in profiles, "Rogue i Priest moraju biti uklonjeni iz profila!"
    faruk = profiles.get("Faruk", {})
    mirza = profiles.get("Mirza", {})

    assert "Shaman" in faruk.get("primary_class", ""), "Faruk mora biti Shaman!"
    assert "Dwarf" in faruk.get("race", ""), "Faruk je Dwarf!"
    assert "Bergbau" in str(faruk.get("professions", [])), "Faruk ima Mining!"
    assert "Engineering" in str(faruk.get("professions", [])), "Faruk ima Engineering!"

    assert "Hunter" in mirza.get("primary_class", ""), "Mirza mora biti Hunter!"
    assert "Kürschnerei" in str(mirza.get("professions", [])), "Mirza ima Skinning!"
    assert "Kräuterkunde" in str(mirza.get("professions", [])), "Mirza ima Herbalism!"
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

    # Check addons section
    addons = data.get("addons", {})
    assert addons.get("items"), "Nedostaje addons sekcija u guides.json!"
    addon_names = [a.get("name") for a in addons.get("items", [])]
    assert "Questie" in addon_names, "Questie addon mora biti u listi!"
    assert "TotemTimers" in addon_names, "TotemTimers za Shamana mora biti u listi!"
    assert "WeaponSwingTimer (SixxFix)" in addon_names, "WeaponSwingTimer za Huntera mora biti u listi!"

    # 2. BiS JSON
    bis_path = os.path.join(BASE_DIR, "data", "bis.json")
    with open(bis_path, "r", encoding="utf-8") as f:
        bis_data = json.load(f)
    classes = bis_data.get("classes", {})
    assert "Hunter" in classes and "Shaman" in classes, "Hunter i Shaman moraju postojati u bis.json!"
    assert "Priest" not in classes, "Priest mora biti uklonjen iz bis.json!"
    assert "Rogue" not in classes, "Rogue mora biti uklonjen iz bis.json!"

    print(f"✅ test_guides_and_bis_json prošao: {total_quests} stabilnih questova, provereni profili i BiS.")

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

    # 4. Orthogonal filter logic & error preservation
    assert "wow_active_profile" in content, "Nedostaje čuvanje profila!"
    assert "wow_active_filter" in content, "Nedostaje čuvanje filtera!"
    assert "wow_active_section" in content, "Nedostaje čuvanje aktivne sekcije!"
    assert "newsLoadError" in content, "Nedostaje newsLoadError čuvanje stanja greške!"

    # 5. Rogue & Priest removed from UI
    assert 'data-f="cls-priest"' not in content, "Priest filter mora biti uklonjen!"
    assert 'data-f="cls-rogue"' not in content, "Rogue filter mora biti uklonjen!"
    assert 'data-cls="Priest"' not in content, "Priest BiS tab mora biti uklonjen!"
    assert 'data-cls="Rogue"' not in content, "Rogue BiS tab mora biti uklonjen!"
    assert 'id="cc-priest"' not in content, "Priest class card mora biti uklonjen!"
    assert 'id="cc-rogue"' not in content, "Rogue class card mora biti uklonjen!"

    # 6. Compact hero, level bar & addons section
    assert "table-responsive" in content, "Nedostaje .table-responsive klasa!"
    assert "bis-pending-card" in content, "Nedostaje bis-pending-card zamena za praznu tabelu!"
    assert "retry-btn" in content, "Nedostaje retry dugme za greške u učitavanju!"
    assert "section-addons" in content, "Nedostaje section-addons sekcija!"
    assert "level-bar" in content, "Nedostaje level-bar kontrola za ručni unos nivoa!"
    assert "setPlayerLevel" in content, "Nedostaje funkcija setPlayerLevel!"

    print("✅ test_index_html prošao sve funkcionalne provere.")

def test_content_relevance_and_categorization():
    """
    Ciljani testovi za Zahtev 3, 8 i 9:
    - Hunter pet vodič prolazi
    - Podcast o tehnologiji i članak o layeringu se odbacuju
    - Nemačko 'bis Level 60' NE aktivira BiS
    - Raspored pečeva (patch-kadenz) NE aktivira Hotfix
    - Sadržaj za druge klase bez Shamana/Huntera se odbacuje
    """
    # 1. Hunter pet guide mora proći
    pet_guide = is_relevant_context(
        "Jäger Pet-Zähm-Guide: Die besten seltenen Tiere in Dun Morogh & Loch Modan",
        "Dunkelpirscher Katze mit Angriffsgeschwindigkeit 1.30 und Furious Howl Wolf für Allianz-Hunter"
    )
    assert pet_guide is True, "Konkretan Hunter pet vodič mora proći relevanciju!"

    # 2. Shaman leveling & totemi mora proći
    shaman_guide = is_relevant_context(
        "WoW Forever Schamane: Totem-Quests und Windfury-Skalierung",
        "Erdstoss-Totem und Steinhaut-Totem schützen die Gruppe und das Begleiter-Pet"
    )
    assert shaman_guide is True, "Shaman totem & leveling vodič mora proći relevanciju!"

    # 3. Tehnički podcast se mora odbaciti
    tech_podcast = is_relevant_context(
        "The WoW: Forever Podcast Episode 6 jetzt verfügbar - Technologie- und Community-Building",
        "In dieser Episode sprechen die Entwickler über Netcode und Community-Strategien"
    )
    assert tech_podcast is False, "Tehnički podcast mora biti odbačen!"

    # 4. Članak o layeringu se mora odbaciti
    layering_article = is_relevant_context(
        "Blizzard arbeitet an den wichtigsten Layering-Problemen in WoW: Forever",
        "Entwickler erklären das Sharding und die Server-Architektur für den Launch"
    )
    assert layering_article is False, "Članak o layeringu mora biti odbačen!"

    # 5. Trailer i hype se moraju odbaciti
    trailer_article = is_relevant_context(
        "World of Warcraft: Forever – Offizieller Release-Trailer 'WARPATH' veröffentlicht",
        "Seht euch den spektakulären Cinematic-Trailer zum weltweiten Launch an"
    )
    assert trailer_article is False, "Trailer i hype se moraju odbaciti!"

    # 6. Retail / The War Within se mora odbaciti
    retail_article = is_relevant_context(
        "The War Within Patch 11.2 Delves Tier List",
        "Die besten Klassen für Tiefen und Mythic+ Dungeons"
    )
    assert retail_article is False, "Retail WoW mora biti odbačen!"

    # 7. Članak isključivo za Rogue & Priest bez Shamana/Huntera se mora odbaciti
    rogue_priest_article = is_relevant_context(
        "Rogue & Priest Klassenänderungen im Detail",
        "Schattenpriester und Meucheln-Schurken erhalten signifikante Schadensanpassungen"
    )
    assert rogue_priest_article is False, "Članak samo za druge klase mora biti odbačen!"

    # 8. Zahtev: TBC Classic Hunter vodič mora biti odbačen
    tbc_hunter = is_relevant_context(
        "TBC Classic Hunter Leveling Guide: Beast Mastery Talente und Pet-Makros",
        "The Burning Crusade bringt neue Talente und Fähigkeiten für Jäger in Outland"
    )
    assert tbc_hunter is False, "TBC Classic Hunter vodič mora biti odbačen!"

    # 9. Zahtev: Primarno Rogue vodič s usputnim spominjanjem Huntera mora biti odbačen
    rogue_incidental_hunter = is_relevant_context(
        "Rogue Leveling and Talent Guide for Classic",
        "Stealth, lockpicking, and best daggers for Rogue leveling. Can sometimes group up with hunters."
    )
    assert rogue_incidental_hunter is False, "Primarno Rogue vodič s usputnim spominjanjem Huntera mora biti odbačen!"

    # 10. Zahtev: Koristan Forever Shaman vodič ne smije biti odbačen samo zato što poredi mehaniku s Retailom
    forever_shaman_retail_comparison = is_relevant_context(
        "WoW Forever Shaman Leveling & Totem Guide",
        "Unlike retail WoW where totems are mostly utility cooldowns, in WoW Forever mana management and totem placement are crucial."
    )
    assert forever_shaman_retail_comparison is True, "Forever Shaman vodič s poređenjem sa Retailom mora biti prihvaćen!"

    # 11. Zahtev: Praktični zajednički vodiči, primjerice prodavači torbi, trebaju ostati prihvaćeni
    bag_vendor_guide = is_relevant_context(
        "WoW Forever: Frühzeitige Taschen-Händler und 8-Slot Bag Fundorte",
        "Hier findet ihr frühe Vendor-Standorte für billige 6-Slot und 8-Slot Taschen in Dun Morogh und Loch Modan."
    )
    assert bag_vendor_guide is True, "Praktični zajednički vodič za torbe/vendore mora biti prihvaćen!"

    # 12. Test kategorije: Nemačko 'bis Level 60' NE sme biti BiS
    cat_bis_german = detect_category("Leveling-Route vom Start bis Level 60 Guide für Allianz")
    assert cat_bis_german != "bis", f"Nemačko 'bis' je pogrešno prepoznato kao BiS kategorija: {cat_bis_german}"
    assert cat_bis_german == "guide", f"Očekivana kategorija 'guide', dobijeno: {cat_bis_german}"

    # 13. Test kategorije: Pravi BiS mora biti BiS
    cat_real_bis = detect_category("WoW Forever: Phase 1 Best-in-Slot Gear Guide für Jäger")
    assert cat_real_bis == "bis", f"Pravi BiS vodič mora dobiti kategoriju 'bis', dobijeno: {cat_real_bis}"

    # 14. Test kategorije: Patch-Kadenz / raspored NE sme biti Hotfix
    cat_kadenz = detect_category("WoW: Forever strebt nach einer 4-monatigen Patch-Kadenz und Roadmap")
    assert cat_kadenz != "hotfix", f"Patch-kadenz je pogrešno prepoznata kao hotfix: {cat_kadenz}"

    # 15. Test kategorije: Pravi hotfix mora biti hotfix
    cat_real_hotfix = detect_category("Blizzard Notfall-Patch: Klassen-Tuning & Live Hotfix für Jäger-Begleiter")
    assert cat_real_hotfix == "hotfix", f"Pravi live hotfix mora dobiti 'hotfix', dobijeno: {cat_real_hotfix}"

    print("✅ test_content_relevance_and_categorization prošao sve testove filtriranja i kategorizacije.")

if __name__ == "__main__":
    test_news_json()
    test_guides_and_bis_json()
    test_index_html()
    test_content_relevance_and_categorization()
    print("🎉 SVI TESTOVI SU USPEŠNO PROŠLI!")