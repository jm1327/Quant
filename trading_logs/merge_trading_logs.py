"""Merge trading log JSON files into one consolidated JSON file.

Scans the `trading_logs/` folder (non-recursive except for dated subfolders) for
JSON files matching patterns used by the TradingJournal (trades_*, orders_*,
account_*, session_*, trading_decisions_*). Produces
`trading_logs/consolidated_trading_logs.json` with structure:

{
  "trades": { "trades_20250923_230142.json": [...], ... },
  "orders": { ... },
  "account": { ... },
  "session": { ... },
  "trading_decisions": { ... },
  "other": { ... }
}

This is a safe, read-only consolidation (no deletions).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any


LOG_DIR = Path(__file__).resolve().parent
OUT_FILE = LOG_DIR / "consolidated_trading_logs.json"


def load_json_file(p: Path) -> Any:
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"__error__": f"Failed to parse {p.name}: {e}"}


def main() -> int:
    patterns = {
        "trades": "trades_*.json",
        "orders": "orders_*.json",
        "account": "account_*.json",
        "session": "session_*.json",
        "trading_decisions": "trading_decisions_*.json",
    }

    consolidated: Dict[str, Dict[str, Any]] = {k: {} for k in patterns.keys()}
    consolidated["other"] = {}

    # scan top-level JSON files
    for p in sorted(LOG_DIR.glob("*.json")):
        name = p.name
        matched = False
        for key, pat in patterns.items():
            if p.match(pat):
                consolidated[key][name] = load_json_file(p)
                matched = True
                break
        if not matched:
            consolidated["other"][name] = load_json_file(p)

    # also scan dated subfolders one level deep
    for sub in sorted([d for d in LOG_DIR.iterdir() if d.is_dir()]):
        for p in sorted(sub.glob("*.json")):
            name = f"{sub.name}/{p.name}"
            matched = False
            for key, pat in patterns.items():
                if p.match(pat):
                    consolidated[key][name] = load_json_file(p)
                    matched = True
                    break
            if not matched:
                consolidated["other"][name] = load_json_file(p)

    # write output
    try:
        with OUT_FILE.open("w", encoding="utf-8") as f:
            json.dump(consolidated, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to write consolidated file: {e}")
        return 2

    # print a short summary
    counts = {k: len(v) for k, v in consolidated.items()}
    print(f"Wrote consolidated trading logs to: {OUT_FILE}")
    print("Counts by category:")
    for k, v in counts.items():
        print(f"  {k}: {v}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
