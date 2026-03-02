import re
from datetime import date
from pathlib import Path

BRIEFINGS_DIR = Path(__file__).parent.parent / "output" / "briefings"
BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def briefing_path(practice_name: str, location: str) -> Path:
    today = date.today().strftime("%Y%m%d")
    name = _slug(f"{practice_name}_{location}_{today}")
    return BRIEFINGS_DIR / f"{name}.md"


def load_briefing(practice_name: str) -> tuple[str, Path] | tuple[None, None]:
    """Find the most recent briefing for a practice by name slug."""
    slug = _slug(practice_name)
    matches = sorted(BRIEFINGS_DIR.glob(f"{slug}*.md"), reverse=True)
    if matches:
        return matches[0].read_text(), matches[0]
    return None, None


def save_briefing(path: Path, practice_name: str, location: str, content: str):
    header = f"# {practice_name} — {location}\n_Generated {date.today()}_\n\n"
    path.write_text(header + content)


def save_followup(briefing_path: Path, content: str, practice_name: str):
    followup_path = briefing_path.with_name(briefing_path.stem + "_followup.md")
    followup_path.write_text(f"# Follow-up: {practice_name}\n\n" + content)
    return followup_path
