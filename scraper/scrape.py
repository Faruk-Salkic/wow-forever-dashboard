import requests
import feedparser
import json
import os
import sys
import hashlib
import time
import re
import urllib.parse
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# ─── GEMINI CLIENT ─────────────────────────────────────────────────────────────
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
client = None

if GEMINI_KEY:
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_KEY)
        print("✅ Google GenAI Klijent uspešno inicijalizovan.")
    except Exception as e:
        print(f"⚠️ google-genai greška: {e}. Pokušavam fallback na legacy...")
        try:
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=GEMINI_KEY)
            client = legacy_genai.GenerativeModel("gemini-2.0-flash")
            print("✅ Legacy generativeai fallback aktivan.")
        except Exception as e2:
            print(f"❌ Neuspešna inicijalizacija AI: {e2}")
            client = None

# ─── KONFIGURACIJA ────────────────────────────────────────────────────────────
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = ["Hunter", "Shaman"]
FACTION = "Alliance"

OUTPUT_FILE   = os.path.join(REPO_DIR, "data", "news.json")
SEEN_IDS_FILE = os.path.join(REPO_DIR, "data", "seen_ids.json")
BACKUP_FILE   = os.path.join(REPO_DIR, "data", "news_backup.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Aktivni, provereni RSS izvori (ispravljeni URL-ovi koji vraćaju HTTP 200)
RSS_FEEDS = [
    {"name": "Blizzard Announcements", "icon": "🔵", "url": "https://us.forums.blizzard.com/en/wow/c/classic/classic-announcements/168.rss", "lang": "en", "official": True},
    {"name": "Blizzard Blue Tracker",  "icon": "🔷", "url": "https://us.forums.blizzard.com/en/wow/c/classic/167.rss",                       "lang": "en", "official": True},
    {"name": "WoWhead Forever",        "icon": "🌐", "url": "https://www.wowhead.com/news/rss/all",                                           "lang": "en", "official": False},
    {"name": "Buffed.de",              "icon": "🇩🇪", "url": "https://www.buffed.de/feed/",                                                  "lang": "de", "official": False},
    {"name": "MMO-Champion",           "icon": "⚔️", "url": "https://www.mmo-champion.com/external.php?do=rss&type=newcontent&sectionid=1&days=2&count=25", "lang": "en", "official": False},
    {"name": "Warcraft Tavern",        "icon": "🍺", "url": "https://www.warcrafttavern.com/feed/",                                          "lang": "en", "official": False},
]

REDDIT_SUBREDDITS = ["wowforever", "classicwow"]

# ─── POMOĆNE FUNKCIJE & DEDUPLIKACIJA ─────────────────────────────────────────
def normalize_url(url):
    """
    Normalizuje URL radi sprečavanja duplikata:
    - Briše tracking parametre (utm_*, ref, source)
    - Normalizuje domen i protokol u lowercase, uklanja www.
    - Uklanja trailing slash i fragment
    """
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip("/")
        queries = urllib.parse.parse_qsl(parsed.query)
        clean_queries = sorted([
            (k, v) for k, v in queries
            if not k.lower().startswith("utm_") and k.lower() not in ["ref", "source", "src", "fbclid"]
        ])
        new_query = urllib.parse.urlencode(clean_queries)
        return urllib.parse.urlunparse((scheme, netloc, path, "", new_query, ""))
    except Exception:
        return url.strip().rstrip("/")

def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

def make_canonical_id(url, fallback_text=""):
    norm_u = normalize_url(url)
    if norm_u:
        return make_id(norm_u)
    return make_id(fallback_text)

def clean_source_text(text):
    """
    Očisti tekst izvora tako da uklanja HTML, suvišne praznine i promenljive elemente.
    Tako se promjena navigacije, timestampova ili formata ne tretira kao stvarna promena.
    """
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', str(text))
    text = re.sub(r'\b\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b', ' ', text)
    text = re.sub(r'\bvor\s+\d+\s+(?:minuten|stunden|tagen|sekunden)\b', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def compute_source_hash(title, content):
    clean_t = clean_source_text(title)
    clean_c = clean_source_text(content)
    combined = (clean_t + " " + clean_c).lower()
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16]

def generate_update_summary(old_title, new_title, old_content, new_content):
    clean_ot = clean_source_text(old_title).lower()
    clean_nt = clean_source_text(new_title).lower()

    if clean_ot and clean_nt and clean_ot != clean_nt:
        t_display = new_title[:50] + "..." if len(new_title) > 50 else new_title
        return f"Titel und Guide-Struktur angepasst: {t_display}"

    clean_oc = clean_source_text(old_content)
    clean_nc = clean_source_text(new_content)

    nums_old = set(re.findall(r'\b\d+(?:[\.,]\d+)?%?\b', clean_oc))
    nums_new = set(re.findall(r'\b\d+(?:[\.,]\d+)?%?\b', clean_nc))
    if nums_old != nums_new:
        return "Talent-Ränge, Schadenswerte oder Attribut-Skalierungen aktualisiert."

    len_diff = len(clean_nc) - len(clean_oc)
    if len_diff > 200:
        return "Leitfaden um neue Abschnitte, Taktiken oder Beute-Hinweise erweitert."
    elif len_diff < -200:
        return "Veraltete Informationen entfernt und Empfehlungen gestrafft."

    return "Inhaltliche Überarbeitung der Empfehlungen und Details."

def merge_and_deduplicate_items(existing_items, incoming_items, sources_health=None, now_iso=None):
    if sources_health is None:
        sources_health = {}
    if now_iso is None:
        now_iso = datetime.now(timezone.utc).isoformat()

    items_by_url = {}

    # 1. Učitaj postojeće stavke sa normalizacijom
    for old_it in existing_items:
        raw_u = old_it.get("url", "")
        norm_u = normalize_url(raw_u)
        old_id = old_it.get("id")
        canonical_id = make_canonical_id(norm_u, old_it.get("title", ""))

        # Filtriraj kroz strogi is_relevant_context
        if not is_relevant_context(old_it.get("title", ""), old_it.get("teaser_de", ""), old_it.get("article_de", "")):
            continue

        if norm_u in items_by_url:
            existing = items_by_url[norm_u]
            migrated = set(existing.get("migrated_ids", []))
            if old_id and old_id != existing["id"]:
                migrated.add(old_id)
            if "migrated_ids" in old_it:
                migrated.update(old_it["migrated_ids"])
            existing["migrated_ids"] = sorted(list(migrated))
        else:
            migrated = set(old_it.get("migrated_ids", []))
            if old_id and old_id != canonical_id:
                migrated.add(old_id)
            old_it["id"] = canonical_id
            old_it["migrated_ids"] = sorted(list(migrated))
            old_it["normalized_url"] = norm_u
            old_it["classes"] = [c for c in detect_classes(old_it.get("title", "") + " " + old_it.get("article_de", "")) if c in CLASSES]
            old_it["category"] = detect_category(old_it.get("title", "") + " " + old_it.get("article_de", ""))

            # Osiguraj da postoji source_content_hash za postojeću stavku ako ga nema
            if "source_content_hash" not in old_it:
                old_it["source_content_hash"] = compute_source_hash(
                    old_it.get("raw_title", old_it.get("title", "")),
                    old_it.get("raw_content", old_it.get("article_de", ""))
                )
            items_by_url[norm_u] = old_it

    # 2. Spoji novo prikupljene stavke
    new_added_count = 0
    updated_count = 0

    for new_it in incoming_items:
        norm_u = new_it["normalized_url"]
        new_hash = new_it.get("source_content_hash") or compute_source_hash(
            new_it.get("raw_title", new_it.get("title", "")),
            new_it.get("raw_content", new_it.get("article_de", ""))
        )
        new_it["source_content_hash"] = new_hash

        if norm_u in items_by_url:
            existing = items_by_url[norm_u]
            old_hash = existing.get("source_content_hash", "")

            # Poređenje očišćenog sadržaja: ako je hash isti, nema stvarne promjene!
            if old_hash and old_hash == new_hash:
                existing["last_checked_at"] = now_iso
                continue

            # Stvarna promjena sadržaja postojećeg vodiča/objave
            updated_count += 1
            diff_note = generate_update_summary(
                existing.get("raw_title", existing.get("title", "")),
                new_it.get("raw_title", new_it.get("title", "")),
                existing.get("raw_content", existing.get("article_de", "")),
                new_it.get("raw_content", new_it.get("article_de", ""))
            )

            existing["title"] = new_it["title"]
            existing["article_de"] = new_it["article_de"]
            existing["teaser_de"] = new_it["teaser_de"]
            existing["radar_status"] = new_it["radar_status"]
            existing["category"] = new_it["category"]
            existing["classes"] = new_it["classes"]
            existing["source_content_hash"] = new_hash
            existing["raw_title"] = new_it.get("raw_title", "")
            existing["raw_content"] = new_it.get("raw_content", "")
            
            # Oznaka Aktualisiert i detalji
            existing["is_updated"] = True
            existing["updated_at"] = now_iso
            existing["update_note"] = diff_note
            existing["content_version"] = existing.get("content_version", 1) + 1
            existing["last_checked_at"] = now_iso
        else:
            # Potpuno nova objava
            new_it["is_updated"] = False
            new_it["content_version"] = 1
            new_it["last_checked_at"] = now_iso
            items_by_url[norm_u] = new_it
            new_added_count += 1

    merged = list(items_by_url.values())
    merged.sort(key=lambda x: (x.get("updated_at") if x.get("is_updated") else x.get("date", "")), reverse=True)

    today_str = datetime.now().strftime("%d.%m.%Y")
    
    # Proveri da li su izvori uspešno provereni
    critical_sources_failed = any(
        ("Fehler" in st or "HTTP 4" in st or "HTTP 5" in st)
        for st in sources_health.values()
    )

    if new_added_count == 0 and updated_count == 0:
        if critical_sources_failed:
            daily_summary_text = "Heute keine neuen relevanten Updates für Shaman und Hunter. (Hinweis: Einige Quellen meldeten Abruffehler; Details im Quellenstatus)."
        else:
            daily_summary_text = "Heute keine neuen relevanten Updates für Shaman und Hunter."
    else:
        active_headlines = []
        for it in merged:
            if it.get("is_updated") and it.get("updated_at", "").startswith(now_iso[:10]):
                active_headlines.append(f"[Aktualisiert] {it['title']}")
            elif not it.get("is_updated") and it.get("fetched_at", "").startswith(now_iso[:10]):
                active_headlines.append(it["title"])
        if not active_headlines:
            active_headlines = [i["title"] for i in merged[:2] if i.get("title")]

        headlines_summary = ("; ".join(active_headlines[:2]) + ".") if active_headlines else "Updates aktiv."

        if new_added_count > 0 and updated_count > 0:
            daily_summary_text = f"Tagesbriefing ({today_str}): {new_added_count} neue und {updated_count} aktualisierte Updates erfasst. Themen: {headlines_summary}"
        elif updated_count > 0:
            daily_summary_text = f"Tagesbriefing ({today_str}): {updated_count} bestehende Leitfäden wurden inhaltlich aktualisiert. Themen: {headlines_summary}"
        else:
            daily_summary_text = f"Tagesbriefing ({today_str}): {new_added_count} neue relevante Updates erfasst. Themen: {headlines_summary}"

    return merged, new_added_count, updated_count, daily_summary_text

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Greška čitanja {path}: {e}")
    return default

def save_json(path, data):
    if "news.json" in path:
        if not isinstance(data, dict) or "items" not in data or not isinstance(data["items"], list):
            raise ValueError("Neispravna struktura podataka za news.json pre snimanja!")
    
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)

