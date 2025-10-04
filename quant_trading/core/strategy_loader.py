#!/usr/bin/env python3
"""Helpers to load strategies configured via environment or .env files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from quant_trading.strategies import BaseStrategy, get_strategy_class, STRATEGY_REGISTRY

DEFAULT_STRATEGY_NAME = "MACD"
ENV_FILE = Path(__file__).resolve().parents[2] / "strategy.env"


def _parse_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def get_active_strategy_name(default: str = DEFAULT_STRATEGY_NAME, file_env: Optional[Dict[str, str]] = None) -> str:
    name = os.environ.get("ACTIVE_STRATEGY")
    if name:
        return name.strip()

    if file_env is None:
        file_env = _parse_env_file(ENV_FILE)
    if "ACTIVE_STRATEGY" in file_env:
        return file_env["ACTIVE_STRATEGY"]

    return default


def _extract_strategy_config(strategy_name: str, env_map: Dict[str, str]) -> Dict[str, str]:
    config: Dict[str, str] = {}
    prefix = f"{strategy_name.upper()}_"

    for key, value in env_map.items():
        upper_key = key.upper()
        if upper_key.startswith(prefix):
            config_key = upper_key[len(prefix):]
            config[config_key] = value

    return config


def load_strategy(strategy_name: Optional[str] = None) -> Tuple[str, BaseStrategy, Dict[str, str]]:
    file_env = _parse_env_file(ENV_FILE)
    selected_name = strategy_name or get_active_strategy_name(file_env=file_env)
    strategy_cls = get_strategy_class(selected_name)
    if strategy_cls is None:
        available = ", ".join(sorted(get_strategy_class_name_list()))
        raise ValueError(
            f"Unknown strategy '{selected_name}'. Available strategies: {available or 'None'}"
        )

    config: Dict[str, str] = {}
    config.update(_extract_strategy_config(selected_name, file_env))
    config.update(_extract_strategy_config(selected_name, dict(os.environ)))

    strategy_instance = strategy_cls()
    if hasattr(strategy_instance, "configure"):
        strategy_instance.configure(config)

    return selected_name, strategy_instance, config


def get_strategy_class_name_list() -> List[str]:
    return list(STRATEGY_REGISTRY.keys())
