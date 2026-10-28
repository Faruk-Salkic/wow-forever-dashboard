import requests
import feedparser
import json
import os
import hashlib
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

# ─── CONFIG ──────────────────────────────────────────────────────────────────
CLASSES = ["Hunter", "Shaman", "Priest", "Rogue"]
FACTION = "Alliance"

RSS_FEEDS = [
    {"name": "Wowhead",     "icon": "🌐", "url": "https://www.wowhead.com/news/rss/all"},
    {"name": "MMO-Champion","icon": "⚔️", "url": "https://www.mmo-champion.com/external.php?do=rss&type=newcontent&sectionid=1&days=1&count=20"},
    {"name": "Icy Veins",   "icon": "❄️", "url": "https://www.icy-veins.com/wow/feed"},
]

REDDIT_SUBREDDITS = ["wow", "classicwow", "wowservers"]
REDDIT_KEYWORDS   = ["forever", "hunter", "shaman", "priest", "rogue",
                     "exploit", "hotfix", "patch", "bug", "bis", "castle",
                     "pvp", "alliance", "nerf", "buff", "tier"]

OUTPUT_FILE = "data/news.json"
SEEN_IDS_FILE = "data/seen_ids.json"

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]

def load_seen_ids():
    if os.path.exists(SEEN_IDS_FILE):
        with open(SEEN_IDS_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen_ids(ids):
    with open(SEEN_IDS_FILE, "w") as f:
        json.dump(list(ids), f)

def load_existing_news():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            return json.load(f)
    return {"items": [], "castle_status": {}, "daily_summary": ""}

def detect_classes(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    mapping = {
        "Hunter":  ["hunter", "pet", "beast mastery", "marksmanship", "survival"],
        "Shaman":  ["shaman", "enhancement", "elemental", "restoration shaman", "totems"],
        "Priest":  ["priest", "holy priest", "shadow priest", "discipline", "disc priest"],
        "Rogue":   ["rogue", "subtlety", "assassination", "combat rogue", "shadowstep"],
    }
    for cls, keywords in mapping.items():
        if any(k in text_lower for k in keywords):
            found.append(cls)
    return found if found else []

def categorise(title: str, summary: str) -> str:
    text = (title + " " + summary).lower()
    if any(w in text for w in ["hotfix", "fix", "patch"]):      return "hotfix"
    if any(w in text for w in ["exploit", "bug", "abuse"]):      return "exploit"
    if any(w in text for w in ["guide", "bis", "build", "tier"]): return "guide"
    if any(w in text for w in ["pvp", "castle", "siege", "wpvp"]): return "pvp"
    if any(w in text for w in ["raid", "dungeon", "mythic"]):    return "pve"
    return "news"

def is_relevant(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(k in text for k in REDDIT_KEYWORDS + ["forever", "wow", "warcraft"])

# ─── SCRAPERS ─────────────────────────────────────────────────────────────────
def scrape_rss_feeds() -> list[dict]:
    items = []
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    for feed_cfg in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_cfg["url"])
            for entry in feed.entries[:30]:
                title   = entry.get("title", "")
                summary = BeautifulSoup(entry.get("summary", ""), "html.parser").get_text()[:300]
                link    = entry.get("link", "")

                # Date filter — only last 24h
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < yesterday:
                        continue

                if not is_relevant(title, summary):
                    continue

                items.append({
                    "id":          make_id(title + link),
                    "date":        datetime.now().strftime("%Y-%m-%d"),
                    "source":      feed_cfg["name"],
                    "source_icon": feed_cfg["icon"],
                    "category":    categorise(title, summary),
                    "classes":     detect_classes(title + " " + summary),
                    "title":       title,
                    "summary":     summary,
                    "url":         link,
                    "is_new":      True,
                    "tags":        detect_classes(title + " " + summary),
                })
        except Exception as e:
            print(f"[RSS] Error for {feed_cfg['name']}: {e}")

    return items

def scrape_reddit() -> list[dict]:
    items = []
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1))

    for sub in REDDIT_SUBREDDITS:
        for kw in ["forever", "hunter", "shaman", "rogue", "priest", "hotfix", "exploit"]:
            try:
                url = f"https://api.pullpush.io/reddit/search/submission/"
                params = {
                    "q":         kw,
                    "subreddit": sub,
                    "size":      10,
                    "after":     int(yesterday.timestamp()),
                    "sort":      "score",
                }
                r = requests.get(url, params=params, timeout=10)
                if r.status_code != 200:
                    continue
                data = r.json().get("data", [])
                for post in data:
                    title   = post.get("title", "")
                    summary = post.get("selftext", "")[:300]
                    link    = f"https://reddit.com{post.get('permalink', '')}"
                    score   = post.get("score", 0)

                    # Skip low-quality posts
                    if score < 10:
                        continue

                    item_id = make_id(title + link)
                    items.append({
                        "id":          item_id,
                        "date":        datetime.now().strftime("%Y-%m-%d"),
                        "source":      f"Reddit r/{sub}",
                        "source_icon": "💬",
                        "category":    categorise(title, summary),
                        "classes":     detect_classes(title + " " + summary),
                        "title":       f"[Reddit] {title}",
                        "summary":     summary or "(no text — link post)",
                        "url":         link,
                        "score":       score,
                        "is_new":      True,
                        "tags":        detect_classes(title + " " + summary),
                    })
            except Exception as e:
                print(f"[Reddit] Error for r/{sub} kw={kw}: {e}")

    # Deduplicate
    seen = set()
    unique = []
    for item in items:
        if item["id"] not in seen:
            seen.add(item["id"])
            unique.append(item)
    return unique

