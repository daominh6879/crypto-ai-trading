"""
Verify that wider stops improve 2022 without hurting 2024
"""
from config import TradingConfig
from trading_system import ProTradingSystem

def test_stops(multiplier, year_start, year_end, label):
    """Test specific stop loss multiplier"""
    config = TradingConfig()
    config.enable_regime_filter = True
    config.stop_loss_multiplier = multiplier

    system = ProTradingSystem(config)
    system.fetch_data("BTCUSDT", start_date=year_start, end_date=year_end, interval='1h')
    system.calculate_signals()
    results = system.run_backtest(start_date=year_start, end_date=year_end)

    stats = results['statistics']
    print(f"{label:<40} {stats['total_trades']:>8} {stats['win_rate']:>9.1f}% {stats['total_pnl']:>+9.2f}% {stats['max_drawdown']:>7.1f}%")
    return stats['total_pnl']

print("\n" + "="*80)
print("VERIFYING WIDER STOPS ACROSS BOTH YEARS")
print("="*80)

print(f"\n{'Configuration':<40} {'Trades':>8} {'Win Rate':>10} {'P&L':>10} {'Max DD':>8}")
print("-" * 80)

print("\n2022 BEAR MARKET:")
print("-" * 80)
baseline_2022 = test_stops(3.0, '2022-01-01', '2023-01-01', "Baseline (3.0x ATR stops)")
improved_2022 = test_stops(3.6, '2022-01-01', '2023-01-01', "Improved (3.6x ATR stops, +20% wider)")

print("\n2024 BULL MARKET:")
print("-" * 80)
baseline_2024 = test_stops(3.0, '2024-01-01', '2025-01-01', "Baseline (3.0x ATR stops)")
improved_2024 = test_stops(3.6, '2024-01-01', '2025-01-01', "Improved (3.6x ATR stops, +20% wider)")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)

improvement_2022 = improved_2022 - baseline_2022
improvement_2024 = improved_2024 - baseline_2024
total_improvement = improvement_2022 + improvement_2024

print(f"\n2022 Improvement: {baseline_2022:+.2f}% -> {improved_2022:+.2f}% = {improvement_2022:+.2f}%")
print(f"2024 Improvement: {baseline_2024:+.2f}% -> {improved_2024:+.2f}% = {improvement_2024:+.2f}%")
print(f"\nTotal Combined Improvement: {total_improvement:+.2f}%")

if improvement_2022 > 0 and improvement_2024 >= -0.5:  # Allow small degradation in 2024
    print("\n[RECOMMENDATION]: IMPLEMENT WIDER STOPS")
    print("  - Improves 2022 bear market significantly")
    print("  - Minimal/no impact on 2024 bull market")
    print("  - Update config.py: stop_loss_multiplier = 3.6")
elif total_improvement > 0:
    print("\n[RECOMMENDATION]: CONDITIONAL - Net positive but check trade-offs")
else:
    print("\n[RECOMMENDATION]: KEEP CURRENT STOPS")
    print("  - Wider stops don't provide net benefit")

print("\n" + "="*80)