def translate_to_german(text):
    if not text:
        return ""
    clean = text.replace("Continue reading »", "").replace("Continue reading", "").replace("Continue Reading »", "").strip()
    
    german_indicators = [" der ", " die ", " das ", " und ", " für ", " mit ", " ist ", " auf ", " nicht ", " wurde ", " werden ", " eine ", " eines "]
    if any(ind in (" " + clean.lower() + " ") for ind in german_indicators):
        return clean

    try:
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": clean[:450], "langpair": "en|de"},
            timeout=5
        )
        if r.status_code == 200:
            translated = r.json().get("responseData", {}).get("translatedText", "")
            if translated and not translated.startswith("MYMEMORY WARNING") and "QUERY LENGTH LIMIT EXCEEDED" not in translated:
                return translated
    except Exception as e:
        print(f"⚠️ Prevod greška: {e}")
    
    return clean

def detect_classes(text):
    """
    Fokus isključivo na Huntera i Shamana.
    Ne dodeljuje klasu ako se samo usput spominje reč 'pet' ili druga klasa.
    """
    t = text.lower()
    detected = []

    hunter_patterns = [
        r'\bhunter\b', r'\bjäger\b', r'\bbeast\s*mastery\b', r'\bbm\s*hunter\b',
        r'\bsurvival\s*hunter\b', r'\bmarksman(?:ship)?\b', r'\btierherrschaft\b',
        r'\bjäger[- ](?:pet|begleiter|talent|schaden|tuning)\b'
    ]
    shaman_patterns = [
        r'\bshaman\b', r'\bschaman(?:e|en)\b', r'\benhancement\s*shaman\b',
        r'\belemental\s*shaman\b', r'\brestoration\s*shaman\b', r'\bverstärker[- ]schaman\b',
        r'\bwindfury\b', r'\bwindzorn\b', r'\berdstoss[- ]?totem\b', r'\bsteinhaut[- ]?totem\b',
        r'\bmanaflut[- ]?totem\b', r'\bsteingestalt\b', r'\bstoneform\b'
    ]

    has_hunter = any(re.search(p, t) for p in hunter_patterns)
    has_shaman = any(re.search(p, t) for p in shaman_patterns)

    if not has_hunter and ("begleiter" in t or "pet" in t):
        if any(w in t for w in ["jäger", "hunter", "zähmen", "tame", "tierherrschaft", "furious howl", "furioses heulen", "knurren"]):
            has_hunter = True

    if has_hunter:
        detected.append("Hunter")
    if has_shaman:
        detected.append("Shaman")

    return detected

