"""
Test dynamic regime-based configuration adjustments
Detect market regime and apply optimal config for each period
"""
import pandas as pd
from config import TradingConfig
from trading_system import ProTradingSystem
from market_regime_detector import MarketRegimeDetector

def test_with_dynamic_config(start_date: str, end_date: str, label: str):
    """
    Test strategy with dynamic regime detection and config adjustment

    Args:
        start_date: Start date for backtest
        end_date: End date for backtest
        label: Label for this test period
    """
    print(f"\n{'='*80}")
    print(f"{label}: {start_date} to {end_date}")
    print(f"{'='*80}")

    # Step 1: Fetch data
    config = TradingConfig()
    system = ProTradingSystem(config)
    print("\n[*] Fetching data...")
    data = system.fetch_data("BTCUSDT", start_date=start_date, end_date=end_date, interval='1h')

    # Step 2: Detect market regime (using entire period)
    print("[*] Detecting market regime...")
    detector = MarketRegimeDetector(data)
    regime, confidence, metrics = detector.detect_regime()  # Use entire period

    # Print analysis
    detector.print_analysis()

    # Step 3: Get recommended config
    recommended_config = detector.get_recommended_config()

    # Step 4: Run baseline backtest (current config)
    print(f"\n[BASELINE TEST - Standard Config]")
    print("-" * 80)
    config_baseline = TradingConfig()
    config_baseline.enable_regime_filter = True  # ADX 20-30 filter

    system_baseline = ProTradingSystem(config_baseline)
    system_baseline.fetch_data("BTCUSDT", start_date=start_date, end_date=end_date, interval='1h')
    system_baseline.calculate_signals()
    results_baseline = system_baseline.run_backtest(start_date=start_date, end_date=end_date)

    stats_baseline = results_baseline['statistics']
    print(f"  Trades: {stats_baseline['total_trades']}")
    print(f"  Win Rate: {stats_baseline['win_rate']:.1f}%")
    print(f"  Total P&L: {stats_baseline['total_pnl']:+.2f}%")
    print(f"  Max DD: {stats_baseline['max_drawdown']:.2f}%")
    print(f"  Profit Factor: {stats_baseline['profit_factor']:.2f}")

    # Step 5: Run optimized backtest (regime-adapted config)
    print(f"\n[OPTIMIZED TEST - Regime-Adapted Config]")
    print("-" * 80)
    print(f"  Applying {recommended_config['strategy_bias']} configuration...")

    config_optimized = TradingConfig()
    config_optimized.enable_regime_filter = True
    config_optimized.stop_loss_multiplier = recommended_config['stop_loss_multiplier']
    config_optimized.take_profit_1_multiplier = recommended_config['take_profit_1_multiplier']
    config_optimized.take_profit_2_multiplier = recommended_config['take_profit_2_multiplier']
    config_optimized.min_bars_gap = recommended_config['min_bars_gap']

    # Apply long/short trade filtering based on regime
    config_optimized.allow_long_trades = recommended_config['allow_long_trades']
    config_optimized.allow_short_trades = recommended_config['allow_short_trades']

    if not recommended_config['allow_long_trades']:
        print("  [!] Applying SHORT-ONLY mode (LONG trades disabled)")

    system_optimized = ProTradingSystem(config_optimized)
    system_optimized.fetch_data("BTCUSDT", start_date=start_date, end_date=end_date, interval='1h')
    system_optimized.calculate_signals()
    results_optimized = system_optimized.run_backtest(start_date=start_date, end_date=end_date)

    stats_optimized = results_optimized['statistics']
    print(f"  Trades: {stats_optimized['total_trades']}")
    print(f"  Win Rate: {stats_optimized['win_rate']:.1f}%")
    print(f"  Total P&L: {stats_optimized['total_pnl']:+.2f}%")
    print(f"  Max DD: {stats_optimized['max_drawdown']:.2f}%")
    print(f"  Profit Factor: {stats_optimized['profit_factor']:.2f}")

    # Step 6: Compare results
    print(f"\n[IMPROVEMENT ANALYSIS]")
    print("-" * 80)
    pnl_improvement = stats_optimized['total_pnl'] - stats_baseline['total_pnl']
    wr_improvement = stats_optimized['win_rate'] - stats_baseline['win_rate']

    print(f"  P&L Improvement: {pnl_improvement:+.2f}%")
    print(f"  Win Rate Improvement: {wr_improvement:+.1f}%")

    if pnl_improvement > 0:
        print(f"  Result: [BETTER] Dynamic config improved performance")
    else:
        print(f"  Result: [NO IMPROVEMENT] Baseline config was better")

    return {
        'regime': regime,
        'confidence': confidence,
        'baseline_pnl': stats_baseline['total_pnl'],
        'optimized_pnl': stats_optimized['total_pnl'],
        'improvement': pnl_improvement,
        'baseline_trades': stats_baseline['total_trades'],
        'optimized_trades': stats_optimized['total_trades'],
        'recommended_config': recommended_config
    }

print("\n" + "="*80)
print("TESTING DYNAMIC REGIME-BASED CONFIGURATION")
print("="*80)

# Test on multiple periods
results = []

# 2022 Bear Market
result_2022 = test_with_dynamic_config('2022-01-01', '2023-01-01', '2022 BEAR MARKET')
results.append(('2022', result_2022))

# 2024 Bull Market
result_2024 = test_with_dynamic_config('2024-01-01', '2025-01-01', '2024 BULL MARKET')
results.append(('2024', result_2024))

# Summary
print("\n\n" + "="*80)
print("SUMMARY - DYNAMIC CONFIG PERFORMANCE")
print("="*80)

print(f"\n{'Year':<8} {'Regime':<12} {'Conf.':<8} {'Baseline':<12} {'Optimized':<12} {'Improvement':<12}")
print("-" * 80)

total_improvement = 0
for year, result in results:
    regime_str = f"{result['regime']}"
    conf_str = f"{result['confidence']*100:.1f}%"
    baseline_str = f"{result['baseline_pnl']:+.2f}%"
    optimized_str = f"{result['optimized_pnl']:+.2f}%"
    improvement_str = f"{result['improvement']:+.2f}%"

    marker = " [BETTER]" if result['improvement'] > 0 else ""
    print(f"{year:<8} {regime_str:<12} {conf_str:<8} {baseline_str:<12} {optimized_str:<12} {improvement_str:<12}{marker}")

    total_improvement += result['improvement']

print("-" * 80)
print(f"{'TOTAL':<8} {'':<12} {'':<8} {'':<12} {'':<12} {total_improvement:+.2f}%")

print("\n[CONCLUSION]")
if total_improvement > 2.0:
    print("  Dynamic regime-based config provides SIGNIFICANT improvement!")
    print("  Recommendation: Implement regime detection in live trading")
elif total_improvement > 0:
    print("  Dynamic regime-based config provides MODEST improvement")
    print("  Recommendation: Consider implementing with manual oversight")
else:
    print("  Dynamic config did not improve performance")
    print("  Recommendation: Keep current universal ADX 20-30 filter")

print("\n" + "="*80)
