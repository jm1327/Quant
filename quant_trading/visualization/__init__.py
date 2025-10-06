"""Visualization utilities for the quant_trading package."""

__all__ = ["TradeVisualizerApp", "launch_trade_visualizer"]


def __getattr__(name: str):
    if name in __all__:
        from .trade_visualizer import TradeVisualizerApp, launch_trade_visualizer

        return {
            "TradeVisualizerApp": TradeVisualizerApp,
            "launch_trade_visualizer": launch_trade_visualizer,
        }[name]
    raise AttributeError(f"module 'quant_trading.visualization' has no attribute {name!r}")
