#!/usr/bin/env python3
"""
Debug why bear market strategy generates no trades in 2022
Check each condition individually
"""
import pandas as pd
from trading_system import ProTradingSystem
from config import TradingConfig

def debug_bear_conditions():
    # Initialize system
    config = TradingConfig()
    config.require_confluence = False  # Ensure we use adaptive strategy
    trading_system = ProTradingSystem(config)
    
    # Load and analyze 2022 data
    print("🔍 Debugging Bear Market Conditions for 2022...")
    trading_system.fetch_data('BTCUSDT', '1h', start_date='2022-01-01', end_date='2022-12-31')
    signals_df = trading_system.calculate_signals()
    
    # Get bear market adaptive config
    regime = trading_system.detect_market_regime(trading_system.data)
    adaptive_config = trading_system.get_adaptive_config(regime)
    adaptive_rsi_oversold = adaptive_config.get('rsi_oversold', 30)
    
    print(f"Market Regime: {regime}")
    print(f"Adaptive RSI Oversold: {adaptive_rsi_oversold}")
    print(f"Total bars: {len(signals_df)}")
    
    # Check individual conditions
    print(f"\n📊 INDIVIDUAL CONDITION ANALYSIS:")
    
    # 1. Basic buy condition
    has_setup = 'setup_buy_setup' in signals_df.columns
    if has_setup:
        basic_condition = signals_df['setup_buy_setup']
        print(f"✅ Setup signals available: {basic_condition.sum()} true out of {len(basic_condition)}")
    else:
        # EMA fallback
        if 'ema_20' in signals_df.columns and 'ema_50' in signals_df.columns:
            basic_condition = signals_df['close'] > signals_df['ema_20']
            print(f"📈 EMA condition (Close > EMA20): {basic_condition.sum()} true out of {len(basic_condition)}")
        else:
            basic_condition = pd.Series(True, index=signals_df.index)
            print(f"⭐ Always true fallback: {basic_condition.sum()} true")
    
    # 2. RSI condition
    rsi_condition = signals_df['rsi'] < adaptive_rsi_oversold
    print(f"📉 RSI < {adaptive_rsi_oversold}: {rsi_condition.sum()} true out of {len(rsi_condition)}")
    
    # 3. MACD condition (relaxed)
    has_macd = 'macd_line' in signals_df.columns and 'signal_line' in signals_df.columns
    if has_macd:
        strict_macd = signals_df['macd_line'] > signals_df['signal_line']
        relaxed_macd = signals_df['macd_line'] > (signals_df['signal_line'] * 0.8)
        print(f"📊 MACD > Signal (strict): {strict_macd.sum()} true")
        print(f"📊 MACD > Signal*0.8 (relaxed): {relaxed_macd.sum()} true")
    else:
        relaxed_macd = pd.Series(True, index=signals_df.index)
        print(f"⭐ MACD always true fallback: {relaxed_macd.sum()}")
    
    # 4. Volume condition
    has_volume = 'volume_vol_bull' in signals_df.columns
    if has_volume:
        volume_condition = signals_df['volume_vol_bull']
        print(f"🔊 Volume bullish: {volume_condition.sum()} true")
    else:
        volume_condition = pd.Series(True, index=signals_df.index)
        print(f"⭐ Volume always true fallback: {volume_condition.sum()}")
    
    # Combined condition
    combined = basic_condition & rsi_condition & relaxed_macd & volume_condition
    print(f"\n🎯 COMBINED BUY CONDITION: {combined.sum()} true out of {len(combined)}")
    
    if combined.sum() > 0:
        print(f"✅ Conditions ARE met {combined.sum()} times!")
        # Show sample dates when conditions are met
        sample_dates = signals_df.index[combined].head(10)
        print(f"Sample trigger dates: {list(sample_dates)}")
    else:
        print(f"❌ No single bar meets all conditions simultaneously")
        
        # Check pairs of conditions
        print(f"\n🔍 PAIRWISE CONDITION CHECK:")
        basic_rsi = (basic_condition & rsi_condition).sum()
        basic_macd = (basic_condition & relaxed_macd).sum()
        rsi_macd = (rsi_condition & relaxed_macd).sum()
        print(f"Basic + RSI: {basic_rsi}")
        print(f"Basic + MACD: {basic_macd}")  
        print(f"RSI + MACD: {rsi_macd}")

if __name__ == "__main__":
    debug_bear_conditions()