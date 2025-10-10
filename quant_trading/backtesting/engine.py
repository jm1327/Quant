"""Core backtesting utilities for strategies in the quant_trading package."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import pandas as pd

from quant_trading.config.strategy_defaults import (
    MACD_FAST_PERIOD,
    MACD_SIGNAL_PERIOD,
    MACD_SLOW_PERIOD,
)
from quant_trading.core.risk_manager import RiskManager
from quant_trading.strategies.base import BaseStrategy


@dataclass
class BacktestSummary:
    """Per-symbol performance snapshot."""

    symbol: str
    total_trades: int
    net_pnl: float
    return_pct: float
    win_rate: float


@dataclass
class BacktestResult:
    """Aggregate backtest result bundle."""

    start: pd.Timestamp
    end: pd.Timestamp
    initial_capital: float
    ending_equity: float
    net_profit: float
    return_pct: float
    annualized_return: float
    max_drawdown: float
    trades: List[Dict[str, Any]] = field(default_factory=list)
    closed_trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)
    summaries: List[BacktestSummary] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "initial_capital": self.initial_capital,
            "ending_equity": self.ending_equity,
            "net_profit": self.net_profit,
            "return_pct": self.return_pct,
            "annualized_return": self.annualized_return,
            "max_drawdown": self.max_drawdown,
            "trades": self.trades,
            "closed_trades": self.closed_trades,
            "equity_curve": self.equity_curve,
            "summaries": [summary.__dict__ for summary in self.summaries],
        }

    def pretty_print(self) -> None:
        lines = [
            "\n=== Backtest Summary ===",
            f"Period: {self.start.date()} -> {self.end.date()}",
            f"Initial Capital: ${self.initial_capital:,.2f}",
            f"Ending Equity:  ${self.ending_equity:,.2f}",
            f"Net Profit:     ${self.net_profit:,.2f}",
            f"Return:         {self.return_pct * 100:.2f}%",
            f"Annualized:     {self.annualized_return * 100:.2f}%",
            f"Max Drawdown:   {self.max_drawdown * 100:.2f}%",
            f"Trades Executed:{len(self.trades)}",
        ]

        if self.closed_trades:
            wins = sum(1 for trade in self.closed_trades if trade["pnl"] > 0)
            win_rate = wins / len(self.closed_trades)
            lines.append(f"Win Rate:      {win_rate * 100:.2f}% ({wins}/{len(self.closed_trades)})")

        for summary in self.summaries:
            lines.append(
                "\n - {symbol}: trades={trades} | pnl=${pnl:,.2f} | return={ret:.2f}% | win-rate={win:.2f}%".format(
                    symbol=summary.symbol,
                    trades=summary.total_trades,
                    pnl=summary.net_pnl,
                    ret=summary.return_pct * 100,
                    win=summary.win_rate * 100,
                )
            )

        print("\n".join(lines))


class HistoricalDataLoader:
    """Load historical bar data from CSV files."""

    def __init__(self, base_dir: Path | str = "market_data", timeframe: str = "5m") -> None:
        self.base_dir = Path(base_dir)
        self.timeframe = timeframe.strip().lower()

    def _resolve_path(self, symbol: str) -> Path:
        filename = f"{symbol.lower()}_{self.timeframe}_bars_macd.csv"
        candidates = [
            self.base_dir / filename,
            self.base_dir / self.timeframe / filename,
            self.base_dir / self.timeframe.upper() / filename,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError(
            "Historical data for '{symbol}' not found. Checked: "
            .format(symbol=symbol)
            + ", ".join(str(path) for path in candidates)
        )

    def load_symbol(self, symbol: str) -> pd.DataFrame:
        path = self._resolve_path(symbol)

        df = pd.read_csv(path, parse_dates=["datetime"])
        if "datetime" not in df.columns:
            raise ValueError(f"CSV {path} must include a 'datetime' column")

        required_cols = {"open", "high", "low", "close", "volume"}
        present = {col.lower() for col in df.columns}
        missing = required_cols.difference(present)
        if missing:
            raise ValueError(f"CSV {path} is missing required columns: {missing}")

        for column in ["open", "high", "low", "close", "volume"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")

        df = df.dropna(subset=["close"]).copy()
        df = df.sort_values("datetime").reset_index(drop=True)

        df = self._compute_macd(df)
        df["symbol"] = symbol.upper()
        return df

    @staticmethod
    def _compute_macd(df: pd.DataFrame) -> pd.DataFrame:
        df = df.drop(columns=["macd", "signal", "hist"], errors="ignore")

        ema_fast = df["close"].ewm(span=MACD_FAST_PERIOD, adjust=False).mean()
        ema_slow = df["close"].ewm(span=MACD_SLOW_PERIOD, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=MACD_SIGNAL_PERIOD, adjust=False).mean()
        hist = macd - signal

        df["macd"] = macd
        df["signal"] = signal
        df["hist"] = hist
        return df

    def load_symbols(self, symbols: Sequence[str]) -> pd.DataFrame:
        frames: List[pd.DataFrame] = []
        for symbol in symbols:
            try:
                frames.append(self.load_symbol(symbol))
            except FileNotFoundError:
                continue
        if not frames:
            raise FileNotFoundError("No historical data found for requested symbols.")
        return pd.concat(frames, ignore_index=True)


class BacktestEngine:
    """Simple event-driven backtesting engine."""

    def __init__(
        self,
        strategy: BaseStrategy,
        *,
        strategy_config: Optional[Dict[str, str]] = None,
        data_loader: Optional[HistoricalDataLoader] = None,
        initial_capital: float = 100_000.0,
        risk_manager: Optional[RiskManager] = None,
        commission_per_trade: float = 0.0,
    ) -> None:
        self.strategy = strategy
        self.strategy_config = strategy_config or {}
        self.data_loader = data_loader or HistoricalDataLoader()
        self.initial_capital = initial_capital
        self.risk_manager = risk_manager or RiskManager()
        self.commission = commission_per_trade

        self._reset_state()

    def _reset_state(self) -> None:
        self.cash: float = float(self.initial_capital)
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.latest_prices: Dict[str, float] = {}
        self.trades: List[Dict[str, Any]] = []
        self.closed_trades: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []
        self.realized_pnl: float = 0.0

    def _ensure_symbol_slot(self, symbol: str) -> None:
        if symbol not in self.positions:
            self.positions[symbol] = {
                "quantity": 0,
                "avg_price": 0.0,
                "entry_time": None,
            }

    def _current_market_value(self) -> float:
        total = 0.0
        for symbol, pos in self.positions.items():
            price = self.latest_prices.get(symbol, pos["avg_price"])
            total += pos["quantity"] * price
        return total

    def _record_trade(
        self,
        timestamp: pd.Timestamp,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        reason: str,
        trade_type: str,
    ) -> None:
        market_value = self._current_market_value()
        trade = {
            "timestamp": timestamp,
            "symbol": symbol,
            "action": action,
            "quantity": int(quantity),
            "price": float(price),
            "cash_after": float(self.cash),
            "market_value_after": float(market_value),
            "equity_after": float(self.cash + market_value),
            "reason": reason,
            "trade_type": trade_type,
            "position_after": int(self.positions[symbol]["quantity"]),
        }
        self.trades.append(trade)

    def _close_position(
        self,
        symbol: str,
        timestamp: pd.Timestamp,
        price: float,
        quantity: int,
        reason: str,
    ) -> None:
        pos = self.positions[symbol]
        if quantity <= 0 or pos["quantity"] == 0:
            return

        direction = "LONG" if pos["quantity"] > 0 else "SHORT"
        qty_to_close = min(abs(pos["quantity"]), quantity)
        avg_price = pos["avg_price"]
        entry_time = pos["entry_time"]

        if direction == "LONG":
            self.cash += qty_to_close * price - self.commission
            realized = (price - avg_price) * qty_to_close
            pos["quantity"] -= qty_to_close
            action = "SELL"
        else:
            self.cash -= qty_to_close * price + self.commission
            realized = (avg_price - price) * qty_to_close
            pos["quantity"] += qty_to_close
            action = "BUY"

        if pos["quantity"] == 0:
            pos["avg_price"] = 0.0
            pos["entry_time"] = None

        self.realized_pnl += realized
        self.closed_trades.append(
            {
                "symbol": symbol,
                "direction": direction,
                "quantity": qty_to_close,
                "entry_price": avg_price,
                "exit_price": price,
                "entry_time": entry_time,
                "exit_time": timestamp,
                "pnl": realized,
            }
        )

        self._record_trade(timestamp, symbol, action, qty_to_close, price, reason, "CLOSE")

    def _open_position(
        self,
        symbol: str,
        timestamp: pd.Timestamp,
        price: float,
        quantity: int,
        action: str,
        reason: str,
        trade_type: str,
    ) -> None:
        if quantity <= 0:
            return

        pos = self.positions[symbol]
        if action == "BUY":
            cost = quantity * price + self.commission
            if self.cash < cost:
                return
            self.cash -= cost
            new_qty = pos["quantity"] + quantity
            if pos["quantity"] >= 0:
                total_cost = pos["avg_price"] * pos["quantity"] + price * quantity
                pos["avg_price"] = total_cost / max(new_qty, 1)
            else:
                pos["avg_price"] = price
            pos["quantity"] = new_qty
            pos["entry_time"] = timestamp
        else:  # SELL / opening short
            proceeds = quantity * price - self.commission
            self.cash += proceeds
            new_qty = pos["quantity"] - quantity
            if pos["quantity"] <= 0:
                total_cost = abs(pos["avg_price"] * pos["quantity"]) + price * quantity
                pos["avg_price"] = total_cost / max(abs(new_qty), 1)
            else:
                pos["avg_price"] = price
            pos["quantity"] = new_qty
            if pos["quantity"] < 0:
                pos["entry_time"] = timestamp
            elif pos["quantity"] == 0:
                pos["entry_time"] = None

        self._record_trade(timestamp, symbol, action, quantity, price, reason, trade_type)

    def run(
        self,
        symbols: Sequence[str],
        *,
        start: Optional[str | pd.Timestamp] = None,
        end: Optional[str | pd.Timestamp] = None,
    ) -> BacktestResult:
        if not isinstance(self.strategy, BaseStrategy):
            raise ValueError("strategy must be an instance of BaseStrategy")

        self.strategy.configure(self.strategy_config)
        self._reset_state()
        for symbol in symbols:
            self._ensure_symbol_slot(symbol.upper())

        data = self.data_loader.load_symbols(symbols)
        if data.empty:
            raise ValueError("No historical data available for backtest.")

        data["datetime"] = pd.to_datetime(data["datetime"], utc=False)
        data = data.sort_values("datetime").reset_index(drop=True)

        max_date = data["datetime"].max()

        start_dt: pd.Timestamp
        if start is None:
            start_dt = max_date - pd.DateOffset(years=2)
        else:
            start_dt = pd.to_datetime(start)

        end_dt: pd.Timestamp = pd.to_datetime(end) if end else max_date

        data = data[(data["datetime"] >= start_dt) & (data["datetime"] <= end_dt)]
        if data.empty:
            raise ValueError("Historical data is empty after applying date filters.")

        for symbol in symbols:
            subset = data[data["symbol"] == symbol.upper()]
            if subset.empty:
                continue
            self.latest_prices[symbol.upper()] = float(subset.iloc[0]["close"])

        for row in data.itertuples(index=False):
            symbol = str(row.symbol).upper()
            price = float(row.close)
            timestamp = pd.Timestamp(row.datetime)

            self._ensure_symbol_slot(symbol)
            self.latest_prices[symbol] = price

            market_value = self._current_market_value()
            equity_before = self.cash + market_value

            account_info = {
                "NetLiquidation": equity_before,
                "AvailableFunds": self.cash,
                "BuyingPower": self.cash,
            }

            pos_snapshot = {
                "position": self.positions[symbol]["quantity"],
                "avg_cost": self.positions[symbol]["avg_price"],
            }

            macd = float(row.macd) if not math.isnan(row.macd) else 0.0
            signal_val = float(row.signal) if not math.isnan(row.signal) else 0.0
            hist = float(row.hist) if not math.isnan(row.hist) else 0.0

            signal = self.strategy.analyze_position_and_signal(
                symbol,
                macd,
                signal_val,
                hist,
                price,
                pos_snapshot,
            )

            trade_decision = self.strategy.should_trade(signal, pos_snapshot)

            if trade_decision.get("should_trade") and signal.get("action") in {"BUY", "SELL"}:
                trade_type = signal.get("trade_type", "OPEN")
                should_open_position = trade_type != "CLOSE"

                if trade_type in {"CLOSE", "CLOSE_AND_REVERSE"}:
                    close_qty = int(signal.get("close_quantity", abs(pos_snapshot["position"])))
                    if close_qty > 0:
                        self._close_position(symbol, timestamp, price, close_qty, signal.get("reason", trade_type))
                        pos_snapshot = {
                            "position": self.positions[symbol]["quantity"],
                            "avg_cost": self.positions[symbol]["avg_price"],
                        }
                    should_open_position = trade_type == "CLOSE_AND_REVERSE"

                if should_open_position:
                    account_info_after = {
                        "NetLiquidation": self.cash + self._current_market_value(),
                        "AvailableFunds": self.cash,
                        "BuyingPower": self.cash,
                    }

                    position_calc = self.risk_manager.calculate_position_size(account_info_after, signal)
                    quantity = int(position_calc.get("quantity", 0)) if position_calc.get("valid") else 0

                    if quantity > 0:
                        self._open_position(
                            symbol,
                            timestamp,
                            price,
                            quantity,
                            signal.get("action", "BUY"),
                            signal.get("reason", "Signal"),
                            trade_type,
                        )

            market_value = self._current_market_value()
            equity_after = self.cash + market_value
            self.equity_curve.append(
                {
                    "datetime": timestamp,
                    "cash": self.cash,
                    "market_value": market_value,
                    "equity": equity_after,
                }
            )

        equity_df = pd.DataFrame(self.equity_curve).drop_duplicates("datetime")
        equity_df = equity_df.sort_values("datetime").reset_index(drop=True)

        if equity_df.empty:
            equity_df = pd.DataFrame(
                [
                    {
                        "datetime": start_dt,
                        "cash": self.initial_capital,
                        "market_value": 0.0,
                        "equity": self.initial_capital,
                    },
                    {
                        "datetime": end_dt,
                        "cash": self.cash,
                        "market_value": self._current_market_value(),
                        "equity": self.cash + self._current_market_value(),
                    },
                ]
            )

        ending_equity = float(equity_df.iloc[-1]["equity"])
        net_profit = ending_equity - self.initial_capital
        total_return = net_profit / self.initial_capital if self.initial_capital else 0.0

        num_days = max((equity_df.iloc[-1]["datetime"] - equity_df.iloc[0]["datetime"]).days, 1)
        annualized_return = (1 + total_return) ** (365 / num_days) - 1 if num_days > 0 else 0.0

        peak = equity_df["equity"].cummax()
        drawdown = (equity_df["equity"] - peak) / peak.replace(0, pd.NA)
        max_drawdown = float(drawdown.min()) if not drawdown.isna().all() else 0.0
        max_drawdown = abs(max_drawdown)

        summaries = self._build_symbol_summaries()

        return BacktestResult(
            start=equity_df.iloc[0]["datetime"],
            end=equity_df.iloc[-1]["datetime"],
            initial_capital=self.initial_capital,
            ending_equity=ending_equity,
            net_profit=net_profit,
            return_pct=total_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            trades=self.trades,
            closed_trades=self.closed_trades,
            equity_curve=equity_df,
            summaries=summaries,
        )

    def _build_symbol_summaries(self) -> List[BacktestSummary]:
        summaries: List[BacktestSummary] = []
        if not self.closed_trades:
            return summaries

        trades_by_symbol: Dict[str, List[Dict[str, Any]]] = {}
        for trade in self.closed_trades:
            trades_by_symbol.setdefault(trade["symbol"], []).append(trade)

        for symbol, trades in trades_by_symbol.items():
            pnl = sum(trade["pnl"] for trade in trades)
            wins = sum(1 for trade in trades if trade["pnl"] > 0)
            summaries.append(
                BacktestSummary(
                    symbol=symbol,
                    total_trades=len(trades),
                    net_pnl=pnl,
                    return_pct=pnl / self.initial_capital if self.initial_capital else 0.0,
                    win_rate=wins / len(trades) if trades else 0.0,
                )
            )
        return summaries
