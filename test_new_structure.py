import os
import json
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def test_new_dashboard_structure():
    html_path = os.path.join(BASE_DIR, "index.html")
    assert os.path.exists(html_path), "index.html ne postoji!"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Nova početna stranica
    assert 'class="player-cards-grid"' in html, "Nedostaje grid sa velikim karticama igrača!"
    assert 'faruk-card' in html and 'mirza-card' in html, "Nedostaju zasebne kartice za Faruka i Mirzu!"
    assert "Faruk" in html and "Schamane" in html, "Faruk Shaman nije jasno označen!"
    assert "Mirza" in html and "Jäger" in html, "Mirza Jäger nije jasno označen!"
    assert "showView('faruk')" in html, "Klik na Faruka mora otvarati profil 'faruk'!"
    assert "showView('mirza')" in html, "Klik na Mirzu mora otvarati profil 'mirza'!"
    assert 'id="home-news-list"' in html, "Nedostaje sekcija stvarnih novosti na početnoj!"
    assert "Daten verarbeitet:" in html, "Diskretno vreme obrade mora biti prisutno!"

    # 2. Lični profili: Was ist jetzt wichtig
    assert 'id="view-faruk"' in html, "Nedostaje zaseban view za Faruka!"
    assert 'id="view-mirza"' in html, "Nedostaje zaseban view za Mirzu!"
    assert "now-card" in html, "Nedostaje 'Was ist jetzt wichtig' kartica!"
    assert "now-talent-faruk" in html and "now-quest-faruk" in html, "Nedostaju brza pitanja za Faruka!"
    assert "now-talent-mirza" in html and "now-quest-mirza" in html, "Nedostaju brza pitanja za Mirzu!"
    assert "updatePlayerProf" in html, "Profesije moraju biti podesive!"

    # 3. Talenti
    assert "Thundering Strikes" in html, "Farukov plan mora sadržavati Thundering Strikes!"
    assert "Stormstrike" in html, "Farukov plan mora sadržavati Stormstrike (Lvl 25)!"
    assert "Spirit Weapons" in html, "Farukov plan mora sadržavati Spirit Weapons (Lvl 30)!"
    assert "Deadly Aspects" in html, "Mirzin plan mora sadržavati Deadly Aspects!"
    assert "Summon Hawk" in html, "Mirzin plan mora sadržavati Summon Hawk (Lvl 25)!"
    assert "Intimidation" in html, "Mirzin plan mora sadržavati Intimidation!"
    assert "toggleTalentTree" in html, "Mora postojati pregled stvarnog talent stabla!"
    assert "toggleLvl60Build" in html, "Mora postojati dugme za pregled lvl 60 builda i respec!"

    # 4. Legacy preporuke
    assert "Thrill of Adventure" in html, "Legacy mora preporučiti Thrill of Adventure!"
    assert "Bountiful Harvest" in html, "Legacy mora sadržavati alternativu za profesije!"
    assert "Talented" in html, "Legacy mora sadržavati talent 'Talented'!"
    assert "setLegacyPoints" in html, "Legacy bodovi moraju biti konfigurabilni (0 do 16)!"

    # 5. Mirzini petovi
    assert "content-m-pets" in html, "Nedostaje sekcija Mirzinih begleitera!"
    assert "Prankenhieb" in html or "Swipe" in html, "Bär mora imati objašnjen Swipe AoE!"
    assert "Katze" in html or "Cat" in html, "Katze mora biti preporučena za burst/PvP!"
    assert "Eber" in html or "Boar" in html, "Eber mora biti naveden za Charge u PvP!"

    # 6. Korisni itemi i questovi
    assert "togglePlayerQuest" in html, "Mora postojati togglePlayerQuest za praćenje!"
    assert "wow_quest_Faruk_" in html and "wow_quest_Mirza_" in html, "Checkliste moraju čuvati stanje po igraču!"

    # 7. Novosti filtriranje
    assert "renderHomeNews" in html, "Nedostaje funkcija renderHomeNews za početnu!"
    assert "slice(0, 4)" in html, "Početna mora prikazati najviše 4 kartice!"

    print("✅ test_new_dashboard_structure: Svi strukturni i funkcionalni zahtevi su uspešno verifikovani!")

if __name__ == "__main__":
    test_new_dashboard_structure()
