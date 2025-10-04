#!/usr/bin/env python3
"""Group generated artifacts into date-based folders for archival."""

import os
import shutil
import re
from datetime import datetime
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def extract_date_from_filename(filename):
    """从文件名中提取日期"""
    for pattern in (r"(\d{8})", r"(\d{4}-\d{2}-\d{2})"):
        match = re.search(pattern, filename)
        if match:
            date_str = match.group(1).replace('-', '')
            try:
                datetime.strptime(date_str, '%Y%m%d')
                return date_str
            except ValueError:
                continue
    return None


def extract_date_from_json_content(filepath):
    """从JSON文件内容中提取日期"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, dict) and 'timestamp' in data:
            timestamp = data['timestamp']
            if isinstance(timestamp, (int, float)):
                dt = datetime.fromtimestamp(timestamp)
                return dt.strftime('%Y%m%d')

        if isinstance(data, list) and data and isinstance(data[0], dict):
            if 'timestamp' in data[0]:
                timestamp = data[0]['timestamp']
                if isinstance(timestamp, (int, float)):
                    dt = datetime.fromtimestamp(timestamp)
                    return dt.strftime('%Y%m%d')

    except Exception as exc:
        print(f"无法解析JSON文件 {filepath}: {exc}")

    return None


def get_file_modification_date(filepath):
    """获取文件修改日期作为备用方案"""
    try:
        timestamp = os.path.getmtime(filepath)
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y%m%d')
    except Exception:
        return None


def organize_files_by_date(base_dir):
    """按日期组织文件"""
    if not base_dir.exists():
        print(f"目录不存在: {base_dir}")
        return

    print(f"组织目录: {base_dir}")

    files = [item for item in base_dir.iterdir() if item.is_file()]

    if not files:
        print("  没有找到文件")
        return

    for file_path in files:
        date_str = extract_date_from_filename(file_path.name)

        if not date_str and file_path.suffix == '.json':
            date_str = extract_date_from_json_content(file_path)

        if not date_str:
            date_str = get_file_modification_date(file_path)

        if date_str:
            date_folder = base_dir / date_str
            date_folder.mkdir(exist_ok=True)

            dest_path = date_folder / file_path.name
            if not dest_path.exists():
                try:
                    shutil.move(str(file_path), str(dest_path))
                    print(f"  移动 {file_path.name} -> {date_str}/{file_path.name}")
                except Exception as exc:
                    print(f"  移动文件失败 {file_path.name}: {exc}")
            else:
                print(f"  文件已存在，跳过: {date_str}/{file_path.name}")
        else:
            print(f"  无法确定日期，跳过: {file_path.name}")


def main():
    """主函数"""
    market_data_dir = PROJECT_ROOT / 'market_data'
    organize_files_by_date(market_data_dir)

    trading_logs_dir = PROJECT_ROOT / 'trading_logs'
    organize_files_by_date(trading_logs_dir)

    print("文件组织完成!")


if __name__ == "__main__":
    main()
