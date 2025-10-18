from __future__ import annotations

from decimal import Decimal
from typing import List

from django.utils import timezone
from rest_framework import serializers

from .models import SimulatedOrder

class BacktestRequestSerializer(serializers.Serializer):
    strategy = serializers.CharField(max_length=64)
    symbols = serializers.ListField(
        child=serializers.CharField(max_length=16),
        allow_empty=False,
    )
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    timeframe = serializers.CharField(max_length=8, default="5m")
    initial_capital = serializers.FloatField(required=False)
    commission = serializers.FloatField(required=False)
    data_dir = serializers.CharField(max_length=255, required=False)
    cache_dir = serializers.CharField(max_length=255, required=False)
    write_cache = serializers.BooleanField(required=False, default=True)

    def validate_symbols(self, value: List[str]) -> List[str]:
        cleaned = [symbol.strip().upper() for symbol in value if symbol.strip()]
        if not cleaned:
            raise serializers.ValidationError("At least one symbol is required.")
        return cleaned

    def validate(self, attrs: dict) -> dict:
        start = attrs.get("start")
        end = attrs.get("end")
        if start and end and start > end:
            raise serializers.ValidationError("'start' date must not be after 'end' date.")
        return attrs


class SimulatedOrderCreateSerializer(serializers.Serializer):
    symbol = serializers.CharField(max_length=16)
    side = serializers.ChoiceField(choices=SimulatedOrder.Side.choices)
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=4, coerce_to_string=False)
    orderType = serializers.ChoiceField(
        choices=SimulatedOrder.OrderType.choices,
        default=SimulatedOrder.OrderType.MARKET,
    )
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate_symbol(self, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise serializers.ValidationError("Symbol cannot be blank.")
        return cleaned

    def create(self, validated_data: dict) -> SimulatedOrder:
        price: Decimal = validated_data.pop("price")
        order_type: str = validated_data.pop("orderType")
        notes: str = validated_data.pop("notes", "")

        limit_price = price if order_type != SimulatedOrder.OrderType.MARKET else None
        return SimulatedOrder.objects.create(
            limit_price=limit_price,
            fill_price=price,
            order_type=order_type,
            status=SimulatedOrder.Status.FILLED,
            filled_at=timezone.now(),
            notes=notes,
            **validated_data,
        )


class SimulatedOrderSerializer(serializers.ModelSerializer):
    orderType = serializers.CharField(source="order_type")
    limitPrice = serializers.DecimalField(
        source="limit_price",
        max_digits=12,
        decimal_places=4,
        allow_null=True,
        coerce_to_string=False,
    )
    fillPrice = serializers.DecimalField(
        source="fill_price",
        max_digits=12,
        decimal_places=4,
        allow_null=True,
        coerce_to_string=False,
    )
    createdAt = serializers.DateTimeField(source="created_at")
    filledAt = serializers.DateTimeField(source="filled_at", allow_null=True)

    class Meta:
        model = SimulatedOrder
        fields = [
            "id",
            "symbol",
            "side",
            "quantity",
            "orderType",
            "status",
            "limitPrice",
            "fillPrice",
            "createdAt",
            "filledAt",
            "notes",
        ]
        read_only_fields = fields
