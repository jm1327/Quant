#!/usr/bin/env python3
"""Analyze decision logs to understand trading pipeline behaviour."""

import json
import datetime
from pathlib import Path
from collections import defaultdict, Counter
import argparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = PROJECT_ROOT / "trading_logs"


def load_decision_data(date_str=None):
    """加载交易决策数据"""
    logs_dir = LOGS_DIR

    if date_str:
        decision_file = logs_dir / f"trading_decisions_{date_str}.json"
    else:
        decision_files = list(logs_dir.glob("trading_decisions_*.json"))
        if not decision_files:
            print("未找到交易决策文件")
            return None
        decision_file = max(decision_files, key=lambda f: f.stat().st_mtime)
        print(f"分析文件: {decision_file}")

    if not decision_file.exists():
        print(f"文件不存在: {decision_file}")
        return None

    try:
        with open(decision_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None


def analyze_decisions(data):
    """分析决策数据"""
    if not data:
        return

    print(f"\n决策分析报告")
    print("=" * 60)

    total_decisions = len(data)
    decision_types = Counter(item['decision'] for item in data)

    print(f"总决策数: {total_decisions}")
    print(f"决策分布:")
    for decision, count in decision_types.most_common():
        percentage = count / total_decisions * 100
        print(f"   {decision}: {count} ({percentage:.1f}%)")

    print(f"\n📊 按股票分析:")
    symbol_stats = defaultdict(lambda: defaultdict(int))
    for item in data:
        symbol = item['symbol']
        decision = item['decision']
        symbol_stats[symbol][decision] += 1

    for symbol, stats in symbol_stats.items():
        total = sum(stats.values())
        print(f"  {symbol}: 总计 {total}")
        for decision, count in stats.items():
            print(f"    - {decision}: {count}")

    print(f"\n🔍 拒绝原因详细分析:")
    analyze_rejection_reasons(data)

    print(f"\n📈 信心度分析:")
    analyze_confidence_distribution(data)

    print(f"\n📊 MACD数据分析:")
    analyze_macd_data(data)


def analyze_rejection_reasons(data):
    """分析拒绝原因"""
    rejections = [item for item in data if item['decision'].startswith('REJECTED')]

    if not rejections:
        print("   ✅ 没有拒绝的决策")
        return

    print(f"   总拒绝数: {len(rejections)}")

    strategy_rejections = [item for item in rejections if item['decision'] == 'REJECTED_BY_STRATEGY']
    if strategy_rejections:
        print(f"\n   🚫 策略拒绝 ({len(strategy_rejections)}个):")
        for item in strategy_rejections:
            symbol = item['symbol']
            reason = item.get('reason', '未知原因')
            confidence = item.get('signal_analysis', {}).get('confidence', 0)
            print(f"     {symbol}: {reason} (信心度: {confidence:.3f})")

    position_rejections = [item for item in rejections if item['decision'] == 'REJECTED_BY_POSITION_CALC']
    if position_rejections:
        print(f"\n   💰 仓位计算拒绝 ({len(position_rejections)}个):")
        for item in position_rejections:
            symbol = item['symbol']
            reason = item.get('reason', '未知原因')
            print(f"     {symbol}: {reason}")

    risk_rejections = [item for item in rejections if item['decision'] == 'REJECTED_BY_RISK_CHECK']
    if risk_rejections:
        print(f"\n   ⚠️  风险检查拒绝 ({len(risk_rejections)}个):")
        for item in risk_rejections:
            symbol = item['symbol']
            reason = item.get('reason', '未知原因')
            risk_check = item.get('risk_check', {})
            position_calc = item.get('position_calc', {})

            print(f"     {symbol}: {reason}")
            if 'position_value' in position_calc and 'NetLiquidation' in str(risk_check):
                position_value = position_calc['position_value']
                print(f"       持仓价值: ${position_value:,.2f}")


def analyze_confidence_distribution(data):
    """分析信心度分布"""
    confidences = []

    for item in data:
        signal_analysis = item.get('signal_analysis', {})
        if 'confidence' in signal_analysis:
            confidences.append(signal_analysis['confidence'])

    if not confidences:
        print("   ❌ 无信心度数据")
        return

    min_conf = min(confidences)
    max_conf = max(confidences)
    avg_conf = sum(confidences) / len(confidences)

    print(f"   范围: {min_conf:.3f} - {max_conf:.3f}")
    print(f"   平均: {avg_conf:.3f}")

    ranges = [
        (0.0, 0.1, "极低"),
        (0.1, 0.2, "很低"),
        (0.2, 0.3, "低"),
        (0.3, 0.5, "中等"),
        (0.5, 0.8, "高"),
        (0.8, 1.0, "极高"),
    ]

    print(f"   分布:")
    for min_val, max_val, label in ranges:
        count = sum(1 for c in confidences if min_val <= c < max_val)
        if count > 0:
            percentage = count / len(confidences) * 100
            print(f"     {label} ({min_val:.1f}-{max_val:.1f}): {count} ({percentage:.1f}%)")


def analyze_macd_data(data):
    """分析MACD数据"""
    macd_data = []

    for item in data:
        if 'macd_data' in item:
            macd_info = item['macd_data']
            macd_info['symbol'] = item['symbol']
            macd_info['decision'] = item['decision']
            macd_data.append(macd_info)

    if not macd_data:
        print("   ❌ 无MACD数据")
        return

    histograms = [abs(item['hist']) for item in macd_data]

    print(f"   Histogram绝对值统计:")
    print(f"     范围: {min(histograms):.6f} - {max(histograms):.6f}")
    print(f"     平均: {sum(histograms)/len(histograms):.6f}")

    print(f"\n   按决策类型分析:")
    decision_macd = defaultdict(list)
    for item in macd_data:
        decision_macd[item['decision']].append(abs(item['hist']))

    for decision, hist_values in decision_macd.items():
        if hist_values:
            avg_hist = sum(hist_values) / len(hist_values)
            print(f"     {decision}: 平均|hist| = {avg_hist:.6f} ({len(hist_values)}个)")


def show_specific_examples(data, num_examples=5):
    """显示具体的拒绝案例"""
    print(f"\n📝 具体案例分析 (显示前{num_examples}个):")
    print("-" * 60)

    rejections = [item for item in data if item['decision'].startswith('REJECTED')]

    for i, item in enumerate(rejections[:num_examples]):
        print(f"\n案例 {i+1}: {item['symbol']}")
        print(f"  决策: {item['decision']}")
        print(f"  原因: {item.get('reason', '未知')}")

        if 'macd_data' in item:
            macd = item['macd_data']
            print(f"  MACD: {macd['macd']:.6f}")
            print(f"  Signal: {macd['signal']:.6f}")
            print(f"  Histogram: {macd['hist']:.6f}")
            print(f"  价格: ${macd['price']:.2f}")

        if 'signal_analysis' in item:
            signal = item['signal_analysis']
            print(f"  信号: {signal['action']}")
            print(f"  信心度: {signal['confidence']:.3f}")

        if 'position_calc' in item:
            pos = item['position_calc']
            if pos.get('valid'):
                print(f"  计算股数: {pos['quantity']}")
                print(f"  风险金额: ${pos['risk_amount']:.2f}")
                print(f"  持仓价值: ${pos['position_value']:.2f}")


def main():
    parser = argparse.ArgumentParser(description='分析交易决策数据')
    parser.add_argument('--date', help='指定日期 (格式: 20250919)')
    parser.add_argument('--examples', type=int, default=5, help='显示案例数量')
    args = parser.parse_args()

    print("交易决策分析器")
    print("=" * 60)

    data = load_decision_data(args.date)
    if not data:
        return

    analyze_decisions(data)
    show_specific_examples(data, args.examples)

    print(f"\n✅ 分析完成")


if __name__ == "__main__":
    main()
