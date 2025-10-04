#!/usr/bin/env python3
"""Lightweight report over recent trading decisions."""

import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = PROJECT_ROOT / "trading_logs"


def load_latest_decision_data():
    """加载最新的交易决策数据"""
    decision_files = list(LOGS_DIR.glob('trading_decisions_*.json'))
    if not decision_files:
        print("未找到交易决策文件")
        return None

    decision_file = max(decision_files, key=lambda f: f.stat().st_mtime)
    print(f"分析文件: {decision_file}")

    try:
        with open(decision_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None


def main():
    print("交易决策分析器")
    print("=" * 50)

    data = load_latest_decision_data()
    if not data:
        return

    total_decisions = len(data)
    decision_types = Counter(item['decision'] for item in data)

    print(f"\n总决策数: {total_decisions}")
    print("决策分布:")
    for decision, count in decision_types.most_common():
        percentage = count / total_decisions * 100
        print(f"  {decision}: {count} ({percentage:.1f}%)")

    print(f"\n拒绝原因详细分析:")

    rejections = [item for item in data if item['decision'].startswith('REJECTED')]

    if not rejections:
        print("  没有拒绝的决策")
        return

    print(f"  总拒绝数: {len(rejections)}")

    strategy_rejections = [item for item in rejections if item['decision'] == 'REJECTED_BY_STRATEGY']
    if strategy_rejections:
        print(f"\n  策略拒绝 ({len(strategy_rejections)}个):")
        for item in strategy_rejections:
            symbol = item['symbol']
            reason = item.get('reason', '未知原因')
            confidence = item.get('signal_analysis', {}).get('confidence', 0)
            print(f"    {symbol}: {reason} (信心度: {confidence:.3f})")

    risk_rejections = [item for item in rejections if item['decision'] == 'REJECTED_BY_RISK_CHECK']
    if risk_rejections:
        print(f"\n  风险检查拒绝 ({len(risk_rejections)}个):")
        for item in risk_rejections:
            symbol = item['symbol']
            reason = item.get('reason', '未知原因')
            position_calc = item.get('position_calc', {})

            print(f"    {symbol}: {reason}")
            if 'position_value' in position_calc:
                position_value = position_calc['position_value']
                risk_amount = position_calc.get('risk_amount', 0)
                print(f"      持仓价值: ${position_value:,.2f}, 风险金额: ${risk_amount:,.2f}")

    print(f"\n信心度分析:")
    confidences = []

    for item in data:
        signal_analysis = item.get('signal_analysis', {})
        if 'confidence' in signal_analysis:
            confidences.append(signal_analysis['confidence'])

    if confidences:
        min_conf = min(confidences)
        max_conf = max(confidences)
        avg_conf = sum(confidences) / len(confidences)

        print(f"  范围: {min_conf:.3f} - {max_conf:.3f}")
        print(f"  平均: {avg_conf:.3f}")

        low_confidence = [c for c in confidences if c < 0.2]
        print(f"  低于0.2的信心度: {len(low_confidence)}个 ({len(low_confidence)/len(confidences)*100:.1f}%)")

    print(f"\n具体案例 (前3个拒绝案例):")
    print("-" * 50)

    for i, item in enumerate(rejections[:3]):
        print(f"\n案例 {i+1}: {item['symbol']}")
        print(f"  决策: {item['decision']}")
        print(f"  原因: {item.get('reason', '未知')}")

        if 'macd_data' in item:
            macd = item['macd_data']
            print(f"  MACD数据: hist={macd['hist']:.6f}, 价格=${macd['price']:.2f}")

        if 'signal_analysis' in item:
            signal = item['signal_analysis']
            print(f"  信号: {signal['action']}, 信心度: {signal['confidence']:.3f}")

        if 'position_calc' in item and item['position_calc'].get('valid'):
            pos = item['position_calc']
            print(f"  计算: {pos['quantity']}股, 价值${pos['position_value']:,.2f}")

    print(f"\n分析完成")


if __name__ == "__main__":
    main()
