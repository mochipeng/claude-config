from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.markdown import Markdown
from rich.rule import Rule

console = Console()


def research_progress():
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


def print_header(practice_name: str, location: str):
    console.print()
    console.print(
        Panel(
            f"[bold white]DayDream Dental — Field Intel[/bold white]\n"
            f"[dim]{practice_name} · {location}[/dim]",
            style="bold blue",
            expand=False,
        )
    )
    console.print()


def print_briefing(briefing_md: str):
    console.print(Rule("[bold]BRIEFING CARD[/bold]", style="blue"))
    console.print(Markdown(briefing_md))


def print_followup(followup_md: str):
    console.print()
    console.print(Rule("[bold]POST-VISIT OUTPUT[/bold]", style="green"))
    console.print(Markdown(followup_md))


def print_saved(path: str):
    console.print()
    console.print(f"[dim]Saved to:[/dim] [bold]{path}[/bold]")
    console.print()


def print_error(msg: str):
    console.print(f"[bold red]Error:[/bold red] {msg}")