def check_castle_status() -> dict:
    """Try to pull WoW castle / world PvP news from Wowhead."""
    try:
        r = requests.get("https://www.wowhead.com/news/rss/all", timeout=10)
        feed = feedparser.parse(r.text)
        for entry in feed.entries[:20]:
            title = entry.get("title", "").lower()
            if any(w in title for w in ["castle", "pvp", "siege", "world boss"]):
                return {
                    "last_checked": datetime.now().isoformat(),
                    "status":       "⚔️ Active event detected!",
                    "details":      entry.get("title", ""),
                    "url":          entry.get("link", ""),
                }
    except Exception as e:
        print(f"[Castle] Error: {e}")

    return {
        "last_checked": datetime.now().isoformat(),
        "status":       "🟢 No active siege",
        "details":      "No castle / World PvP events found in last 24h.",
    }

def build_daily_summary(items: list[dict]) -> str:
    if not items:
        return "📭 Nema novih vijesti danas. Provjeri sutra!"
    class_mentions = {}
    for cls in CLASSES:
        count = sum(1 for i in items if cls in i.get("classes", []))
        if count:
            class_mentions[cls] = count
    parts = [f"📰 {len(items)} novih vijesti danas."]
    for cls, cnt in class_mentions.items():
        emoji = {"Hunter":"🏹","Shaman":"🔵","Priest":"✨","Rogue":"🗡️"}.get(cls,"")
        parts.append(f"{emoji} {cls}: {cnt} update(s)")
    exploits = [i for i in items if i["category"] == "exploit"]
    if exploits:
        parts.append(f"🔴 PAZI: {len(exploits)} exploit(a) pronađen!")
    return " | ".join(parts)

# ─── MAIN ────────────────────────────────────────────────────────────────────
def main():
    print("🔍 Scraping WoW Forever news...")
    seen_ids   = load_seen_ids()
    existing   = load_existing_news()

    # Scrape
    rss_items    = scrape_rss_feeds()
    reddit_items = scrape_reddit()
    all_new      = rss_items + reddit_items

    # Mark truly new items
    new_ids = set()
    for item in all_new:
        item["is_new"] = item["id"] not in seen_ids
        new_ids.add(item["id"])

    # Merge with old (keep last 7 days)
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    old_items = [i for i in existing.get("items", []) if i.get("date", "") >= cutoff]
    old_ids   = {i["id"] for i in old_items}

    merged = [i for i in all_new if i["id"] not in old_ids] + old_items
    # Sort newest first
    merged.sort(key=lambda x: x.get("date", ""), reverse=True)

    castle = check_castle_status()
    summary = build_daily_summary([i for i in merged if i.get("is_new")])

    output = {
        "last_updated":  datetime.now().isoformat(),
        "classes":       CLASSES,
        "faction":       FACTION,
        "items":         merged[:100],  # cap at 100
        "castle_status": castle,
        "daily_summary": summary,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    save_seen_ids(seen_ids | new_ids)
    new_count = sum(1 for i in merged if i.get("is_new"))
    print(f"✅ Done! {new_count} new items. Total: {len(merged)}")

if __name__ == "__main__":
    main()

