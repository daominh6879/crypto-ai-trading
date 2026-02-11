#!/usr/bin/env python3
"""
Script to modify the first _fetch_binance_data method to use comprehensive fetching
"""

def fix_first_fetch_method():
    with open('trading_system.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the first occurrence of _fetch_binance_data method
    method_start = -1
    method_end = -1
    
    for i, line in enumerate(lines):
        if 'def _fetch_binance_data(self, symbol: str, interval: str, days: int = None, start_date: str = None)' in line:
            method_start = i
            break
    
    if method_start == -1:
        print("Could not find the method to modify")
        return
    
    # Find the end of this method (next method or class end)
    indent_level = len(lines[method_start]) - len(lines[method_start].lstrip())
    for i in range(method_start + 1, len(lines)):
        line = lines[i].strip()
        if line and not line.startswith('#'):
            current_indent = len(lines[i]) - len(lines[i].lstrip())
            if current_indent <= indent_level and (line.startswith('def ') or line.startswith('class ')):
                method_end = i
                break
    
    if method_end == -1:
        method_end = len(lines)
    
    # Replace the method with new implementation
    new_method = '''    def _fetch_binance_data(self, symbol: str, interval: str, days: int = None, start_date: str = None) -> pd.DataFrame:
        """Fetch data from Binance with comprehensive multi-chunk support"""
        try:
            # If start_date is specified, use comprehensive fetching for large date ranges
            if start_date:
                return self._fetch_comprehensive_data(symbol, interval, start_date)
            
            # Calculate days based on lookback period if not specified
            if days is None:
                lookback = self.config.lookback_period
                if lookback.endswith('y'):
                    days = int(lookback[:-1]) * 365
                elif lookback.endswith('mo'):
                    days = int(lookback[:-2]) * 30
                elif lookback.endswith('d'):
                    days = int(lookback[:-1])
                else:
                    days = 365  # Default 1 year
            
            # For normal fetching without start_date, limit to what fits in 1000 bars
            days = min(days, 42)  # ~1000 bars for most intervals
            
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
                symbol, interval, limit=limit
            )
            
            if data.empty:
                raise ValueError(f"No data found for symbol {symbol}")
            
            self.data = data
            return data
            
        except Exception as e:
            raise Exception(f"Error fetching data for {symbol}: {str(e)}")

'''
    
    # Replace the method
    new_lines = lines[:method_start] + [new_method] + lines[method_end:]
    
    # Write back
    with open('trading_system.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print(f"Successfully modified the first _fetch_binance_data method (lines {method_start+1}-{method_end})")

if __name__ == "__main__":
    fix_first_fetch_method()