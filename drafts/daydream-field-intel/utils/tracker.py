import csv
import re
from datetime import date
from pathlib import Path

TRACKER_PATH = Path(__file__).parent.parent / "output" / "conference_tracker.csv"

COLUMNS = [
    "Practice Name",
    "Location",
    "Date Added",
    "Briefing",
    "PM Software",
    "In-house Billing",
    "Insurance Mix",
    "Billing Pain Evidence",
    "Key Decision Makers",
    "Overall Pain",
    "Confidence Rating",
    "Follow-up Signal",
    "Voice Notes",
    "Last Updated",
]

# Maps CSV column name → key in the data dict returned by extract agents
_COLUMN_MAP = {
    "Briefing":              "briefing",
    "PM Software":           "pm_software",
    "In-house Billing":      "in_house_billing",
    "Insurance Mix":         "insurance_mix",
    "Billing Pain Evidence": "billing_pain_evidence",
    "Key Decision Makers":   "key_decision_makers",
    "Overall Pain":          "overall_pain",
    "Confidence Rating":     "confidence_rating",
    "Follow-up Signal":      "follow_up_signal",
    "Voice Notes":           "voice_notes",
}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def load_tracker() -> list[dict]:
    if not TRACKER_PATH.exists():
        return []
    with open(TRACKER_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_tracker(rows: list[dict]):
    TRACKER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKER_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def add_or_update(rows: list[dict], practice_name: str, location: str, data: dict) -> list[dict]:
    """Add a new row or update existing row matched by practice name slug."""
    slug = _slug(practice_name)
    today = date.today().isoformat()

    for row in rows:
        if _slug(row.get("Practice Name", "")) == slug:
            for col, key in _COLUMN_MAP.items():
                val = data.get(key)
                if val:  # only overwrite with non-empty values
                    row[col] = val
            row["Last Updated"] = today
            return rows

    # New row
    new_row = {col: "" for col in COLUMNS}
    new_row["Practice Name"] = practice_name
    new_row["Location"]      = location
    new_row["Date Added"]    = today
    new_row["Last Updated"]  = today
    for col, key in _COLUMN_MAP.items():
        val = data.get(key)
        if val:
            new_row[col] = val
    rows.append(new_row)
    return rows


def find_row(rows: list[dict], practice_name: str) -> dict | None:
    slug = _slug(practice_name)
    for row in rows:
        if _slug(row.get("Practice Name", "")) == slug:
            return row
    return None


def sort_by_signal(rows: list[dict]) -> list[dict]:
    order = {"HOT": 0, "WARM": 1, "COLD": 2, "": 3}
    return sorted(rows, key=lambda r: order.get(r.get("Follow-up Signal", ""), 3))
