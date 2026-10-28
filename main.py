"""
Main CLI entry point for Spectre-CLI.
Autonomous digital seance agent for resurrecting forgotten local files and logs.
Hacktoberfest 2026: Ghost in the Machine.
"""

from pathlib import Path
import click
from rich.prompt import Prompt
from rich.status import Status

from spectre import __version__
from spectre.agent import SpectreAgent
from spectre.config import config
from spectre.ui.console import (
    console,
    print_banner,
    print_spectral_box,
    typewriter_print,
    display_audit_table,
)


@click.group()
@click.version_option(version=__version__, prog_name="Spectre-CLI")
def cli():
    """
    Spectre-CLI: Autonomous digital seance for forgotten local files & logs.
    Channel deprecated projects, archived code, and historical logs with local Gemma-2.
    """
    pass


@cli.command("resurrect")
@click.argument("target_path", type=click.Path(exists=True, file_okay=True, dir_okay=True, path_type=Path))
@click.option("--offline", is_flag=True, help="Force offline memory storage & simulation.")
def resurrect_cmd(target_path: Path, offline: bool):
    """
    Ingest, chunk, embed, and store forgotten files or repos into MongoDB Atlas Vector Search.
    """
    print_banner()
    if offline:
        config.offline_mode = True

    agent = SpectreAgent(config)
    target = target_path.resolve()

    console.print(f"[bold cyan]* Commencing digital exhumation on:[/bold cyan] [underline]{target}[/underline]")
    with Status("[italic magenta]Resurrecting forgotten files, chunking tokens, and calculating vectors...[/italic magenta]", console=console):
        result = agent.resurrect(target)

    console.print()
    print_spectral_box(
        f"* Files Exhumed: [bold green]{result['files_scanned']}[/bold green]\n"
        f"* Memory Chunks Indexed: [bold green]{result['chunks_indexed']}[/bold green]\n"
        f"* Vector Tomb Layer: [bold yellow]{result['store_type']}[/bold yellow]\n"
        f"* Ingestion Latency: [dim]{result['elapsed_ms']} ms[/dim]\n\n"
        "[italic]The spirits are now bound to the vector graveyard. Commune with them using: [bold]spectre seance[/bold][/italic]",
        title="Exhumation Complete",
        border_style="green",
    )


@cli.command("seance")
@click.option("--tts/--no-tts", default=False, help="Enable ElevenLabs eerie spoken-word audio generation.")
@click.option("--offline", is_flag=True, help="Run completely offline without cloud calls.")
def seance_cmd(tts: bool, offline: bool):
    """
    Enter the interactive seance chamber to commune with your resurrected codebase.
    """
    print_banner()
    if offline:
        config.offline_mode = True

    agent = SpectreAgent(config)
    stats = agent.get_graveyard_stats()

    console.print(
        f"[dim]Seance Chamber Ready. Resurrected Memories: [bold green]{stats['total_memories']}[/bold green] | "
        f"Memory Store: [bold yellow]{stats['vector_store_backend']}[/bold yellow] | "
        f"Model: [bold cyan]{stats['inference_model']}[/bold cyan][/dim]"
    )
    if tts:
        console.print("[italic magenta]* ElevenLabs Ghostly Whispers: Enabled *[/italic magenta]")
    console.print("[dim]Type your inquiry, or '/audit' for Sentry stats, or 'exit' to depart.[/dim]\n")

    while True:
        try:
            query = Prompt.ask("[bold green]Seeker[/bold green]").strip()
            if not query:
                continue

            if query.lower() in ("exit", "quit", "/exit", "/quit"):
                console.print("\n[italic dim magenta]The seance circle is closed. Rest in peace.[/italic dim magenta]")
                break

            if query.lower() == "/audit":
                display_audit_table(agent.tracer.get_audit_summary())
                continue

            if query.startswith("/tomb "):
                tomb_path = query.replace("/tomb ", "", 1).strip()
                content = agent.tool_read_tomb(tomb_path)
                if content:
                    print_spectral_box(content[:1500] + "\n...(truncated)", title=f"Tomb: {tomb_path}")
                else:
                    console.print(f"[red]Could not open tomb: {tomb_path}[/red]")
                continue

            console.print()
            with Status("[italic magenta]Channeling the digital ether through Gemma-2...[/italic magenta]", console=console):
                result = agent.commune(query, speak=tts)

            console.print(f"[bold magenta]* Spectre [dim]({result['model']} | {result['elapsed_ms']}ms | {result['mastra_backend']})[/dim]:[/bold magenta]")
            typewriter_print(result["response"], delay=0.008)

            if result.get("audio_path"):
                console.print(f"[bold green][Audio] Eerie narration generated:[/bold green] [underline]{result['audio_path']}[/underline]\n")

        except KeyboardInterrupt:
            console.print("\n[italic dim]Seance interrupted. Exiting...[/italic dim]")
            break


@cli.command("inspect")
def inspect_cmd():
    """
    Inspect the memory graveyard, vector index counts, and Sentry audit report.
    """
    print_banner()
    agent = SpectreAgent(config)
    stats = agent.get_graveyard_stats()

    console.print(f"[bold cyan]* Memory Graveyard Status *[/bold cyan]")
    console.print(f"* Total Resurrected Chunks: [bold green]{stats['total_memories']}[/bold green]")
    console.print(f"* Vector Store Layer: [bold yellow]{stats['vector_store_backend']}[/bold yellow]")
    console.print(f"* Local Gemma-2 Connection: {'[green]ONLINE[/green]' if stats['ollama_online'] else '[yellow]OFFLINE (Simulation Active)[/yellow]'}")
    console.print(f"* Mastra Daemon Bridge: {'[green]CONNECTED[/green]' if stats['mastra_online'] else '[yellow]PYTHON-EMBEDDED ENGINE[/yellow]'}")
    console.print(f"* ElevenLabs TTS Configured: {'[green]YES[/green]' if stats['elevenlabs_configured'] else '[dim]NO (Terminal Text Only)[/dim]'}\n")

    display_audit_table(stats["telemetry"])


if __name__ == "__main__":
    cli()
