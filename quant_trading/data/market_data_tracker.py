#!/usr/bin/env python3
"""
IBKR Market Data Tracker
Real-time market data functionality for IBKR TWS
with multi-timeframe bar aggregation and MACD(12,26,9)
"""

from ibapi.contract import Contract
from quant_trading.core.ibkr_connection import IBKRConnection
from quant_trading.config.stock_config import STOCKS
from quant_trading.core.strategy_loader import load_strategy
from quant_trading.core.risk_manager import RiskManager
from quant_trading.core.order_manager import OrderManager
from trading_logs.trading_journal import TradingJournal
import time
import datetime
import csv
import os
from pathlib import Path
from typing import Dict

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:  # pragma: no cover - fallback for older Python
    ZoneInfo = None


BASE_TIMEFRAMES = [1, 3, 5, 10]  # 单位：分钟
DEFAULT_PRIMARY_TIMEFRAME = 5  # 默认用于交易的主时间框架


# ---------- MACD 递推状态 ----------
class MACDState:
    """维护 MACD(12,26,9) 状态"""

    def __init__(self, warmup=30):
        self.ema12 = None
        self.ema26 = None
        self.signal = None
        self.a12 = 2 / (12 + 1)
        self.a26 = 2 / (26 + 1)
        self.a9 = 2 / (9 + 1)
        self.bar_count = 0
        self.warmup = warmup  # 热身期的bar数

    def on_bar(self, close):
        """传入一根K线收盘价，返回 (macd, signal, hist)"""
        self.bar_count += 1

        if self.ema12 is None:
            # 初始化
            self.ema12 = close
            self.ema26 = close
            macd = 0.0
            self.signal = macd
        else:
            self.ema12 = self.a12 * close + (1 - self.a12) * self.ema12
            self.ema26 = self.a26 * close + (1 - self.a26) * self.ema26
            macd = self.ema12 - self.ema26
            self.signal = self.a9 * macd + (1 - self.a9) * self.signal

        hist = macd - self.signal
        return macd, self.signal, hist

    def is_warmed_up(self):
        return self.bar_count >= self.warmup


