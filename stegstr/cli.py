#!/usr/bin/env python3
"""
Stegstr CLI v2.1.5
"""

import sys
import os
import json
import base64
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from stegstr.stego.engine import StegoEngine, StegoMode
from stegstr.platform.simulator import PlatformSimulator
from stegstr.agent.optimizer import StegstrAgent
from stegstr.analysis.steganalysis import StegAnalyzer

console = Console()


@click.group()
@click.version_option(version="2.1.5", prog_name="stegstr")
def cli():
    """Stegstr — Robust steganographic client for social media."""
    pass


@cli.command()
@click.option("--cover", "-c", required=True, type=click.Path(exists=True), help="Cover image path")
@click.option("--message", "-m", required=True, help="Message to hide")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output stego image path")
@click.option("--mode", type=click.Choice([m.name for m in StegoMode]), help="Steganography mode")
@click.option("--platform", "-p", type=click.Choice(["whatsapp_standard", "whatsapp_hd", "telegram_photo",
                                                      "telegram_file", "instagram", "twitter", "facebook",
                                                      "signal", "linkedin", "reddit"]),
              help="Target platform profile")
@click.option("--password", help="Encryption password")
@click.option("--delta", type=float, help="Delta override")
@click.option("--ecc", type=int, help="ECC override")
@click.option("--json", "output_json", is_flag=True, help="Output JSON metadata")
def encode(cover, message, output, mode, platform, password, delta, ecc, output_json):
    """Embed a message into a cover image."""
    engine = StegoEngine(
        mode=StegoMode[mode] if mode else StegoMode.HYBRID,
        password=password,
        delta_override=delta,
        ecc_override=ecc,
    )
    with console.status("[bold green]Embedding message..."):
        meta = engine.embed(cover, message, output, target_platform=platform)
    if output_json:
        click.echo(json.dumps(meta, indent=2, default=str))
    else:
        table = Table(title="Embed Result")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="magenta")
        for k, v in meta.items():
            table.add_row(k, str(v))
        console.print(table)


@cli.command()
@click.option("--stego", "-s", required=True, type=click.Path(exists=True), help="Stego image path")
@click.option("--password", help="Decryption password")
@click.option("--mode", type=click.Choice([m.name for m in StegoMode]), help="Expected mode")
@click.option("--json", "output_json", is_flag=True, help="Output JSON result")
@click.option("--decode", "decode_mode", default="auto", type=click.Choice(["auto", "utf8", "base64", "bytes"]), help="How to decode extracted payload")
def extract(stego, password, mode, output_json, decode_mode):
    """Extract a hidden message from a stego image."""
    engine = StegoEngine(password=password)
    expected = StegoMode[mode] if mode else None
    with console.status("[bold green]Extracting message..."):
        result = engine.extract(stego, expected_mode=expected)
    if result is None:
        if output_json:
            click.echo(json.dumps({"success": False, "error": "No message found or extraction failed"}))
        else:
            console.print("[red]No message found[/red] — wrong password, corrupted image, or no hidden data.")
        sys.exit(1)

    if output_json:
        click.echo(json.dumps({"success": True, **result}, indent=2, default=str))
    else:
        panel = Panel(
            f"[green]{result['message'][:500]}[/green]" + ("..." if len(result['message']) > 500 else ""),
            title="Extracted Message",
            subtitle=f"Mode: {result['mode']} | Delta: {result.get('delta_used', 'auto')} | Encoding: {result.get('encoding', 'utf-8')}"
        )
        console.print(panel)


@cli.command()
@click.option("--cover", "-c", required=True, type=click.Path(exists=True), help="Cover image path")
@click.option("--mode", type=click.Choice([m.name for m in StegoMode]), help="Steganography mode")
@click.option("--platform", "-p", type=click.Choice(["whatsapp_standard", "whatsapp_hd", "telegram_photo",
                                                      "telegram_file", "instagram", "twitter", "facebook",
                                                      "signal", "linkedin", "reddit"]),
              help="Target platform profile")
@click.option("--ecc", type=int, help="ECC override")
def capacity(cover, mode, platform, ecc):
    """Show capacity of a cover image."""
    engine = StegoEngine()
    mode = StegoMode[mode] if mode else StegoMode.ARMOR
    cap = engine.get_capacity(cover, mode, platform=platform, ecc_bytes=ecc)
    console.print(f"[green]Capacity for {mode.name}:[/green] {cap} bytes")


@cli.command()
@click.option("--cover", "-c", required=True, type=click.Path(exists=True), help="Cover image path")
@click.option("--message", "-m", required=True, help="Message to optimize for")
@click.option("--platform", "-p", required=True, type=click.Choice(["whatsapp_standard", "whatsapp_hd", "telegram_photo",
                                                                      "telegram_file", "instagram", "twitter", "facebook",
                                                                      "signal", "linkedin", "reddit"]),
              help="Target platform profile")
@click.option("--depth", type=click.Choice(["quick", "standard", "deep"]), default="standard", help="Search depth")
@click.option("--json", "output_json", is_flag=True, help="Output JSON result")
def optimize(cover, message, platform, depth, output_json):
    """Auto-tune parameters for a platform."""
    engine = StegoEngine()
    with console.status(f"[bold green]Auto-tuning for {platform}..."):
        result = engine.auto_tune(cover, message, platform, search_depth=depth)
    if output_json:
        click.echo(json.dumps(result, indent=2, default=str))
    else:
        table = Table(title="Auto-Tune Result")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="magenta")
        for k, v in result.items():
            table.add_row(k, str(v))
        console.print(table)


@cli.command()
@click.option("--cover", "-c", type=click.Path(exists=True), help="Cover image path")
@click.option("--stego", "-s", type=click.Path(exists=True), help="Stego image path")
def analyze(cover, stego):
    """Analyze steganographic detectability."""
    analyzer = StegAnalyzer()
    if cover and stego:
        report = analyzer.compare(cover, stego)
    elif stego:
        report = analyzer.analyze(stego)
    else:
        console.print("[red]Provide --cover and --stego, or just --stego[/red]")
        sys.exit(1)
    console.print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    cli()
