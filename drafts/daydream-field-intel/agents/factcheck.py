from .base import get_client, run_agent, SONNET

FACTCHECK_PROMPT = """You are a fact-checking agent reviewing a field sales briefing for DayDream Dental.

Your job: review the synthesized briefing and validate the confidence of each claim.

For each section, check:
1. Is this claim directly sourced from the research, or is it inferred/extrapolated?
2. Does it contradict anything in the raw research?
3. Is the confidence rating accurate?

Return the SAME briefing but with:
- ✓ added before well-supported claims
- ⚠ added before uncertain/inferred claims, with a note on what to verify in person
- Any section that has mostly ⚠ flags gets a section-level warning: [LOW CONFIDENCE — verify before visit]

Also append a brief ## FACT-CHECK SUMMARY at the end:
- Overall reliability: HIGH / MEDIUM / LOW
- Top 3 things to verify in person before the meeting
- Any red flags or inconsistencies found

Be ruthlessly honest. A rep walking in with bad intel is worse than no intel."""


async def run_factcheck(briefing: str, research: dict) -> str:
    client = get_client()

    research_block = f"""
RAW RESEARCH (ground truth):

WEBSITE: {research['website']}

REVIEWS: {research['reviews']}

LINKEDIN: {research['linkedin']}

JOBS: {research['jobs']}
"""

    return await run_agent(
        client,
        system=FACTCHECK_PROMPT,
        user_message=f"BRIEFING TO FACT-CHECK:\n{briefing}\n\n{research_block}",
        model=SONNET,
    )
