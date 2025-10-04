import pandas as pd

from quant_trading.backtesting.engine import BacktestEngine, HistoricalDataLoader
from quant_trading.core.risk_manager import RiskManager
from quant_trading.strategies.base import BaseStrategy


class DummyStrategy(BaseStrategy):
    def __init__(self) -> None:
        super().__init__()
        self.step = 0

    def analyze_position_and_signal(self, symbol, macd, signal, hist, close_price, current_positions):
        self.step += 1
        if self.step == 1:
            return {
                "action": "BUY",
                "reason": "enter",
                "entry_price": close_price,
                "stop_loss": close_price * 0.98,
                "confidence": 0.5,
                "trade_type": "OPEN",
            }
        if self.step == 3:
            return {
                "action": "SELL",
                "reason": "exit",
                "entry_price": close_price,
                "stop_loss": close_price * 1.02,
                "confidence": 0.5,
                "trade_type": "CLOSE",
                "close_quantity": abs(current_positions.get("position", 0)) or 0,
            }
        return {
            "action": "HOLD",
            "reason": "hold",
            "entry_price": close_price,
            "stop_loss": close_price * 0.98,
            "confidence": 0.0,
            "trade_type": "NONE",
        }

    def should_trade(self, signal, current_positions):
        return {
            "should_trade": signal["action"] != "HOLD",
            "reason": "test",
            "details": {},
        }


def test_backtest_engine_executes_dummy_strategy(tmp_path):
    data = pd.DataFrame(
        [
            {"datetime": "2024-01-02 09:30:00", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000},
            {"datetime": "2024-01-02 09:35:00", "open": 101, "high": 102, "low": 100, "close": 101, "volume": 900},
            {"datetime": "2024-01-02 09:40:00", "open": 102, "high": 103, "low": 101, "close": 102, "volume": 950},
            {"datetime": "2024-01-02 09:45:00", "open": 101, "high": 102, "low": 100, "close": 100, "volume": 1100},
        ]
    )
    csv_path = tmp_path / "test_5m_bars_macd.csv"
    data.to_csv(csv_path, index=False)

    strategy = DummyStrategy()
    loader = HistoricalDataLoader(base_dir=tmp_path, timeframe="5m")
    engine = BacktestEngine(
        strategy,
        data_loader=loader,
        initial_capital=10_000,
        risk_manager=RiskManager(max_risk_per_trade=0.1, max_position_ratio=0.5),
    )

    result = engine.run(["TEST"], start="2023-01-01", end="2024-12-31")

    assert result.net_profit != 0
    assert result.trades
    assert result.closed_trades
    assert result.equity_curve.iloc[-1]["equity"] == result.ending_equity