#!/usr/bin/env python3
"""
Enhanced debug script to analyze ultra-strict filtering
"""

from config import TradingConfig
from trading_system import ProTradingSystem

def main():
    print("🔍 ULTRA-STRICT MODE DEBUG ANALYSIS")
    print("=" * 60)
    
    # Initialize system
    config = TradingConfig()
    config.symbol = "BTCUSDT"
    system = ProTradingSystem(config)
    
    # Fetch FULL data like in backtest
    print("📊 Fetching comprehensive data from 2025-01-01...")
    data = system.fetch_data(start_date="2025-01-01")
    print(f"✅ Loaded {len(data)} bars")
    
    print("🔍 Calculating signals...")
    signals = system.calculate_signals()
    print(f"✅ Calculated signals for {len(signals)} bars")
    
    # Check for advanced indicators
    advanced_cols = [col for col in signals.columns if col.startswith('advanced_')]
    print(f"\n🔧 Advanced indicators found: {len(advanced_cols)}")
    if len(advanced_cols) > 0:
        print("Advanced columns:", ', '.join(advanced_cols[:5]))  # Show first 5
        if len(advanced_cols) > 5:
            print(f"... and {len(advanced_cols) - 5} more")
    
    # Check signal generation at each stage
    print("\n📊 SIGNAL FILTERING ANALYSIS")
    print("-" * 40)
    
    # Setup conditions
    buy_setups = signals['setup_buy_setup'].sum()
    sell_setups = signals['setup_sell_setup'].sum()
    print(f"1. Setup Conditions:")
    print(f"   Buy setups:      {buy_setups:4d}")
    print(f"   Sell setups:     {sell_setups:4d}")
    
    # Professional vs Original triggers
    prof_buy = signals.get('professional_buy_trigger', None)
    prof_sell = signals.get('professional_sell_trigger', None)
    orig_buy = signals.get('original_buy_trigger', None)  
    orig_sell = signals.get('original_sell_trigger', None)
    
    print(f"\n2. Trigger Conditions:")
    if orig_buy is not None and orig_sell is not None:
        print(f"   Original buy:    {orig_buy.sum():4d}")
        print(f"   Original sell:   {orig_sell.sum():4d}")
        print(f"   Original total:  {orig_buy.sum() + orig_sell.sum():4d}")
    
    if prof_buy is not None and prof_sell is not None:
        print(f"   Professional buy: {prof_buy.sum():4d}")
        print(f"   Professional sell: {prof_sell.sum():4d}")
        print(f"   Professional total: {prof_buy.sum() + prof_sell.sum():4d}")
    
    # Final triggers
    buy_triggers = signals['buy_trigger'].sum()
    sell_triggers = signals['sell_trigger'].sum()
    print(f"   Final buy:       {buy_triggers:4d}")
    print(f"   Final sell:      {sell_triggers:4d}")
    print(f"   Final total:     {buy_triggers + sell_triggers:4d}")
    
    # Final confirmed signals (after gap filtering)
    buy_signals = signals['buy_confirmed'].sum()
    sell_signals = signals['sell_confirmed'].sum()
    print(f"\n3. Final Confirmed Signals:")
    print(f"   Buy confirmed:   {buy_signals:4d}")
    print(f"   Sell confirmed:  {sell_signals:4d}")
    print(f"   TOTAL SIGNALS:   {buy_signals + sell_signals:4d}")
    
    # Calculate filter effectiveness
    if orig_buy is not None and orig_sell is not None:
        orig_total = orig_buy.sum() + orig_sell.sum()
        final_total = buy_signals + sell_signals
        if orig_total > 0:
            reduction = ((orig_total - final_total) / orig_total) * 100
            print(f"\n📉 Signal Reduction: {reduction:.1f}% ({orig_total} → {final_total})")
    
    # Configuration check
    print(f"\n🎛️  CONFIGURATION STATUS")
    print(f"-" * 25)
    print(f"Ultra-strict mode:    {'✅ ENABLED' if config.ultra_strict_mode else '❌ DISABLED'}")
    print(f"Min bars gap:         {config.min_bars_gap}")
    effective_gap = config.min_bars_gap * 2 if config.ultra_strict_mode else config.min_bars_gap
    print(f"Effective gap:        {effective_gap}")
    print(f"Max volatility:       {config.max_volatility_threshold}")
    print(f"Min trend strength:   {config.min_trend_strength}")
    
    # Advanced condition analysis
    if len(advanced_cols) > 0:
        print(f"\n📊 ADVANCED FILTERING CONDITIONS")
        print("-" * 35)
        
        conditions = {
            'trending_market': signals.get('advanced_trending_market', None),
            'normal_volatility': signals.get('advanced_normal_volatility', None), 
            'strong_bull_trend': signals.get('advanced_strong_bull_trend', None),
            'strong_bear_trend': signals.get('advanced_strong_bear_trend', None),
            'ema_separation_bull': signals.get('advanced_ema_separation_bull', None),
            'ema_separation_bear': signals.get('advanced_ema_separation_bear', None)
        }
        
        for name, condition in conditions.items():
            if condition is not None:
                if name.endswith('_bull') or name.endswith('_bear'):
                    # For numeric conditions, show average value
                    avg_val = condition.mean()
                    print(f"   {name:20}: avg={avg_val:.3f}")
                else:
                    # For boolean conditions, show percentage true
                    pct_true = condition.mean() * 100
                    count_true = condition.sum()
                    print(f"   {name:20}: {count_true:4d}/{len(signals)} ({pct_true:5.1f}%)")
        
        # Ultra-strict specific conditions
        if config.ultra_strict_mode:
            print(f"\n🎯 ULTRA-STRICT FILTER ANALYSIS")
            print("-" * 30)
            
            # RSI trend analysis
            rsi_trending_up = (signals['rsi'] > signals['rsi'].shift(2)).sum()
            rsi_trending_down = (signals['rsi'] < signals['rsi'].shift(2)).sum()
            print(f"   RSI trending up:     {rsi_trending_up:4d}")
            print(f"   RSI trending down:   {rsi_trending_down:4d}")
            
            # Volume above average
            vol_above_avg = (signals['volume'] > signals['volume'].rolling(10).mean() * 1.2).sum()
            print(f"   Volume 20% above avg: {vol_above_avg:4d}")
            
            # Price vs EMA20
            price_above_ema20 = (signals['close'] > signals['ema_20']).sum()
            price_below_ema20 = (signals['close'] < signals['ema_20']).sum()
            print(f"   Price above EMA20:   {price_above_ema20:4d}")
            print(f"   Price below EMA20:   {price_below_ema20:4d}")

if __name__ == "__main__":
    main()