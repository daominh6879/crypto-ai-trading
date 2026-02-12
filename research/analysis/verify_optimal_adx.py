"""
Verify the optimal ADX range (20-30) implementation
Compare performance before and after the filter
"""
import pandas as pd
from config import TradingConfig
from trading_system import ProTradingSystem

def run_comparison(start_date: str, end_date: str, label: str):
    """Run backtest with and without the optimal ADX filter"""
    print(f"\n{'='*80}")
    print(f"{label}: {start_date} to {end_date}")
    print(f"{'='*80}\n")

    symbol = "BTCUSDT"

    # Test 1: WITHOUT regime filter (baseline)
    print("[1] BASELINE (No ADX Filter)")
    print("-" * 40)
    config1 = TradingConfig()
    config1.enable_regime_filter = False
    config1.enable_adaptive_parameters = False

    system1 = ProTradingSystem(config1)
    system1.fetch_data(symbol, start_date=start_date, end_date=end_date, interval='1h')
    system1.calculate_signals()
    results1 = system1.run_backtest(start_date=start_date, end_date=end_date)

    stats1 = results1['statistics']
    print(f"   Trades: {stats1['total_trades']}")
    print(f"   Win Rate: {stats1['win_rate']:.1f}%")
    print(f"   Total P&L: {stats1['total_pnl']:+.2f}%")
    print(f"   Max Drawdown: {stats1['max_drawdown']:.2f}%")
    print(f"   Profit Factor: {stats1['profit_factor']:.2f}")

    # Test 2: WITH optimal ADX filter (20-30 range)
    print(f"\n[2] OPTIMAL ADX FILTER (ADX 20-30 only)")
    print("-" * 40)
    config2 = TradingConfig()
    config2.enable_regime_filter = True
    config2.enable_adaptive_parameters = False

    system2 = ProTradingSystem(config2)
    system2.fetch_data(symbol, start_date=start_date, end_date=end_date, interval='1h')
    system2.calculate_signals()
    results2 = system2.run_backtest(start_date=start_date, end_date=end_date)

    stats2 = results2['statistics']
    print(f"   Trades: {stats2['total_trades']}")
    print(f"   Win Rate: {stats2['win_rate']:.1f}%")
    print(f"   Total P&L: {stats2['total_pnl']:+.2f}%")
    print(f"   Max Drawdown: {stats2['max_drawdown']:.2f}%")
    print(f"   Profit Factor: {stats2['profit_factor']:.2f}")

    # Calculate improvement
    print(f"\n[IMPROVEMENT ANALYSIS]")
    print("-" * 40)
    pnl_change = stats2['total_pnl'] - stats1['total_pnl']
    wr_change = stats2['win_rate'] - stats1['win_rate']
    dd_change = stats2['max_drawdown'] - stats1['max_drawdown']

    print(f"   P&L Change: {pnl_change:+.2f}% {'[OK]' if pnl_change > 0 else '[WORSE]'}")
    print(f"   Win Rate Change: {wr_change:+.1f}% {'[OK]' if wr_change > 0 else '[WORSE]'}")
    print(f"   Max DD Change: {dd_change:+.2f}% {'[OK]' if dd_change < 0 else '[WORSE]'}")
    print(f"   Trade Count Change: {stats2['total_trades'] - stats1['total_trades']:+d}")

    return {
        'baseline': results1,
        'optimal': results2,
        'improvement': {
            'pnl': pnl_change,
            'win_rate': wr_change,
            'max_dd': dd_change
        }
    }

if __name__ == '__main__':
    print("\n" + "="*80)
    print("VERIFYING OPTIMAL ADX RANGE (20-30) IMPLEMENTATION")
    print("="*80)

    # Test on bear market (2022)
    bear_results = run_comparison('2022-01-01', '2023-01-01', 'BEAR MARKET 2022')

    # Test on bull market (2024)
    bull_results = run_comparison('2024-01-01', '2025-01-01', 'BULL MARKET 2024')

    # Summary
    print(f"\n\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}\n")

    print("[2022 BEAR MARKET]")
    print(f"   Baseline: {bear_results['baseline']['statistics']['total_pnl']:+.2f}% P&L")
    print(f"   Optimal:  {bear_results['optimal']['statistics']['total_pnl']:+.2f}% P&L")
    print(f"   Improvement: {bear_results['improvement']['pnl']:+.2f}%")

    print(f"\n[2024 BULL MARKET]")
    print(f"   Baseline: {bull_results['baseline']['statistics']['total_pnl']:+.2f}% P&L")
    print(f"   Optimal:  {bull_results['optimal']['statistics']['total_pnl']:+.2f}% P&L")
    print(f"   Improvement: {bull_results['improvement']['pnl']:+.2f}%")

    total_improvement = bear_results['improvement']['pnl'] + bull_results['improvement']['pnl']
    print(f"\n[TOTAL IMPROVEMENT]")
    print(f"   Combined P&L Change: {total_improvement:+.2f}%")
    print(f"   Status: {'[SUCCESS]' if total_improvement > 0 else '[NEEDS REVIEW]'}")

    print("\n" + "="*80)
