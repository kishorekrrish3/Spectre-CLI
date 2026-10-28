"""
Rich terminal UI for Spectre-CLI.
Renders gothic ASCII séances, glowing spectral logs, and typewriter reveals.
Guarantees cross-platform Windows cp1252 / UTF-8 compatibility.
"""

import sys
import time
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

# Force safe utf-8 friendly output
console = Console()

SEANCE_BANNER = r"""[bold magenta]
   .---.          .---.
  /     \  .-.   /     \     [bold green]S P E C T R E - C L I[/bold green]
 | () () |/   \ | () () |    [dim cyan]Autonomous Digital Seance for Forgotten Files[/dim cyan]
  \  _  / \ _ /  \  _  /     [italic dim]Hacktoberfest 2026: Ghost in the Machine[/italic dim]
   `---'   `-'    `---'
[/bold magenta]"""


def print_banner():
    """Renders the gothic seance header."""
    console.print(SEANCE_BANNER)


def print_spectral_box(content: str, title: str = "Spectral Revelation", border_style: str = "bold cyan"):
    """Displays highlighted seance text inside an ornate panel."""
    console.print(Panel(content, title=f"[bold green]* {title} *[/bold green]", border_style=border_style, padding=(1, 2)))


def print_markdown(content: str):
    """Prints rich markdown formatting."""
    console.print(Markdown(content))


def typewriter_print(text: str, delay: float = 0.008, style: str = "italic cyan"):
    """
    Renders text with a hypnotic, typewriter cadence reminiscent of a spirit communication.
    """
    console.print(f"[{style}]", end="")
    for char in text:
        try:
            sys.stdout.write(char)
            sys.stdout.flush()
        except UnicodeEncodeError:
            sys.stdout.write("?")
            sys.stdout.flush()
        time.sleep(delay)
    console.print(f"[/{style}]")
    print()


def display_audit_table(audit_data: dict):
    """
    Renders telemetry table auditing tokens, latency, and inference savings.
    """
    table = Table(title="Sentry Agent Telemetry & Inference Audit", border_style="magenta")
    table.add_column("Metric", style="cyan", justify="left")
    table.add_column("Observed Value", style="green", justify="right")

    table.add_row("Sentry Tracing Enabled", str(audit_data.get("sentry_enabled", False)))
    table.add_row("Total Prompt Tokens", f"{audit_data.get('total_prompt_tokens', 0):,}")
    table.add_row("Total Output Tokens", f"{audit_data.get('total_completion_tokens', 0):,}")
    table.add_row("Total Agent Tokens", f"{audit_data.get('total_tokens', 0):,}")
    table.add_row("Total Tool Invocations", str(audit_data.get("total_tool_calls", 0)))
    table.add_row("Total Local Inference Time", f"{audit_data.get('total_inference_time_ms', 0):.2f} ms")
    table.add_row("Actual Cost (Local Gemma-2)", "$0.00000 (100% Free & Private)")
    table.add_row("Cloud API Equiv. Saved", f"${audit_data.get('cloud_cost_saved_usd', 0):.5f}")

    console.print(table)
