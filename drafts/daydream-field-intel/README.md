# DayDream Dental — Field Visit Intelligence Tool

A CLI tool for field marketing reps. Enter a dental practice name and location — get a structured briefing card before you walk in the door, and a personalized follow-up draft after.

## How it works

```
INPUT: practice name + location
         │
         ▼
┌─────────────────────────────────────────────┐
│         PARALLEL RESEARCH AGENTS (Haiku)    │
│  [Website] [Reviews] [LinkedIn] [Jobs]      │
└──────────────────┬──────────────────────────┘
                   ▼
         [SYNTHESIS AGENT] (Sonnet)
         structures into 6 sections
                   ▼
        [FACT-CHECK AGENT] (Sonnet)
        flags low-confidence claims
                   ▼
        briefing saved to output/briefings/
                   │
         (after the visit)
                   ▼
        voice memo → Whisper → transcript
                   ▼
     [FOLLOW-UP AGENT] → email + CRM bullets
```

## Briefing sections

1. **Practice Profile** — size, specialties, location, independent vs DSO
2. **Technology Signals** — PM software, billing approach, confidence levels
3. **Financial Pain Signals** — review complaints, open billing roles, turnover
4. **DayDream Fit** — 3 tailored talking points + objection rebuttals
5. **Decision Makers** — who to ask for
6. **Confidence Flags** — ⚠ claims to verify in person

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add ANTHROPIC_API_KEY and OPENAI_API_KEY
```

## Usage

```bash
# Pre-visit research
python main.py research "Smile Dental Group" "Austin, TX"

# Post-visit follow-up with voice memo
python main.py followup "Smile Dental Group" --voice ~/Desktop/notes.m4a

# Post-visit follow-up with typed notes
python main.py followup "Smile Dental Group" --notes "Met office manager Sarah, billing coordinator just quit..."
```

Briefings are saved to `output/briefings/` as markdown files for easy reference.
