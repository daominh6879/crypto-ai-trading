"""
Analyze ADX values from backtest data to determine optimal thresholds
"""
import pandas as pd
import numpy as np
from datetime import datetime
from config import TradingConfig
from trading_system import ProTradingSystem

def analyze_adx_for_period(start_date: str, end_date: str, symbol: str = "BTCUSDT"):
    """Analyze ADX values and their relationship to trade performance"""
    print(f"\n{'='*80}")
    print(f"Analyzing ADX for {start_date} to {end_date}")
    print(f"{'='*80}\n")

    # Initialize system
    config = TradingConfig()
    trading_system = ProTradingSystem(config)

    # Fetch and calculate signals
    print("[*] Fetching data...")
    data = trading_system.fetch_data(symbol, start_date=start_date, end_date=end_date, interval='1h')

    print("[*] Calculating indicators...")
    signals = trading_system.calculate_signals()

    # Run backtest to get trade results
    print("[*] Running backtest...")
    results = trading_system.run_backtest(start_date=start_date, end_date=end_date)

    # Analyze ADX distribution
    adx_values = signals['adx_adx'].dropna()

    print(f"\n[ADX Statistics]")
    print(f"   Mean ADX: {adx_values.mean():.2f}")
    print(f"   Median ADX: {adx_values.median():.2f}")
    print(f"   Std Dev: {adx_values.std():.2f}")
    print(f"   Min: {adx_values.min():.2f}")
    print(f"   Max: {adx_values.max():.2f}")

    # Percentiles
    print(f"\n[ADX Percentiles]")
    for p in [10, 20, 25, 30, 40, 50, 60, 70, 75, 80, 90]:
        val = adx_values.quantile(p/100)
        print(f"   {p}th percentile: {val:.2f}")

    # Time in different regimes
    total_bars = len(adx_values)
    choppy_bars = (adx_values < 20).sum()
    neutral_bars = ((adx_values >= 20) & (adx_values <= 25)).sum()
    trending_bars = ((adx_values > 25) & (adx_values <= 30)).sum()
    strong_trending_bars = (adx_values > 30).sum()

    print(f"\n[Time Distribution] (current thresholds):")
    print(f"   Choppy (ADX < 20):      {choppy_bars:5d} bars ({choppy_bars/total_bars*100:5.1f}%)")
    print(f"   Neutral (ADX 20-25):    {neutral_bars:5d} bars ({neutral_bars/total_bars*100:5.1f}%)")
    print(f"   Trending (ADX 25-30):   {trending_bars:5d} bars ({trending_bars/total_bars*100:5.1f}%)")
    print(f"   Strong (ADX > 30):      {strong_trending_bars:5d} bars ({strong_trending_bars/total_bars*100:5.1f}%)")

    # Analyze trades by ADX regime
    if results['trades']:
        print(f"\n[Trade Analysis by ADX Regime]")

        # Match trades with ADX values at entry
        trades_with_adx = []
        for trade in results['trades']:
            if trade is None:
                continue
            entry_time = pd.to_datetime(trade.entry_time)
            # Find closest ADX value
            closest_idx = signals.index.get_indexer([entry_time], method='nearest')[0]
            if closest_idx < len(signals):
                adx_at_entry = signals.iloc[closest_idx]['adx_adx']
                trades_with_adx.append({
                    'entry_time': trade.entry_time,
                    'exit_time': trade.exit_time,
                    'trade_type': trade.trade_type,
                    'entry_price': trade.entry_price,
                    'exit_price': trade.exit_price,
                    'pnl_percent': trade.pnl_percent,
                    'exit_reason': trade.exit_reason,
                    'adx_at_entry': adx_at_entry
                })

        if trades_with_adx:
            trades_df = pd.DataFrame(trades_with_adx)

            # Categorize by ADX
            trades_df['regime'] = 'neutral'
            trades_df.loc[trades_df['adx_at_entry'] < 20, 'regime'] = 'choppy'
            trades_df.loc[(trades_df['adx_at_entry'] >= 20) & (trades_df['adx_at_entry'] <= 25), 'regime'] = 'neutral'
            trades_df.loc[(trades_df['adx_at_entry'] > 25) & (trades_df['adx_at_entry'] <= 30), 'regime'] = 'trending'
            trades_df.loc[trades_df['adx_at_entry'] > 30, 'regime'] = 'strong_trending'

            for regime in ['choppy', 'neutral', 'trending', 'strong_trending']:
                regime_trades = trades_df[trades_df['regime'] == regime]
                if len(regime_trades) > 0:
                    wins = (regime_trades['pnl_percent'] > 0).sum()
                    win_rate = wins / len(regime_trades) * 100
                    avg_pnl = regime_trades['pnl_percent'].mean()

                    print(f"\n   {regime.upper()}:")
                    print(f"      Trades: {len(regime_trades)}")
                    print(f"      Win Rate: {win_rate:.1f}%")
                    print(f"      Avg P&L: {avg_pnl:+.2f}%")
                    print(f"      Total P&L: {regime_trades['pnl_percent'].sum():+.2f}%")
                    print(f"      ADX Range: {regime_trades['adx_at_entry'].min():.1f} - {regime_trades['adx_at_entry'].max():.1f}")

    return {
        'adx_stats': {
            'mean': adx_values.mean(),
            'median': adx_values.median(),
            'std': adx_values.std(),
            'percentiles': {p: adx_values.quantile(p/100) for p in [10, 20, 25, 30, 50, 70, 75, 80, 90]}
        },
        'regime_distribution': {
            'choppy_pct': choppy_bars/total_bars*100,
            'neutral_pct': neutral_bars/total_bars*100,
            'trending_pct': trending_bars/total_bars*100,
            'strong_pct': strong_trending_bars/total_bars*100
        },
        'results': results
    }

def find_optimal_thresholds():
    """Analyze multiple years to find optimal ADX thresholds"""
    print("\n" + "="*80)
    print("FINDING OPTIMAL ADX THRESHOLDS")
    print("="*80)

    years = [
        ('2022-01-01', '2023-01-01', 'Bear/Choppy'),
        ('2024-01-01', '2025-01-01', 'Bull/Trending')
    ]

    all_results = {}

    for start, end, label in years:
        print(f"\n\n{'#'*80}")
        print(f"# {label}: {start} to {end}")
        print(f"{'#'*80}")
        result = analyze_adx_for_period(start, end)
        all_results[label] = result

    # Summary recommendations
    print("\n\n" + "="*80)
    print("RECOMMENDATIONS")
    print("="*80)

    print("\n[Current Thresholds]")
    print(f"   adx_ranging_threshold: 20")
    print(f"   adx_trending_threshold: 25")
    print(f"   adx_strong_trend_threshold: 30")

    print("\n[Analysis]")
    for label, result in all_results.items():
        print(f"\n   {label}:")
        print(f"      Median ADX: {result['adx_stats']['median']:.1f}")
        print(f"      Choppy time: {result['regime_distribution']['choppy_pct']:.1f}%")
        print(f"      Trending time: {result['regime_distribution']['trending_pct'] + result['regime_distribution']['strong_pct']:.1f}%")

    return all_results

if __name__ == '__main__':
    results = find_optimal_thresholds()
