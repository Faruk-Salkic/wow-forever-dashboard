import requests
import feedparser
import json
import os
import hashlib
import google.generativeai as genai
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

# ─── CONFIG ──────────────────────────────────────────────────────────────────
CLASSES = ["Hunter", "Shaman", "Priest", "Rogue"]
FACTION = "Alliance"

# Gemini AI setup
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel("gemini-2.0-flash")
else:
    ai_model = None

# ─── SOURCES ─────────────────────────────────────────────────────────────────
RSS_FEEDS = [
    # German sources
    {"name": "Buffed.de",       "icon": "🇩🇪", "url": "https://www.buffed.de/feed/",              "lang": "de"},
    {"name": "GameStar WoW",    "icon": "🇩🇪", "url": "https://www.gamestar.de/themen/world-of-warcraft/news/rss.xml", "lang": "de"},
    # English sources
    {"name": "Wowhead",         "icon": "🌐", "url": "https://www.wowhead.com/news/rss/all",       "lang": "en"},
    {"name": "MMO-Champion",    "icon": "⚔️", "url": "https://www.mmo-champion.com/external.php?do=rss&type=newcontent&sectionid=1&days=1&count=25", "lang": "en"},
    {"name": "Icy Veins",       "icon": "❄️", "url": "https://www.icy-veins.com/wow/feed",         "lang": "en"},
    {"name": "WoW Blue Tracker","icon": "🔵", "url": "https://www.wowhead.com/blue-tracker/rss",   "lang": "en"},
]

REDDIT_SUBREDDITS = ["wow", "classicwow", "wowforever"]
REDDIT_KEYWORDS   = [
    "hunter", "shaman", "priest", "rogue",
    "exploit", "hotfix", "patch", "bug", "bis", "best in slot",
    "castle", "pvp", "alliance", "nerf", "buff",
    "leveling", "talent", "pet", "instance", "raid", "dungeon",
    "forever", "4.11", "tier list"
]

OUTPUT_FILE   = "data/news.json"
BIS_FILE      = "data/bis.json"
SEEN_IDS_FILE = "data/seen_ids.json"

# ─── HELPERS ─────────────────────────────────────────────────────────────────
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
    text = text.lower()
    mapping = {
        "Hunter":  ["hunter", "jäger", "beast mastery", "bm hunter", "marksman", "survival", "pet", "beast"],
        "Shaman":  ["shaman", "schamane", "enhancement", "elemental", "resto shaman", "totem"],
        "Priest":  ["priest", "priester", "holy priest", "shadow priest", "discipline", "disc"],
        "Rogue":   ["rogue", "schurke", "subtlety", "assassination", "combat", "shadowstep", "stealth"],
    }
    return [cls for cls, kws in mapping.items() if any(k in text for k in kws)]

def categorise(text):
    text = text.lower()
    if any(w in text for w in ["exploit", "abuse", "broken", "bug"]):     return "exploit"
    if any(w in text for w in ["hotfix", "fix", "patch", "update"]):      return "hotfix"
    if any(w in text for w in ["bis", "best in slot", "gear", "item"]):   return "bis"
    if any(w in text for w in ["guide", "talent", "build", "leveling"]):  return "guide"
    if any(w in text for w in ["pvp", "castle", "siege", "arena"]):       return "pvp"
    if any(w in text for w in ["raid", "dungeon", "instance", "boss"]):   return "pve"
    if any(w in text for w in ["pet", "hunter", "tame", "beast"]):        return "hunter"
    return "news"

def is_relevant(title, summary):
    text = (title + " " + summary).lower()
    return any(k in text for k in REDDIT_KEYWORDS + ["wow", "warcraft", "azeroth", "forever"])