def detect_category(text):
    """
    Detekcija kategorije sa zaštitom od lažnih BiS i Hotfix pogodaka:
    - Nemačko 'bis Level 60' ili 'bis zur Stufe' NE sme aktivirati BiS!
    - Najave budućih pečeva i kadenca NE smeju aktivirati Hotfix!
    """
    t = text.lower()

    if any(k in t for k in ["exploit", "abuse", "glitch", "gold farm exploit"]):
        return "exploit"

    if any(k in t for k in ["leitfaden", "starter-leitfaden", "starter-guide", "leveling-route", "leveling guide", "pet-guide", "tame-guide", "quest-guide", "cheat-sheet"]):
        return "guide"

    is_bis = False
    if re.search(r'\b(best[- ]in[- ]slot|pre[- ]?bis|bis[- ]?(?:liste|list|gear|items?|tabelle|guide))\b', t):
        is_bis = True
    elif re.search(r'\bBiS\b', text):
        if not re.search(r'\b[bB]is (?:level|stufe|zum|zur|dahin|ende)\b', text, re.IGNORECASE):
            is_bis = True

    if is_bis:
        return "bis"

    is_future_cadence = any(k in t for k in [
        "patch-kadenz", "patch kadenz", "patch-zyklus", "patch cadence",
        "4-monatig", "17-wochen", "zeitplan", "roadmap", "kadenz",
        "future patch", "timegating", "interview"
    ])
    if not is_future_cadence:
        if any(k in t for k in ["hotfix", "hotfixes", "live-hotfix", "notfall-patch", "klassen-tuning", "balance-änderung", "tuning-anpassung", "gefixt"]) or (any(w in t for w in ["buff", "nerf"]) and any(w in t for w in ["patch", "tuning", "balancing", "balance", "hotfix", "volksfähigkeiten"])):
            return "hotfix"

    if any(k in t for k in ["guide", "tipps"]):
        return "guide"

    if any(k in t for k in ["pvp", "battleground", "duell", "arena", "ehrensystem"]):
        return "pvp"

    return "news"

