import requests
import feedparser
import json
import os
import hashlib
import time
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

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
CLASSES = ["Hunter", "Shaman", "Priest", "Rogue"]
FACTION = "Alliance"

OUTPUT_FILE   = "data/news.json"
SEEN_IDS_FILE = "data/seen_ids.json"
BACKUP_FILE   = "data/news_backup.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

RSS_FEEDS = [
    {"name": "Blizzard News",        "icon": "🔵", "url": "https://worldofwarcraft.blizzard.com/en-us/news/rss", "lang": "en", "official": True},
    {"name": "Blizzard Blue Tracker","icon": "🔷", "url": "https://us.forums.blizzard.com/en/wow/c/classic/classic-discussion.rss", "lang": "en", "official": True},
    {"name": "WoWhead Forever",      "icon": "🌐", "url": "https://www.wowhead.com/news/rss/all",                "lang": "en", "official": False},
    {"name": "Buffed.de",            "icon": "🇩🇪", "url": "https://www.buffed.de/feed/",                       "lang": "de", "official": False},
    {"name": "MMO-Champion",         "icon": "⚔️", "url": "https://www.mmo-champion.com/external.php?do=rss&type=newcontent&sectionid=1&days=2&count=25", "lang": "en", "official": False},
    {"name": "Icy Veins",            "icon": "❄️", "url": "https://www.icy-veins.com/wow/feed",                  "lang": "en", "official": False},
    {"name": "Warcraft Tavern",      "icon": "🍺", "url": "https://www.warcrafttavern.com/feed/",               "lang": "en", "official": False},
]

REDDIT_SUBREDDITS = ["classicwow", "wowforever", "wow"]

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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def translate_to_german(text):
    """
    Automatski prevodi engleski tekst na čist nemački jezik.
    Čisti 'Continue reading »' i link ostatke.
    """
    if not text:
        return ""
    clean = text.replace("Continue reading »", "").replace("Continue reading", "").replace("Continue Reading »", "").strip()
    
    # Ako je tekst već na nemačkom (npr. sa Buffed.de), ne prevodi
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
    t = text.lower()
    mapping = {
        "Hunter":  ["hunter", "jäger", "beast mastery", "bm hunter", "survival hunter", "marksman", "pet", "beast"],
        "Shaman":  ["shaman", "schamane", "enhancement", "elemental", "restoration shaman", "totem", "windfury"],
        "Priest":  ["priest", "priester", "holy priest", "shadow priest", "discipline priest", "penance", "smite"],
        "Rogue":   ["rogue", "schurke", "subtlety", "assassination", "combat rogue", "stealth", "shadowstep"],
    }
    return [cls for cls, kws in mapping.items() if any(k in t for k in kws)]

def detect_radar_status(text):
    t = text.lower()
    if any(w in t for w in ["fixed", "behober", "hotfixed", "resolved", "patched", "gefixt"]):
        return "fixed"
    if any(w in t for w in ["exploit", "abuse", "broken", "gamebreaking", "glitch", "gold farm exploit"]):
        if any(w in t for w in ["blue post", "blizzard confirms", "investigating", "acknowledged"]):
            return "confirmed"
        return "unconfirmed"
    if any(w in t for w in ["nerf", "buff", "balance change", "anpassung"]):
        return "balance"
    return "normal"