# ---------- 主类 ----------
class MarketDataTracker(IBKRConnection):
    """
    Real-time market data tracking functionality for IBKR TWS
    with multi-timeframe bar aggregation and MACD
    """

    def __init__(self, client_id=2, enable_trading=False):
        super().__init__(client_id)

        # L1 实时数据缓存
        self.market_data = {}
        self.active_requests = set()

        # 多股票状态管理 - 基于reqId
        self.req_to_symbol = {}  # reqId -> symbol 映射
        self.current_bars = {}  # reqId -> {timeframe: current_bar}
        self.bars = {}  # reqId -> {timeframe: [bars]}
        self.csv_files = {}  # reqId -> {timeframe: csv_file_path}
        self.macd_states = {}  # reqId -> {timeframe: MACDState}

        # 交易功能模块
        self.enable_trading = enable_trading
        self.strategy_name = None
        self.strategy = None
        self.strategy_config: Dict[str, str] = {}
        self.primary_timeframe = DEFAULT_PRIMARY_TIMEFRAME
        self.risk_manager = None
        self.order_manager = None
        self.trading_journal = None

        if enable_trading:
            try:
                strategy_name, strategy_instance, strategy_config = load_strategy()
            except ValueError as exc:
                print(f"加载交易策略失败: {exc}")
                raise

            self.strategy_name = strategy_name
            self.strategy = strategy_instance
            self.strategy_config = strategy_config
            self.primary_timeframe = self._resolve_primary_timeframe(strategy_config)
            self.risk_manager = RiskManager()
            self.order_manager = OrderManager(self)
            self.trading_journal = TradingJournal()
            print(
                f"交易功能已启用，当前策略: {strategy_name} (时间框架: {self.primary_timeframe}m)"
            )

        if ZoneInfo:
            self.market_timezone = ZoneInfo("America/New_York")
        else:
            try:
                import pytz

                self.market_timezone = pytz.timezone("America/New_York")
            except ImportError:
                self.market_timezone = None

        self.timeframes = sorted(set(BASE_TIMEFRAMES + [self.primary_timeframe]))

    def _setup_stock(self, req_id, symbol):
        """为指定股票设置状态和CSV文件"""
        self.req_to_symbol[req_id] = symbol
        self.current_bars[req_id] = {tf: None for tf in self.timeframes}
        self.bars[req_id] = {tf: [] for tf in self.timeframes}
        self.macd_states[req_id] = {tf: MACDState(warmup=30) for tf in self.timeframes}
        self.csv_files[req_id] = {}

        base_dir = "market_data"
        os.makedirs(base_dir, exist_ok=True)

        for timeframe in self.timeframes:
            timeframe_dir = os.path.join(base_dir, f"{timeframe}m")
            os.makedirs(timeframe_dir, exist_ok=True)

            csv_file = os.path.join(
                timeframe_dir,
                f"{symbol.lower()}_{timeframe}m_bars_macd.csv"
            )
            self.csv_files[req_id][timeframe] = csv_file

            if not os.path.exists(csv_file):
                with open(csv_file, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "datetime", "open", "high", "low", "close", "volume",
                        "macd", "signal", "hist"
                    ])

    def _resolve_primary_timeframe(self, strategy_config: Dict[str, str]) -> int:
        raw = strategy_config.get("TIMEFRAME") if strategy_config else None
        if raw is None:
            return DEFAULT_PRIMARY_TIMEFRAME

        try:
            value = int(str(raw).strip())
            if value <= 0:
                raise ValueError
            return value
        except (ValueError, TypeError):
            print(
                f"⚠️ 策略时间框架配置无效: '{raw}', 将回退到 {DEFAULT_PRIMARY_TIMEFRAME}m"
            )
            return DEFAULT_PRIMARY_TIMEFRAME

    def _get_market_datetime(self):
        """获取当前美东时间，若无法获取，则返回本地时间"""
        if self.market_timezone is not None:
            if ZoneInfo:
                return datetime.datetime.now(self.market_timezone)
            else:
                return datetime.datetime.now(self.market_timezone)
        return datetime.datetime.now()

    def _is_within_trading_window(self, current_dt=None):
        """检查是否处于允许下单的时间窗口（10:00-16:00 ET）"""
        if current_dt is None:
            current_dt = self._get_market_datetime()

        start_time = datetime.time(10, 0)
        end_time = datetime.time(16, 0)
        current_time = current_dt.time()

        return start_time <= current_time < end_time

    def on_connection_established(self):
        print("Ready to request market data")
        if self.enable_trading:
            self.request_account_info()

    def nextValidId(self, orderId):
        """TWS返回下一个有效订单ID"""
        super().nextValidId(orderId)

        if self.enable_trading and hasattr(self, "order_manager"):
            self.order_manager.set_next_order_id(orderId)

    # ---------- TWS 回调 ----------
    def tickPrice(self, reqId, tickType, price, attrib):
        if reqId not in self.market_data:
            self.market_data[reqId] = {}

        tick_types = {
            1: "BID",
            2: "ASK",
            4: "LAST",
            6: "HIGH",
            7: "LOW",
            9: "CLOSE",
        }
        tick_name = tick_types.get(tickType, f"TICK_{tickType}")
        self.market_data[reqId][tick_name] = price

        if tick_name == "LAST" and reqId in self.req_to_symbol:
            try:
                self._update_bar(reqId, price)
            except Exception as e:
                print(f"[WARN] update_bar failed for {self.req_to_symbol[reqId]}: {e}")

        symbol = self.req_to_symbol.get(reqId, f"ReqID_{reqId}")
        print(f"Price Update - {symbol}, {tick_name}: {price}")

    def tickSize(self, reqId, tickType, size):
        if reqId not in self.market_data:
            self.market_data[reqId] = {}

        size_types = {
            0: "BID_SIZE",
            3: "ASK_SIZE",
            5: "LAST_SIZE",
            8: "VOLUME",
        }
        tick_name = size_types.get(tickType, f"SIZE_{tickType}")
        self.market_data[reqId][tick_name] = size

        if tick_name == "LAST_SIZE":
            self._add_volume(reqId, size)

        symbol = self.req_to_symbol.get(reqId, f"ReqID_{reqId}")
        print(f"Size Update - {symbol}, {tick_name}: {size}")

    def tickString(self, reqId, tickType, value):
        """Receive tick string data - 处理RTVolume"""
        if tickType == 48 and reqId in self.req_to_symbol:  # 48 = RT_VOLUME
            try:
                parts = value.split(';')
                if len(parts) >= 2 and parts[0] and parts[1]:
                    price = float(parts[0])
                    size = int(float(parts[1]))

                    symbol = self.req_to_symbol[reqId]
                    print(f"RT Trade - {symbol}, PRICE: {price}, SIZE: {size}")

                    self._update_bar(reqId, price)
                    self._add_volume(reqId, size)

            except (ValueError, IndexError) as e:
                symbol = self.req_to_symbol.get(reqId, f"ReqID_{reqId}")
                print(f"[WARN] Failed to parse RTVolume for {symbol}: {value}, error: {e}")

    # ---------- 5m K线聚合 ----------
    def _get_bar_start(self, timestamp, timeframe):
        """计算给定时间在指定时间框架下的K线开始时间"""
        if timeframe <= 0:
            raise ValueError("timeframe must be positive")

        base_time = timestamp.replace(second=0, microsecond=0)
        minutes_to_subtract = timestamp.minute % timeframe
        return base_time - datetime.timedelta(minutes=minutes_to_subtract)

    def _update_bar(self, req_id, last_price):
        now = datetime.datetime.now()

        for timeframe in self.timeframes:
            bar_start = self._get_bar_start(now, timeframe)
            current_bar = self.current_bars[req_id][timeframe]

            if current_bar is None:
                self.current_bars[req_id][timeframe] = {
                    "datetime": bar_start,
                    "open": last_price,
                    "high": last_price,
                    "low": last_price,
                    "close": last_price,
                    "volume": 0,
                }
                continue

            if bar_start > current_bar["datetime"]:
                self._close_bar(req_id, timeframe)
                self.current_bars[req_id][timeframe] = {
                    "datetime": bar_start,
                    "open": last_price,
                    "high": last_price,
                    "low": last_price,
                    "close": last_price,
                    "volume": 0,
                }
            else:
                current_bar["close"] = last_price
                current_bar["high"] = max(current_bar["high"], last_price)
                current_bar["low"] = min(current_bar["low"], last_price)

    def _add_volume(self, req_id, size):
        if req_id not in self.current_bars:
            return

        for timeframe, bar in self.current_bars[req_id].items():
            if bar is not None:
                bar["volume"] += size

    def _close_bar(self, req_id, timeframe):
        """封口当前Bar，计算MACD并写入CSV"""
        if req_id not in self.current_bars:
            return

        bar_data = self.current_bars[req_id].get(timeframe)
        if not bar_data:
            return

        bar = bar_data.copy()
        symbol = self.req_to_symbol[req_id]

        macd_state = self.macd_states[req_id][timeframe]
        macd, signal, hist = macd_state.on_bar(bar["close"])
        bar["macd"], bar["signal"], bar["hist"] = macd, signal, hist
        self.bars[req_id][timeframe].append(bar)

        warmed = macd_state.is_warmed_up()
        tag = "" if warmed else " (warming up)"

        if warmed:
            print(f"Closed {timeframe}m bar for {symbol}: {bar}")

            if self.enable_trading and timeframe == self.primary_timeframe:
                self._analyze_trading_signal(req_id, symbol, macd, signal, hist, bar["close"])
        else:
            bar_display = bar.copy()
            bar_display.pop('macd', None)
            bar_display.pop('signal', None)
            bar_display.pop('hist', None)
            print(f"Closed {timeframe}m bar for {symbol}{tag}: {bar_display}")

        macd_out = (f"{macd:.6f}", f"{signal:.6f}", f"{hist:.6f}") if warmed else ("", "", "")

        csv_file = self.csv_files[req_id][timeframe]
        with open(csv_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                bar["datetime"].strftime("%Y-%m-%d %H:%M:%S"),
                bar["open"], bar["high"], bar["low"], bar["close"], bar["volume"],
                macd_out[0], macd_out[1], macd_out[2]
            ])

        self.current_bars[req_id][timeframe] = None

    def _close_all_active_bars(self, req_id):
        if req_id not in self.current_bars:
            return

        for timeframe in self.timeframes:
            bar = self.current_bars[req_id].get(timeframe)
            if bar is not None:
                self._close_bar(req_id, timeframe)

    # ---------- 合约 & 订阅 ----------
    def create_stock_contract(self, symbol, exchange="SMART", currency="USD"):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = exchange
        contract.currency = currency

        primary_exchanges = {
            "AAPL": "NASDAQ", "GOOGL": "NASDAQ", "MSFT": "NASDAQ",
            "TSLA": "NASDAQ", "AMZN": "NASDAQ", "META": "NASDAQ",
            "NVDA": "NASDAQ", "NFLX": "NASDAQ", "AMD": "NASDAQ",
            "INTC": "NASDAQ", "NVTS": "NASDAQ", "HIMS": "NASDAQ",
            "SMR": "NYSE", "NBIS": "NASDAQ", "TEM": "NYSE"
        }

        if symbol in primary_exchanges:
            contract.primaryExchange = primary_exchanges[symbol]

        return contract

    def request_market_data(self, contract, req_id=None):
        if req_id is None:
            req_id = len(self.active_requests) + 1

        self._setup_stock(req_id, contract.symbol)

        self.active_requests.add(req_id)
        self.reqMktData(req_id, contract, "233", False, False, [])
        print(f"Requesting market data for {contract.symbol} with ReqID: {req_id}")
        return req_id

    def cancel_market_data(self, req_id):
        if req_id in self.active_requests:
            self.cancelMktData(req_id)
            self.active_requests.remove(req_id)
            print(f"Cancelled market data request: {req_id}")

    def cancel_all_market_data(self):
        for req_id in list(self.active_requests):
            self.cancel_market_data(req_id)

    def get_market_data(self, req_id):
        return self.market_data.get(req_id, {})

    # ---------- 账户信息获取 ----------
    def accountSummary(self, reqId, account, tag, value, currency):
        """接收账户摘要信息"""
        if not hasattr(self, 'account_info'):
            self.account_info = {}

        if tag in ['NetLiquidation', 'AvailableFunds', 'BuyingPower']:
            try:
                self.account_info[tag] = float(value)
                print(f"账户信息 - {tag}: ${float(value):,.2f}")
            except ValueError:
                pass

    def accountSummaryEnd(self, reqId):
        """账户摘要信息接收完毕"""
        print("账户信息更新完成")

        if self.enable_trading and hasattr(self, 'trading_journal'):
            self.trading_journal.log_account_info(self.account_info)

    def request_account_info(self):
        """请求账户信息"""
        print("请求账户信息...")
        self.reqAccountSummary(1001, "All", "NetLiquidation,AvailableFunds,BuyingPower")

    def get_account_info(self):
        """获取当前账户信息"""
        return getattr(self, 'account_info', {})

    # ---------- 交易信号分析 ----------
    def _analyze_trading_signal(self, req_id, symbol, macd, signal, hist, close_price):
        """分析交易信号并执行交易"""
        if not self.enable_trading:
            return

        try:
            current_positions = self.order_manager.get_positions().get(symbol, {'position': 0})

            print(f"\n[{symbol}] MACD数据: macd={macd:.6f}, signal={signal:.6f}, hist={hist:.6f}, price=${close_price:.2f}")

            trading_signal = self.strategy.analyze_position_and_signal(
                symbol, macd, signal, hist, close_price, current_positions
            )

            current_market_dt = self._get_market_datetime()
            decision_log = {
                'symbol': symbol,
                'macd_data': {'macd': macd, 'signal': signal, 'hist': hist, 'price': close_price},
                'current_position': current_positions.get('position', 0),
                'signal_analysis': trading_signal,
                'timestamp': time.time(),
                'market_time': current_market_dt.isoformat(),
                'strategy': self.strategy_name,
                'strategy_timeframe': self.primary_timeframe
            }

            if trading_signal['action'] == 'HOLD':
                decision_log['decision'] = 'NO_SIGNAL'
                decision_log['reason'] = trading_signal['reason']

                if trading_signal.get('trade_type') != 'NONE':
                    print(f"[{symbol}] 决策: {decision_log['decision']} - {trading_signal['reason']}")
                    self._log_trading_decision(decision_log)
                return

            if not self._is_within_trading_window(current_market_dt):
                decision_log['decision'] = 'SKIPPED_OUT_OF_WINDOW'
                decision_log['reason'] = '当前时间不在允许下单窗口(10:00-16:00 ET)'
                decision_log['trading_window'] = {
                    'start': '10:00',
                    'end': '16:00',
                    'timezone': 'America/New_York'
                }
                print(f"[{symbol}] 决策: SKIPPED_OUT_OF_WINDOW - 仅在10:00-16:00 ET间交易 (当前: {current_market_dt.strftime('%Y-%m-%d %H:%M:%S %Z')})")
                self._log_trading_decision(decision_log)
                return

            should_trade_result = self.strategy.should_trade(trading_signal, current_positions)
            decision_log['should_trade_check'] = should_trade_result

            if not should_trade_result['should_trade']:
                decision_log['decision'] = 'REJECTED_BY_STRATEGY'
                decision_log['reason'] = should_trade_result['reason']
                decision_log['details'] = should_trade_result['details']
                print(f"[{symbol}] 决策: {decision_log['decision']} - {should_trade_result['reason']}")
                self._log_trading_decision(decision_log)
                return

            print(f"[{symbol}] 决策: SIGNAL_APPROVED - {trading_signal['action']} ({trading_signal['reason']})")
            decision_log['decision'] = 'SIGNAL_APPROVED'

            account_info = self.get_account_info()
            if not account_info:
                print(f"[{symbol}] 无法获取账户信息，跳过交易")
                return

            position_calc = self._calculate_smart_position_size(account_info, trading_signal, current_positions)
            decision_log['position_calc'] = position_calc

            if not position_calc['valid']:
                decision_log['decision'] = 'REJECTED_BY_POSITION_CALC'
                decision_log['reason'] = position_calc['reason']
                print(f"[{symbol}] 决策: {decision_log['decision']} - {position_calc['reason']}")
                self._log_trading_decision(decision_log)
                return

            risk_check = self.risk_manager.validate_trade(account_info, trading_signal, position_calc)
            decision_log['risk_check'] = risk_check

            if not risk_check['valid']:
                decision_log['decision'] = 'REJECTED_BY_RISK_CHECK'
                decision_log['reason'] = risk_check['reason']
                print(f"[{symbol}] 决策: {decision_log['decision']} - {risk_check['reason']}")
                self._log_trading_decision(decision_log)
                return

            print(f"[{symbol}] 决策: ORDER_SUBMITTED - 尝试提交订单")
            decision_log['decision'] = 'ORDER_SUBMITTED'
            order_result = self._execute_smart_trade(req_id, symbol, trading_signal, position_calc)
            decision_log['order_result'] = order_result

            if order_result:
                decision_log['final_status'] = 'ORDER_SUCCESS'
                print(f"[{symbol}] 决策: ORDER_SUCCESS - 订单提交成功")
                if hasattr(self, 'trading_journal'):
                    self.trading_journal.log_trade_signal(symbol, trading_signal, position_calc, order_result)
            else:
                decision_log['final_status'] = 'ORDER_FAILED'
                decision_log['reason'] = '订单提交失败'
                print(f"[{symbol}] 决策: ORDER_FAILED - 订单提交失败")

            self._log_trading_decision(decision_log)

        except Exception as e:
            decision_log = {
                'symbol': symbol,
                'decision': 'ERROR',
                'reason': str(e),
                'timestamp': time.time()
            }
            print(f"[{symbol}] 决策: ERROR - 交易信号分析失败: {e}")
            self._log_trading_decision(decision_log)

    def _execute_trade(self, req_id, symbol, signal, position_calc):
        """执行交易"""
        try:
            contract = self.create_stock_contract(symbol)

            result = self.order_manager.place_bracket_order(
                contract=contract,
                action=signal['action'],
                quantity=position_calc['quantity'],
                entry_price=signal['entry_price'],
                stop_loss=signal['stop_loss']
            )

            if result:
                print(f"[{symbol}] 交易执行成功:")
                print(f"  动作: {signal['action']}")
                print(f"  数量: {position_calc['quantity']}股")
                print(f"  入场价: ${signal['entry_price']:.2f}")
                print(f"  止损价: ${signal['stop_loss']:.2f}")
                print(f"  风险金额: ${position_calc['risk_amount']:.2f}")
                print(f"  持仓价值: ${position_calc['position_value']:.2f}")

                return result

        except Exception as e:
            print(f"[{symbol}] 交易执行失败: {e}")
            return None

    def _calculate_smart_position_size(self, account_info, signal, current_positions):
        """
        智能仓位计算：区分开仓和平仓逻辑
        """
        trade_type = signal.get('trade_type', 'OPEN')
        current_pos = current_positions.get('position', 0)

        if trade_type == 'CLOSE_AND_REVERSE':
            close_quantity = signal.get('close_quantity', abs(current_pos))

            new_position_calc = self.risk_manager.calculate_position_size(account_info, signal)

            if not new_position_calc['valid']:
                return new_position_calc

            total_quantity = close_quantity + new_position_calc['quantity']
            total_position_value = total_quantity * signal['entry_price']

            new_risk = new_position_calc['risk_amount']

            return {
                'quantity': total_quantity,
                'risk_amount': new_risk,
                'position_value': total_position_value,
                'valid': True,
                'reason': f'平仓{close_quantity}股 + 新开仓{new_position_calc["quantity"]}股',
                'trade_type': trade_type,
                'close_quantity': close_quantity,
                'new_quantity': new_position_calc['quantity']
            }
        else:
            return self.risk_manager.calculate_position_size(account_info, signal)

    def _execute_smart_trade(self, req_id, symbol, signal, position_calc):
        """
        智能交易执行：支持平仓+反手逻辑
        """
        try:
            contract = self.create_stock_contract(symbol)
            trade_type = signal.get('trade_type', 'OPEN')

            if trade_type == 'CLOSE_AND_REVERSE':
                result = self.order_manager.place_bracket_order(
                    contract=contract,
                    action=signal['action'],
                    quantity=position_calc['quantity'],
                    entry_price=signal['entry_price'],
                    stop_loss=signal['stop_loss']
                )

                if result:
                    close_qty = position_calc.get('close_quantity', 0)
                    new_qty = position_calc.get('new_quantity', 0)

                    print(f"[{symbol}] 平仓+反手交易执行成功:")
                    print(f"  动作: {signal['action']} {position_calc['quantity']}股")
                    print(f"  平仓: {close_qty}股, 新开仓: {new_qty}股")
                    print(f"  入场价: ${signal['entry_price']:.2f}")
                    print(f"  止损价: ${signal['stop_loss']:.2f}")
                    print(f"  风险金额: ${position_calc['risk_amount']:.2f}")
                    print(f"  持仓价值: ${position_calc['position_value']:.2f}")

                return result
            else:
                return self._execute_trade(req_id, symbol, signal, position_calc)

        except Exception as e:
            print(f"[{symbol}] 智能交易执行失败: {e}")
            return None

    def _log_trading_decision(self, decision_log):
        """记录交易决策过程"""
        try:
            if not hasattr(self, 'decision_logs'):
                self.decision_logs = []

            self.decision_logs.append(decision_log)

            logs_dir = Path('trading_logs')
            logs_dir.mkdir(exist_ok=True)

            import datetime
            today = datetime.date.today().strftime('%Y%m%d')
            decision_file = logs_dir / f'trading_decisions_{today}.json'

            import json
            with open(decision_file, 'w', encoding='utf-8') as f:
                json.dump(self.decision_logs, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"[Error] 决策日志记录失败: {e}")

    def get_decision_summary(self):
        """获取决策统计概要"""
        if not hasattr(self, 'decision_logs') or not self.decision_logs:
            return {'total': 0}

        decisions = [log['decision'] for log in self.decision_logs]
        summary = {
            'total': len(decisions),
            'no_signal': decisions.count('NO_SIGNAL'),
            'rejected_by_strategy': decisions.count('REJECTED_BY_STRATEGY'),
            'rejected_by_position_calc': decisions.count('REJECTED_BY_POSITION_CALC'),
            'rejected_by_risk_check': decisions.count('REJECTED_BY_RISK_CHECK'),
            'signal_approved': decisions.count('SIGNAL_APPROVED'),
            'order_submitted': decisions.count('ORDER_SUBMITTED'),
            'order_success': decisions.count('ORDER_SUCCESS'),
            'order_failed': decisions.count('ORDER_FAILED'),
            'skipped_out_of_window': decisions.count('SKIPPED_OUT_OF_WINDOW'),
            'errors': decisions.count('ERROR')
        }

        return summary

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        """转发给订单管理器（已优化：避免重复显示）"""
        if self.enable_trading and hasattr(self, 'order_manager'):
            self.order_manager.orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)

            if hasattr(self, 'trading_journal'):
                self.trading_journal.log_order_update(str(orderId), status, filled, avgFillPrice)

    def openOrder(self, orderId, contract, order, orderState):
        """转发给订单管理器（已优化：简化显示）"""
        if self.enable_trading and hasattr(self, 'order_manager'):
            self.order_manager.openOrder(orderId, contract, order, orderState)

    def execDetails(self, reqId, contract, execution):
        """转发给订单管理器"""
        if self.enable_trading and hasattr(self, 'order_manager'):
            self.order_manager.execDetails(reqId, contract, execution)


