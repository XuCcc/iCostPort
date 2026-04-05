"""CLI entry point for icostport."""

import click


@click.group()
def cli() -> None:
    """Bill exports to ICost (.xlsx)."""


@cli.command("convert")
def convert_cmd() -> None:
    """Convert source files to ICost format (pipeline wired in later steps)."""
    click.echo("convert: not implemented yet.")


def main() -> None:
    cli()
