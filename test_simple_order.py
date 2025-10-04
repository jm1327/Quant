#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最简单的市价单测试（已修复 EtradeOnly 问题）
- 等 nextValidId 后下单
- 显式关闭 eTradeOnly / firmQuoteOnly
- 只下一个市价 BUY 订单（立即成交）
"""

import time
from ibapi.contract import Contract
from ibapi.order import Order
from quant_trading.core.ibkr_connection import IBKRConnection  # 你已有的连接封装

class SimpleOrderTest(IBKRConnection):
    def __init__(self, client_id=986):
        super().__init__(client_id)
        self.next_order_id = None
        self.order_sent = False
        self.last_status = {}  # 记录上次状态，避免重复显示

    # --- 必须拿到这个回调再下单 ---
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.next_order_id = orderId
        print(f"[nextValidId] 起始订单ID: {orderId}")

        # 连接建立 & nextValidId 到手后就下单（只下 1 次）
        if not self.order_sent:
            self.place_simple_market_buy()

    def on_connection_established(self):
        print("连接成功，等待 nextValidId...")

    def create_aapl_contract(self) -> Contract:
        c = Contract()
        c.symbol = "AAPL"
        c.secType = "STK"
        c.currency = "USD"
        c.exchange = "SMART"
        c.primaryExchange = "NASDAQ"   # 避免识别歧义，推荐加上
        return c

    def place_simple_market_buy(self):
        if self.next_order_id is None:
            print("尚未获得 nextValidId，无法下单")
            return

        contract = self.create_aapl_contract()

        order = Order()
        order.action = "BUY"
        order.orderType = "MKT"  # 改为市价单
        order.totalQuantity = 1
        # 市价单不需要lmtPrice
        order.tif = "DAY"

        # --- 关键：显式关闭不被支持的属性 ---
        order.eTradeOnly = False
        order.firmQuoteOnly = False
        # 启用盘前盘后交易
        order.outsideRth = True

        oid = self.next_order_id
        print("准备提交订单：")
        print(f"  ID: {oid}, AAPL BUY 1 @ MARKET (DAY)")
        print("  eTradeOnly=False, firmQuoteOnly=False, outsideRth=True")
        print("  [MKT] 市价单 - 立即按市价成交")
        print("  [RTH] 支持盘前盘后交易")

        try:
            self.placeOrder(oid, contract, order)
            self.order_sent = True
            # 下一次可用的 ID 递增（如果还要继续下第二单）
            self.next_order_id += 1
            print("[Success] 市价单已提交")
        except Exception as e:
            print(f"[Error] 市价单下单失败: {e}")

    # --- 状态与错误回调 ---
    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice,
                    permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        # 检查状态是否有变化，避免重复显示
        status_key = f"{orderId}_{status}_{filled}_{avgFillPrice}"
        if status_key not in self.last_status:
            self.last_status[status_key] = True

            if status == "PreSubmitted":
                print(f"📤 订单 {orderId} 已提交，等待执行...")
            elif status == "Submitted":
                print(f"⏳ 订单 {orderId} 已确认，等待成交...")
            elif status == "Filled":
                print(f"✅ 订单 {orderId} 已成交！")
                print(f"   成交数量: {filled} 股")
                print(f"   成交价格: ${avgFillPrice:.2f}")
            elif status == "Cancelled":
                print(f"❌ 订单 {orderId} 已取消")
            else:
                print(f"📊 订单 {orderId} 状态: {status}")

    def openOrder(self, orderId, contract, order, orderState):
        # openOrder通常在orderStatus之前调用，简化显示
        pass  # 不重复显示，主要信息在orderStatus中显示

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        # 10268 就是 EtradeOnly 不支持；135 是用错了不存在的订单ID
        print(f"❗ 错误 {errorCode}: {errorString}")
        if advancedOrderRejectJson:
            print(f"   详细: {advancedOrderRejectJson}")

def main():
    print("[Test] AAPL 市价买单测试（支持盘前盘后交易）")
    print("[Warning] 请在纸交易环境运行（TWS Paper / IB Gateway Paper）")
    print("[Info] 此订单支持盘前盘后交易（outsideRth=True）")
    print("[MKT] 市价单将立即按当前市价成交")

    ok = input(f"确认以市价买入 1 股 AAPL（立即成交）？(yes/no): ").strip().lower()
    if ok != "yes":
        return

    app = SimpleOrderTest(client_id=986)
    try:
        if app.connect_to_tws(port=7497):
            print("已连接，等待回调…（Ctrl+C 退出）")
            while True:
                time.sleep(1)
        else:
            print("连接失败")
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        app.disconnect_from_tws()
        print("结束")

if __name__ == "__main__":
    main()
