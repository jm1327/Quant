from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, Iterable, List

import pandas as pd
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from quant_trading.backtesting.cache_exporter import export_backtest_caches
from quant_trading.backtesting.engine import BacktestEngine, HistoricalDataLoader
from quant_trading.config.stock_config import STOCKS
from quant_trading.config.strategy_defaults import DEFAULT_COMMISSION, INITIAL_CAPITAL
from quant_trading.core.strategy_loader import get_strategy_class_name_list, load_strategy

from .serializers import BacktestRequestSerializer


def _to_iso(value: Any) -> Any:
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat()
    return value


def _serialize_equity_curve(frame: pd.DataFrame) -> List[Dict[str, Any]]:
    if frame.empty:
        return []
    records: List[Dict[str, Any]] = []
    for record in frame.to_dict(orient="records"):
        normalized = {key: _to_iso(val) for key, val in record.items()}
        records.append(normalized)
    return records


def _serialize_trades(trades: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    serialized: List[Dict[str, Any]] = []
    for trade in trades:
        normalized = {key: _to_iso(val) for key, val in trade.items()}
        serialized.append(normalized)
    return serialized


class StrategyListView(APIView):
    """Return the list of registered strategy names."""

    def get(self, request, *args, **kwargs):
        strategies = get_strategy_class_name_list()
        return Response({"strategies": strategies, "defaultSymbols": STOCKS})


class BacktestView(APIView):
    """Execute a historical backtest using stored market data."""

    serializer_class = BacktestRequestSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        requested_name = params["strategy"].strip()
        available = get_strategy_class_name_list()
        selected_name = next((name for name in available if name.lower() == requested_name.lower()), None)
        if selected_name is None:
            return Response(
                {
                    "detail": f"Unknown strategy '{requested_name}'. Available strategies: {', '.join(sorted(available)) or 'None'}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        _, strategy_instance, config = load_strategy(strategy_name=selected_name)
        config = dict(config)

        timeframe = params.get("timeframe") or config.get("TIMEFRAME", "5m")
        data_dir = params.get("data_dir") or "market_data"
        cache_dir = params.get("cache_dir") or "backtest_results"
        initial_capital = params.get("initial_capital") or INITIAL_CAPITAL
        commission = params.get("commission") or DEFAULT_COMMISSION

        if timeframe:
            minutes_part = timeframe.lower().rstrip("m")
            if minutes_part.isdigit():
                config["TIMEFRAME"] = minutes_part

        loader = HistoricalDataLoader(base_dir=data_dir, timeframe=timeframe)

        engine = BacktestEngine(
            strategy_instance,
            strategy_config=config,
            data_loader=loader,
            initial_capital=initial_capital,
            commission_per_trade=commission,
        )

        try:
            result = engine.run(
                params["symbols"],
                start=params.get("start"),
                end=params.get("end"),
            )
        except FileNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        response_payload: Dict[str, Any] = {
            "start": _to_iso(result.start),
            "end": _to_iso(result.end),
            "initialCapital": result.initial_capital,
            "endingEquity": result.ending_equity,
            "netProfit": result.net_profit,
            "returnPct": result.return_pct,
            "annualizedReturn": result.annualized_return,
            "maxDrawdown": result.max_drawdown,
            "trades": _serialize_trades(result.trades),
            "closedTrades": _serialize_trades(result.closed_trades),
            "equityCurve": _serialize_equity_curve(result.equity_curve),
            "summaries": [
                {
                    "symbol": summary.symbol,
                    "totalTrades": summary.total_trades,
                    "netPnl": summary.net_pnl,
                    "returnPct": summary.return_pct,
                    "winRate": summary.win_rate,
                }
                for summary in result.summaries
            ],
        }

        if params.get("write_cache", True):
            written = export_backtest_caches(
                result=result,
                loader=loader,
                symbols=params["symbols"],
                timeframe=timeframe,
                strategy_name=selected_name,
                output_dir=cache_dir,
            )
            response_payload["cacheFiles"] = [str(path) for path in written]

        return Response(response_payload)
