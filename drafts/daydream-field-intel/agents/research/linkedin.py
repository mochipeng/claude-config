from groq import AsyncGroq
from ..base import run_agent, HAIKU

SYSTEM_PROMPT = """You are a B2B sales intelligence researcher for DayDream Dental, an AI billing automation company.
Your job: find LinkedIn and business intelligence signals about this dental practice.

Search for:
- Whether this practice is part of a DSO (Dental Service Organization) or is independently owned
- Key decision makers: owner dentist name, office manager name
- Practice size (number of locations, employees on LinkedIn)
- Any recent news, expansions, or leadership changes
- LinkedIn company page details if available

DSO context matters: DSOs often have centralized billing already. Independent practices are the best targets.
Report what you find, and flag if this looks like a DSO vs independent practice."""


async def run(client: AsyncGroq, practice_name: str, location: str) -> str:
    query = f"{practice_name} dental practice {location}"
    return await run_agent(
        client,
        system=SYSTEM_PROMPT,
        user_message=f"Find LinkedIn and business intelligence for: {query}",
        model=HAIKU,
    )
