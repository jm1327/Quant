#!/usr/bin/env python3
"""RSI-based trading strategy implementation."""

from __future__ import annotations

import math
from typing import Dict, Any

import pandas as pd

from .base import BaseStrategy
from quant_trading.config.strategy_defaults import RSI_DEFAULT_CONFIG


class RSIStrategy(BaseStrategy):
    """Trading strategy driven by RSI overbought/oversold levels."""

    name = "RSI"

    def __init__(self) -> None:
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.last_signals: Dict[str, Dict[str, Any]] = {}

        # Apply default configuration values
        self.timeframe_minutes = int(RSI_DEFAULT_CONFIG.get("TIMEFRAME", "5"))
        self.rsi_period = int(RSI_DEFAULT_CONFIG.get("RSI_PERIOD", "14"))
        self.oversold_threshold = float(RSI_DEFAULT_CONFIG.get("OVERSOLD_THRESHOLD", "30"))
        self.overbought_threshold = float(RSI_DEFAULT_CONFIG.get("OVERBOUGHT_THRESHOLD", "70"))
        self.exit_oversold = float(RSI_DEFAULT_CONFIG.get("EXIT_OVERSOLD", "50"))
        self.exit_overbought = float(RSI_DEFAULT_CONFIG.get("EXIT_OVERBOUGHT", "50"))

        # Price history for RSI calculation
        self.price_history: Dict[str, list] = {}

    def configure(self, config: Dict[str, str]) -> None:
        super().configure(config)
        
        config = dict(config or {})

        # Timeframe configuration
        raw_timeframe = config.get("TIMEFRAME") or RSI_DEFAULT_CONFIG.get("TIMEFRAME")
        if raw_timeframe is not None:
            try:
                value = int(str(raw_timeframe).strip())
                if value > 0:
                    self.timeframe_minutes = value
            except (ValueError, TypeError):
                pass
        
        # RSI period configuration
        raw_period = config.get("RSI_PERIOD") or RSI_DEFAULT_CONFIG.get("RSI_PERIOD")
        if raw_period is not None:
            try:
                value = int(str(raw_period).strip())
                if 2 <= value <= 100:
                    self.rsi_period = value
            except (ValueError, TypeError):
                pass
        
        # Threshold configurations
        raw_oversold = config.get("OVERSOLD_THRESHOLD") or RSI_DEFAULT_CONFIG.get("OVERSOLD_THRESHOLD")
        if raw_oversold is not None:
            try:
                value = float(str(raw_oversold).strip())
                if 0 <= value <= 50:
                    self.oversold_threshold = value
            except (ValueError, TypeError):
                pass
        
        raw_overbought = config.get("OVERBOUGHT_THRESHOLD") or RSI_DEFAULT_CONFIG.get("OVERBOUGHT_THRESHOLD")
        if raw_overbought is not None:
            try:
                value = float(str(raw_overbought).strip())
                if 50 <= value <= 100:
                    self.overbought_threshold = value
            except (ValueError, TypeError):
                pass
        
        raw_exit_oversold = config.get("EXIT_OVERSOLD") or RSI_DEFAULT_CONFIG.get("EXIT_OVERSOLD")
        if raw_exit_oversold is not None:
            try:
                value = float(str(raw_exit_oversold).strip())
                if 0 <= value <= 100:
                    self.exit_oversold = value
            except (ValueError, TypeError):
                pass
        
        raw_exit_overbought = config.get("EXIT_OVERBOUGHT") or RSI_DEFAULT_CONFIG.get("EXIT_OVERBOUGHT")
        if raw_exit_overbought is not None:
            try:
                value = float(str(raw_exit_overbought).strip())
                if 0 <= value <= 100:
                    self.exit_overbought = value
            except (ValueError, TypeError):
                pass

    def _calculate_rsi(self, symbol: str, current_price: float) -> float:
        """Calculate RSI for the given symbol and current price."""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(current_price)
        
        # Keep only the required number of prices (period + 1 for price changes)
        if len(self.price_history[symbol]) > self.rsi_period + 1:
            self.price_history[symbol] = self.price_history[symbol][-(self.rsi_period + 1):]
        
        prices = self.price_history[symbol]
        
        # Need at least 2 prices to calculate changes
        if len(prices) < 2:
            return 50.0  # Neutral RSI when insufficient data
        
        # Calculate price changes
        changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        if len(changes) < self.rsi_period:
            # Use available data for partial RSI calculation
            gains = [change for change in changes if change > 0]
            losses = [-change for change in changes if change < 0]
        else:
            # Use only the most recent period
            recent_changes = changes[-self.rsi_period:]
            gains = [change for change in recent_changes if change > 0]
            losses = [-change for change in recent_changes if change < 0]
        
        if not gains and not losses:
            return 50.0
        
        avg_gain = sum(gains) / len(changes) if gains else 0.0
        avg_loss = sum(losses) / len(changes) if losses else 0.0
        
        if avg_loss == 0:
            return 100.0  # No losses, maximum RSI
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    def analyze_position_and_signal(
        self,
        symbol: str,
        macd: float,
        signal: float,
        hist: float,
        close_price: float,
        current_positions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze RSI and generate trading signals."""
        
        # Calculate current RSI
        current_rsi = self._calculate_rsi(symbol, close_price)
        
        # Get current position
        current_qty = current_positions.get("position", 0)
        
        # Initialize signal
        trade_signal = {
            "action": "HOLD",
            "reason": f"RSI: {current_rsi:.2f}",
            "entry_price": close_price,
            "stop_loss": close_price * 0.95 if current_qty >= 0 else close_price * 1.05,
            "confidence": 0.0,
            "trade_type": "OPEN",
            "rsi": current_rsi,
        }
        
        # Entry signals
        if current_qty == 0:  # No position
            if current_rsi <= self.oversold_threshold:
                # RSI oversold - buy signal
                trade_signal.update({
                    "action": "BUY",
                    "reason": f"RSI oversold: {current_rsi:.2f} <= {self.oversold_threshold}",
                    "confidence": min(1.0, (self.oversold_threshold - current_rsi) / 10.0 + 0.5),
                    "stop_loss": close_price * 0.95,
                })
            elif current_rsi >= self.overbought_threshold:
                # RSI overbought - sell signal
                trade_signal.update({
                    "action": "SELL",
                    "reason": f"RSI overbought: {current_rsi:.2f} >= {self.overbought_threshold}",
                    "confidence": min(1.0, (current_rsi - self.overbought_threshold) / 10.0 + 0.5),
                    "stop_loss": close_price * 1.05,
                })
        
        # Exit signals
        elif current_qty > 0:  # Long position
            if current_rsi >= self.exit_oversold:
                # Exit long when RSI recovers from oversold
                trade_signal.update({
                    "action": "SELL",
                    "reason": f"Exit long: RSI recovered to {current_rsi:.2f}",
                    "confidence": 1.0,
                    "trade_type": "CLOSE",
                    "close_quantity": abs(current_qty),
                })
        
        elif current_qty < 0:  # Short position
            if current_rsi <= self.exit_overbought:
                # Exit short when RSI recovers from overbought
                trade_signal.update({
                    "action": "BUY",
                    "reason": f"Exit short: RSI recovered to {current_rsi:.2f}",
                    "confidence": 1.0,
                    "trade_type": "CLOSE",
                    "close_quantity": abs(current_qty),
                })
        
        return trade_signal

    def should_trade(
        self, 
        signal: Dict[str, Any], 
        current_positions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine if we should execute the trade based on confidence and risk management."""
        
        confidence = signal.get("confidence", 0.0)
        action = signal.get("action", "HOLD")
        
        # Always execute exit signals
        if signal.get("trade_type") == "CLOSE":
            return {"should_trade": True, "reason": "Exit signal"}
        
        # Execute entry signals based on confidence threshold
        min_confidence = 0.6  # Require at least 60% confidence for entry
        should_execute = action in {"BUY", "SELL"} and confidence >= min_confidence
        
        reason = f"RSI signal confidence: {confidence:.2f}"
        if not should_execute and action in {"BUY", "SELL"}:
            reason += f" (below threshold {min_confidence})"
        
        return {"should_trade": should_execute, "reason": reason}