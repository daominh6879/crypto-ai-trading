#!/usr/bin/env python3
"""
Quick test with balanced professional settings
"""

from config import TradingConfig
from trading_system import ProTradingSystem

def test_balanced_settings():
    """Test with more balanced professional settings"""
    print("🎯 TESTING BALANCED PROFESSIONAL SETTINGS")
    print("=" * 50)
    
    # Create config with balanced settings
    config = TradingConfig()
    
    # Force balanced settings
    config.ultra_strict_mode = False  # Disable ultra-strict
    config.min_bars_gap = 3          # Standard gap
    config.max_volatility_threshold = 4.0  # More flexible
    config.min_trend_strength = 0.3   # Relaxed trend requirement
    
    print(f"Ultra-strict mode: {config.ultra_strict_mode}")
    print(f"Min bars gap: {config.min_bars_gap}")
    print(f"Max volatility: {config.max_volatility_threshold}")
    print(f"Min trend strength: {config.min_trend_strength}")
    
    # Quick backtest with balanced settings
    system = ProTradingSystem(config)
    
    print("\n📊 Fetching data and running balanced backtest...")
    system.fetch_data(symbol="BTCUSDT", start_date="2025-01-01")
    system.calculate_signals()
    
    # Count signals before backtest
    signals = system.signals
    buy_count = signals['buy_confirmed'].sum() if 'buy_confirmed' in signals.columns else 0
    sell_count = signals['sell_confirmed'].sum() if 'sell_confirmed' in signals.columns else 0
    
    print(f"\n📈 Signal Count:")
    print(f"  Buy signals: {buy_count}")
    print(f"  Sell signals: {sell_count}")
    print(f"  Total signals: {buy_count + sell_count}")
    
    if buy_count + sell_count > 20:  # If we have reasonable signal count
        results = system.run_backtest(start_date="2025-01-01")
        stats = system.position_manager.get_trade_statistics()
        
        print(f"\n📊 BALANCED RESULTS:")
        print(f"  Total Trades: {stats['total_trades']}")
        print(f"  Win Rate: {stats['win_rate']:.1f}%")
        print(f"  Total P&L: {stats['total_return']:.2f}%")
        print(f"  Max Drawdown: {stats['max_drawdown']:.2f}%")
        
        # This should be much better than 10 trades!
        if stats['total_trades'] >= 30:
            print("\n✅ SUCCESS: Professional trade frequency achieved!")
        else:
            print(f"\n⚠️  Still too few trades ({stats['total_trades']}) - needs more adjustment")

if __name__ == "__main__":
    test_balanced_settings()