"""Choose a scheduled event by its cron expression, never by runner start hour."""
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

CONFIG = Path(__file__).resolve().parents[1] / "data/update_policy.json"


def policy_at(now=None, config=None):
    config = config or json.loads(CONFIG.read_text())
    now = now or datetime.now(timezone.utc)
    cutoff = datetime.fromisoformat(config["frequent_until"])
    launch = now < cutoff
    last_day = (cutoff.astimezone(ZoneInfo(config["timezone"]))-timedelta(days=1)).strftime('%d.%m.')
    return {"mode": "launch" if launch else "daily", "interval_hours": 2 if launch else 24,
            "timezone": config["timezone"], "frequent_until": config["frequent_until"],
            "schedule": config["frequent_cron"] if launch else config["daily_cron"],
            "description_de": f"Alle 2 Stunden bis einschließlich {last_day}; danach täglich um 11:50 (Wien)." if launch
                              else "Tägliche Quellenprüfung um 11:50 (Wien)."}


def should_run(event, schedule="", now=None, config=None):
    if event != "schedule":
        return True
    return schedule == policy_at(now, config)["schedule"]


if __name__ == "__main__":
    policy = policy_at()
    run = should_run(os.environ.get("GITHUB_EVENT_NAME", "workflow_dispatch"), os.environ.get("TRIGGER_CRON", ""))
    print(json.dumps({**policy, "run_update": run}, ensure_ascii=False))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"run_update={str(run).lower()}\nmode={policy['mode']}\n")
