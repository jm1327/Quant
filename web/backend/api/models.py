from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils import timezone


class SimulatedOrder(models.Model):
    """Store simulated paper-trading orders for dashboard status."""

    class Side(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"

    class OrderType(models.TextChoices):
        MARKET = "MARKET", "Market"
        LIMIT = "LIMIT", "Limit"
        STOP = "STOP", "Stop"

    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        WORKING = "WORKING", "Working"
        FILLED = "FILLED", "Filled"
        CANCELLED = "CANCELLED", "Cancelled"

    symbol = models.CharField(max_length=16)
    side = models.CharField(max_length=4, choices=Side.choices)
    order_type = models.CharField(max_length=16, choices=OrderType.choices, default=OrderType.MARKET)
    quantity = models.PositiveIntegerField()
    limit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    fill_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.FILLED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    filled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.symbol} {self.side} {self.quantity} ({self.status})"

    def mark_filled(self, price: Decimal | float | None = None) -> None:
        """Utility to mark the order as filled with optional price."""
        self.status = self.Status.FILLED
        if price is not None:
            self.fill_price = price
        if self.filled_at is None:
            self.filled_at = timezone.now()
        self.save(update_fields=["status", "fill_price", "filled_at", "updated_at"])