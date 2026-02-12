#!/usr/bin/env python3

import pandas as pd
import numpy as np
from config import DEFAULT_CONFIG
from binance_provider import BinanceDataProvider
from indicators import TechnicalIndicators
import hashlib

def debug_calculations():
    """Debug where our calculations diverge"""
    
    # Set consistent random seed
    np.random.seed(42)
    
    print("Environment Info:")
    print(f"OS: {pd.api.types.__name__}")
    print(f"Python: 3.13.7")
    print(f"Pandas: {pd.__version__}")
    print(f"NumPy: {np.__version__}")
    
    # Get small sample of data
    provider = BinanceDataProvider(DEFAULT_CONFIG)
    data = provider.get_historical_data('BTCUSDT', '1h', limit=100, start_str='2022-01-01')
    
    print(f"\nData shape: {data.shape}")
    print(f"First close: {data.iloc[0]['Close']:.8f}")
    print(f"Last close: {data.iloc[-1]['Close']:.8f}")
    
    # Calculate indicators 
    indicators = TechnicalIndicators(DEFAULT_CONFIG)
    
    # Test RSI calculation
    rsi_data = indicators.calculate_rsi(data)
    print(f"\nRSI [10]: {rsi_data.iloc[20]:.8f}")  # After warmup period
    print(f"RSI [50]: {rsi_data.iloc[50]:.8f}")
    
    # Test EMA calculation
    ema_data = indicators.calculate_ema(data)
    print(f"\nEMA20 [50]: {ema_data['ema_20'].iloc[50]:.8f}")
    print(f"EMA50 [50]: {ema_data['ema_50'].iloc[50]:.8f}")
    
    # Test ADX calculation  
    adx_data = indicators.calculate_adx(data)
    print(f"\nADX [50]: {adx_data['adx'].iloc[50]:.8f}")
    print(f"DI+ [50]: {adx_data['plus_di'].iloc[50]:.8f}")
    
    # Create hash of key calculations to compare
    key_values = [
        data.iloc[0]['Close'],
        data.iloc[50]['Close'], 
        rsi_data.iloc[50],
        ema_data['ema_20'].iloc[50],
        adx_data['adx'].iloc[50]
    ]
    
    # Convert to strings and hash
    values_str = ''.join([f"{v:.8f}" for v in key_values if pd.notna(v)])
    calc_hash = hashlib.md5(values_str.encode()).hexdigest()
    
    print(f"\nCalculation hash: {calc_hash}")
    print(f"Key values string: {values_str}")

if __name__ == "__main__":
    debug_calculations()