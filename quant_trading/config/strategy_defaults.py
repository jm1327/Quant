"""Centralised defaults for global trading parameters and strategies.

The goal of this module is to keep configuration values human-readable while
serving as the single source of truth for the rest of the codebase.  We use
``dataclasses`` to group related settings and then expose convenient dicts and
constants for callers that want either the structured or flat view of the
defaults.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Mapping


# ---------------------------------------------------------------------------
# Global trading defaults shared by every strategy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GlobalDefaults:
    initial_capital: float = 100_000.0
    default_commission: float = 1.0
    max_risk_per_trade: float = 0.02
    max_position_per_symbol: float = 10_000.0
    max_position_ratio: float = 0.20
    default_stop_loss_pct: float = 0.03
    macd_fast_period: int = 12
    macd_slow_period: int = 26
    macd_signal_period: int = 9
    macd_warmup_bars: int = 30
    min_signal_confidence: float = 0.3
    allow_duplicate_trades: bool = False
    account_update_interval: int = 60
    client_id: int = 982


_GLOBAL = GlobalDefaults()
GLOBAL_DEFAULTS: Dict[str, Any] = {key.upper(): value for key, value in asdict(_GLOBAL).items()}

# Legacy-style constants for modules that still import individual names.
INITIAL_CAPITAL: float = _GLOBAL.initial_capital
DEFAULT_COMMISSION: float = _GLOBAL.default_commission
MAX_RISK_PER_TRADE: float = _GLOBAL.max_risk_per_trade
MAX_POSITION_PER_SYMBOL: float = _GLOBAL.max_position_per_symbol
MAX_POSITION_RATIO: float = _GLOBAL.max_position_ratio
DEFAULT_STOP_LOSS_PCT: float = _GLOBAL.default_stop_loss_pct
MACD_FAST_PERIOD: int = _GLOBAL.macd_fast_period
MACD_SLOW_PERIOD: int = _GLOBAL.macd_slow_period
MACD_SIGNAL_PERIOD: int = _GLOBAL.macd_signal_period
MACD_WARMUP_BARS: int = _GLOBAL.macd_warmup_bars
MIN_SIGNAL_CONFIDENCE: float = _GLOBAL.min_signal_confidence
ALLOW_DUPLICATE_TRADES: bool = _GLOBAL.allow_duplicate_trades
ACCOUNT_UPDATE_INTERVAL: int = _GLOBAL.account_update_interval


# ---------------------------------------------------------------------------
# Strategy-specific defaults
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MACDDefaults:
    timeframe: str = "5"


@dataclass(frozen=True)
class RSIDefaults:
    timeframe: str = "5"
    rsi_period: str = "14"
    oversold_threshold: str = "30"
    overbought_threshold: str = "70"
    exit_oversold: str = "50"
    exit_overbought: str = "50"


MACD_DEFAULT_CONFIG: Dict[str, str] = {key.upper(): value for key, value in asdict(MACDDefaults()).items()}
RSI_DEFAULT_CONFIG: Dict[str, str] = {key.upper(): value for key, value in asdict(RSIDefaults()).items()}


# Mapping used by the strategy loader to seed per-strategy configuration.
STRATEGY_DEFAULT_CONFIGS: Mapping[str, Dict[str, str]] = {
    "MACD": MACD_DEFAULT_CONFIG,
    "RSI": RSI_DEFAULT_CONFIG,
}


__all__ = [
    "GLOBAL_DEFAULTS",
    "INITIAL_CAPITAL",
    "DEFAULT_COMMISSION",
    "MAX_RISK_PER_TRADE",
    "MAX_POSITION_PER_SYMBOL",
    "MAX_POSITION_RATIO",
    "DEFAULT_STOP_LOSS_PCT",
    "MACD_FAST_PERIOD",
    "MACD_SLOW_PERIOD",
    "MACD_SIGNAL_PERIOD",
    "MACD_WARMUP_BARS",
    "MIN_SIGNAL_CONFIDENCE",
    "ALLOW_DUPLICATE_TRADES",
    "ACCOUNT_UPDATE_INTERVAL",
    "MACD_DEFAULT_CONFIG",
    "RSI_DEFAULT_CONFIG",
    "STRATEGY_DEFAULT_CONFIGS",
]
