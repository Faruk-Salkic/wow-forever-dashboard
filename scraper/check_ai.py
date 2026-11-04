"""Small live Gemini check. Credentials stay in headers and never enter diagnostics."""
import json
import os
import re
import sys

import requests


def redact(value, key=""):
    value = str(value or "")
    if key:
        value = value.replace(key, "[REDACTED]")
    return re.sub(r"AIza[\w-]+", "[REDACTED]", value)[:400]


def run():
    key = os.environ.get("GEMINI_API_KEY", "").strip().strip("\"'")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    if not key:
        print(json.dumps({"ok": False, "reason": "MISSING_API_KEY"}))
        return 1
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": "Antworte auf Deutsch als JSON mit title_de, summary_de, action_de. Quelle: Der Quest Underground Assault ist ab Stufe 15 bei Shoni in Stormwind erhältlich. Verwende nur diese Angabe."}]}],
                  "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 1200, "temperature": 0.1}},
            timeout=25,
        )
        data = response.json()
        if not response.ok:
            error = data.get("error", {})
            print(json.dumps({"ok": False, "model": model, "code": response.status_code,
                              "status": error.get("status"), "message": redact(error.get("message"), key),
                              "reasons": [redact(d.get("reason"), key) for d in error.get("details", []) if d.get("reason")]}, ensure_ascii=False))
            return 1
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        brief = json.loads("".join(part.get("text", "") for part in parts if not part.get("thought")))
        valid = all(isinstance(brief.get(field), str) and brief[field].strip() for field in ("title_de", "summary_de", "action_de"))
        print(json.dumps({"ok": valid, "model": model, "sample": brief, "usage": data.get("usageMetadata", {})}, ensure_ascii=False))
        return 0 if valid else 1
    except Exception as error:
        print(json.dumps({"ok": False, "reason": type(error).__name__, "message": redact(error, key)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(run())
