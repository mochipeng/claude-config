#!/usr/bin/env python3
"""
DayDream Dental — Field Visit Intelligence Tool

Commands:
  research             <practice_name> <location>   Generate a pre-visit briefing
  followup             <practice_name> [--voice]    Generate post-visit email + CRM notes
  conference add       <practice_name> <location>   Add practice to conference tracker
  conference voice     <practice_name> [--voice]    Log voice notes into tracker
  conference show                                   Print tracker sorted by follow-up signal
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
from agents.extract import extract_briefing, extract_from_voice
from transcription import transcribe
from utils.tracker import (
    TRACKER_PATH, load_tracker, save_tracker, add_or_update, find_row, sort_by_signal
)

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


# ── conference commands ────────────────────────────────────────────────────────

@cli.group()
def conference():
    """Conference tracker: log practices, auto-populate from briefings, add voice notes."""
    pass


async def _run_research_pipeline(practice_name: str, location: str) -> str:
    """Run the full research pipeline and return the final briefing text."""
    client = get_client()

    async def tracked(coro, progress, task_id, done_label):
        result = await coro
        progress.update(task_id, description=done_label)
        return result

    with display.research_progress() as progress:
        t1 = progress.add_task("[cyan]Website research...",        total=None)
        t2 = progress.add_task("[blue]Reviews research...",        total=None)
        t3 = progress.add_task("[yellow]LinkedIn / DSO signals...", total=None)
        t4 = progress.add_task("[red]Job postings...",             total=None)

        website, reviews, linkedin, jobs = await asyncio.gather(
            tracked(run_website(client, practice_name, location),  progress, t1, "[green]✓ Website"),
            tracked(run_reviews(client, practice_name, location),  progress, t2, "[green]✓ Reviews"),
            tracked(run_linkedin(client, practice_name, location), progress, t3, "[green]✓ LinkedIn"),
            tracked(run_jobs(client, practice_name, location),     progress, t4, "[green]✓ Jobs"),
        )
        raw = {"website": website, "reviews": reviews, "linkedin": linkedin, "jobs": jobs}

        ts = progress.add_task("[cyan]Synthesizing...", total=None)
        briefing = await run_synthesis(practice_name, location, raw)
        progress.update(ts, description="[green]✓ Synthesized")

        tf = progress.add_task("[magenta]Fact-checking...", total=None)
        final = await run_factcheck(briefing, raw)
        progress.update(tf, description="[green]✓ Fact-checked")

    path = briefing_path(practice_name, location)
    save_briefing(path, practice_name, location, final)
    display.print_saved(str(path))
    return final


@conference.command(name="add")
@click.argument("practice_name")
@click.argument("location")
def conference_add(practice_name: str, location: str):
    """Add a practice to the conference tracker. Runs research if no briefing exists."""
    display.print_header(practice_name, location)

    async def _run():
        briefing_text, bpath = load_briefing(practice_name)

        if briefing_text:
            display.console.print(f"[green]✓ Found existing briefing:[/green] [dim]{bpath.name}[/dim]")
        else:
            display.console.print("[yellow]No briefing found — running research...[/yellow]")
            briefing_text = await _run_research_pipeline(practice_name, location)

        display.console.print("[cyan]Extracting tracker fields...[/cyan]")
        data = await extract_briefing(briefing_text)
        data["briefing"] = "Yes"

        rows = load_tracker()
        rows = add_or_update(rows, practice_name, location, data)
        save_tracker(rows)

        signal = data.get("follow_up_signal", "?")
        signal_color = {"HOT": "red", "WARM": "yellow", "COLD": "blue"}.get(signal, "white")
        display.console.print()
        display.console.print(f"[bold]Follow-up signal:[/bold] [{signal_color}]{signal}[/{signal_color}]")
        display.console.print(f"[bold]PM Software:[/bold]       {data.get('pm_software', '—')}")
        display.console.print(f"[bold]In-house Billing:[/bold]  {data.get('in_house_billing', '—')}")
        display.console.print(f"[bold]Decision Makers:[/bold]   {data.get('key_decision_makers', '—')}")
        display.console.print(f"[bold]Confidence:[/bold]        {data.get('confidence_rating', '—')}")
        display.console.print()
        display.console.print(f"[dim]Tracker saved to:[/dim] [bold]{TRACKER_PATH}[/bold]")

    asyncio.run(_run())


@conference.command(name="voice")
@click.argument("practice_name")
@click.option("--voice", "-v", type=click.Path(exists=True), default=None,
              help="Path to voice memo file (mp3, m4a, wav)")
@click.option("--notes", "-n", default=None,
              help="Typed notes as a string")
def conference_voice(practice_name: str, voice: str | None, notes: str | None):
    """Add quick voice/text notes for a practice already in the tracker."""
    if not voice and not notes:
        display.print_error("Provide either --voice <file> or --notes '<text>'")
        raise SystemExit(1)

    rows = load_tracker()
    row = find_row(rows, practice_name)
    if row is None:
        display.print_error(
            f"'{practice_name}' not in tracker. Run `conference add` first."
        )
        raise SystemExit(1)

    async def _run():
        if voice:
            display.console.print("[cyan]Transcribing voice memo...[/cyan]")
            transcript = transcribe(voice)
            display.console.print("[green]✓ Transcription complete[/green]")
            display.console.print(f"[dim]{transcript}[/dim]")
            display.console.print()
        else:
            transcript = notes

        display.console.print("[cyan]Extracting signals from notes...[/cyan]")
        extracted = await extract_from_voice(transcript)

        # Build update dict — voice-confirmed fields override briefing values
        update = {"voice_notes": extracted.get("notes_summary", transcript[:200])}
        if extracted.get("pm_software_confirmed"):
            update["pm_software"]      = extracted["pm_software_confirmed"]
        if extracted.get("in_house_billing_confirmed"):
            update["in_house_billing"] = extracted["in_house_billing_confirmed"]
        if extracted.get("insurance_confirmed"):
            update["insurance_mix"]    = extracted["insurance_confirmed"]
        if extracted.get("follow_up_signal"):
            update["follow_up_signal"] = extracted["follow_up_signal"]

        nonlocal rows
        rows = add_or_update(rows, practice_name, row.get("Location", ""), update)
        save_tracker(rows)

        signal = update.get("follow_up_signal", row.get("Follow-up Signal", "?"))
        signal_color = {"HOT": "red", "WARM": "yellow", "COLD": "blue"}.get(signal, "white")
        display.console.print()
        display.console.print(f"[bold]Updated follow-up signal:[/bold] [{signal_color}]{signal}[/{signal_color}]")
        display.console.print(f"[bold]Notes summary:[/bold] {update['voice_notes']}")
        display.console.print()
        display.console.print(f"[dim]Tracker saved to:[/dim] [bold]{TRACKER_PATH}[/bold]")

    asyncio.run(_run())


@conference.command(name="show")
def conference_show():
    """Print the conference tracker sorted by follow-up signal (HOT first)."""
    from rich.table import Table

    rows = load_tracker()
    if not rows:
        display.console.print("[dim]No practices in tracker yet. Run `conference add` to get started.[/dim]")
        return

    rows = sort_by_signal(rows)

    table = Table(title="Conference Tracker", show_lines=True, header_style="bold cyan")
    table.add_column("Practice",        style="bold", no_wrap=True)
    table.add_column("Signal",          justify="center", width=6)
    table.add_column("PM Software",     width=14)
    table.add_column("In-house Bill.",  justify="center", width=12)
    table.add_column("Pain",            justify="center", width=6)
    table.add_column("Confidence",      justify="center", width=10)
    table.add_column("Decision Makers", width=22)
    table.add_column("Voice Notes",     width=30)

    signal_style = {"HOT": "bold red", "WARM": "bold yellow", "COLD": "bold blue"}

    for r in rows:
        sig = r.get("Follow-up Signal", "")
        table.add_row(
            r.get("Practice Name", ""),
            f"[{signal_style.get(sig, 'white')}]{sig}[/]",
            r.get("PM Software", ""),
            r.get("In-house Billing", ""),
            r.get("Overall Pain", ""),
            r.get("Confidence Rating", ""),
            r.get("Key Decision Makers", ""),
            r.get("Voice Notes", ""),
        )

    display.console.print(table)
    display.console.print(f"[dim]{len(rows)} practice(s)  ·  {TRACKER_PATH}[/dim]")


if __name__ == "__main__":
    cli()