# ─── AI SUMMARIZER ────────────────────────────────────────────────────────────
SUMMARY_PROMPT = """Du bist ein WoW-Experte und schreibst für das Dashboard von Faruk & Mirza (Alliance-Spieler).
Klassen die sie spielen: Hunter (Beast Mastery), Shaman, Priest, Rogue.

Fasse den folgenden Artikel in maximal 3 kurzen Sätzen auf DEUTSCH zusammen.
Fokus auf: Was wurde geändert/entdeckt? Was bedeutet das konkret für die genannten Klassen?
Erwähne wenn relevant: Talente, Leveling-Tipps, Pets (Hunter), BiS-Items, Bosse, Instanzen, PvP.

Falls der Artikel keine dieser Klassen betrifft, schreibe trotzdem eine kurze allgemeine Zusammenfassung.
Keine Einleitung, kein "Hier ist die Zusammenfassung:" — direkt mit dem Inhalt beginnen.

Artikel-Titel: {title}
Artikel-Inhalt: {content}
"""

def ai_summarize(title, content, classes):
    if not ai_model:
        return None
    try:
        prompt = SUMMARY_PROMPT.format(
            title=title,
            content=content[:2000],
        )
        response = ai_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[AI] Summarize error: {e}")
        return None

# ─── SCRAPERS ─────────────────────────────────────────────────────────────────
def scrape_rss_feeds():
    items = []
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    for feed_cfg in RSS_FEEDS:
        try:
            headers = {"User-Agent": "WoW-Dashboard-Bot/1.0"}
            r = requests.get(feed_cfg["url"], headers=headers, timeout=15)
            feed = feedparser.parse(r.text)
            print(f"[RSS] {feed_cfg['name']}: {len(feed.entries)} entries")

            for entry in feed.entries[:20]:
                title   = entry.get("title", "").strip()
                raw_sum = entry.get("summary", "") or entry.get("content", [{}])[0].get("value","")
                summary = BeautifulSoup(raw_sum, "html.parser").get_text()[:1000]
                link    = entry.get("link", "")

                # Date filter
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < yesterday:
                        continue

                if not is_relevant(title, summary):
                    continue

                classes  = detect_classes(title + " " + summary)
                category = categorise(title + " " + summary)

                # AI summary
                ai_sum = ai_summarize(title, summary, classes)

                items.append({
                    "id":           make_id(title + link),
                    "date":         datetime.now().strftime("%Y-%m-%d"),
                    "source":       feed_cfg["name"],
                    "source_icon":  feed_cfg["icon"],
                    "source_lang":  feed_cfg["lang"],
                    "category":     category,
                    "classes":      classes,
                    "title":        title,
                    "summary_orig": summary[:300],
                    "summary_de":   ai_sum or summary[:300],
                    "url":          link,
                    "is_new":       True,
                    "tags":         classes,
                })
        except Exception as e:
            print(f"[RSS] Error {feed_cfg['name']}: {e}")

    return items

def scrape_reddit():
    items = []
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    seen = set()
    for sub in REDDIT_SUBREDDITS:
        for kw in ["forever", "hunter", "shaman", "rogue", "priest", "hotfix", "exploit", "bis", "leveling"]:
            try:
                r = requests.get(
                    "https://api.pullpush.io/reddit/search/submission/",
                    params={"q": kw, "subreddit": sub, "size": 8,
                            "after": int(yesterday.timestamp()), "sort": "score"},
                    timeout=10
                )
                if r.status_code != 200:
                    continue
                for post in r.json().get("data", []):
                    title   = post.get("title", "")
                    content = post.get("selftext", "")[:800]
                    link    = "https://reddit.com" + post.get("permalink", "")
                    score   = post.get("score", 0)
                    if score < 15 or not is_relevant(title, content):
                        continue

                    item_id = make_id(title + link)
                    if item_id in seen:
                        continue
                    seen.add(item_id)

                    classes  = detect_classes(title + " " + content)
                    category = categorise(title + " " + content)
                    ai_sum   = ai_summarize(f"[Reddit r/{sub}] " + title, content, classes)

                    items.append({
                        "id":           item_id,
                        "date":         datetime.now().strftime("%Y-%m-%d"),
                        "source":       f"Reddit r/{sub}",
                        "source_icon":  "💬",
                        "source_lang":  "en",
                        "category":     category,
                        "classes":      classes,
                        "title":        title,
                        "summary_orig": content[:300] or "(Link-Post)",
                        "summary_de":   ai_sum or content[:300],
                        "url":          link,
                        "score":        score,
                        "is_new":       True,
                        "tags":         classes,
                    })
            except Exception as e:
                print(f"[Reddit] r/{sub} kw={kw}: {e}")

    return items

