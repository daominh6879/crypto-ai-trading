"""
Test simple threshold-based regime detection
Conservative approach: Only disable longs in SEVERE bear markets
"""
from config import TradingConfig
from trading_system import ProTradingSystem
from simple_regime_detector import SimpleRegimeDetector

def test_period(start_date: str, end_date: str, label: str):
    """Test a specific period with simple regime detection"""
    print(f"\n{'='*80}")
    print(f"{label}: {start_date} to {end_date}")
    print(f"{'='*80}")

    # Fetch data
    config = TradingConfig()
    system = ProTradingSystem(config)
    print("\n[*] Fetching data...")
    data = system.fetch_data("BTCUSDT", start_date=start_date, end_date=end_date, interval='1h')

    # Detect regime
    print("[*] Detecting market regime...")
    detector = SimpleRegimeDetector(data)
    detector.print_analysis()
    recommended = detector.get_recommended_config()

    # Test 1: Baseline (current config)
    print(f"\n[BASELINE - Standard Config]")
    print("-" * 80)
    config1 = TradingConfig()
    config1.enable_regime_filter = True

    system1 = ProTradingSystem(config1)
    system1.fetch_data("BTCUSDT", start_date=start_date, end_date=end_date, interval='1h')
    system1.calculate_signals()
    results1 = system1.run_backtest(start_date=start_date, end_date=end_date)

    stats1 = results1['statistics']
    print(f"  Trades: {stats1['total_trades']}")
    print(f"  Win Rate: {stats1['win_rate']:.1f}%")
    print(f"  Total P&L: {stats1['total_pnl']:+.2f}%")
    print(f"  Max DD: {stats1['max_drawdown']:.2f}%")

    # Test 2: With regime-adaptive config
    print(f"\n[ADAPTIVE - Regime-Based Config]")
    print("-" * 80)
    if recommended['regime'] == 'SEVERE_BEAR':
        print(f"  [*] SEVERE BEAR detected - Disabling LONG trades")
    else:
        print(f"  [*] Normal conditions - Using standard config")

    config2 = TradingConfig()
    config2.enable_regime_filter = True
    config2.allow_long_trades = recommended['allow_long_trades']
    config2.allow_short_trades = recommended['allow_short_trades']
    config2.stop_loss_multiplier = recommended['stop_loss_multiplier']
    config2.take_profit_1_multiplier = recommended['take_profit_1_multiplier']
    config2.take_profit_2_multiplier = recommended['take_profit_2_multiplier']
    config2.min_bars_gap = recommended['min_bars_gap']

    system2 = ProTradingSystem(config2)
    system2.fetch_data("BTCUSDT", start_date=start_date, end_date=end_date, interval='1h')
    system2.calculate_signals()
    results2 = system2.run_backtest(start_date=start_date, end_date=end_date)

    stats2 = results2['statistics']
    print(f"  Trades: {stats2['total_trades']}")
    print(f"  Win Rate: {stats2['win_rate']:.1f}%")
    print(f"  Total P&L: {stats2['total_pnl']:+.2f}%")
    print(f"  Max DD: {stats2['max_drawdown']:.2f}%")

    # Compare
    print(f"\n[COMPARISON]")
    print("-" * 80)
    pnl_diff = stats2['total_pnl'] - stats1['total_pnl']
    wr_diff = stats2['win_rate'] - stats1['win_rate']
    print(f"  P&L Change: {pnl_diff:+.2f}%")
    print(f"  Win Rate Change: {wr_diff:+.1f}%")
    print(f"  Trade Count Change: {stats2['total_trades'] - stats1['total_trades']:+d}")

    if pnl_diff > 0.5:
        print(f"  Result: [IMPROVEMENT] Adaptive config is better!")
    elif pnl_diff < -0.5:
        print(f"  Result: [WORSE] Baseline config is better")
    else:
        print(f"  Result: [NEUTRAL] No significant difference")

    return {
        'label': label,
        'regime': recommended['regime'],
        'baseline_pnl': stats1['total_pnl'],
        'adaptive_pnl': stats2['total_pnl'],
        'improvement': pnl_diff,
        'baseline_trades': stats1['total_trades'],
        'adaptive_trades': stats2['total_trades'],
    }

print("\n" + "="*80)
print("TESTING SIMPLE REGIME-BASED CONFIGURATION")
print("="*80)

# Test multiple periods
results = []

# 2022 - Severe bear market
result_2022 = test_period('2022-01-01', '2023-01-01', '2022 BEAR MARKET')
results.append(result_2022)

# 2024 - Bull market
result_2024 = test_period('2024-01-01', '2025-01-01', '2024 BULL MARKET')
results.append(result_2024)

# 2020 - Mixed (COVID crash + recovery)
result_2020 = test_period('2020-01-01', '2021-01-01', '2020 MIXED MARKET')
results.append(result_2020)

# Final Summary
print("\n\n" + "="*80)
print("FINAL SUMMARY - SIMPLE REGIME DETECTION")
print("="*80)

print(f"\n{'Year':<20} {'Regime':<15} {'Baseline':<12} {'Adaptive':<12} {'Improvement':<12}")
print("-" * 80)

total_baseline = 0
total_adaptive = 0

for r in results:
    marker = " [BETTER]" if r['improvement'] > 0.5 else ""
    print(f"{r['label']:<20} {r['regime']:<15} {r['baseline_pnl']:+11.2f}% {r['adaptive_pnl']:+11.2f}% {r['improvement']:+11.2f}%{marker}")
    total_baseline += r['baseline_pnl']
    total_adaptive += r['adaptive_pnl']

total_improvement = total_adaptive - total_baseline

print("-" * 80)
print(f"{'TOTAL':<20} {'':<15} {total_baseline:+11.2f}% {total_adaptive:+11.2f}% {total_improvement:+11.2f}%")

print(f"\n[CONCLUSION]")
if total_improvement > 5.0:
    print(f"  Simple regime detection provides SIGNIFICANT improvement: {total_improvement:+.2f}%")
    print(f"  Recommendation: IMPLEMENT in production")
    print(f"  - Automatically disables LONG trades in severe bear markets")
    print(f"  - Keeps standard config in normal conditions")
    print(f"  - Conservative thresholds prevent false positives")
elif total_improvement > 0:
    print(f"  Simple regime detection provides modest improvement: {total_improvement:+.2f}%")
    print(f"  Recommendation: Consider implementing with monitoring")
else:
    print(f"  No improvement from regime detection: {total_improvement:+.2f}%")
    print(f"  Recommendation: Keep current universal config")

print("\n" + "="*80)
