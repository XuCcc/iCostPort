"""icostport 命令行入口。"""

from __future__ import annotations

from pathlib import Path

import click


@click.group()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="更详细的日志输出。",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """账单导出转 ICost（.xlsx）。"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


@cli.command("convert")
@click.argument(
    "paths",
    nargs=-1,
    type=click.Path(exists=True, path_type=Path),
    required=True,
)
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help=(
        "YAML 配置文件路径；省略时按顺序查找 "
        "ICOSTPORT_CONFIG -> ./config.yml -> ~/.config/icostport/config.yml。"
    ),
)
@click.option(
    "-o",
    "--output",
    "output",
    type=click.Path(path_type=Path),
    required=True,
    help="输出 .xlsx 路径。",
)
@click.pass_context
def convert_cmd(
    ctx: click.Context,
    paths: tuple[Path, ...],
    config: Path | None,
    output: Path,
) -> None:
    """将若干源文件转换为 ICost 可导入表格。"""
    from icostport.pipeline import run

    verbose = bool(ctx.obj.get("verbose"))
    run(list(paths), output, config, verbose=verbose)


def main() -> None:
    cli(obj={})
