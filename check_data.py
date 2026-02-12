#!/usr/bin/env python3

from config import DEFAULT_CONFIG
from binance_provider import BinanceDataProvider
import pandas as pd

def check_binance_data():
    """Check what data we're getting from Binance"""
    provider = BinanceDataProvider(DEFAULT_CONFIG)
    
    # Get a small sample of data
    print("Fetching sample data from Binance...")
    data = provider.get_historical_data('BTCUSDT', '1h', 
                                       limit=96,
                                       start_str='2022-01-01')
    
    print(f"\nTotal bars: {len(data)}")
    print(f"Date range: {data.index[0]} to {data.index[-1]}")
    print(f"\nFirst few rows:")
    print(data.head(3))
    print(f"\nLast few rows:")
    print(data.tail(3))
    
    # Check specific prices
    print(f"\nFirst close price: {data.iloc[0]['Close']:,.2f}")
    print(f"Last close price: {data.iloc[-1]['Close']:,.2f}")
    
    # Check for any issues
    print(f"\nData quality check:")
    print(f"Missing values: {data.isnull().sum().sum()}")
    print(f"Duplicate timestamps: {data.index.duplicated().sum()}")

if __name__ == "__main__":
    check_binance_data()