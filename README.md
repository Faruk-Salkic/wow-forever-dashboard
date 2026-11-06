# Faruk & Mirza · WoW Forever

Jednostavan duo vodič: početna s dva profila i najviše četiri korisne novosti iz posljednjih sedam dana. Faruk je Dwarf Shaman, Mirza Hunter s otvorenim izborom rase. Profesije i level su podesivi.

[Otvori dashboard](https://faruk-salkic.github.io/wow-forever-dashboard/)

## Raspored

- Početna: zajedničke novosti, novi questovi, korisni itemi i Addons. Detalji i postojeće dungeon checkliste ostaju sklopljeni dok ih ne otvorite.
- Faruk: Shaman vijesti, dva stalna linka za levelanje/talente i kratke klasne napomene.
- Mirza: Hunter vijesti, dva stalna linka za levelanje/talente, pet promjene i kratke klasne napomene.
- Klase se usmjeravaju prema naslovu/linku i oznakama izvora. Opći vodiči ne dobijaju klasnu oznaku samo zbog usputnog spominjanja klase.
- Na stranici se ne učitavaju lokalni talent ni Legacy kalkulatori. Svaki profil ima direktan link na Wowhead za planiranje talenata.
- Leveli, profesije, pročitane vijesti i odvojene quest kvačice ostaju sačuvani u istim lokalnim browser ključevima. Nema automatske sinhronizacije između uređaja.

## Novosti i dnevni raspored

`.github/workflows/scrape.yml` tokom početne dvije sedmice provjerava izvore **svaka dva sata**, u 17. minuti parnog sata po Beču. Od **19.11.2026.** automatski se vraća na dnevnu provjeru u **11:50 Europe/Vienna**. `data/update_policy.json` i `scraper/update_policy.py` biraju odgovarajući termin, bez duplog dnevnog osvježavanja. GitHub red čekanja i Pages deployment mogu kasniti. Promjena ljetnog i zimskog vremena obrađuje se kroz nativni `timezone`.

`scraper/check_dungeons.py` u svakom od tih prolaza provjerava pripremu za sve instance obuhvaćene Forever vodičem i izdvaja questove za Alliance Shamana/Huntera. Prikaz razlikuje preporučeni level instance od minimalnog levela za prihvatanje, te navodi mjesto preuzimanja i poznate preduvjete. Stvarne promjene levela, NPC-a ili preduvjeta objavljuje `scraper/publish_editorial.py` u novostima s izvorima i linkom na checklistu. Prva provjera postavlja referencu; nepromijenjen sadržaj i greške ne stvaraju novu vijest. Ako je izvor blokiran, ostaju prethodni podaci s datumom posljednje uspješne provjere. Pokrivenost izvora nije garancija da je svaki quest u igri uključen.

`scraper/check_guides.py` u istom poslu provjerava četiri odabrana Method/Icy Veins vodiča iz `data/guide_sources.json`. Profil prikazuje linkove i kada nema novih vijesti. `data/recommendations.json` razlikuje posljednji pokušaj, uspješnu provjeru i stvarnu izmjenu glavnog teksta ili ugrađene raspodjele talenata. Build podaci ulaze samo u fingerprint; kalkulator se ne kopira na dashboard. Prva provjera postavlja baseline bez lažnog ažuriranja; greška zadržava prethodni hash i vrijeme uspješne provjere. Nakon 26 sati bez uspješne provjere profil upozorava da provjera kasni, uz toleranciju za red čekanja i promjenu sata.

Linkovi otvaraju aktuelne preporuke autora, bez lokalnog kalkulatora. Noviji članak se ne proglašava automatski boljim buildom. Oznaka „Inhalt geändert” znači da se sadržaj izvora promijenio. Dnevni posao izričito traži Pages build i čeka završetak jer push s `GITHUB_TOKEN` sam ne pokreće Pages. Izmjena scrapera, konfiguracije vodiča ili dnevnog workflow-a pokreće i provjeru odmah, bez čekanja narednog termina.

Scraper pregledava sve vraćene RSS stavke, Method i Icy Veins Forever indeks te Reddit RSS. Prati konkretne questove, predmete, petove, spellove, profesije i korisne zajedničke mehanike. Marketing, PTR/tehničke teme, podcasti i nepovezane verzije igre se odbacuju. Izvori imaju odvojene brojače ulaznih, relevantnih i obrađenih stavki te neuspjelih čitanja članaka.

Reddit: r/wowforever do 100 najnovijih stavki; r/classicwow pretraga za Forever; dodatno r/woweconomy samo za Forever teme o profesijama i ekonomiji. Namjenski Forever post ne mora ponavljati ime igre u naslovu. RSS ograničenja i greške ostaju vidljivi u statusu izvora; Reddit savjeti su nepotvrđeni. Generička pitanja i kartice bez korisnog njemačkog sažetka ostaju u arhivi umjesto da potiskuju korisne objave s početne.

`scraper/check_quest_rewards.py` svakog dana čita Wowhead Forever quest listu i objavljene item podatke. Izdvaja Alliance/Both questove za Huntera, Shamana i zajedničke nagrade, uključujući postojeće questove s promijenjenim nagradama. Pregled ispod „Quests, interessante Items” pokazuje malu listu prema vašem levelu, konkretne nazive itema i linkove. Quest-stufe i minimalni level za prihvatanje prikazani su odvojeno. Nema tvrdnje da je predmet automatski BiS niti poređenja s opremom koju nosite.

Wowheadov učitani katalog je ograničen, obično na 1.000 redova; ovo nije garancija da su obuhvaćeni svi novi questovi. `data/quest_reward_state.json` drži hashove za poređenje, a `data/quest_rewards.json` samo mali izbor nagrada. Prvi prolaz ne stvara dnevne obavijesti. „Neu in Forever” označava razliku prema Classicu; „Neu entdeckt” označava kasniji prvi nalaz u praćenom katalogu. Promjena popularnosti ne stvara novu obavijest; promjena nagrade ili statova stvara. Nedostajući podaci se ne izmišljaju, a pad izvora zadržava posljednji ispravan pregled.

Kanonski URL sprečava duplikate. Početna dodatno grupiše identične naslove/događaje, bez spajanja različitih questova samo zato što imaju istu klasu i kategoriju. Stalni pregledi klasa i vodiči bez poznatog datuma ne zauzimaju dnevni pregled.

Hash koristi glavni sadržaj članka. Prva migracija na novi način ekstrakcije postavlja referentno stanje bez lažne obavijesti. Neuspješno čitanje članka čuva prethodni dobar sadržaj. Promjena prevoda sama po sebi ne stvara novu verziju.

Sažeci koriste postojeći `GEMINI_API_KEY` u GitHub Secrets. `GEMINI_MODEL` može se promijeniti kroz environment; podrazumijevano je `gemini-3.5-flash-lite`. Stari `gemini-2.0-flash` je ugašen. Ako sažimanje ili prijevod nisu dostupni, ostaju ručno provjerene njemačke napomene ili jasna napomena da kratki izvještaj nije dostupan. Reddit ostaje nepotvrđen community izvor. Ne izmišljaju se NPC-evi, nagrade ili drop šanse.

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
python scraper/check_guides.py
python scraper/check_quest_rewards.py
```

`Verify dashboard` provjerava push i pull requestove, uključujući odvajanje zajedničkih i klasnih vijesti. Dnevni posao više ne preuzima podatke za kalkulatore.

`data/discoveries.json` sadrži kratke provjerene praktične napomene i izvore. `data/guides.json` zadržava stabilne ID-eve postojećih dungeon questova; prije puta treba provjeriti konkretne zahtjeve u igri. `data/news.json` čuva sažetke i hashove; puni izvorni članci obrađuju se samo u memoriji i ne objavljuju se u bazi. Browser dobija `data/feed.json`, a vrijeme obrade nije isto što i vrijeme Pages objave.

Ručni `quest_gear` pregledi u `data/discoveries.json` dopunjuju automatski izbor: konkretna nagrada, minimalni level, mjesto preuzimanja, prethodni zadaci i kada ih uklopiti u rutu. Klase imaju svoje napomene, a zajednički prstenovi i trinketi ostaju na početnoj. Zajednički pregledi koriste `show_from_level`, odvojeno od minimalnog levela za prihvatanje. U profilu ostaju vidljivi i kasniji ciljevi s oznakom „Für später vormerken”, čak i kada level još nije podešen; najbliži ciljevi dolaze prvi, a prestare preporuke otpadaju prema `max_level`. Isti quest iz automatskog kataloga tada se ne ponavlja. Nepotvrđena live dostupnost i otvoreni preduvjeti pišu uz napomenu.

`assets/items-core.js` povezuje nagrade s njemačkim Wowhead Forever tooltipovima (`domain=de.forever`). Originalna imena ostaju vidljiva; ikone i kratki rezervni opisi ručno odabranih itema dolaze iz Forever podataka s datumom provjere. Službeni Wowhead widget učitava se asinhrono, pa njegov prekid ne blokira dashboard; klik i dalje otvara Forever item. Na mobitelu dodir otvara taj link.
