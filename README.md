# IBKR TWS Trading Tools

Modular Python tools for connecting to Interactive Brokers TWS and accessing trading data.

## Architecture

The project uses a modular architecture with the following components:

- **`quant_trading.core.ibkr_connection`** – Base connection class for TWS
- **`quant_trading.core.portfolio_tracker`** – Portfolio and account information retrieval
- **`quant_trading.data.market_data_tracker`** – Real-time market data functionality (aggregates 1/3/5/10 minute bars with MACD)

## Prerequisites

### 1. Start TWS and Configure API

1. Launch Interactive Brokers Trader Workstation (TWS)
2. Login to your Paper Trading account
3. Configure API settings:
   - Menu: Edit → Global Configuration → API → Settings
   - Check "Enable ActiveX and Socket Clients"
   - Set Socket Port to 7497 (default for Paper Trading)
   - Ensure "Read-Only API" is unchecked
   - Click OK to save settings

### 2. Install Dependencies

```bash
# Activate virtual environment
venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

## Available Scripts

### Portfolio Tracker

Retrieve portfolio and account information:

```bash
# Activate virtual environment
venv\Scripts\activate

# Run portfolio tracker
python -m quant_trading.core.portfolio_tracker
```

**Features:**
- Account cash balances (by currency)
- Current position information
- Detailed portfolio data including market values and P&L

### Market Data Tracker

Get real-time market data:

```bash
# Activate virtual environment
venv\Scripts\activate

# Run market data tracker
python -m quant_trading.data.market_data_tracker
```

**Features:**
- Real-time price updates
- Bid/Ask spreads
- Volume data
- Last trade information
- 1/3/5/10 minute bar aggregation with MACD(12,26,9)

### Historical Backtesting

Evaluate strategies against stored historical data (defaults to the most recent two years):

```powershell
# Activate virtual environment
venv\Scripts\activate

# Run backtest across default symbol list using MACD strategy
python -m quant_trading.backtesting.run_backtest --timeframe 5m --data-dir market_data
```

**Highlights:**
- Reuses the active strategy defined in `strategy.env` (override via `--strategy`).
- Automatically constrains the sample to the latest two years unless `--start`/`--end` are provided.
- Accepts plain OHLCV CSVs; the backtest engine recalculates MACD/Signal/Hist on the fly to mirror live processing.
- Generates trade blotter, equity curve, and per-symbol summaries directly in the console.
- Supports commission assumptions and custom symbol baskets.
- Pair it with the `fetch_historical_data.py` tool (see below) to populate fresh OHLCV datasets directly from TWS.

### 5-Minute Trade Visualization GUI

Inspect a single symbol's 5-minute candlesticks and trade markers over the past year using the integrated GUI:

```powershell
# Activate virtual environment
venv\Scripts\activate

# Run a backtest (writes cached JSON into backtest_results/<timeframe>/)
python -m quant_trading.backtesting.run_backtest --timeframe 5m --data-dir market_data

# Launch the visualizer (reads cached JSON under backtest_results/)
python -m quant_trading.visualization.trade_visualizer --timeframe 5m --cache-dir backtest_results
```

Features:
- Automatically scans `backtest_results/<timeframe>/` for cached `*_backtest.json` files, with in-app drop-downs to switch timeframe and symbol.
- Uses cached backtest results (candles + trades) stored under `backtest_results/`, so the GUI loads instantly without re-running simulations.
- Overlays long/short entry and exit markers on the candlestick chart (green up arrow = long entry, blue down arrow = long exit, red down arrow = short entry, orange up arrow = short exit).
- Displays period coverage, closed-trade count, net profit, return, and max drawdown in the header for quick performance review.

> **Tip:** Re-run `python -m quant_trading.backtesting.run_backtest` whenever you refresh the CSV data or adjust strategy settings so the visualization reflects the latest trades. Use `--cache-dir` to choose a different output location or `--no-cache` to suppress cache generation.

## Web Dashboard

Control backtests and review performance in a browser. The backend lives under `web/backend/` (Django + Django REST Framework) and the frontend under `web/frontend/` (React + Ant Design).

### Backend (Django API)

```powershell
# Activate your Python environment
venv\Scripts\activate

# Install updated dependencies
pip install -r requirements.txt

# Apply migrations (keeps the DB ready for future models)
python web/backend/manage.py migrate

