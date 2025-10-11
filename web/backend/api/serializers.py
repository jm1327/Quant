from __future__ import annotations

from typing import List

from rest_framework import serializers


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
