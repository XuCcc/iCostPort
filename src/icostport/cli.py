"""icostport 命令行入口。"""

import click


@click.group()
def cli() -> None:
    """账单导出转 ICost（.xlsx）。"""


@cli.command("convert")
def convert_cmd() -> None:
    """将源文件转换为 ICost 格式（流水线将在后续步骤接入）。"""
    click.echo("convert: not implemented yet.")


def main() -> None:
    cli()
