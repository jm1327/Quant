#!/usr/bin/env python3
"""Risk and position sizing utilities."""

import math


class RiskManager:
    """Provide position sizing and risk validation helpers."""

    def __init__(self, max_risk_per_trade: float = 0.02, max_position_ratio: float = 0.20):
        self.max_risk_per_trade = max_risk_per_trade
        self.max_position_ratio = max_position_ratio

    def calculate_position_size(self, account_info, signal):
        entry_price = signal["entry_price"]
        stop_loss = signal["stop_loss"]

        if not entry_price or not stop_loss:
            return {
                "quantity": 0,
                "risk_amount": 0,
                "position_value": 0,
                "valid": False,
                "reason": "Missing entry or stop loss price",
            }

        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return {
                "quantity": 0,
                "risk_amount": 0,
                "position_value": 0,
                "valid": False,
                "reason": "Invalid stop loss price",
            }

        net_liquidation = account_info.get("NetLiquidation", 0)
        if net_liquidation <= 0:
            return {
                "quantity": 0,
                "risk_amount": 0,
                "position_value": 0,
                "valid": False,
                "reason": "Net liquidation value is invalid",
            }

        max_risk_amount = net_liquidation * self.max_risk_per_trade
        qty_risk = math.floor(max_risk_amount / risk_per_share)

        available_funds = account_info.get("AvailableFunds", 0)
        buying_power = account_info.get("BuyingPower", 0)
        usable_funds = min(available_funds, buying_power)
        if usable_funds <= 0:
            return {
                "quantity": 0,
                "risk_amount": 0,
                "position_value": 0,
                "valid": False,
                "reason": f"Insufficient capital: available ${available_funds:.2f}, buying power ${buying_power:.2f}",
                "details": {"available_funds": available_funds, "buying_power": buying_power},
            }

        qty_cash = math.floor(usable_funds / entry_price)

        max_position_value = net_liquidation * self.max_position_ratio
        qty_position_ratio = math.floor(max_position_value / entry_price)

        final_quantity = max(1, min(qty_risk, qty_cash, qty_position_ratio))

        if final_quantity <= 0:
            return {
                "quantity": 0,
                "risk_amount": 0,
                "position_value": 0,
                "valid": False,
                "reason": "Calculated position size is zero",
            }

        actual_risk = final_quantity * risk_per_share
        position_value = final_quantity * entry_price

        if position_value > usable_funds:
            return {
                "quantity": 0,
                "risk_amount": 0,
                "position_value": 0,
                "valid": False,
                "reason": f"Required capital ${position_value:.2f} exceeds available funds ${usable_funds:.2f}",
                "details": {
                    "required_funds": position_value,
                    "available_funds": usable_funds,
                    "entry_price": entry_price,
                    "quantity": final_quantity,
                },
            }

        return {
            "quantity": final_quantity,
            "risk_amount": actual_risk,
            "position_value": position_value,
            "valid": True,
            "reason": (
                "Position sizing constraints: "
                f"risk {qty_risk} shares, capital {qty_cash} shares, position ratio {qty_position_ratio} shares"
            ),
            "details": {
                "risk_constraint": qty_risk,
                "cash_constraint": qty_cash,
                "position_ratio_constraint": qty_position_ratio,
                "max_position_value": max_position_value,
                "risk_per_share": risk_per_share,
                "max_risk_amount": max_risk_amount,
                "usable_funds": usable_funds,
            },
        }

    def validate_trade(self, account_info, signal, position_calc):
        risk_ratio = position_calc["risk_amount"] / account_info["NetLiquidation"]
        if risk_ratio > self.max_risk_per_trade * 1.1:
            return {
                "valid": False,
                "reason": f"Risk ratio {risk_ratio:.3f} exceeds limit {self.max_risk_per_trade:.3f}",
            }

        return {"valid": True, "reason": "Risk check passed"}

    def get_stop_loss_price(self, entry_price, action, stop_loss_pct: float = 0.03):
        if action == "BUY":
            return entry_price * (1 - stop_loss_pct)
        if action == "SELL":
            return entry_price * (1 + stop_loss_pct)
        return entry_price
