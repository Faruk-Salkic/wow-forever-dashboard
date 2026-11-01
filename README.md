# Faruk & Mirza · WoW Forever

Jednostavan duo vodič: početna s dva profila i najviše četiri korisne novosti iz posljednjih sedam dana. Faruk je Dwarf Shaman, Mirza Hunter s otvorenim izborom rase. Profesije i level su podesivi.

[Otvori dashboard](https://faruk-salkic.github.io/wow-forever-dashboard/)

## Profili i kalkulatori

- Kompletna tri talent stabla za svaku klasu, uz rankove, preduslove, ograničenje po levelu i ukupno 51 bod.
- Odvojeni prijedlozi za duo levelanje, tačan redoslijed bodova i puni build do 60. To su praktični prijedlozi, ne izmjereni najbolji raid buildovi.
- Legacy kalkulator: tri stabla, zajednički limit od 16, početno 0 otključanih bodova. Ciljevi: mješovito, skupljanje, proizvodnja ili brzo levelanje. Talented utiče na računanje ranijih klasnih bodova.
- Planovi, profesije, leveli i quest kvačice ostaju lokalno u browseru. Izvoz/uvoz buildova služi za ručni prijenos; nema automatske sinhronizacije dva računara.
- Stalni vodiči su u sklopivim sekcijama. Quest lista podrazumijevano prikazuje bliži raspon levela.

Podaci kalkulatora preuzeti su iz [Talents Forever](https://talentsforever.com/about), pod licencom [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Adaptacija: samo Shaman, Hunter i objavljeni Legacy talenti, stabilni identifikatori i prilagođen interfejs. Izvorni tekstovi rankova ostaju na engleskom. Autor izvora: Chris Baldwin. Nazivi, ikone i tekst igre pripadaju Blizzard Entertainmentu. Datum i beta build prikazani su uz kalkulator; podaci nisu obećanje da je svaka vrijednost potvrđena na live serveru.

## Novosti i dnevni raspored

`.github/workflows/scrape.yml` pokreće se svaki dan u **11:50 Europe/Vienna**, s ciljem osvježavanja oko podneva. GitHub red čekanja i Pages deployment mogu kasniti; nema garancije tačno u 12:00. Promjena ljetnog i zimskog vremena obrađuje se kroz nativni `timezone`.

Scraper pregledava sve vraćene RSS stavke, Method i Icy Veins Forever indeks te Reddit RSS. Prati konkretne questove, predmete, petove, spellove, profesije i korisne zajedničke mehanike. Marketing, PTR/tehničke teme, podcasti i nepovezane verzije igre se odbacuju. Izvori imaju odvojene brojače ulaznih, relevantnih i obrađenih stavki te neuspjelih čitanja članaka.

Kanonski URL sprečava duplikate. Početna dodatno grupiše identične naslove/događaje, bez spajanja različitih questova samo zato što imaju istu klasu i kategoriju. Stalni pregledi klasa i vodiči bez poznatog datuma ne zauzimaju dnevni pregled.

Hash koristi glavni sadržaj članka. Prva migracija na novi način ekstrakcije postavlja referentno stanje bez lažne obavijesti. Neuspješno čitanje članka čuva prethodni dobar sadržaj. Promjena prevoda sama po sebi ne stvara novu verziju.

Sažeci koriste postojeći `GEMINI_API_KEY` u GitHub Secrets. `GEMINI_MODEL` može se promijeniti kroz environment; podrazumijevano je `gemini-3.5-flash-lite`. Stari `gemini-2.0-flash` je ugašen. Ako sažimanje ili prijevod nisu dostupni, ostaju ručno provjerene njemačke napomene ili jasno označen originalni tekst. Reddit ostaje nepotvrđen community izvor. Ne izmišljaju se NPC-evi, nagrade ili drop šanse.

## Provjera i pokretanje

Python 3.11+ i Node 22; frontend nema npm zavisnosti ni build korak.

```bash
pip install -r scraper/requirements.txt
python test_dashboard.py
python test_new_structure.py
python -m unittest discover -s tests -p 'test_*.py'
node scripts/check_frontend.js
node --test tests/*.test.js
```

```bash
python scraper/scrape.py
python scripts/update_planner_data.py
```

Dnevni workflow provjerava i novi izvoz talent podataka. Ako izvor promijeni format ili preporuke više nisu valjane na novim stablima, zadržava se posljednji dobar snapshot. Promjene tada treba pregledati uz prikazani datum izvora. `Verify dashboard` dodatno provjerava push i pull requestove.

`data/discoveries.json` sadrži kratke provjerene praktične napomene i izvore. `data/guides.json` zadržava stabilne ID-eve postojećih dungeon questova; prije puta treba provjeriti konkretne zahtjeve u igri. `data/news.json` je puna dnevna baza; browser dobija manji `data/feed.json` bez kopije punog izvornog teksta, a vrijeme obrade nije isto što i vrijeme Pages objave.