# Launch the API server on http://127.0.0.1:8000
python web/backend/manage.py runserver
```

Key endpoints:
- `GET /api/strategies/` returns registered strategies and default symbols
- `POST /api/backtests/` triggers the backtest engine; accepts `strategy`, `symbols`, `timeframe`, optional `start`, `end`, `initial_capital`, `commission`, and `write_cache`
- `GET/POST /api/simulated-orders/` persists paper-trade fills so the UI can display a simulated order blotter
- `GET /api/portfolio/` connects to the paper TWS session and returns cash balances, open positions, and market value totals

Adjust runtime settings with environment variables (e.g. `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CORS_ALLOWED_ORIGINS`). Static files collect into `staticfiles/`, SQLite lives at the repo root by default.

### Frontend (React + Ant Design)

```powershell
cd web/frontend
npm install

# Start the Vite dev server (defaults to http://127.0.0.1:5173)
npm run dev
```

During development the Vite proxy forwards `/api` calls to `http://localhost:8000`. Override with a `.env` file beside `package.json`:

```
VITE_API_BASE_URL=http://192.168.0.20:8000
```

The dashboard provides strategy selection, symbol/timeframe configuration, optional date range, and renders summary stats, per-symbol metrics, trade logs, and cache file paths.

Use the navigation toggle to switch between the historical backtest workspace and a simulated trading page where you can log paper trades, manually toggle the IBKR paper connection, inspect real-time portfolio balances (market value, daily P&L, unrealized ratios), and monitor recent activity.

### Historical Data Downloader

Use the bundled script to fetch raw OHLCV bars from IBKR and write them into `market_data/`:

```powershell
python -m quant_trading.tools.fetch_historical_data --symbols SMR --duration "6 M" --bar-size "5 mins"
```

Key flags:
- `--all-hours` includes pre/after-hours quotes (otherwise only regular trading hours).
- `--end-datetime` sets the cutoff timestamp (default: now).
- `--output-dir` changes the save directory (default: `market_data/`).

生成的文件命名为 `<symbol>_<timeframe>_bars_macd.csv`，已自动补充 MACD/Signal/Hist 字段，可直接用于回测。

### Strategy Selection

- Active strategy is defined in `strategy.env` (`ACTIVE_STRATEGY=MACD` by default).
- Additional strategies can be registered under `strategies/` and referenced by name.
- Runtime override is possible via the `ACTIVE_STRATEGY` environment variable.
- Strategy-specific settings are declared with the strategy prefix, e.g. `MACD_TIMEFRAME=3` to trade on 3-minute bars (must match generated aggregations).

## Usage in Your Own Scripts

You can use the base connection class to build your own functionality:

```python
from ibkr_connection import IBKRConnection

class MyTrader(IBKRConnection):
    def on_connection_established(self):
        # Your custom logic here
        pass

# Use it
trader = MyTrader(client_id=123)
if trader.connect_to_tws():
    # Do your work
    trader.disconnect_from_tws()
```

## Sample Output

### Portfolio Tracker
```
============================================================
IBKR PAPER TRADING PORTFOLIO SUMMARY
============================================================

Cash Balances:
------------------------------

CashBalance:
  USD: 995000.00
  
Current Positions:
------------------------------
AAPL (USD): 100 shares, Avg Cost: 150.00

Portfolio Details:
------------------------------

Market Value by Currency:
  USD: 15500.00

Detailed Holdings:
  AAPL (USD): Position 100, Market Value 15500.00, Unrealized P&L 500.00
============================================================
```

### Market Data Tracker
```
Price Update - ReqID: 1, LAST: 150.25
Size Update - ReqID: 1, LAST_SIZE: 100
Price Update - ReqID: 1, BID: 150.20
Price Update - ReqID: 1, ASK: 150.30
```

## Troubleshooting

If connection fails, please check:

1. TWS is running and logged into Paper Trading account
2. API settings are properly configured
3. Port 7497 is available
4. Windows firewall allows TWS connections
5. No other API connections are occupying TWS
6. Each script uses a different client ID to avoid conflicts

## Important Notes

- Scripts use port 7497 for Paper Trading account
- For live trading, change port to 7496 and use with caution
- Each script uses a different client ID to prevent conflicts
- Scripts are read-only and do not execute trades (market data tracker)
- Connection timeout is set to 30 seconds
- All scripts can be extended for custom functionality