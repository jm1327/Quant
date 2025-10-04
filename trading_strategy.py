#!/usr/bin/env python3
"""Legacy module for backward compatibility.

Re-exports the MACD strategy implementation to avoid breaking older imports.
Going forward, prefer using :mod:`strategies.macd` or ``strategy_loader``.
"""

from quant_trading.strategies.macd import MACDStrategy as TradingStrategy  # noqa: F401

__all__ = ["TradingStrategy", "MACDStrategy"]