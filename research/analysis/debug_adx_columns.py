"""
Debug script to check ADX column existence and values
"""
import pandas as pd
from config import TradingConfig
from trading_system import ProTradingSystem

# Initialize system
config = TradingConfig()
config.enable_regime_filter = True

system = ProTradingSystem(config)
system.fetch_data("BTCUSDT", start_date='2024-01-01', end_date='2024-02-01', interval='1h')
signals = system.calculate_signals()

print("\n[CHECKING ADX COLUMNS]")
print("="*80)

# Check if columns exist
adx_cols = [col for col in signals.columns if 'adx' in col.lower()]
print(f"\nAll ADX-related columns ({len(adx_cols)}):")
for col in sorted(adx_cols):
    print(f"  - {col}")

# Check specific columns we need
required_cols = ['advanced_adx_choppy', 'advanced_adx_strong_trending', 'advanced_adx_trending']
print(f"\n[REQUIRED COLUMNS CHECK]")
for col in required_cols:
    exists = col in signals.columns
    if exists:
        true_count = signals[col].sum()
        total_count = len(signals)
        pct = (true_count / total_count * 100)
        print(f"  {col}: EXISTS - {true_count}/{total_count} bars ({pct:.1f}%)")
    else:
        print(f"  {col}: MISSING")

# Check ADX value distribution
if 'adx_adx' in signals.columns:
    adx_values = signals['adx_adx'].dropna()
    print(f"\n[ADX VALUE DISTRIBUTION]")
    print(f"  Mean: {adx_values.mean():.2f}")
    print(f"  Median: {adx_values.median():.2f}")
    print(f"  ADX < 20: {(adx_values < 20).sum()} bars ({(adx_values < 20).sum()/len(adx_values)*100:.1f}%)")
    print(f"  ADX 20-30: {((adx_values >= 20) & (adx_values <= 30)).sum()} bars ({((adx_values >= 20) & (adx_values <= 30)).sum()/len(adx_values)*100:.1f}%)")
    print(f"  ADX > 30: {(adx_values > 30).sum()} bars ({(adx_values > 30).sum()/len(adx_values)*100:.1f}%)")
