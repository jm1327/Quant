#!/usr/bin/env python3
"""
交易日志模块
记录交易信号、订单状态、账户信息并生成会话总结
"""

import json
import time
import datetime
from pathlib import Path


class TradingJournal:
    """交易日志记录器"""

    def __init__(self):
        self.session_start = time.time()
        self.session_id = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        # 确保日志目录存在
        self.logs_dir = Path('trading_logs')
        self.logs_dir.mkdir(exist_ok=True)

        # 各类日志存储
        self.trades_log = []          # 交易信号记录
        self.orders_log = []          # 订单状态记录
        self.account_log = []         # 账户信息记录
        self.session_summary = {}     # 会话总结

        print(f"[交易日志] 会话开始: {self.session_id}")

    def log_trade_signal(self, symbol, signal, position_calc, order_result):
        """记录交易信号"""
        trade_record = {
            'timestamp': time.time(),
            'datetime': datetime.datetime.now().isoformat(),
            'symbol': symbol,
            'signal': signal,
            'position_calc': position_calc,
            'order_result': order_result,
            'session_id': self.session_id
        }

        self.trades_log.append(trade_record)

        # 实时保存交易记录
        trades_file = self.logs_dir / f'trades_{self.session_id}.json'
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump(self.trades_log, f, indent=2, ensure_ascii=False)

        print(f"[交易日志] 记录交易信号: {symbol} {signal['action']}")

    def log_order_update(self, order_id, status, filled, avg_price):
        """记录订单状态更新"""
        order_record = {
            'timestamp': time.time(),
            'datetime': datetime.datetime.now().isoformat(),
            'order_id': order_id,
            'status': status,
            'filled': filled,
            'avg_price': avg_price,
            'session_id': self.session_id
        }

        self.orders_log.append(order_record)

        # 实时保存订单记录
        orders_file = self.logs_dir / f'orders_{self.session_id}.json'
        with open(orders_file, 'w', encoding='utf-8') as f:
            json.dump(self.orders_log, f, indent=2, ensure_ascii=False)

        print(f"[交易日志] 记录订单更新: {order_id} -> {status}")

    def log_account_info(self, account_info):
        """记录账户信息"""
        account_record = {
            'timestamp': time.time(),
            'datetime': datetime.datetime.now().isoformat(),
            'account_info': account_info,
            'session_id': self.session_id
        }

        self.account_log.append(account_record)

        # 实时保存账户记录
        account_file = self.logs_dir / f'account_{datetime.date.today().strftime("%Y%m%d")}.json'
        with open(account_file, 'w', encoding='utf-8') as f:
            json.dump(self.account_log, f, indent=2, ensure_ascii=False)

        print(f"[交易日志] 记录账户信息更新")

    def generate_session_summary(self):
        """生成会话总结"""
        session_end = time.time()
        session_duration = session_end - self.session_start

        # 统计交易数据
        total_trades = len(self.trades_log)
        buy_orders = sum(1 for trade in self.trades_log if trade['signal'].get('action') == 'BUY')
        sell_orders = sum(1 for trade in self.trades_log if trade['signal'].get('action') == 'SELL')

        # 统计订单状态
        filled_orders = sum(1 for order in self.orders_log if order['status'] == 'Filled')
        cancelled_orders = sum(1 for order in self.orders_log if order['status'] == 'Cancelled')

        # 计算交易品种
        symbols_traded = list(set(trade['symbol'] for trade in self.trades_log))

        # 生成总结
        summary = {
            'session_id': self.session_id,
            'start_time': datetime.datetime.fromtimestamp(self.session_start).isoformat(),
            'end_time': datetime.datetime.fromtimestamp(session_end).isoformat(),
            'duration_seconds': round(session_duration, 2),
            'duration_formatted': self._format_duration(session_duration),
            'trading_stats': {
                'total_signals': total_trades,
                'buy_signals': buy_orders,
                'sell_signals': sell_orders,
                'symbols_traded': symbols_traded,
                'unique_symbols': len(symbols_traded)
            },
            'order_stats': {
                'total_orders': len(self.orders_log),
                'filled_orders': filled_orders,
                'cancelled_orders': cancelled_orders,
                'fill_rate': round(filled_orders / len(self.orders_log) * 100, 2) if self.orders_log else 0
            },
            'account_updates': len(self.account_log)
        }

        self.session_summary = summary

        # 保存会话总结
        summary_file = self.logs_dir / f'session_{self.session_id}.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # 打印总结
        self._print_summary(summary)

        return summary

    def _format_duration(self, seconds):
        """格式化时间长度"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)

        if hours > 0:
            return f"{hours}小时{minutes}分{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分{seconds}秒"
        else:
            return f"{seconds}秒"

    def _print_summary(self, summary):
        """打印会话总结"""
        print("\n" + "="*60)
        print("📊 交易会话总结")
        print("="*60)
        print(f"🕐 会话时间: {summary['start_time']} - {summary['end_time']}")
        print(f"⏱️  持续时长: {summary['duration_formatted']}")
        print(f"🎯 交易信号: {summary['trading_stats']['total_signals']} 个")
        print(f"   📈 买入信号: {summary['trading_stats']['buy_signals']} 个")
        print(f"   📉 卖出信号: {summary['trading_stats']['sell_signals']} 个")
        print(f"📦 交易品种: {summary['trading_stats']['unique_symbols']} 个 {summary['trading_stats']['symbols_traded']}")
        print(f"📋 订单状态:")
        print(f"   ✅ 已成交: {summary['order_stats']['filled_orders']} 个")
        print(f"   ❌ 已取消: {summary['order_stats']['cancelled_orders']} 个")
        print(f"   📊 成交率: {summary['order_stats']['fill_rate']}%")
        print(f"💰 账户更新: {summary['account_updates']} 次")
        print("="*60)
        print(f"📄 详细日志保存在: trading_logs/session_{self.session_id}.json")
        print("="*60)

    def get_session_stats(self):
        """获取当前会话统计"""
        return {
            'session_id': self.session_id,
            'trades_count': len(self.trades_log),
            'orders_count': len(self.orders_log),
            'account_updates': len(self.account_log),
            'session_duration': time.time() - self.session_start
        }

    def export_to_csv(self):
        """导出交易记录到CSV文件"""
        if not self.trades_log:
            print("[交易日志] 无交易记录可导出")
            return

        import csv

        csv_file = self.logs_dir / f'trades_export_{self.session_id}.csv'

        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # 写入表头
            writer.writerow([
                'timestamp', 'datetime', 'symbol', 'action', 'confidence',
                'entry_price', 'stop_loss', 'quantity', 'trade_type', 'reason'
            ])

            # 写入数据
            for trade in self.trades_log:
                signal = trade['signal']
                position = trade.get('position_calc', {})

                writer.writerow([
                    trade['timestamp'],
                    trade['datetime'],
                    trade['symbol'],
                    signal.get('action', ''),
                    signal.get('confidence', 0),
                    signal.get('entry_price', 0),
                    signal.get('stop_loss', 0),
                    position.get('quantity', 0),
                    signal.get('trade_type', ''),
                    signal.get('reason', '')
                ])

        print(f"[交易日志] 交易记录已导出到: {csv_file}")
        return csv_file