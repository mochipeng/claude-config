import asyncio
import anthropic
from .website import run as run_website
from .reviews import run as run_reviews
from .linkedin import run as run_linkedin
from .jobs import run as run_jobs


async def run_research(practice_name: str, location: str) -> dict:
    """Runs 4 research agents in parallel. Returns dict: website, reviews, linkedin, jobs."""
    client = anthropic.AsyncAnthropic()
    website, reviews, linkedin, jobs = await asyncio.gather(
        run_website(client, practice_name, location),
        run_reviews(client, practice_name, location),
        run_linkedin(client, practice_name, location),
        run_jobs(client, practice_name, location),
    )
    return {
        "website": website,
        "reviews": reviews,
        "linkedin": linkedin,
        "jobs": jobs,
    }
