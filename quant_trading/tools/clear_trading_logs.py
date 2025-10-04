#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utilities for purging generated trading logs."""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRADING_LOGS_DIR = PROJECT_ROOT / "trading_logs"


def clear_trading_logs():
    """清除所有交易日志文件"""

    trading_logs_dir = TRADING_LOGS_DIR

    print("🧹 交易日志清理工具")
    print("=" * 50)

    if not trading_logs_dir.exists():
        print("ℹ️  trading_logs目录不存在，无需清理")
        return

    files_to_delete = [file_path for file_path in trading_logs_dir.rglob("*") if file_path.is_file()]

    if not files_to_delete:
        print("ℹ️  trading_logs目录为空，无需清理")
        return

    print(f"📁 发现 {len(files_to_delete)} 个日志文件:")
    for file_path in files_to_delete:
        relative_path = file_path.relative_to(PROJECT_ROOT)
        file_size = file_path.stat().st_size
        print(f"   📄 {relative_path} ({file_size:,} bytes)")

    print("")

    confirm = input("❓ 确认删除所有交易日志文件? (yes/no): ").strip().lower()

    if confirm not in ['yes', 'y']:
        print("❌ 取消清理操作")
        return

    deleted_count = 0
    error_count = 0

    print("\n🗑️  开始清理...")

    for file_path in files_to_delete:
        try:
            file_path.unlink()
            relative_path = file_path.relative_to(PROJECT_ROOT)
            print(f"   ✅ 已删除: {relative_path}")
            deleted_count += 1
        except Exception as exc:
            relative_path = file_path.relative_to(PROJECT_ROOT)
            print(f"   ❌ 删除失败: {relative_path} - {exc}")
            error_count += 1

    try:
        for dir_path in sorted(trading_logs_dir.rglob("*"), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                relative_path = dir_path.relative_to(PROJECT_ROOT)
                print(f"   📁 已删除空目录: {relative_path}")
    except Exception as exc:
        print(f"   ⚠️  删除空目录时出错: {exc}")

    print("\n" + "=" * 50)
    print("✅ 清理完成!")
    print(f"   删除文件: {deleted_count}")
    if error_count > 0:
        print(f"   删除失败: {error_count}")
    remaining = len(list(trading_logs_dir.rglob('*'))) if trading_logs_dir.exists() else 0
    print(f"   剩余文件: {remaining}")


def clear_specific_logs():
    """选择性清除特定类型的日志"""

    trading_logs_dir = TRADING_LOGS_DIR

    if not trading_logs_dir.exists():
        print("ℹ️  trading_logs目录不存在")
        return

    print("\n📋 选择要清除的日志类型:")
    print("1. 交易记录 (trade_*.json)")
    print("2. 账户信息 (account_*.json)")
    print("3. 会话总结 (session_*.json)")
    print("4. 所有日志文件")
    print("5. 取消")

    choice = input("\n请选择 (1-5): ").strip()

    patterns = {
        '1': ["trade_*.json"],
        '2': ["account_*.json"],
        '3': ["session_*.json"],
        '4': ["*.json", "*.log", "*.txt"],
        '5': []
    }

    if choice == '5' or choice not in patterns:
        print("❌ 取消操作")
        return

    files_to_delete = []
    for pattern in patterns[choice]:
        files_to_delete.extend(trading_logs_dir.glob(pattern))

    if not files_to_delete:
        print("ℹ️  未找到匹配的文件")
        return

    print(f"\n📁 找到 {len(files_to_delete)} 个文件:")
    for file_path in files_to_delete:
        print(f"   📄 {file_path.name}")

    confirm = input(f"\n❓ 确认删除这些文件? (yes/no): ").strip().lower()

    if confirm in ['yes', 'y']:
        deleted = 0
        for file_path in files_to_delete:
            try:
                file_path.unlink()
                print(f"   ✅ 已删除: {file_path.name}")
                deleted += 1
            except Exception as exc:
                print(f"   ❌ 删除失败: {file_path.name} - {exc}")

        print(f"\n✅ 完成! 删除了 {deleted} 个文件")
    else:
        print("❌ 取消删除")


def main():
    """主函数"""

    print("🧹 交易日志清理工具")
    print("=" * 50)
    print("1. 清除所有交易日志")
    print("2. 选择性清除")
    print("3. 退出")

    choice = input("\n请选择操作 (1-3): ").strip()

    if choice == '1':
        clear_trading_logs()
    elif choice == '2':
        clear_specific_logs()
    elif choice == '3':
        print("👋 再见!")
    else:
        print("❌ 无效选择")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用户中断操作")
    except Exception as exc:
        print(f"\n❌ 发生错误: {exc}")
