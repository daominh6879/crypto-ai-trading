#!/usr/bin/env python3
"""
Debug script to test the comprehensive data fetching directly
"""

import sys
sys.path.append('.')

from trading_system import ProTradingSystem
from config import DEFAULT_CONFIG
import pandas as pd

def test_comprehensive_fetch():
    try:
        # Initialize trading system
        system = ProTradingSystem(DEFAULT_CONFIG)
        
        print("=== Testing Comprehensive Data Fetch ===")
        print(f"Testing fetch_data with start_date='2025-11-01'...")
        
        # Call fetch_data directly
        data = system.fetch_data('BTCUSDT', interval='1h', start_date='2025-11-01')
        
        print(f"Result: {len(data)} bars from {data.index[0]} to {data.index[-1]}")
        print(f"Date range: {data.index[0].date()} to {data.index[-1].date()}")
        
        # Check if we got more than 1000 bars
        if len(data) > 1000:
            print("✅ SUCCESS: Got more than 1000 bars - comprehensive fetching working!")
        else:
            print("❌ ISSUE: Still only got 1000 bars or less")
            print("This suggests comprehensive fetching is not being called")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_comprehensive_fetch()