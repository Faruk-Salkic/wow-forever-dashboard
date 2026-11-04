"""Extract quest facts from the linked Forever guide, preserving player quest IDs."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

if __package__:
    from .scrape import load_json, save_json
else:
    from scrape import load_json, save_json

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ROOT / "data/guides.json"
OVERRIDES = ROOT / "data/dungeon_overrides.json"
SOURCE = "https://www.wowhead.com/forever/guide/dungeons/every-dungeon-quest-location"
LEGACY_IDS = {
    "The Defias Brotherhood": "dm_defias_chain", "Underground Assault": "dm_underground_assault",
    "Oh Brother...": "dm_oh_brother", "The Unsent Letter": "dm_unsent_letter",
    "Crime and Punishment": "stk_crime_punishment", "What Comes Around...": "stk_what_comes_around",
    "The Color of Blood": "stk_color_of_blood", "Quell the Uprising": "stk_riot",
    "The Grand Betrayal": "gnome_thermaplugg", "Data Rescue": "gnome_cards",
    "In the Name of the Light": "sm_in_the_name_of_light", "Mythology of the Titans": "sm_mythology_titans",
    "Gahz'rilla": "zf_gahzrilla", "Scarab Shells": "zf_scarab_shells",
    "Tiara of the Deep": "zf_tiara_of_deep", "Nekrum's Medallion": "zf_nekrum_amulet",
    "Into The Temple of Atal'Hakkar": "st_into_temple", "Jammal'an the Prophet": "st_jammalan",
    "Dark Iron Legacy": "brd_shadowforge_key", "Jail Break!": "brd_jailbreak_onyxia"
}
DUNGEON_IDS = {"The Deadmines":"dm", "The Stockades":"stockades", "Gnomeregan":"gnomer",
               "Scarlet Monastery":"sm", "Zul'Farrak":"zf", "Temple of Atal'Hakkar - Sunken Temple":"st",
               "Blackrock Depths BRD":"brd"}
HORDE_TOWNS = re.compile(r"Orgrimmar|Undercity|Thunder Bluff|Shadowprey|Stonard|Sepulcher|Kargath|The Bulwark|Brill,", re.I)


def metadata(html):
    values = {}
    for m in re.finditer(r"WH\.Gatherer\.addData\(\s*5\s*,\s*\d+\s*,\s*", html):
        values.update(json.JSONDecoder().raw_decode(html[m.end():].lstrip())[0])
    return values


def quest_id(link):
    match = re.search(r"/forever/quest=(\d+)", urllib.parse.unquote(link or ""))
    return int(match[1]) if match else None


def parse_guide(html, now=None, overrides=None):
    now = now or datetime.now(timezone.utc).isoformat()
    soup = BeautifulSoup(html, "html.parser")
    quest_data = metadata(html)
    if not quest_data: raise ValueError("Quest-Metadaten fehlen")
    by_name = {}
    for qid, info in quest_data.items(): by_name.setdefault(info.get("name_enus", ""), []).append((int(qid), info))
    dungeons, current, seen = [], None, set()
    skipped = 0
    # Some source tables have orphaned <tr> nodes; walk rows in document order.
    for element in soup.find_all(["h2", "tr"]):
        if element.name == "h2":
            title = element.get_text(" ", strip=True)
            if "Dungeon Quests" not in title and not title.startswith("Every Quest in City of Dalaran"):
                current = None; continue
            name = re.sub(r" Dungeon Quests.*$|^Every Quest in | in World of Warcraft: Forever$", "", title)
            slug = DUNGEON_IDS.get(name) or re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
            intro = []
            for next_element in element.next_elements:
                if getattr(next_element, "name", None) in {"h2", "table"}: break
                if isinstance(next_element, str): intro.append(str(next_element))
            intro = " ".join(intro)
            level = re.search(r"At Level\s*:\s*Level\s*(\d+)", intro, re.I)
            current = {"id":slug, "name":name, "recommended_level":int(level[1]) if level else None,
                       "source_url":SOURCE, "quests":[]}
            dungeons.append(current)
            continue
        if current is None: continue
        for row in [element]:
            cells = row.find_all("td", recursive=False)
            if len(cells) != 6: continue
            title = cells[0].get_text(" ", strip=True)
            if title == "Quest": continue
            link = cells[0].find("a", href=True)
            qid = quest_id(link.get("href")) if link else None
            if not qid:
                candidates = by_name.get(title, [])
                if len(candidates) == 1: qid = candidates[0][0]
            if not qid or str(qid) not in quest_data:
                skipped += 1; continue
            info = quest_data[str(qid)]
            if info.get("_side") not in {1, 3} or info.get("reqclass", 0) not in {0, 4, 64, 68}: continue
            level = re.search(r"\d+", cells[1].get_text())
            if not level: skipped += 1; continue
            min_level = int(level[0])
            if not 1 <= min_level <= 60: skipped += 1; continue
            parts = re.split(r"<br\s*/?>", str(cells[5]), maxsplit=1, flags=re.I)
            pickup_soup = BeautifulSoup(parts[0], "html.parser")
            pickup = pickup_soup.get_text(" ", strip=True)
            if HORDE_TOWNS.search(pickup): continue
            notes = BeautifulSoup(parts[1] if len(parts)>1 else "", "html.parser")
            prerequisites = []
            for anchor in cells[5].select('a[href*="/quest="]'):
                text = anchor.get_text(" ", strip=True)
                if text and text not in prerequisites: prerequisites.append(text)
            for bold in cells[5].select("b"):
                text = bold.get_text(" ", strip=True)
                if text in by_name and text not in prerequisites: prerequisites.append(text)
            flags = cells[4].get_text(" ", strip=True)
            followups = prerequisites if "Pre" not in flags else []
            if "Pre" not in flags or "Same prerequisites" in notes.get_text(): prerequisites = []
            count = re.search(r"Complete\s+(\d+)\s+quests", notes.get_text(" ", strip=True), re.I)
            npc_names = [a.get_text(" ", strip=True) for a in pickup_soup.select('a[href*="/npc="]')]
            coord = re.search(r"/way\s+(\d+(?:\.\d+)?)[, ]+(\d+(?:\.\d+)?)", pickup)
            key = (current["id"], qid)
            if key in seen: continue
            seen.add(key)
            stable_id = LEGACY_IDS.get(title, f"quest_{qid}")
            progress_id = stable_id
            if any(q["id"] == stable_id for d in dungeons for q in d["quests"]): stable_id += "_"+current["id"]
            inside = bool(re.search(r"Drop|Esc|Interactable", flags, re.I) or pickup.lower().startswith(("inside",current["name"].lower())))
            mask = info.get("reqclass",0)
            quest = {"id":stable_id,"progress_id":progress_id,"game_id":qid,"title":title,"min_lvl":min_level,
                     "giver":", ".join(npc_names) or ("Abholort in der Quelle prüfen" if pickup in {"TBD", ""} else re.split(r"/way|\. Complete|\. Requires",pickup.split(" - ")[-1])[0].strip()),
                     "pickup":pickup if pickup != "TBD" else "Abholort noch offen",
                     "location_confirmed":pickup not in {"TBD", ""},
                     "coordinates": [float(coord[1]),float(coord[2])] if coord else None,
                     "classes": ["Hunter"] if mask==4 else ["Shaman"] if mask==64 else ["Hunter","Shaman"] if mask==68 else [],
                     "faction":"Alliance" if info["_side"]==1 else "Both", "race_limited":bool(info.get("reqrace",0)),
                     "phase":"inside" if inside else "before", "requires_chain":"Pre" in flags,
                     "prerequisites":prerequisites,"followups":followups,"prerequisite_steps":int(count[1]) if count else None,
                     "prepare_from_level":min_level,"chain":"", "reward":"Belohnungen im Quest-Link prüfen.",
                     "url":f"https://www.wowhead.com/forever/quest={qid}", "source_url":SOURCE}
            quest.update((overrides or {}).get("quests", {}).get(str(qid), {}))
            dungeon_override = (overrides or {}).get("dungeons", {}).get(current["id"], {})
            correction = dungeon_override.get("replace_minimum", {}).get(str(quest["min_lvl"]))
            if correction is not None:
                quest["min_lvl"] = correction
                quest["prepare_from_level"] = min(quest["prepare_from_level"], correction)
            if dungeon_override.get("notice"):
                current.update(notice=dungeon_override["notice"],notice_source=dungeon_override.get("source_url"))
            current["quests"].append(quest)
    total = sum(len(d["quests"]) for d in dungeons)
    if len(dungeons)<10 or total<40: raise ValueError("Dungeon-Guide unvollständig; vorherige Daten bleiben erhalten")
    # Canonical facts exclude scrape time and popularity, so repeated checks are quiet.
    keys = ["game_id","title","min_lvl","giver","pickup","coordinates","classes","faction","phase","requires_chain","prerequisites","prepare_from_level","prepare_quest"]
    facts = json.dumps([{ "name":d["name"], "level":d["recommended_level"], "quests":[{k:q.get(k) for k in keys} for q in d["quests"]]} for d in dungeons], sort_keys=True, ensure_ascii=False)
    return {"title":"Dungeon-Quests · unterwegs vorbereiten", "dungeons":dungeons,
            "checked_at":now,"last_success_at":now,"source_url":SOURCE,"status":"ok","error":"",
            "source_hash":hashlib.sha256(facts.encode()).hexdigest()[:16],"skipped_rows":skipped,
            "coverage_note":"Forever-Guide mit Beta-/Classic-Referenzen. Offene Angaben bleiben markiert; Voraussetzungen im Spiel bestätigen."}


def detail_level(html, qid):
    match = re.search(r"\$\.extend\(g_quests\["+str(qid)+r"\],\s*",html)
    if not match: raise ValueError("Quest-Detaildaten fehlen")
    data = json.JSONDecoder().raw_decode(html[match.end():].lstrip())[0]
    if data.get("id") != qid or not isinstance(data.get("reqlevel"),int) or not 1<=data["reqlevel"]<=60:
        raise ValueError("Mindestlevel im Questdatensatz unbestätigt")
    return data["reqlevel"]


def refresh(previous, html=None, now=None):
    now = now or datetime.now(timezone.utc).isoformat()
    try:
        check_details = html is None
        if html is None:
            response = requests.get(SOURCE, timeout=20)
            response.raise_for_status(); html = response.text
        overrides = load_json(str(OVERRIDES), {})
        overrides = copy.deepcopy(overrides)
        old_quests = {str(q.get("game_id")):q for d in previous.get("dungeons",[]) for q in d.get("quests",[])}
        details = [(qid,item) for qid,item in overrides.get("quests",{}).items() if item.get("evidence_url")]
        def check_detail(pair):
            qid,item = pair
            old = old_quests.get(qid,{})
            if old.get("evidence_checked_at"):
                item["min_lvl"] = old["min_lvl"]
                item["evidence_checked_at"] = old["evidence_checked_at"]
            if check_details:
                try:
                    result = requests.get(item["evidence_url"],timeout=15);result.raise_for_status()
                    item.update(min_lvl=detail_level(result.text,int(qid)),evidence_checked_at=now,detail_status="ok")
                except Exception:
                    item["detail_status"] = "error"
            return qid,item
        with ThreadPoolExecutor(max_workers=3) as pool:
            for qid,item in pool.map(check_detail,details):overrides["quests"][qid]=item
        current = parse_guide(html, now, overrides)
        if any(q.get("detail_status")=="error" for d in current["dungeons"] for q in d["quests"]):current["detail_warning"]="Einzelne Quest-Detailseiten konnten nicht erneut geprüft werden. Letzte belegte Werte bleiben erhalten."
        current["changed_at"] = (now if previous.get("source_hash") and previous["source_hash"]!=current["source_hash"] else previous.get("changed_at"))
        return current
    except Exception as error:
        return {**previous,"checked_at":now,"status":"error","error":str(error)[:160]}


if __name__ == "__main__":
    guides = load_json(str(GUIDES), {})
    result = refresh(guides.get("dungeon_quests", {}))
    guides["dungeon_quests"] = result
    save_json(str(GUIDES), guides)
    print(f"Dungeon preparation: {result['status']}; {len(result.get('dungeons',[]))} dungeons; "
          f"{sum(len(d['quests']) for d in result.get('dungeons',[]))} quests.")
    if result.get("error"): print("::warning::Dungeon source unavailable; previous verified preparation data retained.")
