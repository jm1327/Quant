import json
from pathlib import Path

import pandas as pd

from quant_trading.visualization.trade_visualizer import BacktestCacheRepository


def _write_cache(path: Path, *, timeframe: str) -> None:
	payload = {
		"symbol": "AAPL",
		"timeframe": timeframe,
		"start": "2025-01-01T09:30:00",
		"end": "2025-01-01T09:35:00",
		"initial_capital": 100_000,
		"ending_equity": 100_500,
		"net_profit": 500.0,
		"return_pct": 0.005,
		"max_drawdown": 0.01,
		"total_trades": 1,
		"win_rate": 1.0,
		"closed_trades": [],
		"candles": [
			{
				"datetime": "2025-01-01T09:30:00",
				"open": 100.0,
				"high": 101.0,
				"low": 99.5,
				"close": 100.5,
				"volume": 1_000,
			}
		],
	}
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(payload), encoding="utf-8")


def test_repository_discovers_timeframes_and_symbols(tmp_path):
	root = tmp_path / "backtest_results"
	five_min = root / "5m" / "aapl_5m_backtest.json"
	one_min = root / "1m" / "aapl_1m_backtest.json"
	_write_cache(five_min, timeframe="5m")
	_write_cache(one_min, timeframe="1m")

	repo = BacktestCacheRepository(cache_dir=root, timeframe="5m")

	assert sorted(repo.list_timeframes()) == ["1m", "5m"]
	assert repo.list_symbols() == ["AAPL"]

	repo.set_timeframe("1m")
	assert repo.list_symbols() == ["AAPL"]


def test_load_returns_parsed_dataframe(tmp_path):
	root = tmp_path / "backtest_results"
	cache_path = root / "5m" / "aapl_5m_backtest.json"
	_write_cache(cache_path, timeframe="5m")

	repo = BacktestCacheRepository(cache_dir=root, timeframe="5m")
	cached = repo.load("AAPL")

	assert cached.metadata["symbol"] == "AAPL"
	assert isinstance(cached.prices, pd.DataFrame)
	assert list(cached.prices.columns) == ["Open", "High", "Low", "Close", "Volume"]
	assert not cached.prices.empty
