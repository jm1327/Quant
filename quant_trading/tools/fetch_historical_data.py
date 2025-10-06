#!/usr/bin/env python3
"""Download historical bar data from IBKR TWS/Gateway and store it as CSV."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from ibapi.contract import Contract

from quant_trading.backtesting.engine import HistoricalDataLoader
from quant_trading.core.ibkr_connection import IBKRConnection
from quant_trading.config.stock_config import STOCKS


def timeframe_to_suffix(bar_size: str) -> str:
    parts = bar_size.strip().lower().split()
    if not parts:
        return bar_size.replace(" ", "")
    if len(parts) == 1:
        return parts[0]
    value, unit = parts[0], parts[1]
    mapping = {
        "sec": "s",
        "secs": "s",
        "second": "s",
        "seconds": "s",
        "min": "m",
        "mins": "m",
        "minute": "m",
        "minutes": "m",
        "hour": "h",
        "hours": "h",
        "day": "d",
        "days": "d",
        "week": "w",
        "weeks": "w",
        "month": "mo",
        "months": "mo",
    }
    for key, suffix in mapping.items():
        if unit.startswith(key):
            return f"{value}{suffix}"
    return bar_size.replace(" ", "")


class HistoricalDataDownloader(IBKRConnection):
    """TWS client dedicated to fetching historical bar data."""

    NON_FATAL_ERROR_CODES = {2176, 366}

    def __init__(
        self,
        *,
        client_id: int,
        output_dir: Path | str,
        duration: str,
        bar_size: str,
        what_to_show: str,
        use_rth: bool,
        format_date: int,
        timeout: int,
    ) -> None:
        super().__init__(client_id=client_id)
        self.output_dir = Path(output_dir)
        self.duration = duration
        self.bar_size = bar_size
        self.what_to_show = what_to_show
        self.use_rth = 1 if use_rth else 0
        self.format_date = format_date
        self.timeout = timeout

        self._next_req_id = 9000
        self._requests: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # IB API callbacks
    # ------------------------------------------------------------------
    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        super().error(reqId, errorCode, errorString, advancedOrderRejectJson)
        if reqId in self._requests:
            if errorCode in self.NON_FATAL_ERROR_CODES:
                # Log as a warning but allow the request to complete successfully.
                request = self._requests[reqId]
                symbol = request.get("symbol", f"reqId={reqId}")
                print(
                    f"Warning for {symbol}: ({errorCode}) {errorString}",
                )
                return
            self._requests[reqId]["error"] = (errorCode, errorString)
            self._requests[reqId]["done"] = True

    def historicalData(self, reqId, bar):  # noqa: N802 (IB API naming)
        request = self._requests.get(reqId)
        if request is None:
            return
        request["bars"].append(
            {
                "datetime": bar.date,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
        )

    def historicalDataEnd(self, reqId, start, end):  # noqa: N802
        request = self._requests.get(reqId)
        if request is None:
            return
        print(f"Historical data for {request['symbol']} completed: {start} -> {end}")
        request["done"] = True

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def fetch_symbol(
        self,
        symbol: str,
        *,
        exchange: str,
        currency: str,
        end_datetime: str,
    ) -> Optional[pd.DataFrame]:
        req_id = self._allocate_req_id()
        self._requests[req_id] = {"symbol": symbol.upper(), "bars": [], "done": False}

        contract = self._create_stock_contract(symbol, exchange, currency)
        print(
            f"Requesting {self.duration} of {self.bar_size} data for {symbol.upper()} (end={end_datetime or 'now'})"
        )
        self.reqHistoricalData(
            req_id,
            contract,
            end_datetime,
            self.duration,
            self.bar_size,
            self.what_to_show,
            self.use_rth,
            self.format_date,
            False,
            [],
        )

        success = self.wait_for_completion(lambda: self._requests[req_id].get("done", False), self.timeout, 1)
        self.cancelHistoricalData(req_id)

        if not success:
            print(f"Timed out waiting for historical data for {symbol.upper()}")
            return None

        if "error" in self._requests[req_id]:
            print(f"Request for {symbol.upper()} ended with error: {self._requests[req_id]['error']}")
            return None

        rows = self._requests[req_id]["bars"]
        if not rows:
            print(f"No historical records returned for {symbol.upper()}")
            return None

        df = pd.DataFrame(rows)
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.dropna(subset=["datetime"]).sort_values("datetime").reset_index(drop=True)
        for column in ["open", "high", "low", "close", "volume"]:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        df = df.dropna(subset=["close"])  # ensure clean series

        df = HistoricalDataLoader._compute_macd(df)
        return df

    def save_dataframe(self, df: pd.DataFrame, symbol: str) -> Path:
        suffix = timeframe_to_suffix(self.bar_size)
        filename = f"{symbol.lower()}_{suffix}_bars_macd.csv"
        output_path = self.output_dir / filename
        self.output_dir.mkdir(parents=True, exist_ok=True)

        df_out = df.copy()
        df_out["datetime"] = df_out["datetime"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df_out.to_csv(output_path, index=False)

        print(f"Saved {len(df_out)} rows to {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _allocate_req_id(self) -> int:
        self._next_req_id += 1
        return self._next_req_id

    @staticmethod
    def _create_stock_contract(symbol: str, exchange: str, currency: str) -> Contract:
        contract = Contract()
        contract.symbol = symbol.upper()
        contract.secType = "STK"
        contract.exchange = exchange
        contract.currency = currency
        contract.primaryExchange = exchange
        return contract


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download historical bar data from IBKR.")
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Symbols to download (e.g. AAPL MSFT). Defaults to stock_config.STOCKS when omitted.",
    )
    parser.add_argument("--duration", default="2 Y", help="Duration string, e.g. '2 Y', '6 M', '10 D'")
    parser.add_argument("--bar-size", default="5 mins", help="Bar size setting, e.g. '5 mins', '10 mins', '1 hour'")
    parser.add_argument("--what-to-show", default="TRADES", help="Data type, e.g. TRADES, MIDPOINT, BID, ASK")
    parser.add_argument("--exchange", default="SMART", help="Exchange routing (default SMART)")
    parser.add_argument("--currency", default="USD", help="Currency code (default USD)")
    parser.add_argument("--end-datetime", default="", help="End datetime in YYYYMMDD HH:MM:SS format (empty = now)")
    parser.add_argument("--client-id", type=int, default=710, help="Client ID for the API session")
    parser.add_argument("--host", default="127.0.0.1", help="TWS / Gateway host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=7497, help="TWS Paper port (default 7497)")
    parser.add_argument("--timeout", type=int, default=180, help="Timeout in seconds for each request")
    parser.add_argument(
        "--all-hours",
        action="store_true",
        help="Include pre/post market data (sets useRTH=0). Default only regular trading hours.",
    )
    parser.add_argument(
        "--output-dir",
        default="market_data",
        help=(
            "Base directory for CSV output (default market_data). Files are organized into a timeframe subfolder, "
            "e.g. market_data/5m."
        ),
    )
    parser.add_argument(
        "--connect-timeout", type=int, default=15, help="Timeout in seconds for establishing the TWS connection"
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.symbols:
        target_symbols = [symbol.upper() for symbol in args.symbols]
    else:
        target_symbols = [symbol.upper() for symbol in STOCKS]
        if not target_symbols:
            print("No symbols provided and stock_config.STOCKS is empty; nothing to download.")
            return 1
        print(
            "No --symbols argument supplied; defaulting to stock_config.STOCKS: "
            + ", ".join(target_symbols)
        )

    timeframe_suffix = timeframe_to_suffix(args.bar_size)
    output_dir = Path(args.output_dir) / timeframe_suffix
    print(f"Writing CSV output to {output_dir}")

    downloader = HistoricalDataDownloader(
        client_id=args.client_id,
        output_dir=output_dir,
        duration=args.duration,
        bar_size=args.bar_size,
        what_to_show=args.what_to_show,
        use_rth=not args.all_hours,
        format_date=1,
        timeout=args.timeout,
    )

    if not downloader.connect_to_tws(args.host, args.port, timeout=args.connect_timeout):
        print("Failed to connect to TWS/Gateway. Ensure it is running and API access is enabled.")
        return 1

    try:
        for symbol in target_symbols:
            df = downloader.fetch_symbol(
                symbol,
                exchange=args.exchange,
                currency=args.currency,
                end_datetime=args.end_datetime,
            )
            if df is not None and not df.empty:
                downloader.save_dataframe(df, symbol)
            time.sleep(1)
    finally:
        downloader.disconnect_from_tws()

    return 0


if __name__ == "__main__":
    sys.exit(main())
