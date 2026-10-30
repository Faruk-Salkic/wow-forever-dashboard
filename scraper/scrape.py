import requests
import feedparser
import json
import os
import sys
import hashlib
import time
import re
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

RSS_FEEDS = [
    {"name": "Blizzard News",         "icon": "🔵", "url": "https://worldofwarcraft.blizzard.com/en-us/news/rss", "lang": "en", "official": True},
    {"name": "Blizzard Blue Tracker", "icon": "🔷", "url": "https://us.forums.blizzard.com/en/wow/c/classic/classic-discussion.rss", "lang": "en", "official": True},
    {"name": "WoWhead Forever",       "icon": "🌐", "url": "https://www.wowhead.com/news/rss/all", "lang": "en", "official": False},
    {"name": "Buffed.de",             "icon": "🇩🇪", "url": "https://www.buffed.de/feed/", "lang": "de", "official": False},
    {"name": "MMO-Champion",          "icon": "⚔️", "url": "https://www.mmo-champion.com/external.php?do=rss&type=newcontent&sectionid=1&days=2&count=25", "lang": "en", "official": False},
    {"name": "Icy Veins Forever",     "icon": "❄️", "url": "https://www.icy-veins.com/wow/feed", "lang": "en", "official": False},
    {"name": "Method Forever",        "icon": "🛡️", "url": "https://www.method.gg/feed", "lang": "en", "official": False},
    {"name": "Warcraft Tavern",       "icon": "🍺", "url": "https://www.warcrafttavern.com/feed/", "lang": "en", "official": False},
]

REDDIT_SUBREDDITS = ["wowforever", "classicwow"]

