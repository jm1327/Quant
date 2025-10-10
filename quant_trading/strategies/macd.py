#!/usr/bin/env python3
"""MACD-based trading strategy implementation."""

from __future__ import annotations

from typing import Dict, Any

from .base import BaseStrategy
from quant_trading.config.strategy_defaults import MACD_DEFAULT_CONFIG


class MACDStrategy(BaseStrategy):
    """Trading strategy driven by MACD histogram crossovers."""

    name = "MACD"

    def __init__(self) -> None:
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.last_signals: Dict[str, Dict[str, Any]] = {}
        default_timeframe = int(MACD_DEFAULT_CONFIG.get("TIMEFRAME", "5"))
        self.timeframe_minutes = default_timeframe

    def configure(self, config: Dict[str, str]) -> None:
        super().configure(config)
        if not config:
            config = {}
        raw = config.get("TIMEFRAME") or MACD_DEFAULT_CONFIG.get("TIMEFRAME")
        if raw is None:
            return
        try:
            value = int(str(raw).strip())
            if value <= 0:
                raise ValueError
            self.timeframe_minutes = value
        except (ValueError, TypeError):
            pass

    def analyze_macd_signal(
        self,
        symbol: str,
        macd: float,
        signal: float,
        hist: float,
        close_price: float
    ) -> Dict[str, Any]:
        """Produce a raw trading signal based purely on MACD histogram."""
        last_hist = self.last_signals.get(symbol, {}).get('hist', 0)
        last_macd = self.last_signals.get(symbol, {}).get('macd', 0)

        self.last_signals[symbol] = {
            'macd': macd,
            'signal': signal,
            'hist': hist,
            'price': close_price
        }

        if hist > 0 and last_hist <= 0:
            stop_loss_pct = 0.03
            stop_loss = close_price * (1 - stop_loss_pct)
            return {
                'action': 'BUY',
                'reason': 'Histogram转正(金叉)',
                'entry_price': close_price,
                'stop_loss': stop_loss,
                'confidence': min(0.8, abs(hist) / 0.3),
                'trade_type': 'OPEN'
            }

        if hist < 0 and last_hist >= 0:
            stop_loss_pct = 0.03
            stop_loss = close_price * (1 + stop_loss_pct)
            return {
                'action': 'SELL',
                'reason': 'Histogram转负(死叉)',
                'entry_price': close_price,
                'stop_loss': stop_loss,
                'confidence': min(0.8, abs(hist) / 0.3),
                'trade_type': 'OPEN'
            }

        return {
            'action': 'HOLD',
            'reason': '无明确信号',
            'entry_price': close_price,
            'stop_loss': None,
            'confidence': 0.0,
            'trade_type': 'NONE'
        }

    def should_trade(self, signal: Dict[str, Any], current_positions: Dict[str, Any]) -> Dict[str, Any]:
        if signal['confidence'] < 0.1:
            return {
                'should_trade': False,
                'reason': f'信心度过低 ({signal["confidence"]:.2f} < 0.1)',
                'details': {'confidence': signal['confidence'], 'threshold': 0.1}
            }

        current_pos = current_positions.get('position', 0)
        if signal['action'] == 'BUY' and current_pos > 0:
            return {
                'should_trade': False,
                'reason': f'已有多头持仓，不重复买入 (当前持仓: {current_pos}股)',
                'details': {'current_position': current_pos, 'signal_action': signal['action']}
            }
        if signal['action'] == 'SELL' and current_pos < 0:
            return {
                'should_trade': False,
                'reason': f'已有空头持仓，不重复卖出 (当前持仓: {current_pos}股)',
                'details': {'current_position': current_pos, 'signal_action': signal['action']}
            }

        return {
            'should_trade': True,
            'reason': '通过交易条件检查',
            'details': {'confidence': signal['confidence'], 'current_position': current_pos}
        }

    def analyze_position_and_signal(
        self,
        symbol: str,
        macd: float,
        signal: float,
        hist: float,
        close_price: float,
        current_positions: Dict[str, Any]
    ) -> Dict[str, Any]:
        base_signal = self.analyze_macd_signal(symbol, macd, signal, hist, close_price)

        if base_signal['action'] == 'HOLD':
            return base_signal

        current_pos = current_positions.get('position', 0)

        if current_pos == 0:
            return base_signal

        if base_signal['action'] == 'BUY':
            if current_pos < 0:
                return {
                    'action': 'BUY',
                    'reason': f'平空仓({abs(current_pos)}股) + 开多仓 - {base_signal["reason"]}',
                    'entry_price': close_price,
                    'stop_loss': close_price * 0.97,
                    'confidence': base_signal['confidence'],
                    'trade_type': 'CLOSE_AND_REVERSE',
                    'close_quantity': abs(current_pos),
                    'current_position': current_pos
                }
            return {
                'action': 'HOLD',
                'reason': f'已有多头持仓({current_pos}股)，不加仓',
                'entry_price': close_price,
                'stop_loss': None,
                'confidence': 0.0,
                'trade_type': 'NONE'
            }

        if base_signal['action'] == 'SELL':
            if current_pos > 0:
                return {
                    'action': 'SELL',
                    'reason': f'平多仓({current_pos}股) + 开空仓 - {base_signal["reason"]}',
                    'entry_price': close_price,
                    'stop_loss': close_price * 1.03,
                    'confidence': base_signal['confidence'],
                    'trade_type': 'CLOSE_AND_REVERSE',
                    'close_quantity': current_pos,
                    'current_position': current_pos
                }
            return {
                'action': 'HOLD',
                'reason': f'已有空头持仓({abs(current_pos)}股)，不加仓',
                'entry_price': close_price,
                'stop_loss': None,
                'confidence': 0.0,
                'trade_type': 'NONE'
            }

        return base_signal