def detect_radar_status(text):
    t = text.lower()
    if any(w in t for w in ["fixed", "behoben", "hotfixed", "resolved", "patched", "gefixt"]):
        return "fixed"
    if any(w in t for w in ["exploit", "abuse", "broken", "gamebreaking", "glitch", "gold farm exploit"]):
        if any(w in t for w in ["blue post", "blizzard confirms", "investigating", "acknowledged"]):
            return "confirmed"
        return "unconfirmed"
    if any(w in t for w in ["nerf", "buff", "balance change", "anpassung"]):
        return "balance"
    return "normal"

def is_relevant_context(title, summary, full_text=""):
    """
    Rigorozni filter:
    1. Odbacuje druge ekspanzije (TBC Classic, WotLK, Cata, Retail) i druge igre.
    2. Odbacuje tehničke rasprave (layering, arhitektura servera), podcaste, trailere.
    3. Odbacuje članke koji su primarno o drugim klasama (npr. Rogue vodič koji usput spominje Huntera).
    4. NE odbacuje koristan Forever Shaman vodič samo zato što u tekstu poredi mehaniku s Retailom.
    5. Prihvata praktične zajedničke vodiče (prodavači torbi, camping, tamnice) u WoW Foreveru.
    """
    combined = (title + " " + summary + " " + full_text[:1200]).lower()
    title_l = title.lower()

    # 1. Druge ekspanzije i verzije (TBC Classic, WotLK, Retail sezone)
    other_expansions_patterns = [
        r'\b(the burning crusade|burning crusade|tbc classic|tbc)\b',
        r'\b(wrath of the lich king|wotlk classic|wotlk)\b',
        r'\b(cataclysm classic|mop classic)\b',
        r'\b(dragonflight|shadowlands|the war within|midnight)\b',
        r'\b(delves|tiefen|mythic\+)\b'
    ]
    if any(re.search(p, combined) for p in other_expansions_patterns):
        return False

    # 2. Druge igre i platforme
    other_games = ["red dead", "rdr2", "diablo", "overwatch", "hearthstone", "gta", "playstation", "xbox", "nintendo", "spirit crossing"]
    if any(g in combined for g in other_games):
        return False

    # 3. Tehnička infrastruktura, podcasti, traileri, PR kadenca (Zahtev 3)
    exclude_keywords = [
        "layering", "server-architektur", "server architecture", "sharding", "netcode",
        "backend", "infrastruktur", "hardware", "grafik-upgrades", "wasser-upgrades",
        "beleuchtung", "lighting upgrade", "graphic upgrade",
        "podcast", "episode", "community-building", "community building", "ign-interview",
        "release-trailer", "offizieller trailer", "warpath", "cinematic", "rekord", "hype",
        "beliebtheit", "spielerzahlen", "verkaufszahlen", "soundtrack",
        "1.000 neue quests versprochen", "1000 neue quests", "patch-kadenz", "patch kadenz",
        "4-monatigen patch", "17-wochen", "timegating",
        "tier list", "tier-liste", "dps-ranking", "heiler-ranking", "tank-ranking"
    ]
    if any(b in combined for b in exclude_keywords):
        return False

    has_forever = any(m in combined for m in ["forever", "wow forever", "classic forever", "legacy system", "camping system"])
    
    # 4. Provera za Retail: Ako je članak čisto o Retailu bez 'forever' konteksta, odbaci.
    # Ako je o Foreveru i samo POREDI mehaniku s Retailom, DOZVOLI!
    if "retail" in combined and not has_forever:
        return False

    our_classes = detect_classes(combined)

    # 5. Provera fokusa klase: Ako je naslov ili primarni sadržaj o drugoj klasi (npr. Rogue), odbaci!
    other_class_patterns = [
        r'\b(rogue|schurke|schurken)\b', r'\b(priest|priester)\b',
        r'\b(mage|magier)\b', r'\b(paladin|paladine)\b',
        r'\b(druid|druide|druiden)\b', r'\b(warlock|hexenmeister)\b',
        r'\b(warrior|krieger)\b'
    ]
    is_title_other_class = any(re.search(p, title_l) for p in other_class_patterns)
    is_title_our_class = any(re.search(p, title_l) for p in [r'\b(hunter|jäger)\b', r'\b(shaman|schamane|schamanen)\b'])

    if is_title_other_class and not is_title_our_class:
        # Primarno vodič za drugu klasu (čak i ako usput spominje Jägera/Huntera)
        return False

    other_mentions = sum(len(re.findall(p, combined)) for p in other_class_patterns)
    our_mentions = sum(len(re.findall(p, combined)) for p in [r'\b(hunter|jäger|tierherrschaft)\b', r'\b(shaman|schamane|schamanen|windfury|windzorn|totem)\b'])

    if other_mentions >= 3 and our_mentions <= 1 and not is_title_our_class:
        return False

    # 6. Prihvaćeni slučajevi:
    # A) Specifično za Huntera ili Shamana:
    if our_classes:
        gameplay_words = [
            "hotfix", "patch", "exploit", "talent", "buff", "nerf", "bis",
            "pet", "begleiter", "damage", "totem", "windfury", "ability",
            "fähigkeit", "leveling", "guide", "leitfaden", "tuning", "zähm", "tame",
            "waffe", "weapon", "quest"
        ]
        if any(g in combined for g in gameplay_words):
            return True

    # B) Praktični zajednički vodiči za obojicu (prodavači torbi, camping, tamnice, profesije):
    common_practical_words = [
        "tasche", "taschen", "bag vendor", "beutel", "händler", "vendor",
        "camping", "legacy", "dungeon", "quest", "leveling", "gold",
        "todesminen", "deadmines", "verlies", "stockades", "gnomeregan",
        "bergbau", "mining", "engineering", "ingenieur", "kürschnerei", "skinning", "kräuterkunde", "herbalism",
        "starter", "start"
    ]
    if has_forever and any(g in combined for g in common_practical_words):
        return True

    return False

