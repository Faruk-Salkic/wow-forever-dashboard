"""Merge dated dashboard notes as editorial updates, not fabricated game announcements."""
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from . import scrape as S
else:
    import scrape as S

ROOT = Path(__file__).resolve().parents[1]


def publish():
    now = datetime.now(timezone.utc).isoformat()
    records = S.load_json(str(ROOT/"data/editorial_updates.json"), {"items":[]})["items"]
    incoming = []
    for item in records:
        url = S.normalize_url(item["url"])
        incoming.append({**item,"id":S.make_canonical_id(url),"normalized_url":url,
                         "raw_title":"WoW Forever: "+item["title"],"raw_content":item["article_de"],
                         "source":"Dashboard · Questvorbereitung","source_icon":"🏰","radar_status":"Redaktionell",
                         "verified_type":"Redaktioneller Hinweis mit verlinkten Quellen","date_basis":"editorial",
                         "fetched_at":now,"specific_change":True,"summary_mode":"curated","content_extractor":2,
                         "source_content_hash":S.compute_source_hash(item["title"],item["article_de"]),
                         "has_source_baseline":True})
    data = S.load_json(str(ROOT/"data/news.json"), {"items":[]})
    # Publishing our note must not re-filter or rewrite unrelated source articles.
    note_urls = {item["normalized_url"] for item in incoming}
    notes = [item for item in data["items"] if S.normalize_url(item["url"]) in note_urls]
    untouched = [item for item in data["items"] if S.normalize_url(item["url"]) not in note_urls]
    merged,new,updated,_ = S.merge_and_deduplicate_items(notes,incoming,{},now)
    current = {item["normalized_url"]:item for item in incoming}
    for item in merged:
        for field in ["references","internal_action"]:
            if field in current[item["normalized_url"]]:item[field]=current[item["normalized_url"]][field]
    items = sorted(untouched+merged,key=lambda item:item.get("updated_at") if item.get("is_updated") else item.get("date",""),reverse=True)
    data.update(items=items,total_count=len(items),new_count=data.get("new_count",0)+new,updated_count=data.get("updated_count",0)+updated)
    if new or updated:data["daily_summary"] = data.get("daily_summary","")+" Zusätzlich wurde der Hinweis zur Dungeon-Vorbereitung aktualisiert."
    S.save_json(str(ROOT/"data/news.json"),data);S.save_json(str(ROOT/"data/feed.json"),S.make_client_payload(data))
    print(f"Editorial notes: {new} new, {updated} updated; stable IDs retained.")


if __name__ == "__main__": publish()
