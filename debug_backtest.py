#!/usr/bin/env python3
"""
Debug script to investigate why backtest is generating 0 trades
"""

import pandas as pd
import numpy as np
from binance_provider import BinanceDataProvider
from indicators import TechnicalIndicators
from config import TradingConfig

def debug_signals():
    """Debug signal generation to find the issue"""
    
    config = TradingConfig()
    provider = BinanceDataProvider(config)
    indicators = TechnicalIndicators(config)
    
    print("🔍 DEBUG: Fetching data for signal analysis...")
    
    # Get data from last year for better debugging
    data = provider.get_historical_data('BTCUSDT', '1h', 1000)  # Get 1000 bars of 1h data
    
    if data is None or len(data) < 50:
        print("❌ ERROR: Insufficient data for analysis")
        return
    
    print(f"✅ Got {len(data)} bars of data")
    print(f"📊 Data range: {data.index[0]} to {data.index[-1]}")
    
    # Calculate indicators
    print("🔍 DEBUG: Calculating indicators...")
    indicators_df = indicators.calculate_all_indicators(data)
    
    if indicators_df is None:
        print("❌ ERROR: Failed to calculate indicators")
        return
    
    print(f"✅ Calculated indicators for {len(indicators_df)} bars")
    
    # Check for NaN values
    nan_cols = indicators_df.columns[indicators_df.isna().any()].tolist()
    print(f"🔍 DEBUG: Columns with NaN values: {nan_cols}")
    
    # Check basic signal conditions
    basic_conditions = {
        'rsi_range': ((indicators_df['rsi'] > 30) & (indicators_df['rsi'] < 70)).sum(),
        'macd_bullish': (indicators_df['macd_line'] > indicators_df['signal_line']).sum(),
        'macd_bearish': (indicators_df['macd_line'] < indicators_df['signal_line']).sum(),
        'histogram_positive': (indicators_df['histogram'] > 0).sum(),
        'histogram_negative': (indicators_df['histogram'] < 0).sum(),
        'volume_bull': indicators_df['volume_vol_bull'].sum() if 'volume_vol_bull' in indicators_df.columns else 0,
        'volume_bear': indicators_df['volume_vol_bear'].sum() if 'volume_vol_bear' in indicators_df.columns else 0,
    }
    
    print("\n🔍 DEBUG: Basic signal condition counts:")
    for condition, count in basic_conditions.items():
        print(f"  {condition}: {count}")
    
    # Check advanced conditions if they exist
    if 'advanced_trending_market' in indicators_df.columns:
        advanced_conditions = {
            'trending_market': indicators_df['advanced_trending_market'].sum(),
            'strong_bull_trend': indicators_df['advanced_strong_bull_trend'].sum(),
            'strong_bear_trend': indicators_df['advanced_strong_bear_trend'].sum(),
            'normal_volatility': indicators_df['advanced_normal_volatility'].sum(),
            'high_volatility': indicators_df['advanced_high_volatility'].sum(),
        }
        
        print("\n🔍 DEBUG: Advanced condition counts:")
        for condition, count in advanced_conditions.items():
            print(f"  {condition}: {count}")
    else:
        print("⚠️  WARNING: No advanced conditions found")
    
    # Check basic buy/sell setups
    basic_buy_setup = (
        (indicators_df['rsi'] > 50) &
        (indicators_df['macd_line'] > indicators_df['signal_line']) &
        (indicators_df['histogram'] > 0)
    )
    
    basic_sell_setup = (
        (indicators_df['rsi'] < 50) &
        (indicators_df['macd_line'] < indicators_df['signal_line']) &
        (indicators_df['histogram'] < 0)
    )
    
    print(f"\n🔍 DEBUG: Basic setup counts:")
    print(f"  basic_buy_setup: {basic_buy_setup.sum()}")
    print(f"  basic_sell_setup: {basic_sell_setup.sum()}")
    
    # Show last few rows of key indicators
    print(f"\n🔍 DEBUG: Last 5 rows of key indicators:")
    key_cols = ['close', 'rsi', 'macd_line', 'signal_line', 'histogram', 'ema_20', 'ema_50']
    available_cols = [col for col in key_cols if col in indicators_df.columns]
    print(indicators_df[available_cols].tail())
    
    print("\n✅ DEBUG: Signal analysis completed")

if __name__ == "__main__":
    debug_signals()