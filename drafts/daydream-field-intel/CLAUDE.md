# DayDream Field Intel — Project Instructions

## What this is
A CLI tool for DayDream Dental field marketing reps. Given a dental practice name and location, it:
1. Runs 4 parallel research agents (website, reviews, LinkedIn, jobs)
2. Synthesizes findings into a structured briefing card
3. Fact-checks and flags uncertain claims
4. Saves the briefing as markdown to `output/briefings/`
5. Post-visit: transcribes a voice memo and generates a follow-up email + CRM notes

## Architecture
- `agents/research/` — 4 Haiku agents run in parallel (cheap, fast)
- `agents/synthesis.py` — Sonnet synthesizes research into 6-section briefing
- `agents/factcheck.py` — Sonnet reviews and flags low-confidence claims
- `agents/followup.py` — Sonnet drafts follow-up email + CRM bullets
- `transcription/whisper.py` — OpenAI Whisper for voice memo transcription
- `utils/display.py` — Rich terminal UI
- `utils/storage.py` — Save/load briefings from `output/briefings/`
- `tools/` — Web search (DuckDuckGo) and web fetch (httpx + BS4)

## Running
```bash
python main.py research "Practice Name" "City, State"
python main.py followup "Practice Name" --voice path/to/memo.m4a
python main.py followup "Practice Name" --notes "typed notes here"
```

## Environment
Requires `.env` with:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY` (for Whisper)
