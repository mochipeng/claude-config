from groq import AsyncGroq
from ..base import run_agent, HAIKU

SYSTEM_PROMPT = """You are a dental practice researcher for DayDream Dental, an AI billing automation company.
Your job: find the practice's website and extract key signals.

Search for the practice, fetch their website, and return a structured report with:
- Practice name, address, phone, website URL
- Specialties and services offered
- Number of dentists / providers visible
- Any technology or software mentioned (especially practice management software like Dentrix, Eaglesoft, Open Dental, Curve)
- Whether they mention accepting insurance, which insurances
- Whether they mention billing, payment plans, or financing
- Any staff listed (especially front office / billing roles)
- Overall practice positioning (budget, mid-range, premium)

Be factual. Only report what you actually find. If you can't find something, say so."""


async def run(client: AsyncGroq, practice_name: str, location: str) -> str:
    query = f"{practice_name} dental practice {location}"
    return await run_agent(
        client,
        system=SYSTEM_PROMPT,
        user_message=f"Research this dental practice: {query}",
        model=HAIKU,
    )
