#!/usr/bin/env python3
"""
Script to fix the trading_system.py file by adding proper limit calculation
"""

def fix_trading_system():
    with open('trading_system.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix both instances of the missing limit calculation
    old_pattern = '''            # Limit to Binance API limits
            days = min(days, 365)  # Max 1 year for most intervals
            
            data = self.binance_provider.get_historical_data(
                symbol, interval, limit=limit, start_str=start_date
            )'''
    
    new_pattern = '''            # Limit to Binance API limits
            days = min(days, 365)  # Max 1 year for most intervals
            
            # Calculate appropriate limit based on interval
            if interval.endswith('h'):
                hours_per_bar = int(interval[:-1])
                bars_per_day = 24 // hours_per_bar
                limit = min(1000, days * bars_per_day)
            elif interval.endswith('m'):
                minutes_per_bar = int(interval[:-1])
                bars_per_day = (24 * 60) // minutes_per_bar
                limit = min(1000, days * bars_per_day)
            else:
                limit = min(1000, days)  # Daily or default
            
            data = self.binance_provider.get_historical_data(
                symbol, interval, limit=limit, start_str=start_date
            )'''
    
    # Replace all occurrences
    updated_content = content.replace(old_pattern, new_pattern)
    
    # Write back to file
    with open('trading_system.py', 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("Fixed trading_system.py - added limit calculation logic")

if __name__ == "__main__":
    fix_trading_system()