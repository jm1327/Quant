from __future__ import annotations

from typing import Any, Dict


class BaseStrategy:
    """Base class for all trading strategies."""

    name: str = "BASE"

    def __init__(self) -> None:
        self.config: Dict[str, str] = {}

    def analyze_position_and_signal(
        self,
        symbol: str,
        macd: float,
        signal: float,
        hist: float,
        close_price: float,
        current_positions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return a trading decision dictionary compatible with existing workflow."""
        raise NotImplementedError

    def should_trade(self, signal: Dict[str, Any], current_positions: Dict[str, Any]) -> Dict[str, Any]:
        """Decide if the generated signal should result in real trading action."""
        raise NotImplementedError

    def configure(self, config: Dict[str, str]) -> None:
        """Store configuration for the strategy instance."""
        self.config = dict(config or {})
