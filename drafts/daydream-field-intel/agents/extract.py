import json
from .base import get_client, call_model, SMART_MODEL

BRIEFING_EXTRACT_PROMPT = """You extract structured data from a dental practice sales briefing.
Return ONLY a valid JSON object — no markdown fences, no explanation, nothing else.

{
  "pm_software":            "string, or Unknown",
  "in_house_billing":       "Yes / No / Unknown",
  "insurance_mix":          "string, or Unknown",
  "billing_pain_evidence":  "1-2 sentence summary, or None found",
  "key_decision_makers":    "comma-separated names and roles, or Unknown",
  "overall_pain":           "HIGH / MEDIUM / LOW / Unknown",
  "confidence_rating":      "HIGH / MEDIUM / LOW",
  "follow_up_signal":       "HOT / WARM / COLD"
}

Rules:
- confidence_rating: HIGH if practice size + PM software + in-house billing are all known;
  MEDIUM if 1-2 are known; LOW if none are known.
- follow_up_signal: HOT = high pain + independent practice + at least one named decision maker;
  WARM = medium pain OR some unknowns but still potential; COLD = low pain or clear DSO affiliation."""

VOICE_EXTRACT_PROMPT = """You extract key signals from a conference voice note or conversation transcript.
Return ONLY a valid JSON object — no markdown fences, no explanation, nothing else.

{
  "pm_software_confirmed":       "string or null",
  "in_house_billing_confirmed":  "Yes / No / null",
  "insurance_confirmed":         "string or null",
  "pain_points":                 "1-2 sentence summary or null",
  "follow_up_signal":            "HOT / WARM / COLD",
  "notes_summary":               "2-3 sentence summary of the conversation"
}

Only populate confirmed fields if explicitly mentioned. Do not infer.
follow_up_signal: HOT = clear interest or pain expressed; WARM = open but noncommittal; COLD = not interested."""


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


async def extract_briefing(briefing_text: str) -> dict:
    client = get_client()
    raw = await call_model(
        client,
        system=BRIEFING_EXTRACT_PROMPT,
        user=f"Extract from this briefing:\n\n{briefing_text}",
        model=SMART_MODEL,
    )
    return _parse_json(raw)


async def extract_from_voice(transcript: str) -> dict:
    client = get_client()
    raw = await call_model(
        client,
        system=VOICE_EXTRACT_PROMPT,
        user=f"Extract from this transcript:\n\n{transcript}",
        model=SMART_MODEL,
    )
    return _parse_json(raw)
