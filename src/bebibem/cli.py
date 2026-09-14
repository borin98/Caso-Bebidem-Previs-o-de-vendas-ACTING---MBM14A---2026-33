"""Command-line entry point for the BebiBem forecasting pipeline."""

from __future__ import annotations

import argparse
import logging
import traceback
from collections.abc import Sequence
from pathlib import Path

from .config import DEFAULT_INPUT, DEFAULT_OUTDIR, FIGURE_FORMATS, SEED
from .io_data import InputError
from .pipeline import PipelineConfig, run

LOGGER = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gera a previsão de demanda da loja própria BebiBem."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="CSV de entrada")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR, help="diretório de saída")
    parser.add_argument("--formats", default=",".join(FIGURE_FORMATS), help="formatos: png,svg,pdf")
    parser.add_argument("--poly-degree", type=int, default=None, help="grau polinomial entre 1 e 5")
    parser.add_argument("--ma-windows", default="3,12", help="janelas de média móvel")
    parser.add_argument(
        "--horizon-years", type=int, default=1, help="horizonte futuro: 1, 2 ou 3 anos"
    )
    parser.add_argument("--k-months", type=int, default=None, help="número de clusters mensais")
    parser.add_argument("--units-per-case", type=int, default=None, help="unidades por caixa")
    parser.add_argument("--steps", default=None, help="etapas separadas por vírgula")
    parser.add_argument("--seed", type=int, default=SEED, help="semente dos modelos")
    parser.add_argument(
        "--timeseries",
        action="store_true",
        help="executa modelos de séries temporais (Holt-Winters, SARIMA, Fourier)",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=("debug", "info", "warning", "error"),
        help="nível de log",
    )
    return parser


def _parse_int_list(value: str, option: str) -> tuple[int, ...]:
    if value.strip() == "":
        raise InputError(f"{option} não pode ser vazio")
    try:
        values = tuple(int(item.strip()) for item in value.split(","))
    except ValueError as error:
        raise InputError(f"{option} deve conter inteiros separados por vírgula") from error
    if len(values) == 0:
        raise InputError(f"{option} não pode ser vazio")
    return values


def _config_from_args(args: argparse.Namespace) -> PipelineConfig:
    formats = tuple(item.strip() for item in args.formats.split(","))
    windows = _parse_int_list(args.ma_windows, "--ma-windows")
    steps = None if args.steps is None else tuple(item.strip() for item in args.steps.split(","))
    return PipelineConfig(
        input=args.input,
        outdir=args.outdir,
        formats=formats,
        poly_degree=args.poly_degree,
        ma_windows=windows,
        horizon_years=args.horizon_years,
        k_months=args.k_months,
        units_per_case=args.units_per_case,
        steps=steps,
        seed=args.seed,
        log_level=args.log_level,
        timeseries=args.timeseries,
    )


def _print_summary(result, formats: Sequence[str]) -> None:
    format_count = max(1, len(tuple(formats)))
    figure_count = len(result.figures) // format_count
    print(f"Figuras: {figure_count}")
    print(f"Tabelas: {len(result.tables)}")
    if len(result.annual_forecast) == 0:
        return
    for row in result.annual_forecast.itertuples(index=False):
        total = int(row.unidades_previstas_total)
        print(f"Total anual — {row.produto} ({row.ano}): {total} unidades")


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the documented process exit code."""
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s: %(message)s",
        force=True,
    )
    try:
        config = _config_from_args(args)
        result = run(config)
    except InputError as error:
        print(f"Erro de validação: {error}")
        return 2
    except Exception as error:  # noqa: BLE001 — CLI must map unexpected failures to exit code 1.
        if args.log_level == "debug":
            traceback.print_exc()
            return 1
        print(f"Erro inesperado: {error}")
        return 1
    _print_summary(result, config.formats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
