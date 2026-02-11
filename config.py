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
    
    # ==================== RSI ====================
    rsi_length: int = 14
    rsi_overbought: int = 68  # Slightly lower for earlier exits (better win rate)
    rsi_oversold: int = 32    # Slightly higher for better entries
    
    # ==================== MACD ====================
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    
    # ==================== TRADING RULES ====================
    use_trend_filter: bool = True   # Only trade with EMA200 trend (ENABLED for better quality)
    min_bars_gap: int = 5          # Increased to reduce overtrading (was 1)
    require_confirmation: bool = True  # Wait for confirmation candle
    allow_short_trades: bool = False   # Disable shorts - focus on longs only

    # Professional Signal Quality Controls
    min_risk_reward_ratio: float = 2.0  # Minimum R:R ratio for trade entry
    max_daily_trades: int = 3          # Limit trades per day to reduce overtrading
    require_confluence: bool = False     # Disable complex confluence for now
    ultra_strict_mode: bool = False     # Disable ultra-strict temporarily to allow trades

    # Volatility Controls
    max_volatility_threshold: float = 3.0  # Lower threshold to avoid choppy markets (was 3.8)
    min_trend_strength: float = 0.5       # Stronger trend requirement (was 0.35)
    
    # ==================== RISK MANAGEMENT ====================
    atr_length: int = 14
    stop_loss_multiplier: float = 2.5      # Wider stops to avoid premature exits (was 1.8)
    take_profit_1_multiplier: float = 3.0  # More realistic TP1 (was 2.2)
    take_profit_2_multiplier: float = 5.0  # Higher TP2 for better R:R (was 3.5)
    trailing_stop_factor: float = 0.65     # Tighter trailing to lock profits (was 0.75)
    trailing_activation: float = 0.02     # Activate trailing at 2% profit (was 2.5%)
    
    # Enhanced Risk Controls
    max_position_size: float = 0.015        # 1.5% max position size (reduced from 2%)
    max_daily_loss: float = 0.05          # 5% max daily loss before stopping
    max_drawdown_limit: float = 0.15      # 15% max drawdown before reducing size
    
    # ==================== DISPLAY SETTINGS ====================
    show_moving_averages: bool = True
    show_zones: bool = True  # Overbought/Oversold zones
    show_levels: bool = True  # TP/SL levels
    show_labels: bool = True  # Entry/Exit labels
    
    # ==================== DATA SETTINGS ====================
    symbol: str = "AAPL"  # Default symbol
    interval: str = "1d"   # Data interval (1m, 5m, 15m, 1h, 1d, etc.)
    lookback_period: str = "1y"  # Get more data for better backtesting (was "2y")
    
    # ==================== ALERT SETTINGS ====================
    enable_alerts: bool = True
    alert_sound: bool = False
    log_trades: bool = True
    
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
    use_trend_filter=True,
    require_confirmation=True,
    rsi_oversold=25,
    rsi_overbought=75,
    min_bars_gap=5,
    stop_loss_multiplier=3.0,
    take_profit_1_multiplier=3.0,
    take_profit_2_multiplier=5.0
)