def fetch_full_text(url):
    if not url:
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for noise in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                noise.decompose()
            text = soup.get_text(separator="\n", strip=True)
            return text[:3500]
    except Exception:
        pass
    return ""

# ─── POSEBNI SCRAPERI ZA ICY VEINS & METHOD (HTML VODIČI) ─────────────────────
def scrape_icy_veins_forever():
    """
    Icy Veins nema stabilan /wow/feed (vraća 404), ali ima aktivnu sekciju za WoW Forever vodiče.
    """
    url = "https://www.icy-veins.com/wow-forever/class-guides"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return f"HTTP {r.status_code}", []
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/wow-forever/" in href and any(c in href.lower() for c in ["hunter", "shaman"]):
                full_url = urllib.parse.urljoin("https://www.icy-veins.com", href)
                raw_text = a.get_text(strip=True) or href.split("/")[-1].replace("-", " ").title()
                title = f"Icy Veins Forever: {raw_text}"
                summary = f"Offizieller WoW Forever Klassen-Leitfaden von Icy Veins für {raw_text}. Behandelt Talente, Rotationen und Ausrüstungs-Skalierung."
                if not any(x["url"] == full_url for x in items):
                    items.append({
                        "url": full_url,
                        "title": title,
                        "summary": summary,
                        "source": "Icy Veins Forever",
                        "source_icon": "❄️"
                    })
        return f"OK ({len(items)} Leitfäden)", items
    except Exception as e:
        return f"Fehler: {str(e)[:40]}", []

