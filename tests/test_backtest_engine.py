from __future__ import annotations

import pandas as pd

from quant_trading.backtesting.engine import BacktestEngine, HistoricalDataLoader
from quant_trading.strategies.base import BaseStrategy


class DummyLoader(HistoricalDataLoader):
	def __init__(self, frame: pd.DataFrame) -> None:
		self._frame = frame

	def load_symbols(self, symbols):  # type: ignore[override]
		return self._frame.copy()


class AlwaysExitStrategy(BaseStrategy):
	"""Strategy that opens on the first bar and closes on the second."""

	name = "ALWAYS_EXIT"

	def analyze_position_and_signal(
		self,
		symbol: str,
		macd: float,
		signal: float,
		hist: float,
		close_price: float,
		current_positions,
	):
		if current_positions["position"] == 0:
			return {
				"action": "BUY",
				"reason": "enter",
				"entry_price": close_price,
				"stop_loss": close_price * 0.95,
				"confidence": 1.0,
				"trade_type": "OPEN",
			}
		return {
			"action": "SELL",
			"reason": "exit",
			"entry_price": close_price,
			"stop_loss": close_price * 1.05,
			"confidence": 1.0,
			"trade_type": "CLOSE",
			"close_quantity": abs(current_positions["position"]),
		}

	def should_trade(self, signal, current_positions):
		return {"should_trade": signal["confidence"] >= 1.0, "reason": "always"}


class StubRiskManager:
	def calculate_position_size(self, account_info, signal):
		return {"quantity": 1, "valid": True}


def test_backtest_engine_executes_round_trip():
	frame = pd.DataFrame(
		{
			"datetime": pd.to_datetime(["2024-01-01 09:30", "2024-01-01 09:35"]),
			"open": [100.0, 101.0],
			"high": [101.0, 102.0],
			"low": [99.0, 100.5],
			"close": [100.5, 101.5],
			"volume": [1000, 1200],
			"macd": [0.1, 0.2],
			"signal": [0.05, 0.1],
			"hist": [0.05, 0.1],
			"symbol": ["AAPL", "AAPL"],
		}
	)

	engine = BacktestEngine(
		strategy=AlwaysExitStrategy(),
		data_loader=DummyLoader(frame),
		initial_capital=100_000,
		risk_manager=StubRiskManager(),
	)

	result = engine.run(["AAPL"], start="2024-01-01", end="2024-01-02")

	assert len(result.trades) == 2
	assert len(result.closed_trades) == 1
	closed = result.closed_trades[0]
	assert closed["symbol"] == "AAPL"
	assert closed["quantity"] == 1
	assert result.net_profit == closed["pnl"]
