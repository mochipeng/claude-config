#!/usr/bin/env python3
"""
DayDream Dental — Field Visit Intelligence Tool

Commands:
  research  <practice_name> <location>   Generate a pre-visit briefing
  followup  <practice_name> [--voice]    Generate post-visit email + CRM notes
"""
import asyncio

from agents.base import get_client
import click
from dotenv import load_dotenv

from utils import display
from utils.storage import briefing_path, load_briefing, save_briefing, save_followup
from agents.research.website import run as run_website
from agents.research.reviews import run as run_reviews
from agents.research.linkedin import run as run_linkedin
from agents.research.jobs import run as run_jobs
from agents.synthesis import run_synthesis
from agents.factcheck import run_factcheck
from agents.followup import run_followup
from transcription import transcribe

load_dotenv()


# ── research command ───────────────────────────────────────────────────────────

@click.group()
def cli():
    pass


@cli.command()
@click.argument("practice_name")
@click.argument("location")
def research(practice_name: str, location: str):
    """Generate a pre-visit briefing for a dental practice."""
    display.print_header(practice_name, location)

    async def _run():
        client = get_client()

        async def tracked(coro, progress, task_id, done_label: str):
            result = await coro
            progress.update(task_id, description=done_label)
            return result

        with display.research_progress() as progress:
            t1 = progress.add_task("[cyan]Website research...", total=None)
            t2 = progress.add_task("[blue]Reviews research...", total=None)
            t3 = progress.add_task("[yellow]LinkedIn / DSO signals...", total=None)
            t4 = progress.add_task("[red]Job postings...", total=None)

            website, reviews, linkedin, jobs = await asyncio.gather(
                tracked(run_website(client, practice_name, location), progress, t1, "[green]✓ Website research"),
                tracked(run_reviews(client, practice_name, location), progress, t2, "[green]✓ Reviews research"),
                tracked(run_linkedin(client, practice_name, location), progress, t3, "[green]✓ LinkedIn / DSO signals"),
                tracked(run_jobs(client, practice_name, location), progress, t4, "[green]✓ Job postings"),
            )
            raw = {"website": website, "reviews": reviews, "linkedin": linkedin, "jobs": jobs}

            ts = progress.add_task("[cyan]Synthesizing briefing...", total=None)
            briefing = await run_synthesis(practice_name, location, raw)
            progress.update(ts, description="[green]✓ Briefing synthesized")

            tf = progress.add_task("[magenta]Fact-checking...", total=None)
            final = await run_factcheck(briefing, raw)
            progress.update(tf, description="[green]✓ Fact-check complete")

        display.print_briefing(final)

        path = briefing_path(practice_name, location)
        save_briefing(path, practice_name, location, final)
        display.print_saved(str(path))

    asyncio.run(_run())


# ── followup command ───────────────────────────────────────────────────────────

@cli.command()
@click.argument("practice_name")
@click.option("--voice", "-v", type=click.Path(exists=True), default=None,
              help="Path to voice memo file (mp3, m4a, wav, etc.)")
@click.option("--notes", "-n", default=None,
              help="Post-visit notes as a string (alternative to --voice)")
def followup(practice_name: str, voice: str | None, notes: str | None):
    """Generate a follow-up email and CRM notes after a visit."""
    if not voice and not notes:
        display.print_error("Provide either --voice <audio_file> or --notes '<text>'")
        raise SystemExit(1)

    briefing, path = load_briefing(practice_name)
    if not briefing:
        display.print_error(
            f"No briefing found for '{practice_name}'. Run `research` first."
        )
        raise SystemExit(1)

    display.console.print(f"[dim]Using briefing:[/dim] [bold]{path.name}[/bold]")

    async def _run():
        if voice:
            display.console.print("[cyan]Transcribing voice memo...[/cyan]")
            transcript = transcribe(voice)
            display.console.print("[green]✓ Transcription complete[/green]")
            display.console.print()
            display.console.print("[dim]Transcript:[/dim]")
            display.console.print(f"[italic]{transcript}[/italic]")
            display.console.print()
        else:
            transcript = notes

        display.console.print("[cyan]Generating follow-up...[/cyan]")
        result = await run_followup(briefing, transcript)
        display.print_followup(result)

        followup_path = save_followup(path, result, practice_name)
        display.print_saved(str(followup_path))

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
