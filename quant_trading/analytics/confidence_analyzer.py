#!/usr/bin/env python3
"""Inspect confidence scores derived from MACD histogram magnitudes."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGS_DIR = PROJECT_ROOT / "trading_logs"


def analyze_confidence():
    """分析信心度计算"""
    decision_files = list(LOGS_DIR.glob('trading_decisions_*.json'))
    if not decision_files:
        print("未找到交易决策文件")
        return

    decision_file = max(decision_files, key=lambda f: f.stat().st_mtime)

    with open(decision_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print("信心度计算详细分析")
    print("=" * 60)
    print("公式: confidence = min(0.8, abs(hist) / 0.3)")
    print("=" * 60)

    data_with_confidence = []
    for item in data:
        if 'signal_analysis' in item and 'macd_data' in item:
            confidence = item['signal_analysis'].get('confidence', 0)
            hist = item['macd_data']['hist']
            data_with_confidence.append({
                'symbol': item['symbol'],
                'hist': hist,
                'confidence': confidence,
                'action': item['signal_analysis']['action'],
                'price': item['macd_data']['price']
            })

    data_with_confidence.sort(key=lambda x: x['confidence'], reverse=True)

    print(f"\n信心度最高的10个信号:")
    print("-" * 60)
    for i, item in enumerate(data_with_confidence[:10]):
        calculated_conf = min(0.8, abs(item['hist']) / 0.3)
        print(f"{i+1:2d}. {item['symbol']:5s} - hist={item['hist']:8.6f}, "
              f"计算值={calculated_conf:.3f}, 实际值={item['confidence']:.3f}, "
              f"动作={item['action']}")

    print(f"\n信心度最低的10个信号:")
    print("-" * 60)
    for i, item in enumerate(data_with_confidence[-10:]):
        calculated_conf = min(0.8, abs(item['hist']) / 0.3)
        print(f"{i+1:2d}. {item['symbol']:5s} - hist={item['hist']:8.6f}, "
              f"计算值={calculated_conf:.3f}, 实际值={item['confidence']:.3f}, "
              f"动作={item['action']}")

    print(f"\nHistogram绝对值分布分析:")
    print("-" * 60)

    hist_values = [abs(item['hist']) for item in data_with_confidence]
    hist_values.sort()

    ranges = [
        (0.0, 0.01, "极小"),
        (0.01, 0.03, "很小"),
        (0.03, 0.06, "小"),
        (0.06, 0.15, "中等"),
        (0.15, 0.3, "较大"),
        (0.3, 1.0, "很大"),
    ]

    for min_val, max_val, label in ranges:
        count = sum(1 for h in hist_values if min_val <= h < max_val)
        if count > 0:
            percentage = count / len(hist_values) * 100
            min_conf = min(0.8, min_val / 0.3)
            max_conf = min(0.8, max_val / 0.3)
            print(f"{label:4s} ({min_val:.2f}-{max_val:.2f}): {count:2d}个 ({percentage:4.1f}%) "
                  f"→ 信心度范围: {min_conf:.3f}-{max_conf:.3f}")

    print(f"\n问题分析:")
    print("-" * 60)

    very_small = sum(1 for h in hist_values if h < 0.06)
    print(f"Histogram < 0.06 (信心度<0.2): {very_small}个 ({very_small/len(hist_values)*100:.1f}%)")
    print(f"这意味着MACD和Signal线非常接近，几乎没有明显的金叉/死叉信号")

    tiny = sum(1 for h in hist_values if h < 0.01)
    print(f"Histogram < 0.01 (信心度<0.033): {tiny}个 ({tiny/len(hist_values)*100:.1f}%)")
    print(f"这些可能是噪音信号，不是真正的趋势变化")


if __name__ == "__main__":
    analyze_confidence()
