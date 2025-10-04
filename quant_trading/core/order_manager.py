#!/usr/bin/env python3
"""Order management helpers for IBKR executions."""

from ibapi.order import Order
from ibapi.contract import Contract
import time


class OrderManager:
    """Track live IBKR orders and provide helpers for bracket/market submissions."""

    def __init__(self, ibkr_client):
        self.client = ibkr_client
        self.next_order_id = 1
        self.active_orders = {}
        self.positions = {}
        self.has_valid_id = False
        self.last_status = {}

    def set_next_order_id(self, order_id):
        self.next_order_id = order_id
        self.has_valid_id = True
        print(f"[订单管理] 设置起始订单ID: {order_id}")

    def has_next_id(self):
        return self.has_valid_id

    def get_next_order_id(self):
        order_id = self.next_order_id
        self.next_order_id += 1
        print(f"[订单管理] 分配订单ID: {order_id}")
        return order_id

    def create_bracket_order(self, action, quantity, entry_price, stop_loss, take_profit=None):
        parent_order = Order()
        parent_order.orderId = self.get_next_order_id()
        parent_order.action = action
        parent_order.orderType = "LMT"
        parent_order.totalQuantity = quantity
        parent_order.lmtPrice = entry_price
        parent_order.transmit = True

        stop_order = Order()
        stop_order.orderId = self.get_next_order_id()
        stop_order.action = "SELL" if action == "BUY" else "BUY"
        stop_order.orderType = "STP"
        stop_order.totalQuantity = quantity
        stop_order.auxPrice = stop_loss
        stop_order.parentId = parent_order.orderId
        stop_order.transmit = False if take_profit else True
        stop_order.outsideRth = True

        orders = [parent_order, stop_order]

        if take_profit:
            profit_order = Order()
            profit_order.orderId = self.get_next_order_id()
            profit_order.action = "SELL" if action == "BUY" else "BUY"
            profit_order.orderType = "LMT"
            profit_order.totalQuantity = quantity
            profit_order.lmtPrice = take_profit
            profit_order.parentId = parent_order.orderId
            profit_order.transmit = True
            profit_order.outsideRth = True

            orders.append(profit_order)

        return orders

    def place_bracket_order(self, contract: Contract, action, quantity, entry_price, stop_loss, take_profit=None):
        try:
            parent_order = Order()
            parent_order.orderId = self.get_next_order_id()
            parent_order.action = action
            parent_order.orderType = "MKT"
            parent_order.totalQuantity = quantity
            parent_order.tif = "DAY"
            parent_order.transmit = True

            parent_order.eTradeOnly = False
            parent_order.firmQuoteOnly = False
            parent_order.outsideRth = True

            print(f"发送主订单(市价) - ID: {parent_order.orderId}, {action} {quantity} {contract.symbol}")
            self.client.placeOrder(parent_order.orderId, contract, parent_order)

            stop_order_id = None
            if action == "BUY":
                stop_order = Order()
                stop_order.orderId = self.get_next_order_id()
                stop_order.action = "SELL"
                stop_order.orderType = "STP"
                stop_order.totalQuantity = quantity
                stop_order.auxPrice = stop_loss
                stop_order.parentId = parent_order.orderId
                stop_order.tif = "GTC"
                stop_order.transmit = True
                stop_order.outsideRth = True

                print(f"发送止损单 - ID: {stop_order.orderId}, 止损价: ${stop_loss:.2f}")
                self.client.placeOrder(stop_order.orderId, contract, stop_order)
                stop_order_id = stop_order.orderId

                stop_info = {
                    "symbol": contract.symbol,
                    "action": "SELL",
                    "quantity": quantity,
                    "stop_loss": stop_loss,
                    "parent_id": parent_order.orderId,
                    "order_type": "STOP",
                    "status": "SUBMITTED",
                    "timestamp": time.time(),
                }
                self.active_orders[stop_order.orderId] = stop_info
            else:
                print("ℹ️ 做空订单，不下自动止损单，仅依靠策略信号平仓")

            order_info = {
                "symbol": contract.symbol,
                "action": action,
                "quantity": quantity,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "parent_id": parent_order.orderId,
                "stop_id": stop_order_id,
                "status": "SUBMITTED" if action == "SELL" else "BRACKET_SUBMITTED",
                "timestamp": time.time(),
                "order_type": "PARENT",
            }

            self.active_orders[parent_order.orderId] = order_info

            if action == "BUY":
                print(f"[Order] 做多市价单已提交: 主单ID={parent_order.orderId}, 止损单ID={stop_order_id}")
            else:
                print(f"[Order] 做空市价单已提交: 主单ID={parent_order.orderId} (无自动止损单)")

            return order_info

        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"[Error] 市价Bracket订单下单失败: {exc}")
            return None

    def create_market_order(self, action, quantity):
        order = Order()
        order.orderId = self.get_next_order_id()
        order.action = action
        order.orderType = "MKT"
        order.totalQuantity = quantity
        order.transmit = True
        order.tif = "DAY"

        order.eTradeOnly = False
        order.firmQuoteOnly = False
        order.outsideRth = True
        return order

    def place_market_order(self, contract: Contract, action, quantity):
        try:
            order = self.create_market_order(action, quantity)

            order_info = {
                "symbol": contract.symbol,
                "action": action,
                "quantity": quantity,
                "order_type": "MARKET",
                "status": "SUBMITTED",
                "timestamp": time.time(),
            }

            self.client.placeOrder(order.orderId, contract, order)
            self.active_orders[order.orderId] = order_info

            print(f"市价单已提交 - ID: {order.orderId}, {action} {quantity} {contract.symbol}")
            return order_info

        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"市价单下单失败: {exc}")
            return None

    def cancel_order(self, order_id):
        try:
            self.client.cancelOrder(order_id)
            if order_id in self.active_orders:
                self.active_orders[order_id]["status"] = "CANCELLED"
            print(f"订单取消请求已发送 - ID: {order_id}")
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"取消订单失败: {exc}")

    def cancel_all_orders(self):
        for order_id in list(self.active_orders.keys()):
            if self.active_orders[order_id]["status"] not in ["FILLED", "CANCELLED"]:
                self.cancel_order(order_id)

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        if orderId in self.active_orders:
            self.active_orders[orderId]["status"] = status
            self.active_orders[orderId]["filled"] = filled
            self.active_orders[orderId]["remaining"] = remaining
            self.active_orders[orderId]["avg_price"] = avgFillPrice

            symbol = self.active_orders[orderId]["symbol"]

            status_key = f"{orderId}_{status}_{filled}_{avgFillPrice}"
            if status_key not in self.last_status:
                self.last_status[status_key] = True

                if status == "PreSubmitted":
                    print(f"📤 [{symbol}] 订单 {orderId} 已提交，等待执行...")
                elif status == "Submitted":
                    print(f"⏳ [{symbol}] 订单 {orderId} 已确认，等待成交...")
                elif status == "Filled":
                    print(f"✅ [{symbol}] 订单 {orderId} 已成交！")
                    print(f"   成交: {filled}股 @ ${avgFillPrice:.2f}")
                elif status == "Cancelled":
                    print(f"❌ [{symbol}] 订单 {orderId} 已取消")
                elif status == "PendingCancel":
                    print(f"🔄 [{symbol}] 订单 {orderId} 取消中...")
                else:
                    print(f"📊 [{symbol}] 订单 {orderId} 状态: {status}")

    def openOrder(self, orderId, contract, order, orderState):
        if orderId not in self.active_orders:
            self.active_orders[orderId] = {
                "symbol": contract.symbol,
                "action": order.action,
                "quantity": order.totalQuantity,
                "order_type": order.orderType,
                "status": "OPEN",
                "timestamp": time.time(),
            }

    def execDetails(self, reqId, contract, execution):
        order_id = execution.orderId
        symbol = contract.symbol

        print(f"成交回报 - {symbol} 订单ID:{order_id} 价格:${execution.price} 数量:{execution.shares}")

        if symbol not in self.positions:
            self.positions[symbol] = {"position": 0, "avg_cost": 0}

        current_pos = self.positions[symbol]["position"]
        if execution.side == "BOT":
            new_position = current_pos + execution.shares
        else:
            new_position = current_pos - execution.shares

        self.positions[symbol]["position"] = new_position

    def get_positions(self):
        return self.positions.copy()

    def get_active_orders(self):
        return {
            k: v
            for k, v in self.active_orders.items()
            if v["status"] not in ["FILLED", "CANCELLED"]
        }