# ─── POMOĆNE FUNKCIJE ─────────────────────────────────────────────────────────
def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

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

    # Hunter obrasci
    hunter_patterns = [
        r'\bhunter\b', r'\bjäger\b', r'\bbeast\s*mastery\b', r'\bbm\s*hunter\b',
        r'\bsurvival\s*hunter\b', r'\bmarksman(?:ship)?\b', r'\btierherrschaft\b',
        r'\bjäger[- ](?:pet|begleiter|talent|schaden|tuning)\b'
    ]
    # Shaman obrasci
    shaman_patterns = [
        r'\bshaman\b', r'\bschaman(?:e|en)\b', r'\benhancement\s*shaman\b',
        r'\belemental\s*shaman\b', r'\brestoration\s*shaman\b', r'\bverstärker[- ]schaman\b',
        r'\bwindfury\b', r'\bwindzorn\b', r'\berdstoss[- ]?totem\b', r'\bsteinhaut[- ]?totem\b',
        r'\bmanaflut[- ]?totem\b', r'\bsteingestalt\b', r'\bstoneform\b'
    ]

    has_hunter = any(re.search(p, t) for p in hunter_patterns)
    has_shaman = any(re.search(p, t) for p in shaman_patterns)

    # Pet uslov: samo ako je u kontekstu lovca/tame-a, a ne vanity petova
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
    - Vodiči (Leitfaden, Starter) imaju prednost nad slučajnim rečima.
    """
    t = text.lower()

    # 1. Exploit
    if any(k in t for k in ["exploit", "abuse", "glitch", "gold farm exploit"]):
        return "exploit"

    # 2. Guides (Starter, Leitfaden, Leveling)
    if any(k in t for k in ["leitfaden", "starter-leitfaden", "starter-guide", "leveling-route", "leveling guide", "pet-guide", "tame-guide", "quest-guide", "cheat-sheet"]):
        return "guide"

    # 3. BiS - precizno prepoznavanje Best-in-Slot
    is_bis = False
    if re.search(r'\b(best[- ]in[- ]slot|pre[- ]?bis|bis[- ]?(?:liste|list|gear|items?|tabelle|guide))\b', t):
        is_bis = True
    elif re.search(r'\bBiS\b', text):
        if not re.search(r'\b[bB]is (?:level|stufe|zum|zur|dahin|ende)\b', text, re.IGNORECASE):
            is_bis = True

    if is_bis:
        return "bis"

    # 4. Hotfix - ne sme biti najava budućeg rasporeda (kadenca)
    is_future_cadence = any(k in t for k in [
        "patch-kadenz", "patch kadenz", "patch-zyklus", "patch cadence",
        "4-monatig", "17-wochen", "zeitplan", "roadmap", "kadenz",
        "future patch", "timegating", "interview"
    ])
    if not is_future_cadence:
        if any(k in t for k in ["hotfix", "hotfixes", "live-hotfix", "notfall-patch", "klassen-tuning", "balance-änderung", "tuning-anpassung", "gefixt"]) or (any(w in t for w in ["buff", "nerf"]) and any(w in t for w in ["patch", "tuning", "balancing", "balance", "hotfix", "volksfähigkeiten"])):
            return "hotfix"

    # 5. Opšti vodiči
    if any(k in t for k in ["guide", "tipps"]):
        return "guide"

    # 6. PvP
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
    1. Odbacuje tehničke rasprave (layering, arhitektura servera), podcaste, trailere, retail WoW, druge igre.
    2. Odbacuje sadržaj samo za druge klase (Priest, Rogue, Mage, Druid, Warlock, Warrior, Paladin).
    3. Prihvata konkretan sadržaj za Shamana i Huntera, te opšti koristan sadržaj za obojicu (Camping, Dungeons, Quests, Bags).
    """
    combined = (title + " " + summary + " " + full_text[:1000]).lower()

    # 1. Hard Blacklist & General News Exclusions (Zahtev 3)
    exclude_keywords = [
        # Druge igre i retail
        "red dead", "rdr2", "diablo", "overwatch", "hearthstone", "gta", "playstation", "xbox", "nintendo", "steam release", "spirit crossing",
        "midnight", "the war within", "dragonflight", "shadowlands", "delves", "tiefen", "mythic+", "retail", "patch 11.", "patch 12.",
        # Layering, server arhitektura i tehničke rasprave
        "layering", "server-architektur", "server architecture", "sharding", "netcode", "backend", "infrastruktur", "hardware",
        "grafik-upgrades", "wasser-upgrades", "beleuchtung", "lighting upgrade", "graphic upgrade",
        # Podcasti, intervjui o tehnologiji i community buildingu
        "podcast", "episode", "community-building", "community building", "ign-interview", "entwickler-interview",
        # Traileri, promo i opšte priče o popularnosti
        "release-trailer", "offizieller trailer", "warpath", "cinematic", "rekord", "hype", "beliebtheit", "spielerzahlen", "verkaufszahlen", "soundtrack", "teaser",
        # Opšte najave bez konkretnih detalja & kadenca pečeva
        "1.000 neue quests versprochen", "1000 neue quests", "patch-kadenz", "patch kadenz", "4-monatigen patch", "17-wochen", "timegating",
        # Tier liste
        "tier list", "tier-liste", "dps-ranking", "heiler-ranking", "tank-ranking"
    ]
    if any(b in combined for b in exclude_keywords):
        return False

    # Store bundle filter
    store_blacklist = ["shop bundle", "housing bundle", "trading post rewards", "sale 50%", "rabattaktion"]
    if any(b in combined for b in store_blacklist) and "forever" not in combined:
        return False

    forever_markers = ["forever", "wow forever", "classic forever", "legacy system", "camping system"]
    has_forever = any(m in combined for m in forever_markers)

    our_classes = detect_classes(combined)

    # Provera za druge klase: ako je članak ekskluzivno o drugim klasama, odbaci
    other_classes = ["rogue", "schurke", "priest", "priester", "mage", "magier", "paladin", "druid", "druide", "warlock", "hexenmeister", "warrior", "krieger"]
    other_count = sum(1 for c in other_classes if c in combined)
    if other_count > 0 and not our_classes:
        general_useful = ["camping", "taschen", "bag vendor", "dungeon", "leveling", "todesminen", "deadmines", "verlies", "stockades", "gnomeregan", "gold"]
        if not any(g in combined for g in general_useful):
            return False

    # 1. Članci specifični za Shamana ili Huntera
    if our_classes:
        gameplay_words = ["hotfix", "patch", "exploit", "talent", "buff", "nerf", "bis", "pet", "begleiter", "damage", "totem", "windfury", "ability", "fähigkeit", "leveling", "guide", "tuning", "zähm", "tame"]
        if any(g in combined for g in gameplay_words):
            return True

    # 2. Opšti praktični sadržaj koji koristi obojici (Camping, Quest nagrade, Torbe, Dungeon vodiči, Profesije)
    general_useful_words = [
        "camping", "legacy", "dungeon", "quest", "leveling", "gold",
        "todesminen", "deadmines", "verlies", "stockades", "gnomeregan",
        "bergbau", "mining", "engineering", "ingenieur", "kürschnerei", "skinning", "kräuterkunde", "herbalism",
        "tasche", "bags", "händler", "vendor", "starter"
    ]
    if has_forever and any(g in combined for g in general_useful_words):
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
    print("🚀 Pokrećem provereni WoW Forever Scraper (Fokus: Shaman & Hunter)...")
    existing_data = load_json(OUTPUT_FILE, {"items": []})
    seen_ids      = set(load_json(SEEN_IDS_FILE, []))

    if existing_data.get("items"):
        save_json(BACKUP_FILE, existing_data)

    collected_new = []
    sources_health = {}

    # 1. RSS Izvori
    for feed_cfg in RSS_FEEDS:
        feed_name = feed_cfg["name"]
        try:
            r = requests.get(feed_cfg["url"], headers=HEADERS, timeout=12)
            if r.status_code != 200:
                sources_health[feed_name] = f"HTTP {r.status_code}"
                continue
            
            feed = feedparser.parse(r.text)
            sources_health[feed_name] = f"OK ({len(feed.entries)} Meldungen)"
            print(f"📡 {feed_name}: {len(feed.entries)} pristiglih stavki.")

            for entry in feed.entries[:15]:
                title   = entry.get("title", "").strip()
                summary = BeautifulSoup(entry.get("summary", "") or "", "html.parser").get_text()[:600]
                link    = entry.get("link", "")

                if not is_relevant_context(title, summary):
                    continue

                full_text = fetch_full_text(link)
                content = full_text if len(full_text) > len(summary) else summary

                item_id = make_id(link if link else (title + summary))
                classes = detect_classes(title + " " + content)
                radar_status = detect_radar_status(title + " " + content)
                category = detect_category(title + " " + content)

                pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub_parsed:
                    pub_date = time.strftime("%Y-%m-%d", pub_parsed)
                else:
                    pub_date = datetime.now().strftime("%Y-%m-%d")

                article_de, teaser_de = generate_ai_summary(title, content, feed_name)

                if not article_de:
                    german_summary = translate_to_german(summary)
                    article_de = f"📌 **Zusammenfassung von {feed_name}:**\n{german_summary}\n\n💡 **Handlungsempfehlung:** Originalquelle für weitere Details im Link unten öffnen."
                    teaser_de  = german_summary[:180] + ("..." if len(german_summary) > 180 else "")

                german_title = translate_to_german(title)
                verified_label = "Blizzard-Bestätigt" if feed_cfg.get("official") else ("Guide / Analyse" if category == "guide" else "Community / Portal")

                collected_new.append({
                    "id": item_id,
                    "date": pub_date,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "source": feed_name,
                    "source_icon": feed_cfg["icon"],
                    "category": category,
                    "verified_type": verified_label,
                    "radar_status": radar_status,
                    "classes": classes,
                    "title": german_title,
                    "teaser_de": teaser_de,
                    "article_de": article_de,
                    "url": link
                })
        except Exception as e:
            sources_health[feed_name] = f"Fehler: {str(e)[:50]}"
            print(f"⚠️ Greška pri čitanju {feed_name}: {e}")

    # 2. Reddit sa proverom verzije i svežine
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

                    if score < 10 or not is_relevant_context(title, content):
                        continue

                    item_id = make_id(link if link else (title + content))
                    radar_status = detect_radar_status(title + " " + content)
                    category = detect_category(title + " " + content)
                    classes = detect_classes(title + " " + content)
                    article_de, teaser_de = generate_ai_summary(title, content, f"Reddit r/{sub}")

                    german_title = translate_to_german(title)
                    german_content = translate_to_german(content)

                    if not article_de:
                        article_de = f"📌 **Community-Meldung (Reddit):**\n{german_content}\n\n💡 **Handlungsempfehlung:** Erfahrung anderer Spieler prüfen und Diskussion im Link unten mitverfolgen."
                        teaser_de = german_content[:180] + ("..." if len(german_content) > 180 else "")

                    collected_new.append({
                        "id": item_id,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "source": f"Reddit r/{sub}",
                        "source_icon": "💬",
                        "category": category,
                        "verified_type": "Community-Diskussion",
                        "radar_status": radar_status,
                        "classes": classes,
                        "title": german_title,
                        "teaser_de": teaser_de,
                        "article_de": article_de,
                        "url": link
                    })
            except Exception as e:
                pass
    
    sources_health["Reddit (r/wowforever & r/classicwow)"] = "OK" if reddit_ok else "Keine neuen Top-Meldungen"

    # 3. Spajanje i ažuriranje postojećih vodiča (isti URL dobija nove podatke bez duplikata)
    old_items_map = {i["id"]: i for i in existing_data.get("items", [])}
    
    # Filtriraj stare stavke kroz rigorozni is_relevant_context kako bismo očistili nebitne
    filtered_old = []
    for item in old_items_map.values():
        if is_relevant_context(item.get("title", ""), item.get("teaser_de", ""), item.get("article_de", "")):
            # Proveri kategoriju i klase
            item["classes"] = [c for c in item.get("classes", []) if c in CLASSES]
            item["category"] = detect_category(item.get("title", "") + " " + item.get("article_de", ""))
            filtered_old.append(item)

    new_ids = set()
    unique_new = []
    for item in collected_new:
        iid = item["id"]
        if iid in old_items_map:
            # Ažuriraj postojeći vodič/vest novim podacima
            old_item = old_items_map[iid]
            old_item["title"] = item["title"]
            old_item["article_de"] = item["article_de"]
            old_item["teaser_de"] = item["teaser_de"]
            old_item["fetched_at"] = item["fetched_at"]
            old_item["radar_status"] = item["radar_status"]
            old_item["category"] = item["category"]
            old_item["classes"] = item["classes"]
        else:
            if iid not in new_ids:
                new_ids.add(iid)
                unique_new.append(item)

    merged = unique_new + [i for i in filtered_old if i["id"] not in new_ids]

    if not merged and filtered_old:
        merged = filtered_old

    # Sortiraj po datumu opadajuće
    merged.sort(key=lambda x: x.get("date", ""), reverse=True)

    today_str = datetime.now().strftime("%d.%m.%Y")
    
    # Zahtev 7: Ako nema novih relevantnih novosti
    if len(unique_new) == 0:
        daily_summary_text = "Heute keine neuen relevanten Updates für Shaman und Hunter."
    else:
        top_headlines = [i["title"] for i in unique_new[:2] if i.get("title")]
        headlines_summary = ("; ".join(top_headlines) + ".") if top_headlines else "Updates aktiv."
        daily_summary_text = f"Tagesbriefing ({today_str}): {len(unique_new)} neue relevante Updates erfasst. Themen: {headlines_summary}"

    result_payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_count": len(merged),
        "new_count": len(unique_new),
        "daily_summary": daily_summary_text,
        "castle_status": {
            "status": "Keine Live-Daten verifiziert",
            "details": "Aktuell liegen keine automatischen Burgen-Telemetriedaten vor. Status wird nach Serverstart über Live-Events angebunden.",
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "verified": False
        },
        "items": merged[:60],
        "sources_status": sources_health
    }

    save_json(OUTPUT_FILE, result_payload)
    save_json(SEEN_IDS_FILE, list(seen_ids | new_ids))
    print(f"✅ Uspešno završeno: {len(unique_new)} novih validnih stavki. Ukupno relevantnih: {len(merged)}")

if __name__ == "__main__":
    run_scraper()