def scrape_method_forever():
    """
    Method nema /feed (vraća 404), ali ima aktivnu sekciju za WoW Forever vodiče.
    """
    url = "https://www.method.gg/wow-forever/class-guides"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return f"HTTP {r.status_code}", []
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/wow-forever/" in href and any(c in href.lower() for c in ["hunter", "shaman"]):
                full_url = urllib.parse.urljoin("https://www.method.gg", href)
                raw_text = a.get_text(strip=True) or href.split("/")[-1].replace("-", " ").title()
                title = f"Method Forever: {raw_text}"
                summary = f"WoW Forever Leveling- und Klassenguide von Method für {raw_text}. Optimiert für schnelles Vorankommen und Endgame-Vorbereitung."
                if not any(x["url"] == full_url for x in items):
                    items.append({
                        "url": full_url,
                        "title": title,
                        "summary": summary,
                        "source": "Method Forever",
                        "source_icon": "🛡️"
                    })
        return f"OK ({len(items)} Leitfäden)", items
    except Exception as e:
        return f"Fehler: {str(e)[:40]}", []

# ─── AI SUMMARIZER SA KONTROLOM HALUCINACIJE ──────────────────────────────────
AI_PROMPT = """Du bist ein hochkarätiger WoW-Forever-Experte und Analyst für das private Dashboard von Faruk (Schamane, Zwerg, Bergbau/Engineering) & Mirza (Jäger, Tierherrschaft, Kürschnerei/Kräuterkunde, Allianz).

WICHTIGSTE REGELN:
- Antworte AUSSCHLIESSLICH auf reinem, flüssigem und professionellem DEUTSCH!
- Behalte wichtige englische Spielbegriffe (Spell-Namen, Quests, Items) in Klammern bei, um die Suche im Spiel zu erleichtern.
- Fokussiere dich NUR auf konkreten spielerischen Nutzen: Was müssen Faruk & Mirza tun, wo finden sie das Item/den NPC, und was lohnt sich?
- ERFINDE KEINE NPC-Namen, Beute-Drops oder Zahlen (Halluzinations-Verbot!). Beziehe dich strikt auf den Quelltext.

STRUKTUR DES BERICHTS:
📌 **Was ist passiert?** (Kernaussage auf Deutsch in 1–2 Sätzen)
🎮 **Bedeutung für Faruk & Mirza:** (Konkret für Schamane, Jäger, Camping-System oder Berufe)
💡 **Handlungsempfehlung:** (Was Faruk & Mirza jetzt tun sollten)
🏷️ **Status:** [Blizzard-Bestätigt | Guide / Analyse | Community-Diskussion]

Titel: {title}
Quelle: {source}
Text:
{content}
"""

