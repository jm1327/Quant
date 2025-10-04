#!/usr/bin/env python3
"""Utilities to purge generated market data files."""

import os
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MARKET_DATA_DIR = PROJECT_ROOT / "market_data"


def clear_market_data():
    """清空market_data目录下的所有CSV文件"""
    data_dir = MARKET_DATA_DIR

    if not data_dir.exists():
        print(f"目录 {data_dir} 不存在")
        return

    files_removed = 0
    for path in data_dir.glob("*.csv"):
        try:
            path.unlink()
            print(f"已删除: {path.name}")
            files_removed += 1
        except Exception as exc:
            print(f"删除失败 {path.name}: {exc}")

    if files_removed == 0:
        print("未找到CSV文件")
    else:
        print(f"\n总共删除了 {files_removed} 个文件")


def clear_entire_directory():
    """删除整个market_data目录"""
    data_dir = MARKET_DATA_DIR

    if not data_dir.exists():
        print(f"目录 {data_dir} 不存在")
        return

    try:
        shutil.rmtree(data_dir)
        print(f"已删除整个目录: {data_dir}")
    except Exception as exc:
        print(f"删除目录失败: {exc}")


if __name__ == "__main__":
    import sys

    print("市场数据清理脚本")
    print("1. 清空CSV文件 (保留目录)")
    print("2. 删除整个目录")

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        clear_entire_directory()
    else:
        clear_market_data()
