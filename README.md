# Faruk & Mirza — WoW Forever Dashboard 🐉

Privatni interaktivni dashboard i vodič za WoW Forever.  
Fokusiran isključivo na potrebe igrača:
- **Faruk** 🌊: Shaman (Dwarf · Enhancement/Resto · Mining & Engineering)
- **Mirza** 🏹: Hunter (Beast Mastery · Skinning & Herbalism)

Stranica: [https://faruk-salkic.github.io/wow-forever-dashboard/](https://faruk-salkic.github.io/wow-forever-dashboard/)  
Repozitorij: [https://github.com/Faruk-Salkic/wow-forever-dashboard](https://github.com/Faruk-Salkic/wow-forever-dashboard)

---

## 🌟 Ključne mogućnosti i arhitektura

1. **Strogi fokus na Shamana i Huntera**:
   - Rogue i Priest su potpuno uklonjeni iz interfejsa, BiS tabela, profila i konfiguracije scrapera.
   - Rigorozni filter sadržaja eliminiše opšte tehničke rasprave (layering, server arhitektura), podcaste, trailere i PR najave bez korisnih detalja.
   - Ako nema novih relevantnih vijesti za naše klase, prikazuje se jasna poruka: *„Heute keine neuen relevanten Updates für Shaman und Hunter.“*

2. **Interaktivni vodiči i level filter**:
   - Odvojeni trajni vodiči od dnevnih novosti (Camping & Legacy, Leveling & Dungeons, Jäger-Pets, BiS-Items, Gold & Berufe, Addons).
   - Ručni unos trenutnog nivoa po igraču (Faruk & Mirza) uz opciju filtriranja zona i tamnica prilagođenih trenutnom nivou.
   - Odvojene kvačice za praćenje dungeon questova (Faruk / Mirza) sačuvane u lokalnom browser spremištu (`localStorage`).

3. **CurseForge Addoni**:
   - Pažljivo odabrani dodaci kompatibilni sa WoW Forever / Classic klijentom: Questie, TotemTimers, WeaponSwingTimer, ClassicCastbars, Leatrix Plus, Details!.
   - Objašnjen konkretan benefit i napomena o eventualnom preklapanju.

4. **Dnevno osvježavanje u 12:00 Europe/Vienna**:
   - GitHub Actions cron je konfigurisan na `50 9,10 * * *` sa automatskom provjerom vremenske zone `Europe/Vienna` u gate poslu.
   - Automatski se prilagođava prelasku sa ljetnog (CEST, UTC+2) na zimsko vrijeme (CET, UTC+1).
   - Pokreće se 10 minuta prije podneva kako bi scraping, validacija i GitHub Pages deployment bili završeni tačno do 12:00.

---

## 🛠️ Pokretanje testova i scrapera lokalno

Pokretanje svih integritetnih provjera (radi na Windows i Linux sistemima):
```bash
python test_dashboard.py
```

Ručno pokretanje scrapera:
```bash
python scraper/scrape.py
```

---

## 📋 Struktura projekta

```
wow-forever-dashboard/
├── index.html                  ← Interaktivni dashboard (UI, profili, level-filter, modal)
├── test_dashboard.py           ← Integritetni testovi i validacija filtriranja
├── data/
│   ├── news.json               ← Filtrirane i provjerene vijesti (njemački jezik)
│   ├── guides.json             ← Dungeon questovi, pet cheat-sheet, rute i Addoni
│   ├── bis.json                ← BiS liste (isključivo Hunter i Shaman)
│   └── seen_ids.json           ← Evidencija ID-eva radi sprečavanja duplikata
├── scraper/
│   ├── scrape.py               ← Pametni scraper sa strogim filterima i AI sažecima
│   └── requirements.txt        ← Python zavisnosti (feedparser, requests, bs4, google-genai)
└── .github/
    └── workflows/
        └── scrape.yml          ← GitHub Actions automatizacija (12:00 Europe/Vienna gate)
```
