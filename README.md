# IBKR TWS Trading Tools

Modular Python tools for connecting to Interactive Brokers TWS and accessing trading data.

## Architecture

The project uses a modular architecture with the following components:

- **`ibkr_connection.py`** - Base connection class for TWS
- **`portfolio_tracker.py`** - Portfolio and account information retrieval
- **`market_data_tracker.py`** - Real-time market data functionality (aggregates 1/3/5/10 minute bars with MACD)

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
python portfolio_tracker.py
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
python market_data_tracker.py
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

### Historical Data Downloader

Use the bundled script to fetch raw OHLCV bars from IBKR and write them into `market_data/`:

```powershell
python -m quant_trading.tools.fetch_historical_data --symbols SMR --duration "6 M" --bar-size "5 mins"
```

Key flags:
- `--all-hours` includes pre/after-hours quotes (otherwise仅常规交易时段)。
- `--end-datetime` 指定截止时间（默认当前）。
- `--output-dir` 自定义保存目录（默认 `market_data/`）。

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