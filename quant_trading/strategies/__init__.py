"""Strategy registry and convenience helpers."""

from typing import Dict, Optional, Type

from .base import BaseStrategy
from .macd import MACDStrategy
from .rsi import RSIStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    "MACD": MACDStrategy,
    "RSI": RSIStrategy,
}


def register_strategy(name: str, strategy_cls: Type[BaseStrategy]) -> None:
    """Register a new strategy class under the provided name."""
    STRATEGY_REGISTRY[name.upper()] = strategy_cls


def get_strategy_class(name: str) -> Optional[Type[BaseStrategy]]:
    """Fetch a registered strategy class by name (case-insensitive)."""
    if not name:
        return None
    return STRATEGY_REGISTRY.get(name.upper())
