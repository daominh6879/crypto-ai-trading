"""
Deep analysis of 2022 trades to identify additional improvements
Current state: -12.66% with ADX 20-30 filter (improved from -31.73%)
Goal: Find patterns in losing trades to further optimize
"""
import pandas as pd
import numpy as np
from config import TradingConfig
from trading_system import ProTradingSystem
from datetime import datetime

def analyze_2022_trades_deep():
    print("\n" + "="*80)
    print("DEEP ANALYSIS: 2022 BEAR MARKET TRADES")
    print("="*80)

    # Run backtest with optimal ADX filter
    config = TradingConfig()
    config.enable_regime_filter = True  # ADX 20-30 filter enabled
    config.enable_adaptive_parameters = False

    system = ProTradingSystem(config)
    print("\n[*] Fetching 2022 data...")
    system.fetch_data("BTCUSDT", start_date='2022-01-01', end_date='2023-01-01', interval='1h')

    print("[*] Calculating signals...")
    signals = system.calculate_signals()

    print("[*] Running backtest...")
    results = system.run_backtest(start_date='2022-01-01', end_date='2023-01-01')

    # Create detailed trades dataframe
    trades_data = []
    for trade in results['trades']:
        if trade is None:
            continue

        entry_time = pd.to_datetime(trade.entry_time)
        exit_time = pd.to_datetime(trade.exit_time)

        # Find signals at entry
        entry_idx = signals.index.get_indexer([entry_time], method='nearest')[0]
        if entry_idx >= len(signals):
            continue

        entry_signal = signals.iloc[entry_idx]

        trades_data.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'trade_type': trade.trade_type,
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'pnl_percent': trade.pnl_percent,
            'exit_reason': trade.exit_reason,
            'duration_hours': (exit_time - entry_time).total_seconds() / 3600,
            # Market indicators at entry
            'adx': entry_signal.get('adx_adx', 0),
            'rsi': entry_signal.get('rsi', 0),
            'macd_histogram': entry_signal.get('histogram', 0),
            'atr': entry_signal.get('atr', 0),
            'atr_pct': (entry_signal.get('atr', 0) / entry_signal.get('close', 1)) * 100,
            'price': entry_signal.get('close', 0),
            'ema_20': entry_signal.get('ema_20', 0),
            'ema_50': entry_signal.get('ema_50', 0),
            'volume': entry_signal.get('volume', 0),
            'high_volatility': entry_signal.get('advanced_high_volatility', False),
        })

    if not trades_data:
        print("\n[!] No trades found in 2022 with current filters")
        return

    trades_df = pd.DataFrame(trades_data)

    # Categorize trades
    trades_df['outcome'] = trades_df['pnl_percent'].apply(lambda x: 'WIN' if x > 0 else 'LOSS')
    trades_df['month'] = trades_df['entry_time'].dt.month
    trades_df['week'] = trades_df['entry_time'].dt.isocalendar().week

    print(f"\n[OVERALL STATISTICS]")
    print("="*80)
    total_trades = len(trades_df)
    winners = len(trades_df[trades_df['outcome'] == 'WIN'])
    losers = len(trades_df[trades_df['outcome'] == 'LOSS'])
    win_rate = (winners / total_trades * 100) if total_trades > 0 else 0

    print(f"Total Trades: {total_trades}")
    print(f"Winners: {winners} ({win_rate:.1f}%)")
    print(f"Losers: {losers} ({100-win_rate:.1f}%)")
    print(f"Total P&L: {trades_df['pnl_percent'].sum():.2f}%")
    print(f"Avg Win: {trades_df[trades_df['outcome']=='WIN']['pnl_percent'].mean():.2f}%")
    print(f"Avg Loss: {trades_df[trades_df['outcome']=='LOSS']['pnl_percent'].mean():.2f}%")

    # 1. ANALYZE BY TRADE DIRECTION
    print(f"\n[1] TRADE DIRECTION ANALYSIS")
    print("="*80)
    for direction in ['LONG', 'SHORT']:
        dir_trades = trades_df[trades_df['trade_type'] == direction]
        if len(dir_trades) > 0:
            wins = len(dir_trades[dir_trades['outcome'] == 'WIN'])
            wr = (wins / len(dir_trades) * 100)
            pnl = dir_trades['pnl_percent'].sum()
            avg_pnl = dir_trades['pnl_percent'].mean()
            print(f"\n{direction}:")
            print(f"  Trades: {len(dir_trades)}")
            print(f"  Win Rate: {wr:.1f}%")
            print(f"  Total P&L: {pnl:+.2f}%")
            print(f"  Avg P&L: {avg_pnl:+.2f}%")

    # 2. ANALYZE LOSING TRADES PATTERNS
    print(f"\n[2] LOSING TRADES DEEP DIVE")
    print("="*80)
    losers_df = trades_df[trades_df['outcome'] == 'LOSS']

    if len(losers_df) > 0:
        print(f"\nCharacteristics of {len(losers_df)} losing trades:")
        print(f"  Avg ADX: {losers_df['adx'].mean():.1f}")
        print(f"  Avg RSI: {losers_df['rsi'].mean():.1f}")
        print(f"  Avg ATR %: {losers_df['atr_pct'].mean():.2f}%")
        print(f"  Avg Duration: {losers_df['duration_hours'].mean():.1f} hours")
        print(f"  High Volatility: {losers_df['high_volatility'].sum()} trades ({losers_df['high_volatility'].sum()/len(losers_df)*100:.1f}%)")

        print(f"\n  Exit Reasons:")
        exit_reasons = losers_df['exit_reason'].value_counts()
        for reason, count in exit_reasons.items():
            pnl = losers_df[losers_df['exit_reason'] == reason]['pnl_percent'].sum()
            print(f"    {reason}: {count} trades ({pnl:+.2f}% total)")

    # 3. COMPARE WINNERS VS LOSERS
    print(f"\n[3] WINNERS vs LOSERS COMPARISON")
    print("="*80)
    winners_df = trades_df[trades_df['outcome'] == 'WIN']

    if len(winners_df) > 0 and len(losers_df) > 0:
        print(f"\n{'Metric':<20} {'Winners':>15} {'Losers':>15} {'Difference':>15}")
        print("-" * 68)

        metrics = {
            'ADX': ('adx', 1),
            'RSI': ('rsi', 1),
            'ATR %': ('atr_pct', 2),
            'Duration (hrs)': ('duration_hours', 1),
            'MACD Histogram': ('macd_histogram', 4),
        }

        for name, (col, decimals) in metrics.items():
            win_avg = winners_df[col].mean()
            loss_avg = losers_df[col].mean()
            diff = win_avg - loss_avg
            print(f"{name:<20} {win_avg:>15.{decimals}f} {loss_avg:>15.{decimals}f} {diff:>+15.{decimals}f}")

    # 4. MONTHLY PERFORMANCE
    print(f"\n[4] MONTHLY BREAKDOWN")
    print("="*80)
    print(f"\n{'Month':<12} {'Trades':>8} {'Win Rate':>10} {'P&L':>10}")
    print("-" * 42)

    for month in sorted(trades_df['month'].unique()):
        month_trades = trades_df[trades_df['month'] == month]
        month_wins = len(month_trades[month_trades['outcome'] == 'WIN'])
        month_wr = (month_wins / len(month_trades) * 100)
        month_pnl = month_trades['pnl_percent'].sum()
        month_name = datetime(2022, month, 1).strftime('%B')
        print(f"{month_name:<12} {len(month_trades):>8} {month_wr:>9.1f}% {month_pnl:>+9.2f}%")

    # 5. IDENTIFY OPTIMAL ADDITIONAL FILTERS
    print(f"\n[5] OPTIMAL FILTER RECOMMENDATIONS")
    print("="*80)

    # Test different RSI ranges
    print(f"\nRSI Range Analysis:")
    rsi_ranges = [
        ('< 40', lambda df: df['rsi'] < 40),
        ('40-45', lambda df: (df['rsi'] >= 40) & (df['rsi'] < 45)),
        ('45-50', lambda df: (df['rsi'] >= 45) & (df['rsi'] < 50)),
        ('50-55', lambda df: (df['rsi'] >= 50) & (df['rsi'] < 55)),
        ('55-60', lambda df: (df['rsi'] >= 55) & (df['rsi'] < 60)),
        ('60-70', lambda df: (df['rsi'] >= 60) & (df['rsi'] < 70)),
        ('> 70', lambda df: df['rsi'] > 70),
    ]

    print(f"  {'Range':<12} {'Trades':>8} {'Win Rate':>10} {'Avg P&L':>10} {'Total P&L':>10}")
    print("  " + "-" * 52)

    for range_name, filter_func in rsi_ranges:
        range_trades = trades_df[filter_func(trades_df)]
        if len(range_trades) > 0:
            wins = len(range_trades[range_trades['outcome'] == 'WIN'])
            wr = (wins / len(range_trades) * 100)
            avg_pnl = range_trades['pnl_percent'].mean()
            total_pnl = range_trades['pnl_percent'].sum()
            marker = " [GOOD]" if avg_pnl > 0 and wr > 50 else " [BAD]" if avg_pnl < -1 else ""
            print(f"  {range_name:<12} {len(range_trades):>8} {wr:>9.1f}% {avg_pnl:>+9.2f}% {total_pnl:>+9.2f}%{marker}")

    # Test volatility impact
    print(f"\nVolatility Analysis:")
    print(f"  {'Condition':<25} {'Trades':>8} {'Win Rate':>10} {'Total P&L':>10}")
    print("  " + "-" * 55)

    high_vol = trades_df[trades_df['high_volatility'] == True]
    normal_vol = trades_df[trades_df['high_volatility'] == False]

    for name, subset in [('High Volatility', high_vol), ('Normal Volatility', normal_vol)]:
        if len(subset) > 0:
            wins = len(subset[subset['outcome'] == 'WIN'])
            wr = (wins / len(subset) * 100)
            pnl = subset['pnl_percent'].sum()
            print(f"  {name:<25} {len(subset):>8} {wr:>9.1f}% {pnl:>+9.2f}%")

    # 6. SIMULATE POTENTIAL IMPROVEMENTS
    print(f"\n[6] IMPROVEMENT SIMULATIONS")
    print("="*80)

    scenarios = [
        ("Current (ADX 20-30)", trades_df),
        ("+ Skip RSI < 45 for LONG", trades_df[(trades_df['trade_type'] == 'SHORT') | (trades_df['rsi'] >= 45)]),
        ("+ Skip RSI > 55 for SHORT", trades_df[(trades_df['trade_type'] == 'LONG') | (trades_df['rsi'] <= 55)]),
        ("+ Skip High Volatility", trades_df[trades_df['high_volatility'] == False]),
        ("+ Only trade May-Dec", trades_df[trades_df['month'] >= 5]),
    ]

    print(f"\n{'Scenario':<35} {'Trades':>8} {'Win Rate':>10} {'P&L':>10} {'Improvement':>12}")
    print("-" * 77)

    baseline_pnl = trades_df['pnl_percent'].sum()
    for scenario_name, scenario_df in scenarios:
        if len(scenario_df) > 0:
            wins = len(scenario_df[scenario_df['outcome'] == 'WIN'])
            wr = (wins / len(scenario_df) * 100)
            pnl = scenario_df['pnl_percent'].sum()
            improvement = pnl - baseline_pnl
            marker = " [BETTER]" if improvement > 0 else ""
            print(f"{scenario_name:<35} {len(scenario_df):>8} {wr:>9.1f}% {pnl:>+9.2f}% {improvement:>+11.2f}%{marker}")

    # 7. RECOMMENDATIONS
    print(f"\n[7] ACTIONABLE RECOMMENDATIONS")
    print("="*80)

    # Calculate best improvements
    best_improvements = []

    # RSI filter for longs
    long_rsi_45 = trades_df[(trades_df['trade_type'] == 'SHORT') | (trades_df['rsi'] >= 45)]
    long_rsi_improvement = long_rsi_45['pnl_percent'].sum() - baseline_pnl
    if long_rsi_improvement > 0:
        best_improvements.append(('Skip LONG trades when RSI < 45', long_rsi_improvement))

    # Volatility filter
    no_high_vol = trades_df[trades_df['high_volatility'] == False]
    vol_improvement = no_high_vol['pnl_percent'].sum() - baseline_pnl
    if vol_improvement > 0:
        best_improvements.append(('Skip high volatility periods', vol_improvement))

    # Sort by improvement
    best_improvements.sort(key=lambda x: x[1], reverse=True)

    if best_improvements:
        print("\nTop improvements identified:")
        for i, (rec, improvement) in enumerate(best_improvements[:3], 1):
            print(f"  {i}. {rec}: {improvement:+.2f}% improvement")
    else:
        print("\nNo significant improvements found beyond current ADX 20-30 filter.")
        print("Consider:")
        print("  - Accept 2022 as a bear market with unavoidable losses")
        print("  - Focus on capital preservation rather than profit")
        print("  - Use different strategies for bear markets (mean reversion, range trading)")

    return trades_df

if __name__ == '__main__':
    trades_df = analyze_2022_trades_deep()
