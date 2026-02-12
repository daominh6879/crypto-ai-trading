"""
Configuration settings for the Pro Trader System
Converted from TradingView Pine Script
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TradingConfig:
    """Main configuration class for all trading parameters"""
    
    # ==================== MOVING AVERAGES ====================
    ema_20_length: int = 20
    ema_50_length: int = 50
    ema_200_length: int = 200  # Trend Filter
    
    # ==================== RSI (BULL-MARKET OPTIMIZED) ====================
    rsi_length: int = 14
    rsi_overbought: int = 75  # More permissive for bull markets (was 68, now 75)
    rsi_oversold: int = 30    # More permissive for entries (was 32, now 30)
    
    # ==================== MACD ====================
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # ==================== TRADING RULES ====================
    min_bars_gap: int = 4          # Gap between signals 
    require_confluence: bool = False   # Disable confluence for more trades

    # Volatility Controls 
    max_volatility_threshold: float = 3.2  # Allow more volatility in bull markets 
    min_trend_strength: float = 0.45       # Lower threshold for more opportunities
    
    # ==================== ADX & MARKET REGIME DETECTION ====================
    adx_length: int = 14                   # ADX calculation period
    adx_trending_threshold: float = 25     # ADX > 25 = trending market
    adx_ranging_threshold: float = 18      # ADX < 18 = choppy/ranging market (was 20, now 18)
    
    # ==================== LIVE TRADING REGIME DETECTION ====================
    regime_lookback_days: int = 90            # Days to look back for regime detection (90 = ~3 months)
    adx_strong_trend_threshold: float = 35 # ADX > 35 = very strong trend (was 30, now 35)

    # ==================== ADAPTIVE PARAMETERS ====================
    enable_adaptive_parameters: bool = True   # Enable dynamic risk parameters based on market regime
    enable_regime_filter: bool = True        # Filter to optimal ADX range - ENABLED based on data analysis

    # ==================== RISK MANAGEMENT (SWING TRADING - BASE VALUES) ====================
    atr_length: int = 14
    stop_loss_multiplier: float = 3.0      # WIDER stops for swing trades (was 2.4)
    take_profit_1_multiplier: float = 4.0  # BIGGER targets (was 3.2)
    take_profit_2_multiplier: float = 8.0  # HUGE targets for big winners (was 6.0)
    partial_exit_at_tp1: float = 0.5       # Exit 50% position at TP1, let 50% run to TP2
    trailing_stop_factor: float = 0.55     # Looser trailing for swing (was 0.62)
    trailing_activation: float = 0.025     # Activate trailing at 2.5% profit (was 2%)
    dynamic_trailing: bool = True          # Use dynamic trailing based on profit level

    # Adaptive parameters for CHOPPY markets (tighter risk management)
    choppy_stop_loss_multiplier: float = 2.0      # Tighter stops in choppy markets
    choppy_take_profit_1_multiplier: float = 2.5  # Smaller targets
    choppy_take_profit_2_multiplier: float = 4.0  # More realistic targets

    # Adaptive parameters for STRONG TRENDING markets (wider for bigger moves)
    trending_stop_loss_multiplier: float = 3.5    # Wider stops for trends
    trending_take_profit_1_multiplier: float = 5.0  # Bigger targets
    trending_take_profit_2_multiplier: float = 10.0  # Huge targets for strong trends
    
    # ==================== DATA SETTINGS ====================
    symbol: str = "BTCUSDT"  # Default symbol
    interval: str = "1h"   # Data interval (1m, 5m, 15m, 1h, 1d, etc.) - OPTIMIZED FOR A+ PERFORMANCE
    lookback_period: str = "1y"  # Get more data for better backtesting (was "2y")
    
    # ==================== TRADING MODE ====================
    paper_trading: bool = True  # True = Paper trading, False = Real trading
    enable_telegram: bool = True  # Enable Telegram notifications
    initial_paper_balance: float = 10000.0  # Starting balance for paper trading
    
    def validate(self):
        """Validate configuration parameters"""
        if not (15 <= self.rsi_oversold <= 40):
            raise ValueError("RSI oversold must be between 15 and 40")
        if not (60 <= self.rsi_overbought <= 85):
            raise ValueError("RSI overbought must be between 60 and 85")
        if self.rsi_oversold >= self.rsi_overbought:
            raise ValueError("RSI oversold must be less than overbought")
        if self.min_bars_gap < 1:
            raise ValueError("Minimum bars gap must be at least 1")
        if self.stop_loss_multiplier <= 0:
            raise ValueError("Stop loss multiplier must be positive")
        if self.take_profit_1_multiplier <= 0:
            raise ValueError("Take profit 1 multiplier must be positive")
        if self.take_profit_2_multiplier <= 0:
            raise ValueError("Take profit 2 multiplier must be positive")


# Default configuration instance
DEFAULT_CONFIG = TradingConfig()


# Preset configurations for different trading styles
SCALPING_CONFIG = TradingConfig(
    ema_20_length=10,
    ema_50_length=25,
    rsi_oversold=25,
    rsi_overbought=75,
    min_bars_gap=1,
    stop_loss_multiplier=1.5,
    take_profit_1_multiplier=2.0,
    take_profit_2_multiplier=3.0,
    interval="5m"
)

SWING_CONFIG = TradingConfig(
    ema_20_length=20,
    ema_50_length=50,
    ema_200_length=200,
    rsi_oversold=30,
    rsi_overbought=70,
    min_bars_gap=5,
    stop_loss_multiplier=2.5,
    take_profit_1_multiplier=4.0,
    take_profit_2_multiplier=6.0,
    interval="1d"
)

CONSERVATIVE_CONFIG = TradingConfig(
    rsi_oversold=25,
    rsi_overbought=75,
    min_bars_gap=5,
    stop_loss_multiplier=3.0,
    take_profit_1_multiplier=3.0,
    take_profit_2_multiplier=5.0
)