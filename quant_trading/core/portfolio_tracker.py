#!/usr/bin/env python3
"""Portfolio tracking utilities built atop the shared IBKR connection."""

import pandas as pd
from collections import defaultdict

from .ibkr_connection import IBKRConnection


class PortfolioTracker(IBKRConnection):
    """Fetch and summarize portfolio/account state from IBKR."""

    def __init__(self, client_id: int = 1):
        super().__init__(client_id)
        self.portfolio_items = []
        self.account_values = defaultdict(dict)
        self.positions = []
        self.portfolio_downloaded = False
        self.account_downloaded = False
        self.positions_downloaded = False

    def on_connection_established(self):
        print("Requesting account and position data...")
        self.reqAccountUpdates(True, "")
        self.reqPositions()

    def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):
        self.portfolio_items.append(
            {
                "symbol": contract.symbol,
                "secType": contract.secType,
                "currency": contract.currency,
                "exchange": contract.exchange,
                "position": position,
                "marketPrice": marketPrice,
                "marketValue": marketValue,
                "averageCost": averageCost,
                "unrealizedPNL": unrealizedPNL,
                "realizedPNL": realizedPNL,
                "accountName": accountName,
            }
        )

    def updateAccountValue(self, key, val, currency, accountName):
        self.account_values[key][currency] = {"value": val, "accountName": accountName}

    def accountDownloadEnd(self, accountName):
        print(f"Account {accountName} data download completed")
        self.account_downloaded = True

    def portfolioDownloadEnd(self):
        print("Portfolio data download completed")
        self.portfolio_downloaded = True

    def position(self, account, contract, position, avgCost):
        self.positions.append(
            {
                "account": account,
                "symbol": contract.symbol,
                "secType": contract.secType,
                "currency": contract.currency,
                "exchange": contract.exchange,
                "position": position,
                "avgCost": avgCost,
            }
        )

    def positionEnd(self):
        print("Position data download completed")
        self.positions_downloaded = True

    def get_cash_balances(self):
        cash_balances = {}
        for key in ["CashBalance", "TotalCashValue", "AvailableFunds"]:
            if key in self.account_values:
                cash_balances[key] = self.account_values[key]
        return cash_balances

    def get_positions_df(self):
        if not self.positions:
            return pd.DataFrame()
        return pd.DataFrame(self.positions)

    def get_portfolio_df(self):
        if not self.portfolio_items:
            return pd.DataFrame()
        return pd.DataFrame(self.portfolio_items)

    def get_portfolio_summary(self):
        print("\n" + "=" * 60)
        print("IBKR PAPER TRADING PORTFOLIO SUMMARY")
        print("=" * 60)

        print("\nCash Balances:")
        print("-" * 30)
        cash_balances = self.get_cash_balances()
        if cash_balances:
            for key, currencies in cash_balances.items():
                print(f"\n{key}:")
                for currency, info in currencies.items():
                    print(f"  {currency}: {info['value']}")
        else:
            print("No cash balance data available")

        if self.positions:
            print("\nCurrent Positions:")
            print("-" * 30)
            positions_df = self.get_positions_df()
            for _, pos in positions_df.iterrows():
                if float(pos["position"]) != 0:
                    print(
                        f"{pos['symbol']} ({pos['currency']}): {pos['position']} shares, Avg Cost: {pos['avgCost']}"
                    )
        else:
            print("\nNo current positions")

        if self.portfolio_items:
            print("\nPortfolio Details:")
            print("-" * 30)
            portfolio_df = self.get_portfolio_df()
            currency_summary = portfolio_df.groupby("currency")["marketValue"].sum()
            print("\nMarket Value by Currency:")
            for currency, value in currency_summary.items():
                print(f"  {currency}: {value:.2f}")

            print("\nDetailed Holdings:")
            for _, item in portfolio_df.iterrows():
                if float(item["position"]) != 0:
                    print(
                        f"  {item['symbol']} ({item['currency']}): Position {item['position']}, "
                        f"Market Value {item['marketValue']:.2f}, "
                        f"Unrealized P&L {item['unrealizedPNL']:.2f}"
                    )
        else:
            print("\nNo portfolio items")

        print("\n" + "=" * 60)

    def fetch_portfolio_data(self, timeout: int = 30) -> bool:
        if not self.is_connected():
            print("Not connected to TWS")
            return False

        def data_complete():
            return self.account_downloaded and self.positions_downloaded

        success = self.wait_for_completion(data_complete, timeout)

        if success:
            print("Portfolio data fetch completed")
        else:
            print("Portfolio data fetch timed out")

        return success


def main():
    print("IBKR Portfolio Tracker")
    print("Connecting to TWS Paper Trading account...")
    print("Please ensure TWS is running and API is enabled")
    print("TWS Settings: Global Configuration -> API Settings -> Enable ActiveX and Socket Clients")

    tracker = PortfolioTracker(client_id=981)

    try:
        if tracker.connect_to_tws(port=7497):
            if tracker.fetch_portfolio_data():
                tracker.get_portfolio_summary()
            else:
                print("Failed to fetch portfolio data")
        else:
            print("Failed to connect to TWS")

        tracker.disconnect_from_tws()

    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"Error: {exc}")
        print("\nPlease check:")
        print("1. TWS is running")
        print("2. API is enabled")
        print("3. Port 7497 is available (Paper Trading)")
        print("4. Firewall allows connections")


if __name__ == "__main__":
    main()
