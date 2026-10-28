import requests
import feedparser
import json
import os
import hashlib
import time
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

# ─── CONFIG ───────────────────────────────────────────────────────────────────
CLASSES = ["Hunter", "Shaman", "Priest", "Rogue"]
FACTION = "Alliance"

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel("gemini-2.0-flash")
else:
    ai_model = None

OUTPUT_FILE   = "data/news.json"
BIS_FILE      = "data/bis.json"
SEEN_IDS_FILE = "data/seen_ids.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}

# ─── SOURCES ──────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    {"name": "Buffed.de",        "icon": "🇩🇪", "url": "https://www.buffed.de/feed/",              "lang": "de"},
    {"name": "GameStar WoW",     "icon": "🇩🇪", "url": "https://www.gamestar.de/themen/world-of-warcraft/news/rss.xml", "lang": "de"},
    {"name": "Wowhead",          "icon": "🌐", "url": "https://www.wowhead.com/news/rss/all",        "lang": "en"},
    {"name": "MMO-Champion",     "icon": "⚔️", "url": "https://www.mmo-champion.com/external.php?do=rss&type=newcontent&sectionid=1&days=1&count=25", "lang": "en"},
    {"name": "Icy Veins",        "icon": "❄️", "url": "https://www.icy-veins.com/wow/feed",          "lang": "en"},
    {"name": "WoW Blue Tracker", "icon": "🔵", "url": "https://www.wowhead.com/blue-tracker/rss",    "lang": "en"},
]

