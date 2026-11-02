"""Daily checks of selected leveling guides; store fingerprints, never source copies."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re

if __package__:
    from .scrape import compute_source_hash, fetch_document, load_json, save_json
else:
    from scrape import compute_source_hash, fetch_document, load_json, save_json

ROOT = Path(__file__).resolve().parents[1]
SOURCES_FILE = ROOT / "data/guide_sources.json"
OUTPUT_FILE = ROOT / "data/recommendations.json"


def check_guides(sources, previous=None, fetcher=None, now=None):
    """Initial reads set a baseline; failed reads retain the last successful state."""
    fetcher = fetcher or fetch_document
    now = now or datetime.now(timezone.utc).isoformat()
    old_items = {item["id"]: item for item in (previous or {}).get("items", [])}
    if not sources or len({item["id"] for item in sources}) != len(sources):
        raise ValueError("Guide sources must be nonempty and have unique IDs")
    with ThreadPoolExecutor(max_workers=4) as pool:
        documents = list(pool.map(fetcher, [item["url"] for item in sources]))
    items = []
    for source, doc in zip(sources, documents):
        old = old_items.get(source["id"], {})
        # A replacement URL gets its own baseline, even if the configuration ID stays.
        if old.get("url") != source["url"]:
            old = {}
        item = {**old, **source, "checked_at": now}
        title, text = doc.get("title", ""), doc.get("text", "")
        valid = (len(text) >= 250 and "forever" in title.lower()
                 and re.search(r"\b" + re.escape(source["class"]) + r"\b", title, re.I))
        if doc.get("error") or not valid:
            item.update(status="error", error=doc.get("error") or "Guide-Inhalt nicht bestätigt")
        else:
            # Include embedded talent allocations: a changed build can leave the prose identical.
            material = compute_source_hash(title, text) + json.dumps(doc.get("talent_builds", []), sort_keys=True)
            fingerprint = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
            changed = bool(old.get("source_content_hash") and old["source_content_hash"] != fingerprint)
            item.update(status="ok", error="", last_success_at=now,
                        source_content_hash=fingerprint, source_updated_at=doc.get("date") or None,
                        content_version=old.get("content_version", 1) + int(changed),
                        changed_at=now if changed else old.get("changed_at"))
            # Do not present the author's unfinished beta build as a complete level-60 build.
            item["notice"] = ("Stufe-60-Build im Guide noch nicht vollständig; zusätzliche Legacy-Punkte beachten."
                              if re.search(r"Level\s*60.{0,100}(?:will be updated|in due course)", text, re.I)
                              else "")
        items.append(item)
    return {"checked_at": now, "items": items}


def run():
    sources = load_json(str(SOURCES_FILE), {}).get("items", [])
    previous = load_json(str(OUTPUT_FILE), {"items": []})
    result = check_guides(sources, previous)
    save_json(str(OUTPUT_FILE), result)
    ok = sum(item["status"] == "ok" for item in result["items"])
    print(f"Leveling guides: {ok}/{len(sources)} checked successfully; previous good data retained on failure.")
    for item in result["items"]:
        print(f"  {item['player']} · {item['source']}: {item['status']}" + (f" ({item['error']})" if item['error'] else ""))


if __name__ == "__main__":
    run()
