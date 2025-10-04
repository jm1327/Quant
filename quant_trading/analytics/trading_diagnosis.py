#!/usr/bin/env python3
"""Diagnose why MACD signals didn't result in trades."""

import pandas as pd
import os
from pathlib import Path

from quant_trading.core.strategy_loader import load_strategy

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MARKET_DATA_DIR = PROJECT_ROOT / "market_data"


def analyze_csv_signals(csv_file):
    """分析CSV文件中的MACD信号"""

    if not os.path.exists(csv_file):
        print(f"文件不存在: {csv_file}")
        return

    try:
        df = pd.read_csv(csv_file)
        print(f"\n[Analysis] 分析文件: {csv_file}")
        print(f"总K线数: {len(df)}")

        warmup_bars = 30
        if len(df) <= warmup_bars:
            print(f"[Warning] K线数量({len(df)}) <= 热身期({warmup_bars})，无交易信号")
            return

        df_valid = df.iloc[warmup_bars:].copy()
        print(f"热身期后有效K线数: {len(df_valid)}")

        strategy_name, _, strategy_config = load_strategy()
        timeframe = strategy_config.get("TIMEFRAME", "5") if strategy_config else "5"
        print(f"使用策略: {strategy_name} (时间框架: {timeframe}m)")
        signals_found = 0
        high_confidence_signals = 0

        print(f"\n[Signal Check] 逐K线分析信号:")
        print("时间\t\t\t动作\t信心度\t原因")
        print("-" * 80)

        for i in range(1, len(df_valid)):
            current = df_valid.iloc[i]
            previous = df_valid.iloc[i - 1]

            if pd.isna(current['macd']) or pd.isna(current['signal']) or pd.isna(current['hist']):
                continue

            if pd.isna(previous['macd']) or pd.isna(previous['signal']) or pd.isna(previous['hist']):
                continue

            symbol = os.path.basename(csv_file).split('_')[0].upper()

            macd = current['macd']
            signal_line = current['signal']
            hist = current['hist']
            close_price = current['close']

            last_hist = previous['hist']
            last_macd = previous['macd']

            if (hist > 0 and last_hist <= 0 and macd > signal_line and macd > last_macd):

                confidence = min(0.8, abs(hist) / 0.5)
                signals_found += 1

                status = "[PASS]" if confidence >= 0.3 else "[REJECT]"
                if confidence >= 0.3:
                    high_confidence_signals += 1

                print(f"{current['datetime']}\tBUY\t{confidence:.3f}\t{status} - MACD金叉 + histogram转正")

            elif (hist < 0 and last_hist >= 0 and macd < signal_line and macd < last_macd):

                confidence = min(0.8, abs(hist) / 0.5)
                signals_found += 1

                status = "[PASS]" if confidence >= 0.3 else "[REJECT]"
                if confidence >= 0.3:
                    high_confidence_signals += 1

                print(f"{current['datetime']}\tSELL\t{confidence:.3f}\t{status} - MACD死叉 + histogram转负")

        print(f"\n[Statistics] 统计结果:")
        print(f"发现信号总数: {signals_found}")
        print(f"高信心度信号(>=0.3): {high_confidence_signals}")
        print(f"被信心度门槛拒绝: {signals_found - high_confidence_signals}")

        if signals_found == 0:
            print("[Result] 未发现任何MACD交叉信号")
        elif high_confidence_signals == 0:
            print("[Result] 所有信号都被信心度门槛拒绝")
        else:
            print(f"[Result] 有 {high_confidence_signals} 个信号应该能触发交易")

    except Exception as e:
        print(f"分析失败: {e}")


def main():
    """主函数"""
    print("[Diagnosis] 交易信号诊断工具")
    print("=" * 60)

    strategy_name, _, strategy_config = load_strategy()
    raw_timeframe = strategy_config.get("TIMEFRAME") if strategy_config else None
    try:
        timeframe_minutes = int(str(raw_timeframe).strip()) if raw_timeframe is not None else 5
    except (ValueError, TypeError):
        timeframe_minutes = 5

    print(f"使用策略: {strategy_name} (时间框架: {timeframe_minutes}m)")

    market_data_dir = MARKET_DATA_DIR

    if not market_data_dir.exists():
        print("❌ market_data目录不存在")
        return

    timeframe_dir = market_data_dir / f"{timeframe_minutes}m"
    if not timeframe_dir.exists():
        print(f"❌ 未找到时间框架目录: {timeframe_dir}")
        return

    pattern = f"*_{timeframe_minutes}m_bars_macd.csv"
    csv_files = list(timeframe_dir.glob(pattern))

    if not csv_files:
        print("[Error] 未找到MACD数据文件")
        return

    print(f"[Files] 找到 {len(csv_files)} 个数据文件")

    for csv_file in csv_files[:3]:
        analyze_csv_signals(csv_file)

    print(f"\n[Suggestions] 建议:")
    print("1. 降低信心度门槛: confidence < 0.3 → confidence < 0.2")
    print("2. 减少热身期: warmup=30 → warmup=20")
    print("3. 放宽信号条件: 去掉macd > last_macd条件")
    print("4. 检查是否启用了交易功能")


if __name__ == "__main__":
    main()
