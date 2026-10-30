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
from scraper.scrape import (
    is_relevant_context,
    detect_classes,
    detect_category,
    normalize_url,
    merge_and_deduplicate_items,
    compute_source_hash,
    clean_source_text,
    CLASSES
)

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

    # Check data processing timestamp
    assert data.get("data_processed_at") or data.get("published_at"), "Nedostaje timestamp obrade podataka (data_processed_at)!"

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

    # 7. Tracking izmena i oznake ažuriranja
    assert "hasPendingUpdate" in content, "Nedostaje funkcija hasPendingUpdate!"
    assert "wow_read_versions" in content, "Nedostaje spremanje pročitane verzije u localStorage!"
    assert "update-badge" in content, "Nedostaje stil ili bedž update-badge za ažurirane vodiče!"
    assert "Daten verarbeitet:" in content, "Vrijeme obrade podataka mora biti prikazano kao 'Daten verarbeitet:'!"

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

def test_guide_update_tracking():
    """
    Ciljani test za praćenje izmjena postojećih vodiča:
    - Isti URL s promijenjenim sadržajem mora ostati JEDAN zapis i pojaviti se među dnevnim ažuriranjima.
    - Ponovno preuzimanje identičnog sadržaja ne smije stvarati obavijest.
    - Oznaka 'is_updated' i 'update_note' se dodeljuju kod promene.
    - Dnevni pregled uključuje ažurirane vodiče i ne tvrdi lažno 'keine neuen Updates'.
    """
    test_url = "https://www.wowhead.com/forever/guide=shaman-leveling-enhancement"
    initial_title = "WoW Forever Schamane Leveling Guide"
    initial_content = "Windfury Rank 1 skalira sa 20% weapon damage. Totems aufstellen ab Level 4."
    
    # 1. Početno stanje: vodič u bazi
    initial_item = {
        "id": "shaman_guide_canon_id",
        "url": test_url,
        "normalized_url": normalize_url(test_url),
        "title": initial_title,
        "teaser_de": "Schamane Leveling Guide für WoW Forever.",
        "article_de": initial_content,
        "date": "2026-10-29",
        "fetched_at": "2026-10-29T10:00:00Z",
        "source": "Wowhead Forever",
        "source_icon": "🌐",
        "category": "guide",
        "verified_type": "Guide / Analyse",
        "radar_status": "normal",
        "classes": ["Shaman"],
        "raw_title": initial_title,
        "raw_content": initial_content,
        "source_content_hash": compute_source_hash(initial_title, initial_content)
    }

    # 2. Ponovno preuzimanje IDENTIČNOG sadržaja sa istog URL-a (npr. sutrašnji scrape)
    # Razlika u fetched_at ili blagoj rečeničnoj promeni AI teasera ne sme izazvati ažuriranje!
    same_scraped_item = {
        "url": test_url,
        "normalized_url": normalize_url(test_url),
        "title": initial_title,
        "teaser_de": "Schamane Leveling Guide für WoW Forever (vom KI-Modell neu formuliert).",
        "article_de": "📌 **Zusammenfassung:**\n" + initial_content,
        "date": "2026-10-30",
        "fetched_at": "2026-10-30T10:00:00Z",
        "source": "Wowhead Forever",
        "source_icon": "🌐",
        "category": "guide",
        "verified_type": "Guide / Analyse",
        "radar_status": "normal",
        "classes": ["Shaman"],
        "raw_title": initial_title,
        "raw_content": initial_content,
        "source_content_hash": compute_source_hash(initial_title, initial_content)
    }

    merged_1, new_cnt_1, upd_cnt_1, summary_1 = merge_and_deduplicate_items(
        existing_items=[initial_item],
        incoming_items=[same_scraped_item],
        sources_health={"WoWhead Forever": "OK"},
        now_iso="2026-10-30T11:50:00Z"
    )

    # Verifikacija identičnog sadržaja:
    assert len(merged_1) == 1, f"Očekivan tačno 1 zapis na istom URL-u, dobijeno: {len(merged_1)}"
    assert new_cnt_1 == 0, f"Ponovno preuzimanje ne sme prijaviti novu stavku: {new_cnt_1}"
    assert upd_cnt_1 == 0, f"Identičan sadržaj ne sme prijaviti ažuriranje: {upd_cnt_1}"
    assert "Heute keine neuen relevanten Updates" in summary_1, f"Dnevni pregled mora glasiti da nema novih ažuriranja: {summary_1}"
    assert merged_1[0].get("is_updated") is not True, "Identičan sadržaj ne sme dobiti is_updated: True!"

    # 3. Preuzimanje sa STVARNO PROMIJENJENIM sadržajem na istom URL-u (promijenjene brojke/scaling)
    updated_content = "Windfury Rank 1 wurde gebufft auf 35% weapon damage. Totems haben nun reduzierte Manakosten um 15%."
    changed_scraped_item = {
        "url": test_url,
        "normalized_url": normalize_url(test_url),
        "title": "WoW Forever Schamane Leveling Guide (Aktualisiert für Hotfix)",
        "teaser_de": "Schamane Guide mit neuen Werten nach Hotfix.",
        "article_de": updated_content,
        "date": "2026-10-30",
        "fetched_at": "2026-10-30T12:00:00Z",
        "source": "Wowhead Forever",
        "source_icon": "🌐",
        "category": "guide",
        "verified_type": "Guide / Analyse",
        "radar_status": "normal",
        "classes": ["Shaman"],
        "raw_title": "WoW Forever Schamane Leveling Guide (Aktualisiert für Hotfix)",
        "raw_content": updated_content,
        "source_content_hash": compute_source_hash("WoW Forever Schamane Leveling Guide (Aktualisiert für Hotfix)", updated_content)
    }

    merged_2, new_cnt_2, upd_cnt_2, summary_2 = merge_and_deduplicate_items(
        existing_items=merged_1,
        incoming_items=[changed_scraped_item],
        sources_health={"WoWhead Forever": "OK"},
        now_iso="2026-10-30T12:00:00Z"
    )

    # Verifikacija promjene sadržaja:
    assert len(merged_2) == 1, f"Mora ostati tačno 1 zapis na istom URL-u, dobijeno: {len(merged_2)}"
    assert new_cnt_2 == 0, f"Ažurirani vodič na istom URL-u nije nova stavka (new_cnt mora biti 0): {new_cnt_2}"
    assert upd_cnt_2 == 1, f"Ažurirani vodič mora biti prepoznat kao aktualisiert (upd_cnt == 1): {upd_cnt_2}"
    
    updated_rec = merged_2[0]
    assert updated_rec.get("is_updated") is True, "Ažurirani zapis mora imati is_updated == True!"
    assert updated_rec.get("update_note"), "Ažurirani zapis mora imati kratak opis izmjene (update_note)!"
    assert updated_rec.get("content_version", 1) >= 2, "Ažurirani zapis mora imati uvećan content_version!"
    assert "Heute keine neuen relevanten Updates" not in summary_2, f"Dnevni pregled ne sme reći da nema novosti kada postoji ažuriranje: {summary_2}"
    assert "aktualisiert" in summary_2.lower(), f"Dnevni pregled mora spomenuti ažurirane vodiče: {summary_2}"

    print("✅ test_guide_update_tracking prošao: isti URL ostaje 1 zapis, razlikuje novu obavijest od identičnog preuzimanja.")

if __name__ == "__main__":
    test_news_json()
    test_guides_and_bis_json()
    test_index_html()
    test_content_relevance_and_categorization()
    test_guide_update_tracking()
    print("🎉 SVI TESTOVI SU USPEŠNO PROŠLI!")