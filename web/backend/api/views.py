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
from quant_trading.core.portfolio_tracker import PortfolioTracker

from .models import SimulatedOrder
from .serializers import BacktestRequestSerializer, SimulatedOrderCreateSerializer, SimulatedOrderSerializer


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


class SimulatedOrderListCreateView(APIView):
    """Persist simulated (paper) orders so the dashboard can display recent actions."""

    def get(self, request, *args, **kwargs):
        queryset = SimulatedOrder.objects.all()[:100]
        serializer = SimulatedOrderSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = SimulatedOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        response_data = SimulatedOrderSerializer(order).data
        return Response(response_data, status=status.HTTP_201_CREATED)


class PortfolioSnapshotView(APIView):
    """Connect to IBKR paper trading and return a portfolio snapshot."""

    def get(self, request, *args, **kwargs):
        port = int(request.query_params.get("port", 7497))
        client_id = int(request.query_params.get("clientId", 981))
        timeout = int(request.query_params.get("timeout", 15))

        tracker = PortfolioTracker(client_id=client_id)
        if not tracker.connect_to_tws(port=port):
            return Response({"detail": "Failed to connect to IBKR TWS (paper account)."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        try:
            if not tracker.fetch_portfolio_data(timeout=timeout):
                return Response({"detail": "Timed out while fetching portfolio data."}, status=status.HTTP_504_GATEWAY_TIMEOUT)

            cash_balances = _normalize_cash_balances(tracker.get_cash_balances())
            positions_df = tracker.get_positions_df()
            positions = _normalize_positions(positions_df.to_dict(orient="records")) if not positions_df.empty else []
            holdings = _normalize_holdings(tracker.portfolio_items)
            currency_totals = _market_value_by_currency(tracker)

            payload = {
                "retrievedAt": datetime.utcnow().isoformat() + "Z",
                "cashBalances": cash_balances,
                "positions": positions,
                "holdings": holdings,
                "marketValueByCurrency": currency_totals,
            }
            return Response(payload)
        except Exception as exc:  # pragma: no cover - defensive logging
            return Response({"detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            tracker.disconnect_from_tws()


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_cash_balances(raw: Dict[str, Dict[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for label, currencies in raw.items():
        amounts = []
        for currency, info in currencies.items():
            amount = _safe_float(info.get("value"))
            amounts.append(
                {
                    "currency": currency,
                    "value": amount,
                    "raw": info.get("value"),
                    "accountName": info.get("accountName"),
                }
            )
        normalized.append({"label": label, "amounts": amounts})
    return normalized


def _normalize_positions(raw_positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in raw_positions:
        position = _safe_float(item.get("position")) or 0.0
        if position == 0.0:
            continue
        avg_cost = _safe_float(item.get("averageCost") or item.get("avgCost"))
        market_price = _safe_float(item.get("marketPrice"))
        market_value = _safe_float(item.get("marketValue"))
        unrealized = _safe_float(item.get("unrealizedPnl") or item.get("unrealizedPNL"))
        realized = _safe_float(item.get("realizedPnl") or item.get("realizedPNL"))
        daily = _safe_float(item.get("dailyPnl"))
        ratio = _safe_float(item.get("unrealizedPnlRatio"))
        normalized.append(
            {
                "symbol": item.get("symbol"),
                "position": position,
                "avgCost": avg_cost,
                "marketPrice": market_price,
                "marketValue": market_value,
                "dailyPnl": daily,
                "unrealizedPnl": unrealized,
                "unrealizedPnlRatio": ratio,
                "realizedPnl": realized,
                "currency": item.get("currency"),
                "exchange": item.get("exchange"),
                "secType": item.get("secType"),
            }
        )
    return normalized


def _normalize_holdings(raw_holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in raw_holdings:
        position = _safe_float(item.get("position")) or 0.0
        if position == 0:
            continue
        normalized.append(
            {
                "symbol": item.get("symbol"),
                "position": position,
                "marketValue": _safe_float(item.get("marketValue")),
                "unrealizedPnl": _safe_float(item.get("unrealizedPNL")),
                "realizedPnl": _safe_float(item.get("realizedPNL")),
                "averageCost": _safe_float(item.get("averageCost")),
                "currency": item.get("currency"),
                "accountName": item.get("accountName"),
            }
        )
    return normalized


def _market_value_by_currency(tracker: PortfolioTracker) -> List[Dict[str, Any]]:
    frame = tracker.get_portfolio_df()
    if frame.empty:
        return []
    summary = frame.groupby("currency")["marketValue"].sum().reset_index()
    result: List[Dict[str, Any]] = []
    for row in summary.itertuples(index=False):
        result.append({"currency": getattr(row, "currency"), "marketValue": float(getattr(row, "marketValue", 0.0))})
    return result