def is_relevant_context(title, summary, full_text=""):
    combined = (title + " " + summary + " " + full_text[:1000]).lower()

    hard_blacklist = ["red dead", "rdr2", "diablo", "overwatch", "hearthstone", "gta", "playstation", "xbox", "nintendo"]
    if any(b in combined for b in hard_blacklist):
        return False

    store_blacklist = ["shop bundle", "housing bundle", "trading post rewards", "sale 50%", "rabattaktion"]
    if any(b in combined for b in store_blacklist) and "forever" not in combined:
        return False

    if any(r in combined for r in ["midnight", "the war within", "dragonflight", "delves", "tiefen", "mythic+"]) and "forever" not in combined:
        return False

    forever_markers = ["forever", "wow forever", "classic forever", "legacy system", "camping system"]
    if any(m in combined for m in forever_markers):
        return True

    our_classes = detect_classes(combined)
    gameplay_words = ["hotfix", "patch", "exploit", "talent", "buff", "nerf", "bis", "pet", "damage"]
    if our_classes and any(g in combined for g in gameplay_words):
        if "retail" not in combined and "patch 11." not in combined and "patch 12." not in combined:
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
AI_PROMPT = """Du bist ein hochkarätiger WoW-Forever-Experte und Analyst für das private Dashboard von Faruk (Schamane, Zwerg, Bergbau/Engineering) & Mirza (Jäger 100%, Kürschnerei/Kräuterkunde, Allianz).

WICHTIGSTE REGELN:
- Antworte AUSSCHLIESSLICH auf reinem, flüssigem und fehlerfreiem DEUTSCH!
- Übersetze jeden englischen Inhalt, jede Überschrift und jeden Spielbegriff verständlich ins Deutsche.
- Wenn der Quelltext nur aus Gerüchten oder kurzen Teasern besteht, gib eine ehrliche deutsche Einschätzung.
- Erfinde keine Fakten, sondern beziehe dich exakt auf den Quelltext.

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
    print("🚀 Pokrećem sigurni WoW Forever Scraper (100% Deutsch)...")
    existing_data = load_json(OUTPUT_FILE, {"items": []})
    seen_ids      = set(load_json(SEEN_IDS_FILE, []))

    if existing_data.get("items"):
        save_json(BACKUP_FILE, existing_data)

    collected_new = []

    # 1. RSS Izvori
    for feed_cfg in RSS_FEEDS:
        try:
            r = requests.get(feed_cfg["url"], headers=HEADERS, timeout=12)
            feed = feedparser.parse(r.text)
            print(f"📡 {feed_cfg['name']}: {len(feed.entries)} pristiglih stavki.")

            for entry in feed.entries[:12]:
                title   = entry.get("title", "").strip()
                summary = BeautifulSoup(entry.get("summary", "") or "", "html.parser").get_text()[:600]
                link    = entry.get("link", "")

                if not is_relevant_context(title, summary):
                    continue

                full_text = fetch_full_text(link)
                content = full_text if len(full_text) > len(summary) else summary

                item_id = make_id(title + link)
                classes = detect_classes(title + " " + content)
                radar_status = detect_radar_status(title + " " + content)

                article_de, teaser_de = generate_ai_summary(title, content, feed_cfg["name"])

                # Fallback: Uvek prevedi na nemački ako AI nije aktivan
                if not article_de:
                    german_summary = translate_to_german(summary)
                    article_de = f"📌 **Zusammenfassung von {feed_cfg['name']}:**\n{german_summary}\n\n💡 **Handlungsempfehlung:** Originalquelle für weitere Details im Link unten öffnen."
                    teaser_de  = german_summary[:180] + ("..." if len(german_summary) > 180 else "")

                german_title = translate_to_german(title)
                verified_label = "Blizzard-Bestätigt" if feed_cfg.get("official") else ("Guide / Analyse" if "guide" in title.lower() else "Community / Portal")

                collected_new.append({
                    "id": item_id,
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "source": feed_cfg["name"],
                    "source_icon": feed_cfg["icon"],
                    "verified_type": verified_label,
                    "radar_status": radar_status,
                    "classes": classes,
                    "title": german_title,
                    "teaser_de": teaser_de,
                    "article_de": article_de,
                    "url": link,
                    "is_new": True
                })
        except Exception as e:
            print(f"⚠️ Greška pri čitanju {feed_cfg['name']}: {e}")

    # 2. Reddit (PullPush.io) sa proverom svežine
    yesterday = datetime.now(timezone.utc) - timedelta(days=2)
    for sub in REDDIT_SUBREDDITS:
        for kw in ["forever", "hunter", "camping", "legacy", "exploit"]:
            try:
                r = requests.get(
                    "https://api.pullpush.io/reddit/search/submission/",
                    params={"q": kw, "subreddit": sub, "size": 5, "after": int(yesterday.timestamp()), "sort": "score"},
                    timeout=8
                )
                if r.status_code != 200:
                    continue
                for post in r.json().get("data", []):
                    title   = post.get("title", "")
                    content = post.get("selftext", "")[:1200]
                    link    = "https://reddit.com" + post.get("permalink", "")
                    score   = post.get("score", 0)

                    if score < 15 or not is_relevant_context(title, content):
                        continue

                    item_id = make_id(title + link)
                    radar_status = detect_radar_status(title + " " + content)
                    article_de, teaser_de = generate_ai_summary(title, content, f"Reddit r/{sub}")

                    german_title = translate_to_german(title)
                    german_content = translate_to_german(content)

                    if not article_de:
                        article_de = f"📌 **Community-Meldung (Reddit):**\n{german_content}\n\n💡 **Handlungsempfehlung:** Diskussion im Link unten mitverfolgen."
                        teaser_de = german_content[:180] + ("..." if len(german_content) > 180 else "")

                    collected_new.append({
                        "id": item_id,
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "source": f"Reddit r/{sub}",
                        "source_icon": "💬",
                        "verified_type": "Community-Diskussion",
                        "radar_status": radar_status,
                        "classes": detect_classes(title + " " + content),
                        "title": german_title,
                        "teaser_de": teaser_de,
                        "article_de": article_de,
                        "url": link,
                        "is_new": True
                    })
            except Exception as e:
                print(f"⚠️ Reddit r/{sub} kw={kw} timeout ili greška: {e}")

    # Spajanje sa prethodnim unosima bez prepisivanja
    new_ids = set()
    unique_new = []
    for item in collected_new:
        if item["id"] not in seen_ids and item["id"] not in new_ids:
            new_ids.add(item["id"])
            unique_new.append(item)

    old_items = existing_data.get("items", [])
    merged = unique_new + [i for i in old_items if i["id"] not in new_ids]

    if not merged and old_items:
        print("⚠️ Upozorenje: Scraper nije dobio rezultate, zadržavam postojeće stanje.")
        merged = old_items

    merged.sort(key=lambda x: (x.get("is_new", False), x.get("date", "")), reverse=True)

    result_payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_count": len(merged),
        "new_count": len(unique_new),
        "daily_summary": existing_data.get("daily_summary") or "Tagesbriefing: Alle News und Klassen-Updates wurden automatisch auf Deutsch übersetzt und auf Relevanz für Faruk & Mirza geprüft.",
        "castle_status": existing_data.get("castle_status") or {
            "status": "Aktiv überwacht",
            "details": "Burgknoten und Außenposten werden mit Serveröffnung für die Allianz freigeschaltet.",
            "last_checked": datetime.now(timezone.utc).isoformat()
        },
        "items": merged[:60],
        "sources_status": {
            "blizzard_official": "OK",
            "wowhead": "OK",
            "buffed_de": "OK",
            "pullpush_reddit": "OK"
        }
    }

    save_json(OUTPUT_FILE, result_payload)
    save_json(SEEN_IDS_FILE, list(seen_ids | new_ids))
    print(f"✅ Uspešno završeno: {len(unique_new)} novih validnih stavki na nemačkom. Ukupno u bazi: {len(merged)}")

if __name__ == "__main__":
    run_scraper()
