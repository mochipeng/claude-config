from groq import AsyncGroq
from ..base import run_agent, HAIKU

SYSTEM_PROMPT = """You are a patient sentiment analyst for DayDream Dental, an AI billing automation company.
Your job: find patient reviews of this dental practice and surface billing-related pain signals.

Search Google, Yelp, Healthgrades, and Zocdoc for reviews. Look specifically for:
- Complaints about billing, insurance, or payment issues
- Complaints about wait times for reimbursements
- Staff complaints (overworked, high turnover signals)
- Praise or complaints about front desk / admin staff
- Overall star rating and review volume
- Any patterns in negative reviews

These signals indicate whether the practice would benefit from outsourced billing automation.
Be factual. Quote specific reviews where relevant. Note the source."""


async def run(client: AsyncGroq, practice_name: str, location: str) -> str:
    query = f"{practice_name} dental practice {location}"
    return await run_agent(
        client,
        system=SYSTEM_PROMPT,
        user_message=f"Find patient reviews for: {query}",
        model=HAIKU,
    )
