"""Utilities for exporting backtest results to cached JSON payloads."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Sequence

import pandas as pd

from .engine import BacktestResult, HistoricalDataLoader


def _sanitize_trade(trade: Dict[str, object]) -> Dict[str, object]:
    cleaned = dict(trade)
    for key in ("entry_time", "exit_time", "timestamp"):
        if key in cleaned and cleaned[key] is not None:
            cleaned[key] = pd.to_datetime(cleaned[key]).isoformat()
    return cleaned


def _serialize_candles(df: pd.DataFrame) -> List[Dict[str, object]]:
    frame = df.copy()
    frame["datetime"] = frame["datetime"].apply(lambda ts: pd.to_datetime(ts).isoformat())
    for column in ["open", "high", "low", "close", "volume"]:
        if column in frame.columns:
            frame[column] = frame[column].astype(float)
    return frame[["datetime", "open", "high", "low", "close", "volume"]].to_dict(orient="records")


def export_backtest_caches(
    *,
    result: BacktestResult,
    loader: HistoricalDataLoader,
    symbols: Sequence[str],
    timeframe: str,
    strategy_name: str,
    output_dir: Path | str,
) -> List[Path]:
    """Write per-symbol cache files compatible with the visualization tools."""

    timeframe_norm = timeframe.strip().lower()
    strategy_norm = strategy_name.upper()
    base_output = Path(output_dir) / strategy_norm / timeframe_norm
    base_output.mkdir(parents=True, exist_ok=True)

    summary_map = {summary.symbol.upper(): summary for summary in result.summaries}

    written: List[Path] = []
    for symbol in symbols:
        symbol_upper = symbol.upper()
        symbol_trades: List[Dict[str, object]] = [
            trade for trade in result.closed_trades if str(trade.get("symbol", "")).upper() == symbol_upper
        ]

        try:
            candles = loader.load_symbol(symbol_upper)
        except FileNotFoundError:
            continue

        candles = candles[(candles["datetime"] >= result.start) & (candles["datetime"] <= result.end)].copy()
        if candles.empty:
            continue

        summary = summary_map.get(symbol_upper)

        net_profit = summary.net_pnl if summary else 0.0
        return_pct = summary.return_pct if summary else 0.0
        win_rate = summary.win_rate if summary else None
        total_trades = summary.total_trades if summary else len(symbol_trades)

        payload = {
            "symbol": symbol_upper,
            "timeframe": timeframe_norm,
            "start": pd.to_datetime(result.start).isoformat(),
            "end": pd.to_datetime(result.end).isoformat(),
            "initial_capital": result.initial_capital,
            "ending_equity": result.ending_equity,
            "net_profit": net_profit,
            "return_pct": return_pct,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "max_drawdown": result.max_drawdown,
            "closed_trades": [_sanitize_trade(trade) for trade in symbol_trades],
            "candles": _serialize_candles(candles),
        }

        symbol_lower = symbol_upper.lower()
        cache_path = base_output / f"{symbol_lower}_{timeframe_norm}_backtest.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        written.append(cache_path)

    return written