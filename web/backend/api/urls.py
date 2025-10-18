from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("strategies/", views.StrategyListView.as_view(), name="strategy-list"),
    path("backtests/", views.BacktestView.as_view(), name="backtest"),
    path("simulated-orders/", views.SimulatedOrderListCreateView.as_view(), name="simulated-order"),
    path("portfolio/", views.PortfolioSnapshotView.as_view(), name="portfolio-snapshot"),
]
