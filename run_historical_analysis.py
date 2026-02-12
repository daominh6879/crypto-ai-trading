#!/usr/bin/env python3
"""
Quick Historical Backtest Analysis Script
Runs comprehensive historical backtests across multiple years

Usage:
  python run_historical_analysis.py                    # Run full analysis 2017-2025
  python run_historical_analysis.py --years 2020 2021 2022  # Specific years
  python run_historical_analysis.py --start-year 2020 --end-year 2023  # Year range
"""

import sys
import argparse
from main import run_historical_backtest
from config import DEFAULT_CONFIG, SCALPING_CONFIG, SWING_CONFIG, CONSERVATIVE_CONFIG

def main():
    parser = argparse.ArgumentParser(description="Historical Backtest Analysis Tool")
    parser.add_argument('--symbol', '-s', default='BTCUSDT', 
                       help='Trading symbol (default: BTCUSDT)')
    parser.add_argument('--config', '-c', choices=['default', 'scalping', 'swing', 'conservative'],
                       default='default', help='Trading configuration')
    parser.add_argument('--start-year', type=int, default=2017, 
                       help='Start year for analysis (default: 2017)')
    parser.add_argument('--end-year', type=int, default=2025, 
                       help='End year for analysis (default: 2025)')
    parser.add_argument('--years', nargs='+', type=int, 
                       help='Specific years to analyze (e.g., --years 2020 2021 2022)')
    
    args = parser.parse_args()
    
    # Select configuration
    config_map = {
        'default': DEFAULT_CONFIG,
        'scalping': SCALPING_CONFIG,
        'swing': SWING_CONFIG,
        'conservative': CONSERVATIVE_CONFIG
    }
    
    selected_config = config_map[args.config]
    selected_config.symbol = args.symbol
    
    print("🚀 HISTORICAL BACKTEST ANALYSIS TOOL")
    print("="*50)
    
    try:
        results = run_historical_backtest(
            symbol=args.symbol,
            config=selected_config,
            years=args.years,
            start_year=args.start_year,
            end_year=args.end_year
        )
        
        print(f"\n💾 Analysis complete! Generated {len(results)} yearly reports.")
        
        # Quick summary
        profitable_years = len([r for r in results if r['pnl_percent'] > 0])
        total_trades = sum(r['trades'] for r in results)
        avg_return = sum(r['pnl_percent'] for r in results) / len(results)
        
        print(f"📈 Quick Summary: {profitable_years}/{len(results)} profitable years, "
              f"{total_trades} total trades, {avg_return:+.1f}% avg annual return")
        
    except KeyboardInterrupt:
        print("\n⏹️  Analysis cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())