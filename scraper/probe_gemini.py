"""One small structured-output request using the same configuration as real briefs."""
import json
from scrape import AI_STATE, GEMINI_MODEL, generate_german_brief

if __name__ == "__main__":
    result = generate_german_brief(
        "API-Verbindungstest",
        "Dies ist ausschließlich ein Verbindungstest für deutsche JSON-Kurzberichte. "
        "Es gibt keine Spielnachricht, keine Questbelohnung und keine neue Spielempfehlung.",
        "Dashboard-Diagnose")
    print("Gemini preflight: " + json.dumps({**AI_STATE, "model": GEMINI_MODEL, "valid_json": bool(result)}))
    if not result:
        print("::warning::Gemini preflight failed; check the sanitized diagnostic above. Source checks continue.")
