"""
Analyze individual LONG trades in 2022 to understand why disabling ALL longs makes it worse.
Find characteristics of WINNING longs vs LOSING longs to create selective filter.
"""
import pandas as pd
from config import TradingConfig
from trading_system import ProTradingSystem

def analyze_long_trades_2022():
    """Analyze each LONG trade in 2022 with ADX filter enabled"""

    print("\n" + "="*80)
    print("ANALYZING LONG TRADES IN 2022 BEAR MARKET")
    print("="*80)

    # Run backtest with ADX 20-30 filter (current optimal config)
    config = TradingConfig()
    config.enable_regime_filter = True

    system = ProTradingSystem(config)
    print("\n[*] Fetching data and running backtest...")
    system.fetch_data("BTCUSDT", start_date='2022-01-01', end_date='2023-01-01', interval='1h')
    system.calculate_signals()
    results = system.run_backtest(start_date='2022-01-01', end_date='2023-01-01')

    # Extract LONG trades only
    trades = results['trades']
    long_trades = [t for t in trades if t.trade_type == 'LONG']

    print(f"\n[*] Found {len(long_trades)} LONG trades in 2022")

    # Get signals to extract RSI/ADX at entry
    signals = system.signals

    # Convert to DataFrame for analysis
    long_data = []
    for trade in long_trades:
        # Find RSI and ADX at entry time
        entry_time = pd.to_datetime(trade.entry_time)
        try:
            # Find closest signal row to entry time
            closest_idx = signals.index.get_indexer([entry_time], method='nearest')[0]
            entry_rsi = signals.iloc[closest_idx]['rsi']
            entry_adx = signals.iloc[closest_idx]['adx_adx']
        except:
            entry_rsi = None
            entry_adx = None

        long_data.append({
            'entry_time': trade.entry_time,
            'exit_time': trade.exit_time,
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'pnl_percent': trade.pnl_percent,
            'outcome': 'WIN' if trade.pnl_percent > 0 else 'LOSS',
            'exit_reason': trade.exit_reason,
            'duration_hours': (pd.to_datetime(trade.exit_time) - pd.to_datetime(trade.entry_time)).total_seconds() / 3600,
            'entry_rsi': entry_rsi,
            'entry_adx': entry_adx,
        })

    df = pd.DataFrame(long_data)

    # Overall statistics
    print("\n" + "="*80)
    print("LONG TRADES SUMMARY")
    print("="*80)
    wins = df[df['outcome'] == 'WIN']
    losses = df[df['outcome'] == 'LOSS']

    print(f"\nTotal LONG trades: {len(df)}")
    print(f"Winners: {len(wins)} ({len(wins)/len(df)*100:.1f}%)")
    print(f"Losers: {len(losses)} ({len(losses)/len(df)*100:.1f}%)")
    print(f"\nWinners P&L: {wins['pnl_percent'].sum():+.2f}%")
    print(f"Losers P&L: {losses['pnl_percent'].sum():+.2f}%")
    print(f"Net P&L: {df['pnl_percent'].sum():+.2f}%")
    print(f"\nAverage Winner: {wins['pnl_percent'].mean():.2f}%")
    print(f"Average Loser: {losses['pnl_percent'].mean():.2f}%")

    # Show individual winning trades
    print("\n" + "="*80)
    print("WINNING LONG TRADES (These get eliminated when we disable longs)")
    print("="*80)
    print(f"\n{'Date':<12} {'Entry':<10} {'Exit':<10} {'P&L':<10} {'Duration':<10} {'RSI':<8} {'ADX':<8} {'Exit Reason':<15}")
    print("-" * 80)

    for _, trade in wins.iterrows():
        date = pd.to_datetime(trade['entry_time']).strftime('%Y-%m-%d')
        print(f"{date:<12} ${trade['entry_price']:<9.0f} ${trade['exit_price']:<9.0f} "
              f"{trade['pnl_percent']:>+6.2f}%   {trade['duration_hours']:>6.1f}h    "
              f"{trade['entry_rsi']:>6.1f}  {trade['entry_adx']:>6.1f}  {trade['exit_reason']:<15}")

    # Show individual losing trades
    print("\n" + "="*80)
    print("LOSING LONG TRADES")
    print("="*80)
    print(f"\n{'Date':<12} {'Entry':<10} {'Exit':<10} {'P&L':<10} {'Duration':<10} {'RSI':<8} {'ADX':<8} {'Exit Reason':<15}")
    print("-" * 80)

    for _, trade in losses.iterrows():
        date = pd.to_datetime(trade['entry_time']).strftime('%Y-%m-%d')
        print(f"{date:<12} ${trade['entry_price']:<9.0f} ${trade['exit_price']:<9.0f} "
              f"{trade['pnl_percent']:>+6.2f}%   {trade['duration_hours']:>6.1f}h    "
              f"{trade['entry_rsi']:>6.1f}  {trade['entry_adx']:>6.1f}  {trade['exit_reason']:<15}")

    # Compare characteristics
    print("\n" + "="*80)
    print("WINNERS VS LOSERS COMPARISON")
    print("="*80)

    print(f"\n{'Metric':<25} {'Winners':<15} {'Losers':<15} {'Difference':<15}")
    print("-" * 80)

    metrics = [
        ('Entry RSI', wins['entry_rsi'].mean(), losses['entry_rsi'].mean()),
        ('Entry ADX', wins['entry_adx'].mean(), losses['entry_adx'].mean()),
        ('Duration (hours)', wins['duration_hours'].mean(), losses['duration_hours'].mean()),
        ('Entry Price', wins['entry_price'].mean(), losses['entry_price'].mean()),
    ]

    for metric_name, win_val, loss_val in metrics:
        diff = win_val - loss_val
        print(f"{metric_name:<25} {win_val:<15.2f} {loss_val:<15.2f} {diff:>+15.2f}")

    # Exit reason breakdown for winners
    print("\n" + "="*80)
    print("WINNING LONG TRADES - EXIT REASONS")
    print("="*80)
    win_exits = wins.groupby('exit_reason').agg({
        'pnl_percent': ['count', 'sum', 'mean']
    }).round(2)
    print(win_exits)

    # Month-by-month breakdown
    print("\n" + "="*80)
    print("MONTHLY BREAKDOWN - LONG TRADES")
    print("="*80)

    df['month'] = pd.to_datetime(df['entry_time']).dt.to_period('M')
    monthly = df.groupby('month').agg({
        'pnl_percent': ['count', 'sum', 'mean'],
        'outcome': lambda x: (x == 'WIN').sum()
    }).round(2)
    monthly.columns = ['Trades', 'Total P&L', 'Avg P&L', 'Wins']
    monthly['Win Rate'] = (monthly['Wins'] / monthly['Trades'] * 100).round(1)
    print(monthly)

    # Key insights
    print("\n" + "="*80)
    print("KEY INSIGHTS")
    print("="*80)

    total_pnl = df['pnl_percent'].sum()
    win_contribution = wins['pnl_percent'].sum()
    loss_contribution = losses['pnl_percent'].sum()

    print(f"\n1. NET P&L BREAKDOWN:")
    print(f"   Winners contribute: {win_contribution:+.2f}%")
    print(f"   Losers contribute: {loss_contribution:+.2f}%")
    print(f"   Net result: {total_pnl:+.2f}%")

    print(f"\n2. WHAT HAPPENS IF WE DISABLE ALL LONGS:")
    print(f"   We lose {win_contribution:+.2f}% from winners")
    print(f"   We avoid {loss_contribution:+.2f}% from losers")
    print(f"   Net impact: {win_contribution + loss_contribution:+.2f}% (WORSE if positive winners > negative losers)")

    # Find filters that could work
    print(f"\n3. POTENTIAL SELECTIVE FILTERS:")

    # Check if RSI threshold could help
    for rsi_threshold in [30, 35, 40, 45, 50]:
        filtered_df = df[df['entry_rsi'] < rsi_threshold]
        if len(filtered_df) > 0:
            filtered_pnl = filtered_df['pnl_percent'].sum()
            filtered_wr = (filtered_df['outcome'] == 'WIN').sum() / len(filtered_df) * 100
            print(f"   Entry RSI < {rsi_threshold}: {len(filtered_df)} trades, {filtered_pnl:+.2f}% P&L, {filtered_wr:.1f}% WR")

    # Check if ADX threshold could help
    for adx_threshold in [20, 22, 24, 25, 27, 30]:
        filtered_df = df[df['entry_adx'] < adx_threshold]
        if len(filtered_df) > 0:
            filtered_pnl = filtered_df['pnl_percent'].sum()
            filtered_wr = (filtered_df['outcome'] == 'WIN').sum() / len(filtered_df) * 100
            print(f"   Entry ADX < {adx_threshold}: {len(filtered_df)} trades, {filtered_pnl:+.2f}% P&L, {filtered_wr:.1f}% WR")

    print("\n" + "="*80)
    print("CONCLUSION")
    print("="*80)
    print("\nWhy disabling ALL longs makes it WORSE:")
    print(f"  - We eliminate {win_contribution:+.2f}% gains from {len(wins)} winning longs")
    print(f"  - We avoid {loss_contribution:+.2f}% losses from {len(losses)} losing longs")
    print(f"  - Net effect: {win_contribution - abs(loss_contribution):+.2f}% (negative = worse)")
    print("\nThe winning longs partially offset the losing longs.")
    print("Blanket disabling all longs removes this positive offset.")
    print("\nBetter approach: Find selective filters that keep winning longs, avoid losing longs.")
    print("="*80)

if __name__ == '__main__':
    analyze_long_trades_2022()