def check_castle_status():
    try:
        feed = feedparser.parse("https://www.wowhead.com/news/rss/all")
        for entry in feed.entries[:20]:
            title = entry.get("title", "").lower()
            if any(w in title for w in ["castle", "pvp", "siege", "world boss", "world pvp"]):
                sum_de = ai_summarize(entry.get("title",""), entry.get("summary",""), [])
                return {
                    "last_checked": datetime.now().isoformat(),
                    "status":       "⚔️ Aktives Event erkannt!",
                    "details":      sum_de or entry.get("title",""),
                    "url":          entry.get("link",""),
                }
    except Exception as e:
        print(f"[Castle] {e}")

    return {
        "last_checked": datetime.now().isoformat(),
        "status":       "🟢 Keine aktive Belagerung",
        "details":      "Keine Welt-PvP / Burg-Events in den letzten 24 Stunden.",
    }

def build_daily_summary_de(items):
    if not items:
        return "📭 Keine neuen Nachrichten heute. Bis morgen!"

    new_items = [i for i in items if i.get("is_new")]
    if not new_items:
        return "📭 Heute keine neuen Updates."

    cls_emoji = {"Hunter":"🏹","Shaman":"🌊","Priest":"✨","Rogue":"🗡️"}
    parts = [f"📰 {len(new_items)} neue Meldungen heute."]
    for cls in CLASSES:
        cnt = sum(1 for i in new_items if cls in i.get("classes",[]))
        if cnt:
            parts.append(f"{cls_emoji.get(cls,'')} {cls}: {cnt} Update(s)")
    exploits = [i for i in new_items if i.get("category") == "exploit"]
    if exploits:
        parts.append(f"🔴 ACHTUNG: {len(exploits)} Exploit(s) gefunden!")
    return " | ".join(parts)

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print("🔍 Scraping WoW Forever news...")
    seen_ids = set(load_json(SEEN_IDS_FILE, []))
    existing = load_json(OUTPUT_FILE, {"items": []})

    rss_items    = scrape_rss_feeds()
    reddit_items = scrape_reddit()
    all_new      = rss_items + reddit_items

    new_ids = set()
    for item in all_new:
        item["is_new"] = item["id"] not in seen_ids
        new_ids.add(item["id"])

    cutoff    = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    old_items = [i for i in existing.get("items", []) if i.get("date","") >= cutoff]
    old_ids   = {i["id"] for i in old_items}
    merged    = [i for i in all_new if i["id"] not in old_ids] + old_items
    merged.sort(key=lambda x: (x.get("is_new", False), x.get("date","")), reverse=True)

    castle  = check_castle_status()
    summary = build_daily_summary_de(merged)

    save_json(OUTPUT_FILE, {
        "last_updated":  datetime.now().isoformat(),
        "classes":       CLASSES,
        "faction":       FACTION,
        "items":         merged[:100],
        "castle_status": castle,
        "daily_summary": summary,
    })
    save_json(SEEN_IDS_FILE, list(seen_ids | new_ids))

    new_count = sum(1 for i in merged if i.get("is_new"))
    print(f"✅ Done! {new_count} neue Einträge. Gesamt: {len(merged)}")

if __name__ == "__main__":
    main()