def main():
    print("IBKR Market Data Tracker - Multi-Stock Edition (1/3/5/10m bars + MACD)")

    stocks = STOCKS

    enable_trading = input("是否启用交易功能? (y/N): ").lower() == 'y'

    if enable_trading:
        print("⚠️  交易功能已启用！程序将根据MACD信号自动下单")
        confirm = input("确认继续? (y/N): ").lower()
        if confirm != 'y':
            print("程序退出")
            return
    else:
        print("仅启用数据收集功能，不会进行交易")

    tracker = MarketDataTracker(client_id=982, enable_trading=enable_trading)

    try:
        print("正在连接到TWS...")
        print("请确认:")
        print("1. TWS或IB Gateway正在运行")
        print("2. API已启用 (Configure → API → Settings)")
        print("3. Socket端口: 7497 (Paper Trading)")
        print("")

        if tracker.connect_to_tws(port=7497):
            for symbol in stocks:
                contract = tracker.create_stock_contract(symbol)
                tracker.request_market_data(contract)

            print(f"Receiving market data for {len(stocks)} stocks: {', '.join(stocks)}")
            print("Press Ctrl+C to stop...")

            while True:
                time.sleep(1)
        else:
            print("Failed to connect to TWS")

        tracker.disconnect_from_tws()

    except KeyboardInterrupt:
        print(f"\nStopping market data tracker...")
        for req_id in list(tracker.current_bars.keys()):
            try:
                tracker._close_all_active_bars(req_id)
            except Exception as e:
                symbol = tracker.req_to_symbol.get(req_id, f"ReqID_{req_id}")
                print(f"[WARN] close_bar on exit failed for {symbol}: {e}")

        tracker.cancel_all_market_data()
        tracker.disconnect_from_tws()

        print(f"Data saved to CSV files:")
        for req_id, timeframe_files in tracker.csv_files.items():
            symbol = tracker.req_to_symbol.get(req_id, f"ReqID_{req_id}")
            for timeframe, csv_file in timeframe_files.items():
                print(f"  {symbol} ({timeframe}m): {csv_file}")

        if enable_trading:
            decision_summary = tracker.get_decision_summary()
            print(f"\n📊 交易决策统计:")
            print(f"  当前策略: {tracker.strategy_name}")
            print(f"  总决策数: {decision_summary.get('total', 0)}")
            print(f"  无信号: {decision_summary.get('no_signal', 0)}")
            print(f"  策略拒绝: {decision_summary.get('rejected_by_strategy', 0)}")
            print(f"  仓位计算拒绝: {decision_summary.get('rejected_by_position_calc', 0)}")
            print(f"  风险检查拒绝: {decision_summary.get('rejected_by_risk_check', 0)}")
            print(f"  信号通过: {decision_summary.get('signal_approved', 0)}")
            print(f"  超出交易时间窗口: {decision_summary.get('skipped_out_of_window', 0)}")
            print(f"  订单提交: {decision_summary.get('order_submitted', 0)}")
            print(f"  订单成功: {decision_summary.get('order_success', 0)}")
            print(f"  订单失败: {decision_summary.get('order_failed', 0)}")
            print(f"  错误: {decision_summary.get('errors', 0)}")

        if enable_trading and hasattr(tracker, 'trading_journal'):
            tracker.trading_journal.generate_session_summary()

    except Exception as e:
        print(f"Error: {e}")

        if enable_trading:
            try:
                decision_summary = tracker.get_decision_summary()
                print(f"\n[Final Stats] 交易决策统计:")
                for key, value in decision_summary.items():
                    print(f"  {key}: {value}")
            except:
                pass

        if enable_trading and hasattr(tracker, 'trading_journal'):
            try:
                tracker.trading_journal.generate_session_summary()
            except:
                pass


if __name__ == "__main__":
    main()
