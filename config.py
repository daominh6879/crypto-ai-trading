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
    
    # ==================== TRADING RULES (BALANCED QUALITY) ====================
    use_trend_filter: bool = True   # Only trade with EMA200 trend
    min_bars_gap: int = 6          # Higher for quality (was 3, tried 8)
    require_confirmation: bool = True  # Wait for confirmation candle
    allow_short_trades: bool = True   # Enable shorts for both directions
    require_pullback_entry: bool = False  # Keep simple

    # Professional Signal Quality Controls
    min_risk_reward_ratio: float = 2.8  # Higher R:R target (was 2.5)
    max_daily_trades: int = 3          # Selective (was 5)
    require_confluence: bool = False     # Simpler is better (was True)
    ultra_strict_mode: bool = False     # Disabled for balanced trading

    # Volatility Controls
    max_volatility_threshold: float = 2.9  # Lower - avoid choppy markets (was 3.0)
    min_trend_strength: float = 0.52       # Stronger trends (was 0.45)
    
    # ==================== RISK MANAGEMENT (SWING TRADING) ====================
    atr_length: int = 14
    stop_loss_multiplier: float = 3.0      # WIDER stops for swing trades (was 2.4)
    take_profit_1_multiplier: float = 4.0  # BIGGER targets (was 3.2)
    take_profit_2_multiplier: float = 8.0  # HUGE targets for big winners (was 6.0)
    partial_exit_at_tp1: float = 0.5       # Exit 50% position at TP1, let 50% run to TP2
    trailing_stop_factor: float = 0.55     # Looser trailing for swing (was 0.62)
    trailing_activation: float = 0.025     # Activate trailing at 2.5% profit (was 2%)
    dynamic_trailing: bool = True          # Use dynamic trailing based on profit level
    
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