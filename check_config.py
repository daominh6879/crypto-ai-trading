#!/usr/bin/env python3

from config import DEFAULT_CONFIG
import pandas as pd

def check_config_values():
    """Check what configuration values are actually being used"""
    
    print("=== CURRENT CONFIGURATION VALUES ===")
    print(f"min_bars_gap: {DEFAULT_CONFIG.min_bars_gap}")
    print(f"max_daily_trades: {DEFAULT_CONFIG.max_daily_trades}")
    print(f"require_confluence: {DEFAULT_CONFIG.require_confluence}")
    print(f"rsi_oversold: {DEFAULT_CONFIG.rsi_oversold}")
    print(f"rsi_overbought: {DEFAULT_CONFIG.rsi_overbought}")
    print(f"enable_adaptive_parameters: {DEFAULT_CONFIG.enable_adaptive_parameters}")
    print(f"enable_regime_filter: {DEFAULT_CONFIG.enable_regime_filter}")
    print(f"min_risk_reward_ratio: {DEFAULT_CONFIG.min_risk_reward_ratio}")
    print(f"max_volatility_threshold: {DEFAULT_CONFIG.max_volatility_threshold}")
    print(f"min_trend_strength: {DEFAULT_CONFIG.min_trend_strength}")
    
    print("\n=== ADAPTIVE PARAMETERS ===")
    print(f"choppy_stop_loss_multiplier: {DEFAULT_CONFIG.choppy_stop_loss_multiplier}")
    print(f"choppy_min_bars_gap: {DEFAULT_CONFIG.choppy_min_bars_gap}")
    print(f"trending_stop_loss_multiplier: {DEFAULT_CONFIG.trending_stop_loss_multiplier}")
    print(f"trending_min_bars_gap: {DEFAULT_CONFIG.trending_min_bars_gap}")
    
    print("\n=== CHECKING IF THESE VALUES ARE DIFFERENT FROM DEFAULTS ===")
    # Check what a fresh config would have
    from config import TradingConfig
    fresh_config = TradingConfig()
    
    changes = []
    if DEFAULT_CONFIG.min_bars_gap != 6:  # Original was 6
        changes.append(f"min_bars_gap changed to {DEFAULT_CONFIG.min_bars_gap}")
    if DEFAULT_CONFIG.max_daily_trades != 3:  # Original was 3
        changes.append(f"max_daily_trades changed to {DEFAULT_CONFIG.max_daily_trades}")
    if DEFAULT_CONFIG.require_confluence != False:  # Original was False
        changes.append(f"require_confluence changed to {DEFAULT_CONFIG.require_confluence}")
    if DEFAULT_CONFIG.enable_adaptive_parameters != False:  # Original was False
        changes.append(f"enable_adaptive_parameters changed to {DEFAULT_CONFIG.enable_adaptive_parameters}")
    
    if changes:
        print("✅ CHANGES DETECTED:")
        for change in changes:
            print(f"   - {change}")
    else:
        print("❌ NO CHANGES DETECTED - config might not be loading our edits!")

if __name__ == "__main__":
    check_config_values()