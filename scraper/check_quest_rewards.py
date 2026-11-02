"""Track factual quest/reward changes in Wowhead's Forever list, without copying guides."""
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone
import requests

if __package__:
    from .scrape import load_json, save_json
else:
    from scrape import load_json, save_json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://www.wowhead.com/forever/quests"
OUTPUT = ROOT / "data/quest_rewards.json"
STATE = ROOT / "data/quest_reward_state.json"
STATS = ("dps", "agi", "str", "int", "sta", "spi", "reqlevel", "slotbak")


def parse_catalog(html):
    match = re.search(r"new\s+Listview\(\{template:\s*['\"]quest['\"].*?\bdata\s*:", html, re.S)
    if not match:
        raise ValueError("Quest-Liste nicht lesbar")
    quests, _ = json.JSONDecoder().raw_decode(html[match.end():].lstrip())
    if not isinstance(quests, list) or not quests or not any(isinstance(q, dict) and q.get("id") and q.get("name") and "envChange" in q for q in quests):
        raise ValueError("Leere Quest-Liste")
    item_data = {}
    for found in re.finditer(r"WH\.Gatherer\.addData\(\s*3\s*,\s*\d+\s*,\s*", html):
        value, _ = json.JSONDecoder().raw_decode(html[found.end():].lstrip())
        item_data.update(value)
    if not item_data:
        raise ValueError("Belohnungsdaten fehlen")
    return quests, item_data


def reward_items(quest, item_data):
    result = []
    for field, choice in [("itemchoices", True), ("itemrewards", False)]:
        for entry in quest.get(field, []):
            item_id, count = entry[:2]
            source = item_data.get(str(item_id), {})
            if not source.get("name_enus"):
                continue  # Unknown item names must never be guessed.
            equip = source.get("jsonequip", {})
            result.append({"id": item_id, "name": source["name_enus"], "count": count,
                           "choice": choice, "quality": source.get("quality", 0),
                           "stats": {key: equip[key] for key in STATS if key in equip},
                           "url": f"https://www.wowhead.com/forever/item={item_id}"})
    return result


def is_candidate(quest, rewards):
    change = quest.get("envChange", {})
    # New in Forever and changes to the rewards of an existing quest are both useful.
    useful_change = change.get("status") == "new" or "rewards_changed" in change.get("labels", [])
    return (useful_change and quest.get("side") in {1, 3}
            and quest.get("reqclass", 0) in {0, 4, 64, 68}
            and 1 <= quest.get("level", 0) <= 60
            and any(item["quality"] >= 2 or item["stats"].get("slotbak") == 18 for item in rewards))


def build_snapshot(quests, item_data, previous_state=None, now=None):
    now = now or datetime.now(timezone.utc).isoformat()
    previous_state = previous_state or {}
    known = dict(previous_state.get("known", {}))
    initialized = bool(previous_state.get("initialized_at"))
    found = []
    seen = set()
    counts = {"discovered": 0, "updated": 0}
    for quest in quests:
        if not isinstance(quest.get("id"), int) or not quest.get("name"):
            continue
        if quest["id"] in seen:
            continue
        seen.add(quest["id"])
        rewards = reward_items(quest, item_data)
        key = str(quest["id"])
        facts = {field: quest.get(field) for field in ("id", "name", "level", "reqlevel", "side", "reqclass", "type", "category", "itemchoices", "itemrewards")}
        fingerprint = hashlib.sha256(json.dumps([facts, rewards], sort_keys=True).encode()).hexdigest()[:16]
        old = known.get(key, {})
        changed = bool(old and old.get("hash") != fingerprint)
        discovered = initialized and not old
        state = {"hash": fingerprint, "first_seen_at": old.get("first_seen_at", now),
                 "changed_at": now if changed or discovered else old.get("changed_at"),
                 "change_kind": ("updated" if changed else "discovered") if changed or discovered else old.get("change_kind", "baseline")}
        known[key] = state
        if not is_candidate(quest, rewards):
            continue
        if changed: counts["updated"] += 1
        if discovered: counts["discovered"] += 1
        mask = quest.get("reqclass", 0)
        classes = (["Hunter"] if mask == 4 else ["Shaman"] if mask == 64 else ["Hunter", "Shaman"] if mask == 68 else [])
        found.append({"id": quest["id"], "name": quest["name"], "level": quest["level"],
                      "min_level": quest.get("reqlevel", 1), "classes": classes,
                      "dungeon": quest.get("type") == 81, "rewards": rewards,
                      "source_change": quest.get("envChange", {}).get("status"),
                      "url": f"https://www.wowhead.com/forever/quest={quest['id']}",
                      "changed_at": state["changed_at"], "change_kind": state["change_kind"]})
    # Keep a small, balanced selection across the journey. A partial list cannot prove removals.
    selected = []
    popularity = {q["id"]: q.get("popularity", 0) for q in quests if isinstance(q, dict) and "id" in q}
    for band in range(0, 60, 10):
        candidates = [q for q in found if band < q["level"] <= band + 10]
        # Prefer concrete gear/weapon rewards within each level band, without calling them BiS.
        candidates.sort(key=lambda q: (not bool(q["changed_at"]), not bool(q["classes"]),
                                       -max(i["quality"] for i in q["rewards"]),
                                       -int(any(i["stats"].get("dps", 0) for i in q["rewards"])),
                                       -popularity[q["id"]], q["min_level"], q["id"]))
        selected.extend(candidates[:8])
    payload = {"source": "Wowhead Forever", "source_url": SOURCE, "status": "ok", "error": "",
               "checked_at": now, "last_success_at": now, "checked_count": len(quests),
               "coverage": "Auswahl aus der geladenen Wowhead-Liste, keine vollständige Quest-Erfassung.",
               "discovered_count": counts["discovered"], "updated_count": counts["updated"], "items": selected}
    state = {"initialized_at": previous_state.get("initialized_at", now), "known": known}
    return payload, state


def refresh(previous, previous_state, fetcher=None, now=None):
    now = now or datetime.now(timezone.utc).isoformat()
    try:
        if fetcher:
            html = fetcher()
        else:
            # Use the HTTP library's own identity rather than an outdated, impersonated browser.
            response = requests.get(SOURCE, timeout=20)
            response.raise_for_status()
            html = response.text
        quests, items = parse_catalog(html)
        return build_snapshot(quests, items, previous_state, now)
    except Exception as error:
        return {**previous, "source": "Wowhead Forever", "source_url": SOURCE, "status": "error",
                "error": str(error)[:160], "checked_at": now, "discovered_count": 0, "updated_count": 0,
                "items": previous.get("items", [])}, previous_state


def run():
    previous = load_json(str(OUTPUT), {"items": []})
    state = load_json(str(STATE), {})
    result, updated_state = refresh(previous, state)
    # State first: an interrupted write must not rediscover every baseline quest tomorrow.
    save_json(str(STATE), updated_state)
    save_json(str(OUTPUT), result)
    print(f"Quest rewards: {result['status']}; {result.get('checked_count', 0)} rows; {len(result['items'])} selected; "
          f"{result.get('discovered_count', 0)} newly discovered, {result.get('updated_count', 0)} changed.")
    if result.get("error"):
        print(result["error"])


if __name__ == "__main__":
    run()
