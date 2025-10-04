#!/usr/bin/env python3
"""
测试修改后的仓位计算逻辑
"""

from quant_trading.core.risk_manager import RiskManager

def test_position_calculation():
    """测试仓位计算"""
    print("测试新的仓位计算逻辑")
    print("=" * 50)

    # 创建风险管理器
    risk_manager = RiskManager()

    # 模拟账户信息
    account_info = {
        'NetLiquidation': 1000000,  # 100万账户净值
        'AvailableFunds': 1000000,
        'BuyingPower': 1000000
    }

    # 测试信号（参考SMR的例子）
    signal = {
        'entry_price': 40.71,
        'stop_loss': 39.49,
        'action': 'BUY'
    }

    # 计算仓位
    result = risk_manager.calculate_position_size(account_info, signal)

    print(f"账户净值: ${account_info['NetLiquidation']:,}")
    print(f"股票价格: ${signal['entry_price']}")
    print(f"止损价格: ${signal['stop_loss']}")
    print(f"每股风险: ${signal['entry_price'] - signal['stop_loss']:.2f}")
    print()

    print("仓位计算结果:")
    print(f"  建议股数: {result['quantity']:,}")
    print(f"  持仓价值: ${result['position_value']:,.2f}")
    print(f"  风险金额: ${result['risk_amount']:,.2f}")
    print(f"  持仓占比: {result['position_value']/account_info['NetLiquidation']*100:.1f}%")
    print(f"  风险占比: {result['risk_amount']/account_info['NetLiquidation']*100:.1f}%")
    print(f"  计算原因: {result['reason']}")

    # 验证风险检查
    print(f"\n风险检查:")
    risk_check = risk_manager.validate_trade(account_info, signal, result)
    print(f"  验证结果: {'通过' if risk_check['valid'] else '失败'}")
    print(f"  检查原因: {risk_check['reason']}")

    # 测试不同价格的股票
    print(f"\n" + "="*50)
    print("测试高价股票 (TSLA $426.61):")

    signal_tsla = {
        'entry_price': 426.61,
        'stop_loss': 413.81,  # 3%止损
        'action': 'SELL'
    }

    result_tsla = risk_manager.calculate_position_size(account_info, signal_tsla)
    print(f"  建议股数: {result_tsla['quantity']:,}")
    print(f"  持仓价值: ${result_tsla['position_value']:,.2f}")
    print(f"  持仓占比: {result_tsla['position_value']/account_info['NetLiquidation']*100:.1f}%")

if __name__ == "__main__":
    test_position_calculation()