def generate_ai_summary(title, content, source):
    if not client or not content or len(content.strip()) < 50:
        return None, None

    try:
        prompt = AI_PROMPT.format(title=title, source=source, content=content[:3000])
        
        if hasattr(client, "models"):
            resp = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            full_text = resp.text.strip()
        else:
            resp = client.generate_content(prompt)
            full_text = resp.text.strip()

        teaser = " ".join([s for s in full_text.split("\n") if s.strip() and not s.startswith("📌")][:2])
        if len(teaser) > 220:
            teaser = teaser[:217] + "..."

        time.sleep(0.4)
        return full_text, teaser
    except Exception as e:
        print(f"⚠️ AI generisanje nije uspelo za '{title[:30]}': {e}")
        return None, None

# ─── GLAVNI SCRAPER FLOW ──────────────────────────────────────────────────────
def run_scraper():
    start_time_utc = datetime.now(timezone.utc).isoformat()
    print("🚀 Pokrećem provereni WoW Forever Scraper (Fokus: Shaman & Hunter)...")
    existing_data = load_json(OUTPUT_FILE, {"items": []})
    seen_ids      = set(load_json(SEEN_IDS_FILE, []))

    if existing_data.get("items"):
        save_json(BACKUP_FILE, existing_data)

    collected_raw = []
    sources_health = {}

    # 1. Provereni RSS Izvori
    for feed_cfg in RSS_FEEDS:
        feed_name = feed_cfg["name"]
        try:
            r = requests.get(feed_cfg["url"], headers=HEADERS, timeout=12)
            if r.status_code != 200:
                sources_health[feed_name] = f"HTTP {r.status_code}"
                print(f"⚠️ {feed_name}: HTTP {r.status_code}")
                continue
            
            feed = feedparser.parse(r.text)
            sources_health[feed_name] = f"OK ({len(feed.entries)} Meldungen)"
            print(f"📡 {feed_name}: {len(feed.entries)} pristiglih stavki.")

            for entry in feed.entries[:15]:
                title   = entry.get("title", "").strip()
                summary = BeautifulSoup(entry.get("summary", "") or "", "html.parser").get_text()[:600]
                link    = entry.get("link", "")
                pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                pub_date = time.strftime("%Y-%m-%d", pub_parsed) if pub_parsed else datetime.now().strftime("%Y-%m-%d")

                collected_raw.append({
                    "title": title,
                    "summary": summary,
                    "url": link,
                    "pub_date": pub_date,
                    "source": feed_name,
                    "source_icon": feed_cfg["icon"],
                    "official": feed_cfg.get("official", False)
                })
        except Exception as e:
            sources_health[feed_name] = f"Fehler: {str(e)[:50]}"
            print(f"⚠️ Greška pri čitanju {feed_name}: {e}")

    # 2. Icy Veins Forever (direktan HTML scraping umesto 404 feeda)
    st_iv, iv_items = scrape_icy_veins_forever()
    sources_health["Icy Veins Forever"] = st_iv
    print(f"📡 Icy Veins Forever: {st_iv}")
    for it in iv_items:
        collected_raw.append({
            "title": it["title"],
            "summary": it["summary"],
            "url": it["url"],
            "pub_date": datetime.now().strftime("%Y-%m-%d"),
            "source": it["source"],
            "source_icon": it["source_icon"],
            "official": False
        })

    # 3. Method Forever (direktan HTML scraping umesto 404 feeda)
    st_m, m_items = scrape_method_forever()
    sources_health["Method Forever"] = st_m
    print(f"📡 Method Forever: {st_m}")
    for it in m_items:
        collected_raw.append({
            "title": it["title"],
            "summary": it["summary"],
            "url": it["url"],
            "pub_date": datetime.now().strftime("%Y-%m-%d"),
            "source": it["source"],
            "source_icon": it["source_icon"],
            "official": False
        })

    # 4. Reddit
    yesterday = datetime.now(timezone.utc) - timedelta(days=2)
    reddit_ok = False
    for sub in REDDIT_SUBREDDITS:
        for kw in ["hunter", "shaman", "camping", "exploit"]:
            try:
                r = requests.get(
                    "https://api.pullpush.io/reddit/search/submission/",
                    params={"q": kw, "subreddit": sub, "size": 5, "after": int(yesterday.timestamp()), "sort": "score"},
                    timeout=8
                )
                if r.status_code != 200:
                    continue
                reddit_ok = True
                for post in r.json().get("data", []):
                    title   = post.get("title", "")
                    content = post.get("selftext", "")[:1200]
                    link    = "https://reddit.com" + post.get("permalink", "")
                    score   = post.get("score", 0)

                    if score < 10:
                        continue

                    collected_raw.append({
                        "title": title,
                        "summary": content,
                        "url": link,
                        "pub_date": datetime.now().strftime("%Y-%m-%d"),
                        "source": f"Reddit r/{sub}",
                        "source_icon": "💬",
                        "official": False
                    })
            except Exception:
                pass
    sources_health["Reddit (r/wowforever & r/classicwow)"] = "OK" if reddit_ok else "Keine neuen Top-Meldungen"

    # 5. Filtriranje sirovih stavki i priprema novih objekata
    processed_new = []
    for item in collected_raw:
        title = item["title"]
        summary = item["summary"]
        link = item["url"]

        if not is_relevant_context(title, summary):
            continue

        full_text = fetch_full_text(link)
        content = full_text if len(full_text) > len(summary) else summary

        norm_url = normalize_url(link)
        src_hash = compute_source_hash(title, content)
        canonical_id = make_canonical_id(norm_url, title + summary)
        classes = detect_classes(title + " " + content)
        radar_status = detect_radar_status(title + " " + content)
        category = detect_category(title + " " + content)

        article_de, teaser_de = generate_ai_summary(title, content, item["source"])

        if not article_de:
            german_summary = translate_to_german(summary)
            article_de = f"📌 **Zusammenfassung von {item['source']}:**\n{german_summary}\n\n💡 **Handlungsempfehlung:** Originalquelle für weitere Details im Link unten öffnen."
            teaser_de  = german_summary[:180] + ("..." if len(german_summary) > 180 else "")

        german_title = translate_to_german(title)
        verified_label = "Blizzard-Bestätigt" if item["official"] else ("Guide / Analyse" if category == "guide" else "Community / Portal")

        processed_new.append({
            "id": canonical_id,
            "migrated_ids": [],
            "date": item["pub_date"],
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": item["source"],
            "source_icon": item["source_icon"],
            "category": category,
            "verified_type": verified_label,
            "radar_status": radar_status,
            "classes": classes,
            "title": german_title,
            "teaser_de": teaser_de,
            "article_de": article_de,
            "url": link,
            "normalized_url": norm_url,
            "raw_title": title,
            "raw_content": content,
            "source_content_hash": src_hash
        })

    # 6. DEDUPLIKACIJA, PRAĆENJE NOVIH I IZMIJENJENIH OBJAVA
    existing_items = existing_data.get("items", [])
    finish_time_utc = datetime.now(timezone.utc).isoformat()

    merged, new_added_count, updated_count, daily_summary_text = merge_and_deduplicate_items(
        existing_items=existing_items,
        incoming_items=processed_new,
        sources_health=sources_health,
        now_iso=finish_time_utc
    )

    result_payload = {
        "scraper_started_at": start_time_utc,
        "data_processed_at": finish_time_utc,
        "last_updated": finish_time_utc,
        "published_at": finish_time_utc,
        "total_count": len(merged),
        "new_count": new_added_count,
        "updated_count": updated_count,
        "daily_summary": daily_summary_text,
        "castle_status": {
            "status": "Keine Live-Daten verifiziert",
            "details": "Aktuell liegen keine automatischen Burgen-Telemetriedaten vor. Status wird nach Serverstart über Live-Events angebunden.",
            "last_checked": finish_time_utc,
            "verified": False
        },
        "items": merged[:60],
        "sources_status": sources_health
    }

    # Ažuriraj seen_ids skup sa svim trenutnim i migriranim ID-evima
    all_known_ids = set(seen_ids)
    for it in merged:
        all_known_ids.add(it["id"])
        for mid in it.get("migrated_ids", []):
            all_known_ids.add(mid)

    save_json(OUTPUT_FILE, result_payload)
    save_json(SEEN_IDS_FILE, sorted(list(all_known_ids)))
    print(f"✅ Uspešno završeno: {new_added_count} novih stavki, {updated_count} ažuriranih. Ukupno unikatnih po URL-u: {len(merged)}")

if __name__ == "__main__":
    run_scraper()
