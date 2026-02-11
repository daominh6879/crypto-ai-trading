#!/usr/bin/env python3
"""
Debug script to check signal generation
"""

from config import TradingConfig
from trading_system import ProTradingSystem

# Initialize system
config = TradingConfig()
config.symbol = "BTCUSDT"
system = ProTradingSystem(config)

# Fetch data and calculate signals
print("Fetching data...")
data = system.fetch_data()
print(f"Loaded {len(data)} bars")

print("Calculating signals...")
signals = system.calculate_signals()

# Check signal generation
print("\n=== SIGNAL ANALYSIS ===")

# Check setup conditions
buy_setups = signals['setup_buy_setup'].sum()
sell_setups = signals['setup_sell_setup'].sum()
print(f"Buy setups: {buy_setups}")
print(f"Sell setups: {sell_setups}")

# Check trigger conditions  
buy_triggers = signals['buy_trigger'].sum()
sell_triggers = signals['sell_trigger'].sum()
print(f"Buy triggers: {buy_triggers}")
print(f"Sell triggers: {sell_triggers}")

# Check final signals
buy_signals = signals['buy_confirmed'].sum()
sell_signals = signals['sell_confirmed'].sum()
print(f"Buy signals: {buy_signals}")
print(f"Sell signals: {sell_signals}")

# Show some sample data
print("\n=== LAST 10 BARS ===")
cols = ['close', 'ema_20', 'ema_50', 'ema_200', 'rsi', 'macd_line', 'signal_line', 'histogram', 
        'setup_buy_setup', 'setup_sell_setup', 'buy_trigger', 'sell_trigger', 'buy_confirmed', 'sell_confirmed']

print(signals[cols].tail(10).to_string())

# Check for any buy/sell signal occurrences
if buy_signals > 0:
    print("\n=== BUY SIGNALS FOUND ===")
    buy_dates = signals[signals['buy_confirmed']].index
    print(f"Buy signal dates: {buy_dates[:5]}")  # Show first 5
    
if sell_signals > 0:
    print("\n=== SELL SIGNALS FOUND ===")
    sell_dates = signals[signals['sell_confirmed']].index
    print(f"Sell signal dates: {sell_dates[:5]}")  # Show first 5

# Check EMA alignment statistics
ema_aligned_bull = ((signals['ema_20'] > signals['ema_50']) & (signals['ema_50'] > signals['ema_200'])).sum()
ema_aligned_bear = ((signals['ema_20'] < signals['ema_50']) & (signals['ema_50'] < signals['ema_200'])).sum()
print(f"\n=== EMA ALIGNMENT ===")
print(f"Bars with bullish EMA alignment: {ema_aligned_bull}")
print(f"Bars with bearish EMA alignment: {ema_aligned_bear}")

# Check RSI stats
rsi_above_50 = (signals['rsi'] > 50).sum()
rsi_below_50 = (signals['rsi'] < 50).sum()
print(f"\n=== RSI STATS ===")
print(f"RSI > 50: {rsi_above_50}")
print(f"RSI < 50: {rsi_below_50}")

# Check MACD stats  
macd_bull = (signals['macd_line'] > signals['signal_line']).sum()
macd_bear = (signals['macd_line'] < signals['signal_line']).sum()
hist_positive = (signals['histogram'] > 0).sum()
hist_negative = (signals['histogram'] < 0).sum()
print(f"\n=== MACD STATS ===")
print(f"MACD bullish: {macd_bull}")
print(f"MACD bearish: {macd_bear}")
print(f"Histogram positive: {hist_positive}")  
print(f"Histogram negative: {hist_negative}")

# Check volume
if 'volume_vol_bull' in signals.columns:
    vol_bull = signals['volume_vol_bull'].sum()
    vol_bear = signals['volume_vol_bear'].sum()
    print(f"\n=== VOLUME STATS ===")
    print(f"Volume bull conditions: {vol_bull}")
    print(f"Volume bear conditions: {vol_bear}")