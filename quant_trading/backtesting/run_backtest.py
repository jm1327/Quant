#!/usr/bin/env python3
"""Command-line interface to run historical backtests."""

from __future__ import annotations

import argparse
from typing import List

from quant_trading.backtesting.engine import BacktestEngine, HistoricalDataLoader
from quant_trading.config.stock_config import STOCKS
from quant_trading.config.trading_config import INITIAL_CAPITAL
from quant_trading.core.strategy_loader import get_strategy_class_name_list, load_strategy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a historical backtest using stored market data.")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=STOCKS,
        help="Symbol list to backtest (default: values from stock_config.STOCKS)",
    )
    parser.add_argument(
        "--start",
        help="Optional start date (YYYY-MM-DD). Defaults to two years before the latest data point.",
    )
    parser.add_argument(
        "--end",
        help="Optional end date (YYYY-MM-DD). Defaults to the latest available date in historical data.",
    )
    parser.add_argument(
        "--strategy",
        help="Override strategy name declared in strategy.env / environment variables.",
    )
    parser.add_argument(
        "--initial-capital",
        type=float,
        default=INITIAL_CAPITAL,
        help="Initial virtual capital for backtesting (default: trading_config.INITIAL_CAPITAL)",
    )
    parser.add_argument(
        "--data-dir",
        default="market_data",
        help="Directory containing historical CSV files (default: market_data)",
    )
    parser.add_argument(
        "--timeframe",
        default="5m",
        help="Timeframe suffix used in historical filenames (default: 5m)",
    )
    parser.add_argument(
        "--commission",
        type=float,
        default=0.0,
        help="Commission per trade execution (flat amount, default: 0)",
    )
    return parser


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    available = get_strategy_class_name_list()
    override_name = args.strategy.upper() if args.strategy else None
    if override_name and override_name not in [name.upper() for name in available]:
        parser.error(
            f"Unknown strategy '{args.strategy}'. Available: {', '.join(sorted(available)) or 'None'}"
        )

    strategy_name, strategy_instance, config = load_strategy(strategy_name=override_name)

    config = dict(config)
    if args.timeframe:
        minutes = args.timeframe.lower().rstrip("m")
        if minutes.isdigit():
            config["TIMEFRAME"] = minutes
    if config:
        strategy_instance.configure(config)

    loader = HistoricalDataLoader(base_dir=args.data_dir, timeframe=args.timeframe)

    engine = BacktestEngine(
        strategy_instance,
        strategy_config=config,
        data_loader=loader,
        initial_capital=args.initial_capital,
        commission_per_trade=args.commission,
    )

    result = engine.run(args.symbols, start=args.start, end=args.end)
    result.pretty_print()


if __name__ == "__main__":
    main()
