from quant_trading.core.risk_manager import RiskManager


def test_calculate_position_size_returns_positive_quantity():
	manager = RiskManager(max_risk_per_trade=0.02, max_position_ratio=0.5)
	account = {"NetLiquidation": 100_000, "AvailableFunds": 100_000, "BuyingPower": 100_000}
	signal = {"entry_price": 100.0, "stop_loss": 95.0}

	result = manager.calculate_position_size(account, signal)

	assert result["valid"] is True
	assert result["quantity"] == 400
	assert result["position_value"] == 40_000


def test_calculate_position_size_invalid_without_stop_loss():
	manager = RiskManager()
	account = {"NetLiquidation": 50_000, "AvailableFunds": 50_000, "BuyingPower": 50_000}
	signal = {"entry_price": 50.0, "stop_loss": None}

	result = manager.calculate_position_size(account, signal)

	assert result["valid"] is False
	assert result["quantity"] == 0