REDDIT_SUBREDDITS = ["wow", "classicwow", "wowforever"]
REDDIT_KEYWORDS   = [
    "hunter","shaman","priest","rogue","exploit","hotfix","patch","bug",
    "bis","best in slot","castle","pvp","alliance","nerf","buff",
    "leveling","talent","pet","instance","raid","dungeon","forever","tier"
]

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def make_id(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def detect_classes(text):
    t = text.lower()
    mapping = {
        "Hunter":  ["hunter","jäger","beast mastery","bm hunter","marksman","survival","pet","beast","hawk","aspect"],
        "Shaman":  ["shaman","schamane","enhancement","elemental","resto shaman","totem","windfury"],
        "Priest":  ["priest","priester","holy priest","shadow priest","discipline","disc","smite","penance"],
        "Rogue":   ["rogue","schurke","subtlety","assassination","combat","shadowstep","stealth","backstab"],
    }
    return [cls for cls, kws in mapping.items() if any(k in t for k in kws)]

def categorise(text):
    t = text.lower()
    if any(w in t for w in ["exploit","abuse","broken","bug","glitch"]): return "exploit"
    if any(w in t for w in ["hotfix","fix","patch","update","nerf","buff"]): return "hotfix"
    if any(w in t for w in ["bis","best in slot","gear","item","loot"]): return "bis"
    if any(w in t for w in ["guide","talent","build","leveling","spec"]): return "guide"
    if any(w in t for w in ["pvp","castle","siege","arena","battleground"]): return "pvp"
    if any(w in t for w in ["raid","dungeon","instance","boss","mythic"]): return "pve"
    return "news"

def is_relevant(title, summary):
    text = (title + " " + summary).lower()
    
    # STRIKTNO ISKLJUČI sve druge ekspanzije / Retail teme:
    blacklist = [
        "midnight", "the war within", "dragonflight", "shadowlands", 
        "battle for azeroth", "bfa", "legion", "warlords of draenor", "wod",
        "mists of pandaria", "cataclysm", "wrath of the lich king", "wotlk",
        "retail", "patch 11.", "patch 12.", "tiefen", "delves", "mythic+"
    ]
    if any(b in text for b in blacklist):
        # Ako izričito spominje "forever", ne odbacuj, inače odbaci sve retail/midnight teme
        if "forever" not in text:
            return False

    # Mora biti vezano za WoW Forever ili ključne mehanike WoW Forevera
    forever_triggers = ["forever", "wow forever", "classic forever"]
    has_forever = any(k in text for k in forever_triggers)
    
    # Ako je u pitanju opšti vanilla/classic hotfix/guide a spominje tvoje klase
    class_triggers = ["hunter", "jäger", "shaman", "schamane", "priest", "priester", "rogue", "schurke"]
    has_class_exploit = any(c in text for c in class_triggers) and any(x in text for x in ["exploit", "hotfix", "bug", "bis", "castle", "burg"])

    return has_forever or has_class_exploit


# ─── FULL ARTICLE FETCHER ─────────────────────────────────────────────────────
def fetch_full_article(url: str) -> str:
    """Fetches full article text from URL."""
    if not url:
        return ""
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        if r.status_code != 200:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")

        # Remove noise
        for tag in soup(["script","style","nav","footer","header","aside",
                         "iframe","form","button",".ad","#ad"]):
            tag.decompose()

        # Try to find main article body
        candidates = [
            soup.find("article"),
            soup.find(class_=lambda c: c and any(x in str(c).lower() for x in ["article","content","post-body","entry"])),
            soup.find("main"),
            soup.find(id=lambda i: i and any(x in str(i).lower() for x in ["content","article","main"])),
        ]
        for el in candidates:
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    return text[:4000]

        # Fallback: full body text
        return soup.get_text(separator="\n", strip=True)[:4000]
    except Exception as e:
        print(f"[Fetch] Error {url}: {e}")
        return ""

# ─── AI SUMMARIZER ────────────────────────────────────────────────────────────
ARTICLE_PROMPT = """Du bist ein WoW-Forever-Experte und schreibst für das private Dashboard von Faruk & Mirza (Allianz-Spieler, Start 04.11.2026).
Die Klassen der Spieler: 🏹 Hunter (Beast Mastery), 🌊 Shaman, ✨ Priest, 🗡️ Rogue.

Schreibe einen vollständigen Bericht auf DEUTSCH (150–250 Wörter) basierend auf dem Artikel unten.

STRUKTUR (verwende diese Abschnitte wenn relevant):
📌 **Was ist passiert?** — Kurze, klare Einleitung
🎮 **Was bedeutet das für unsere Klassen?** — Konkret für Hunter/Shaman/Priest/Rogue
💡 **Was sollten wir tun?** — Handlungsempfehlung, Talent-Tipp, BiS-Hinweis, Pet-Empfehlung oder Exploit-Warnung

Falls der Artikel keine dieser Klassen betrifft, schreibe trotzdem einen informativen Bericht für WoW Forever allgemein.
Keine Einleitung wie "Hier ist der Bericht:" — direkt mit dem Inhalt starten.
Verwende Emojis sparsam aber gezielt.

Artikel-Titel: {title}
Quelle: {source}
Artikel-Text:
{content}
"""

SHORT_PROMPT = """Du bist WoW-Experte. Fasse in 2 Sätzen auf Deutsch zusammen — was ist passiert und was bedeutet das für Hunter/Shaman/Priest/Rogue?
Kein "Zusammenfassung:" — direkt beginnen.
Titel: {title}
Text: {content}
"""

def ai_write_article(title, url, content, source):
    """Uses Gemini to write a full German article."""
    if not ai_model:
        return None, None
    try:
        # Full article
        full_prompt = ARTICLE_PROMPT.format(
            title=title, source=source, content=content[:3500]
        )
        full_resp = ai_model.generate_content(full_prompt)
        full_text = full_resp.text.strip()

        # Short teaser (2 sentences)
        short_prompt = SHORT_PROMPT.format(title=title, content=content[:800])
        short_resp = ai_model.generate_content(short_prompt)
        short_text = short_resp.text.strip()

        time.sleep(0.5)  # Rate limit protection
        return full_text, short_text
    except Exception as e:
        print(f"[AI] Error: {e}")
        return None, None

# ─── SCRAPERS ─────────────────────────────────────────────────────────────────
def scrape_rss_feeds():
    items = []
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    for feed_cfg in RSS_FEEDS:
        try:
            r = requests.get(feed_cfg["url"], headers=HEADERS, timeout=15)
            feed = feedparser.parse(r.text)
            print(f"[RSS] {feed_cfg['name']}: {len(feed.entries)} entries")

            for entry in feed.entries[:15]:
                title   = entry.get("title", "").strip()
                rss_sum = entry.get("summary", "") or ""
                rss_sum = BeautifulSoup(rss_sum, "html.parser").get_text()[:500]
                link    = entry.get("link", "")

                # Date filter
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < yesterday:
                        continue

                if not is_relevant(title, rss_sum):
                    continue

                # Fetch full article
                print(f"  → Fetching: {title[:60]}")
                full_text = fetch_full_article(link)
                content   = full_text if full_text else rss_sum

                classes  = detect_classes(title + " " + content)
                category = categorise(title + " " + content)

                # AI: write German article
                article_de, teaser_de = ai_write_article(title, link, content, feed_cfg["name"])

                items.append({
                    "id":          make_id(title + link),
                    "date":        datetime.now().strftime("%Y-%m-%d"),
                    "source":      feed_cfg["name"],
                    "source_icon": feed_cfg["icon"],
                    "source_lang": feed_cfg["lang"],
                    "category":    category,
                    "classes":     classes,
                    "title":       title,
                    "teaser_de":   teaser_de or rss_sum[:200],
                    "article_de":  article_de or rss_sum,
                    "url":         link,
                    "is_new":      True,
                    "tags":        classes,
                })

        except Exception as e:
            print(f"[RSS] Error {feed_cfg['name']}: {e}")

    return items

def scrape_reddit():
    items = []
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    seen = set()

    for sub in REDDIT_SUBREDDITS:
        for kw in ["forever","hunter","shaman","rogue","priest","hotfix","exploit","bis","leveling","pet"]:
            try:
                r = requests.get(
                    "https://api.pullpush.io/reddit/search/submission/",
                    params={"q":kw,"subreddit":sub,"size":6,"after":int(yesterday.timestamp()),"sort":"score"},
                    timeout=10
                )
                if r.status_code != 200:
                    continue
                for post in r.json().get("data",[]):
                    title   = post.get("title","")
                    content = post.get("selftext","")[:1500]
                    link    = "https://reddit.com" + post.get("permalink","")
                    score   = post.get("score",0)
                    if score < 20 or not is_relevant(title, content):
                        continue
                    item_id = make_id(title + link)
                    if item_id in seen:
                        continue
                    seen.add(item_id)

                    classes  = detect_classes(title + " " + content)
                    category = categorise(title + " " + content)
                    full_content = f"[Reddit r/{sub} | Score: {score}]\n\n{title}\n\n{content}"
                    article_de, teaser_de = ai_write_article(f"[Reddit] {title}", link, full_content, f"Reddit r/{sub}")

                    items.append({
                        "id":          item_id,
                        "date":        datetime.now().strftime("%Y-%m-%d"),
                        "source":      f"Reddit r/{sub}",
                        "source_icon": "💬",
                        "source_lang": "en",
                        "category":    category,
                        "classes":     classes,
                        "title":       title,
                        "teaser_de":   teaser_de or content[:200],
                        "article_de":  article_de or content,
                        "url":         link,
                        "score":       score,
                        "is_new":      True,
                        "tags":        classes,
                    })
            except Exception as e:
                print(f"[Reddit] r/{sub} kw={kw}: {e}")

    return items

def check_castle_status():
    try:
        feed = feedparser.parse("https://www.wowhead.com/news/rss/all")
        for entry in feed.entries[:20]:
            title = entry.get("title","").lower()
            if any(w in title for w in ["castle","pvp","siege","world boss","world pvp"]):
                content = fetch_full_article(entry.get("link",""))
                article_de, _ = ai_write_article(entry.get("title",""), entry.get("link",""), content, "Wowhead")
                return {
                    "last_checked": datetime.now().isoformat(),
                    "status":       "⚔️ Aktives Event erkannt!",
                    "details":      article_de or entry.get("title",""),
                    "url":          entry.get("link",""),
                }
    except Exception as e:
        print(f"[Castle] {e}")
    return {
        "last_checked": datetime.now().isoformat(),
        "status":       "🟢 Keine aktive Belagerung",
        "details":      "Keine Welt-PvP- oder Burg-Events in den letzten 24 Stunden gefunden.",
    }

def build_daily_summary(items):
    new_items = [i for i in items if i.get("is_new")]
    if not new_items:
        return "📭 Heute keine neuen Updates. Bis morgen!"
    cls_e = {"Hunter":"🏹","Shaman":"🌊","Priest":"✨","Rogue":"🗡️"}
    parts = [f"📰 {len(new_items)} neue Meldungen heute."]
    for cls in CLASSES:
        cnt = sum(1 for i in new_items if cls in i.get("classes",[]))
        if cnt:
            parts.append(f"{cls_e.get(cls,'')} {cls}: {cnt} Update(s)")
    if any(i.get("category")=="exploit" for i in new_items):
        n = sum(1 for i in new_items if i.get("category")=="exploit")
        parts.append(f"🔴 ACHTUNG: {n} Exploit(s) entdeckt!")
    return " | ".join(parts)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    print("🔍 Starte WoW Forever Scraper...")
    seen_ids = set(load_json(SEEN_IDS_FILE, []))
    existing = load_json(OUTPUT_FILE, {"items":[]})

    rss_items    = scrape_rss_feeds()
    reddit_items = scrape_reddit()
    all_new      = rss_items + reddit_items

    new_ids = set()
    for item in all_new:
        item["is_new"] = item["id"] not in seen_ids
        new_ids.add(item["id"])

    cutoff    = (datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d")
    old_items = [i for i in existing.get("items",[]) if i.get("date","")>=cutoff]
    old_ids   = {i["id"] for i in old_items}
    merged    = [i for i in all_new if i["id"] not in old_ids] + old_items
    merged.sort(key=lambda x:(x.get("is_new",False),x.get("date","")),reverse=True)

    castle  = check_castle_status()
    summary = build_daily_summary(merged)

    save_json(OUTPUT_FILE, {
        "last_updated":  datetime.now().isoformat(),
        "classes":       CLASSES,
        "faction":       FACTION,
        "items":         merged[:80],
        "castle_status": castle,
        "daily_summary": summary,
    })
    save_json(SEEN_IDS_FILE, list(seen_ids | new_ids))
    new_count = sum(1 for i in merged if i.get("is_new"))
    print(f"✅ Fertig! {new_count} neue Einträge. Gesamt: {len(merged)}")

if __name__ == "__main__":
    main()
