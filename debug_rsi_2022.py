#!/usr/bin/env python3
"""
Debug RSI levels in 2022 to see why no trades are generated
"""
import pandas as pd
from trading_system import ProTradingSystem
from indicators import TechnicalIndicators
from config import TradingConfig
import numpy as np

def debug_rsi_levels():
    # Initialize trading system
    config = TradingConfig()
    trading_system = ProTradingSystem(config)
    
    # Fetch 2022 data using trading system
    data = trading_system._fetch_binance_data('BTCUSDT', '1h', start_date='2022-01-01', end_date='2022-12-31')
    print(f"Loaded {len(data)} bars for 2022")
    
    # Calculate RSI
    indicators = TechnicalIndicators(config)
    rsi_series = indicators.calculate_rsi(data)
    
    # Debug: check RSI series
    print(f"RSI series type: {type(rsi_series)}")
    print(f"RSI series shape: {rsi_series.shape}")
    print(f"RSI has data: {not rsi_series.empty}")
    
    # Analyze RSI distribution
    rsi_values = rsi_series.dropna()
    print(f"\n📊 RSI DISTRIBUTION IN 2022:")
    print(f"Min RSI: {rsi_values.min():.1f}")
    print(f"Max RSI: {rsi_values.max():.1f}")
    print(f"Mean RSI: {rsi_values.mean():.1f}")
    print(f"Median RSI: {rsi_values.median():.1f}")
    
    print(f"\n🎯 RSI PERCENTILES:")
    percentiles = [1, 5, 10, 20, 80, 90, 95, 99]
    for p in percentiles:
        value = np.percentile(rsi_values, p)
        print(f"  {p}th percentile: {value:.1f}")
        
    # Count extreme values
    under_20 = (rsi_values < 20).sum()
    under_25 = (rsi_values < 25).sum()
    under_30 = (rsi_values < 30).sum()
    over_70 = (rsi_values > 70).sum()
    over_75 = (rsi_values > 75).sum()
    over_80 = (rsi_values > 80).sum()
    
    total_bars = len(rsi_values)
    print(f"\n🔢 EXTREME RSI OCCURRENCES (out of {total_bars} bars):")
    print(f"RSI < 20: {under_20} bars ({under_20/total_bars*100:.1f}%)")
    print(f"RSI < 25: {under_25} bars ({under_25/total_bars*100:.1f}%)")
    print(f"RSI < 30: {under_30} bars ({under_30/total_bars*100:.1f}%)")
    print(f"RSI > 70: {over_70} bars ({over_70/total_bars*100:.1f}%)")
    print(f"RSI > 75: {over_75} bars ({over_75/total_bars*100:.1f}%)")
    print(f"RSI > 80: {over_80} bars ({over_80/total_bars*100:.1f}%)")
    
    # Suggest better thresholds
    print(f"\n💡 SUGGESTED CONSERVATIVE THRESHOLDS:")  
    print(f"Very Conservative: RSI {np.percentile(rsi_values, 10):.0f}/{np.percentile(rsi_values, 90):.0f}")
    print(f"Conservative: RSI {np.percentile(rsi_values, 15):.0f}/{np.percentile(rsi_values, 85):.0f}")
    print(f"Moderate: RSI {np.percentile(rsi_values, 20):.0f}/{np.percentile(rsi_values, 80):.0f}")

if __name__ == "__main__":
    debug_rsi_levels()