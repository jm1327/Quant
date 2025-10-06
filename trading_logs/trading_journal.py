#!/usr/bin/env python3
"""
Shim module to provide stable import path:
    from trading_logs.trading_journal import TradingJournal

Re-exports TradingJournal from the latest dated subpackage.
"""

from importlib import import_module

# Update this variable when a new dated module is added
LATEST_SUBPACKAGE = "20250919"

_module = import_module(f"trading_logs.{LATEST_SUBPACKAGE}.trading_journal")
TradingJournal = getattr(_module, "TradingJournal")

__all__ = ["TradingJournal"]


