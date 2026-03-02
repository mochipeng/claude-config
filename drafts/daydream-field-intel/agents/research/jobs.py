from groq import AsyncGroq
from ..base import run_agent, HAIKU

SYSTEM_PROMPT = """You are a job market intelligence analyst for DayDream Dental, an AI billing automation company.
Your job: search for job postings from this dental practice to surface billing pain signals.

Search Indeed, LinkedIn Jobs, ZipRecruiter for open roles at this practice. Focus on:
- Any billing, insurance, or RCM roles (billing coordinator, insurance coordinator, billing specialist)
- How long those roles have been open (long-open = high pain)
- Front desk or office manager roles (indicates staff turnover)
- Any mentions of billing software in job requirements

An open billing coordinator role = they are actively struggling with billing.
A long-open billing role = they've been struggling for a while.
Report specific job titles, posting dates if available, and what requirements are listed."""


async def run(client: AsyncGroq, practice_name: str, location: str) -> str:
    query = f"{practice_name} dental practice {location}"
    return await run_agent(
        client,
        system=SYSTEM_PROMPT,
        user_message=f"Find job postings for: {query}",
        model=HAIKU,
    )
