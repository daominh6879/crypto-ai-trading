"""
Streamlined Trading System for the Pro Trader System
Integrates indicators, signals, position management, and live trading
Converted from TradingView Pine Script with database integration
"""

import pandas as pd
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from config import TradingConfig
from indicators import TechnicalIndicators
from position_manager import EnhancedPositionManager
from binance_provider import BinanceDataProvider, LiveTradingSystem

# Database integration
try:
    from database import get_database
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    print("Warning: Database module not available")


class ProTradingSystem:
    """
    Main trading system that orchestrates all components with live trading capabilities
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
        self.indicators = TechnicalIndicators(config)
        self.position_manager = EnhancedPositionManager(config, config.symbol)
        self.data: Optional[pd.DataFrame] = None
        self.signals: Optional[pd.DataFrame] = None
        self.last_signal_info = {'type': '-', 'bars_ago': 0}
        
        # Database integration
        if HAS_DATABASE:
            self.db = get_database()
        else:
            self.db = None
        
        # Initialize Binance provider
        try:
            self.binance_provider = BinanceDataProvider(config)
            self.live_system = LiveTradingSystem(config, self.binance_provider)
        except Exception as e:
            print(f"Warning: Could not initialize Binance provider: {e}")
            self.binance_provider = None
            self.live_system = None
    
    def fetch_data(self, symbol: Optional[str] = None,
                   interval: Optional[str] = None,
                   days: Optional[int] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch market data using Binance"""
        symbol = symbol or self.config.symbol
        interval = interval or self.config.interval

        if self.binance_provider:
            return self._fetch_binance_data(symbol, interval, days, start_date, end_date)
        else:
            raise ValueError("Binance provider not available")
    
    def _fetch_binance_data(self, symbol: str, interval: str, days: int = None, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """Fetch data from Binance - supports fetching full date ranges"""
        try:
            
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
            
            # Calculate required bars for date range
            if start_date and end_date:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                days = (end_dt - start_dt).days
            
            # Calculate total bars needed
            if interval.endswith('h'):
                bars_per_day = 24 // int(interval.replace('h', ''))
            elif interval.endswith('m'):
                bars_per_day = 1440 // int(interval.replace('m', ''))
            else:
                bars_per_day = 24  # Default for 1h
            
            total_bars_needed = days * bars_per_day
            
            # If we need more than 1000 bars, fetch in chunks
            if total_bars_needed > 1000 and start_date:
                print(f"[*] Fetching {total_bars_needed} bars in chunks (max 1000 per request)")
                data = self._fetch_data_in_chunks(symbol, interval, start_date, end_date)
            elif start_date:
                # Single request for smaller ranges
                data = self.binance_provider.get_historical_data(
                    symbol=symbol,
                    interval=interval,
                    limit=min(1000, total_bars_needed),
                    start_str=start_date
                )
            else:
                # Regular historical data fetch
                limit = min(1000, days * bars_per_day)
                data = self.binance_provider.get_historical_data(
                    symbol=symbol,
                    interval=interval,
                    limit=limit
                )
            
            if data is None or data.empty:
                raise ValueError(f"No data found for symbol {symbol}")
            
            # Convert timezone-aware index to timezone-naive for consistency
            if data.index.tz is not None:
                data.index = data.index.tz_localize(None)
            
            self.data = data
            return data
            
        except Exception as e:
            raise Exception(f"Error fetching data for {symbol}: {str(e)}")

    def _fetch_data_in_chunks(self, symbol: str, interval: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch large date ranges by combining multiple 1000-bar chunks"""
        try:
            all_data = []
            current_start = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Calculate interval in hours for chunk sizing
            if interval == '1h':
                interval_hours = 1
            elif interval == '4h':
                interval_hours = 4
            else:
                interval_hours = 1  # Default
            
            chunk_number = 0
            
            while current_start < end_dt:
                chunk_number += 1
                # Calculate chunk end (1000 bars ahead)
                chunk_hours = 1000 * interval_hours
                chunk_end = current_start + timedelta(hours=chunk_hours)
                
                # Don't go beyond requested end date
                if chunk_end > end_dt:
                    chunk_end = end_dt
                
                start_str = current_start.strftime("%Y-%m-%d")

                try:
                    chunk_data = self.binance_provider.get_historical_data(
                        symbol=symbol,
                        interval=interval,
                        limit=1000,
                        start_str=start_str
                    )

                    if chunk_data is not None and not chunk_data.empty:
                        all_data.append(chunk_data)
                    
                    # Small delay to avoid rate limits
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"[*] Warning: Failed to fetch chunk {chunk_number}: {e}")
                
                # Move to next chunk
                current_start = chunk_end
                
                # Safety limit
                if chunk_number >= 20:  # Max ~2 years of hourly data  
                    print(f"[*] Reached chunk limit ({chunk_number}), stopping")
                    break
            
            # Combine all chunks
            if all_data:
                combined_data = pd.concat(all_data, ignore_index=False)
                combined_data = combined_data.sort_index()
                combined_data = combined_data[~combined_data.index.duplicated(keep='first')]
                
                print(f"[*] Combined {len(combined_data)} total bars from {len(all_data)} chunks") 
                return combined_data
            else:
                raise ValueError("No data retrieved from any chunks")
                
        except Exception as e:
            raise Exception(f"Error fetching chunked data: {str(e)}")

    def detect_market_regime(self, data: pd.DataFrame, lookback_days: int = 90, quiet: bool = False) -> str:
        """
        MULTI-TIMEFRAME REGIME DETECTION
        Combines multiple timeframe analysis for robust regime identification
        Same logic for both backtesting and live trading - NO LOOK-AHEAD BIAS!
        """
        try:
            close = data['Close']
            
            # Define multiple timeframes OPTIMIZED FOR 1H TRADING
            timeframes = {
                'micro': 1,          # 1 day - intraday sentiment (most responsive)
                'nano': 2,           # 2 days - very short-term momentum
                'ultra_short': 3,    # 3 days - immediate market sentiment  
                'short': 7,          # 1 week - short-term trend
                'medium_short': 14,  # 2 weeks - swing trend
                'medium': 30,        # 1 month - monthly trend
                'long': 45,          # 6 weeks - medium-long context (reduced from 60d)
                'macro': 60          # 2 months - major trend context (reduced from 90d)
            }
            
            regime_signals = {}
            
            # Analyze each timeframe
            for tf_name, days in timeframes.items():
                lookback_bars = min(days * 24, len(close) - 20)  # 24 hours per day, keep smaller buffer
                
                if lookback_bars < 20:  # Need minimum data (reduced from 50 for shorter timeframes)
                    regime_signals[tf_name] = 'sideways'
                    continue
                
                recent_data = close.iloc[-lookback_bars:]
                start_price = recent_data.iloc[0]
                end_price = recent_data.iloc[-1]
                
                # Calculate metrics for this timeframe
                total_return = (end_price - start_price) / start_price * 100
                recent_returns = recent_data.pct_change().dropna()
                volatility = recent_returns.std() * 100
                
                # Calculate drawdown for crash detection
                rolling_max = recent_data.expanding().max()
                drawdown = (recent_data / rolling_max - 1) * 100
                max_drawdown = abs(drawdown.min())
                
                # Timeframe-specific thresholds RESTORED TO WORKING VERSION
                if tf_name == 'micro':  # 1 day - ultra sensitive
                    bull_thresh, bear_thresh, vol_thresh, dd_thresh = 3, -2, 1.5, 3
                elif tf_name == 'nano':  # 2 days - hyper sensitive
                    bull_thresh, bear_thresh, vol_thresh, dd_thresh = 4, -2.5, 1.8, 4
                elif tf_name == 'ultra_short':  # 3 days - very sensitive
                    bull_thresh, bear_thresh, vol_thresh, dd_thresh = 5, -3, 2.0, 5
                elif tf_name == 'short':  # 7 days - sensitive
                    bull_thresh, bear_thresh, vol_thresh, dd_thresh = 8, -4, 2.5, 8
                elif tf_name == 'medium_short':  # 14 days - moderate
                    bull_thresh, bear_thresh, vol_thresh, dd_thresh = 12, -6, 3.0, 10
                elif tf_name == 'medium':  # 30 days - balanced
                    bull_thresh, bear_thresh, vol_thresh, dd_thresh = 18, -8, 3.2, 15
                elif tf_name == 'long':  # 45 days - moderate-conservative
                    bull_thresh, bear_thresh, vol_thresh, dd_thresh = 22, -10, 3.4, 18
                else:  # macro - 60 days - conservative
                    bull_thresh, bear_thresh, vol_thresh, dd_thresh = 25, -12, 3.7, 22
                
                # Classify this timeframe
                is_crash = (volatility > 3.0) and (max_drawdown > dd_thresh)
                
                if total_return > bull_thresh:
                    regime_signals[tf_name] = 'bull'
                elif total_return < bear_thresh or is_crash:
                    regime_signals[tf_name] = 'bear'
                elif volatility > vol_thresh:
                    regime_signals[tf_name] = 'volatile'
                else:
                    regime_signals[tf_name] = 'sideways'
                
            # Consensus logic
            micro_regime = regime_signals.get('micro', 'sideways')
            nano_regime = regime_signals.get('nano', 'sideways')
            ultra_short_regime = regime_signals.get('ultra_short', 'sideways')
            short_regime = regime_signals.get('short', 'sideways')

            bull_votes = sum(1 for r in regime_signals.values() if r == 'bull')
            bear_votes = sum(1 for r in regime_signals.values() if r == 'bear')
            volatile_votes = sum(1 for r in regime_signals.values() if r == 'volatile')

            # Stable timeframes (30d/45d/60d) get priority for direction
            stable_bull_votes = sum(1 for tf in ['medium', 'long', 'macro'] if regime_signals.get(tf) == 'bull')
            stable_bear_votes = sum(1 for tf in ['medium', 'long', 'macro'] if regime_signals.get(tf) == 'bear')

            # Decision rules: stable consensus > strong majority > short-term override
            if stable_bull_votes >= 2:
                final_regime = 'bull'
            elif stable_bear_votes >= 2:
                final_regime = 'bear'
            elif bear_votes >= 5:
                final_regime = 'bear'
            elif bull_votes >= 5:
                final_regime = 'bull'
            elif micro_regime == 'bear' and bear_votes >= 3:
                final_regime = 'bear'
            elif micro_regime == 'bull' and bull_votes >= 3:
                final_regime = 'bull'
            elif nano_regime == 'bear' and bear_votes >= 3:
                final_regime = 'bear'
            elif nano_regime == 'bull' and bull_votes >= 3:
                final_regime = 'bull'
            elif ultra_short_regime == 'bear' and bear_votes >= 3:
                final_regime = 'bear'
            elif ultra_short_regime == 'bull' and bull_votes >= 3:
                final_regime = 'bull'
            elif short_regime == 'bear' and bear_votes >= 2:
                final_regime = 'bear'
            elif short_regime == 'bull' and bull_votes >= 2:
                final_regime = 'bull'
            elif volatile_votes >= 4:
                final_regime = 'volatile'
            elif bull_votes >= 3 and bear_votes >= 3:
                final_regime = 'volatile'
            else:
                final_regime = 'sideways'

            if not quiet:
                print(f"[*] Regime: {final_regime.upper()} (Bull={bull_votes}, Bear={bear_votes}, Stable={stable_bull_votes}B/{stable_bear_votes}S)")
            return final_regime
                
        except Exception as e:
            print(f"[*] Regime detection error: {e}")
            return 'sideways'
    
    def get_adaptive_config(self, regime: str) -> dict:
        """Balanced strategies optimized for overall performance"""
        
        # BALANCED BULL STRATEGY - Capture uptrends without overtrading
        bull_config = {
            'rsi_oversold': 40, 'rsi_overbought': 75,  
            'adx_min': 15, 'adx_max': 40, 'min_bars_gap': 4,
            'max_daily_trades': 4, 'enable_shorts': True,  # Moderate frequency
            'strategy': 'Balanced Trend Following', 'risk_level': 'Medium-High'
        }
        
        # ULTRA-CONSERVATIVE BEAR STRATEGY - Optimized for live trading robustness
        bear_config = {
            'rsi_oversold': 20, 'rsi_overbought': 55,   # Even tighter for better quality (was 25/60)
            'adx_min': 25, 'adx_max': 35, 'min_bars_gap': 18,  # Larger gap to avoid whipsaws (was 12, now 18)
            'max_daily_trades': 1, 'enable_shorts': True,  # Max 1 trade per day
            'strategy': 'Conservative Active Trading', 'risk_level': 'Very Low',
            'strict_trend_confirmation': True,
            'enhanced_volatility_filter': True,
            'require_momentum_confluence': True,  # Multiple momentum confirmations
            'dynamic_position_sizing': 0.5  # Half position size in bear markets
        }
        
        # MODERATE VOLATILE STRATEGY - Handle chop without overexposure
        volatile_config = {
            'rsi_oversold': 30, 'rsi_overbought': 70,  
            'adx_min': 20, 'adx_max': 35, 'min_bars_gap': 8,
            'max_daily_trades': 2, 'enable_shorts': True,  # Reduced frequency
            'strategy': 'Selective Swing Trading', 'risk_level': 'Medium'
        }
        
        # BALANCED SIDEWAYS STRATEGY - Range trading with discipline  
        sideways_config = {
            'rsi_oversold': 35, 'rsi_overbought': 70,  
            'adx_min': 18, 'adx_max': 30, 'min_bars_gap': 6,
            'max_daily_trades': 3, 'enable_shorts': True,
            'strategy': 'Disciplined Range Trading', 'risk_level': 'Medium'
        }
        
        # DEFAULT: Mixed/Unknown Market - Conservative Strategy
        default_config = {
            'rsi_oversold': 28, 'rsi_overbought': 72,
            'adx_min': 22, 'adx_max': 38, 'min_bars_gap': 6,
            'max_daily_trades': 2, 'enable_shorts': True,
            'strategy': 'Conservative', 'risk_level': 'Low'
        }
        
        configs = {
            'bull': bull_config,
            'bear': bear_config, 
            'volatile': volatile_config,
            'sideways': sideways_config,
            'mixed': default_config,
            'unknown': default_config
        }
        
        selected_config = configs.get(regime, default_config)
        print(f"[*] Strategy: {selected_config['strategy']} (Risk: {selected_config['risk_level']})")
        
        return selected_config

    def calculate_signals(self, regime_override: str = None) -> pd.DataFrame:
        """Calculate all trading signals with adaptive regime-based parameters"""
        if self.data is None:
            raise ValueError("No data available. Call fetch_data() first.")

        # Detect market regime (or use override for dynamic backtesting)
        if regime_override:
            regime = regime_override
            adaptive_config = self.get_adaptive_config(regime)
        else:
            regime = self.detect_market_regime(
                self.data,
                lookback_days=self.config.regime_lookback_days
            )
            adaptive_config = self.get_adaptive_config(regime)
        
        print(f"[*] Regime: {regime.upper()} | Strategy: {adaptive_config.get('strategy', 'Unknown')} | RSI: {adaptive_config['rsi_oversold']}/{adaptive_config['rsi_overbought']}")
        
        # Store adaptive config for use in signal generation
        self.current_regime = regime
        self.adaptive_config = adaptive_config
        
        # Calculate all indicators
        all_indicators = self.indicators.calculate_all_indicators(self.data)
        
        # Get setup signals
        setup_signals = self.indicators.get_setup_signals(all_indicators)
        
        # Create comprehensive signals DataFrame
        signals_df = pd.DataFrame(index=self.data.index)
        
        # Basic price data
        signals_df['open'] = self.data['Open']
        signals_df['high'] = self.data['High']
        signals_df['low'] = self.data['Low']
        signals_df['close'] = self.data['Close']
        signals_df['volume'] = self.data.get('Volume', 0)
        
        # Moving averages
        for name, series in all_indicators['ema'].items():
            signals_df[name] = series
        
        # Technical indicators
        signals_df['rsi'] = all_indicators['rsi']
        for name, series in all_indicators['macd'].items():
            signals_df[name] = series
        signals_df['atr'] = all_indicators['atr']

        # ADX indicators
        for name, series in all_indicators['adx'].items():
            signals_df[f'adx_{name}'] = series

        # Trend analysis
        for name, series in all_indicators['trend'].items():
            signals_df[f'trend_{name}'] = series
        
        # Momentum analysis
        for name, series in all_indicators['momentum'].items():
            signals_df[f'momentum_{name}'] = series
        
        # Price action
        for name, series in all_indicators['price_action'].items():
            signals_df[f'price_{name}'] = series
        
        # Volume analysis
        for name, series in all_indicators['volume'].items():
            signals_df[f'volume_{name}'] = series
        
        # Advanced market conditions
        if 'advanced' in all_indicators:
            for name, series in all_indicators['advanced'].items():
                signals_df[f'advanced_{name}'] = series
        
        # Setup signals
        for name, series in setup_signals.items():
            signals_df[f'setup_{name}'] = series
        
        # Generate entry triggers
        signals_df = self._generate_entry_signals(signals_df)
        
        self.signals = signals_df
        return signals_df
    
    def _generate_entry_signals(self, signals_df: pd.DataFrame) -> pd.DataFrame:
        """Generate buy and sell entry signals with professional confluence requirements"""
        
        # ============ PROFESSIONAL BUY CRITERIA ============
        # 1. Basic Setup: EMA alignment (from original logic)
        basic_buy_setup = signals_df['setup_buy_setup']
        
        # 2. Enhanced RSI Criteria (much more restrictive)
        rsi_buy_criteria = (
            (signals_df['rsi'] > 40) &  # RSI above 40 (not oversold)
            (signals_df['rsi'] < 75) &  # RSI below 75 (not too overbought)
            signals_df['advanced_rsi_bull_momentum']  # RSI rising with good momentum
        )
        
        # 3. Enhanced MACD Criteria
        macd_buy_criteria = (
            (signals_df['macd_line'] > signals_df['signal_line']) &  # MACD bullish
            (signals_df['histogram'] > 0) &  # Histogram positive
            signals_df['advanced_macd_accelerating_bull']  # MACD accelerating
        )
        
        # 4. Market Condition Filters
        # Enhanced with ADX-based regime filtering
        if self.config.enable_regime_filter:
            # OPTIMAL ADX RANGE: 20-30 (based on backtest analysis)
            # Filter out: ADX < 20 (choppy) AND ADX > 30 (extreme volatility)
            market_conditions_buy = (
                ~signals_df['advanced_adx_choppy'] &  # Not choppy (ADX > 20)
                ~signals_df['advanced_adx_strong_trending'] &  # Not extreme (ADX < 30)
                signals_df['advanced_trending_market'] &  # Price action confirms trend
                signals_df['advanced_strong_bull_trend'] &  # Strong bullish trend
                signals_df['advanced_price_momentum_bull'] &  # Price momentum
                ~signals_df['advanced_high_volatility']  # Avoid high volatility periods
            )
        else:
            # Original filtering without regime filter
            market_conditions_buy = (
                signals_df['advanced_trending_market'] &  # Only trade in trending markets
                signals_df['advanced_strong_bull_trend'] &  # Strong bullish trend
                signals_df['advanced_price_momentum_bull'] &  # Price momentum
                ~signals_df['advanced_high_volatility']  # Avoid high volatility periods
            )
        
        # 5. Volume Confirmation
        volume_buy = signals_df['volume_vol_bull']
        
        # CONFLUENCE BUY SIGNAL: Requires ALL conditions
        professional_buy_trigger = (
            basic_buy_setup &
            rsi_buy_criteria &
            macd_buy_criteria &
            market_conditions_buy &
            volume_buy
        )
        
        # ============ PROFESSIONAL SELL CRITERIA ============
        # 1. Basic Setup: EMA alignment (from original logic)
        basic_sell_setup = signals_df['setup_sell_setup']
        
        # 2. Enhanced RSI Criteria
        rsi_sell_criteria = (
            (signals_df['rsi'] > 25) &  # RSI above 25 (not too oversold)
            (signals_df['rsi'] < 60) &  # RSI below 60 (not overbought)
            signals_df['advanced_rsi_bear_momentum']  # RSI falling with good momentum
        )
        
        # 3. Enhanced MACD Criteria
        macd_sell_criteria = (
            (signals_df['macd_line'] < signals_df['signal_line']) &  # MACD bearish
            (signals_df['histogram'] < 0) &  # Histogram negative
            signals_df['advanced_macd_accelerating_bear']  # MACD accelerating down
        )
        
        # 4. Market Condition Filters
        # Enhanced with ADX-based regime filtering
        if self.config.enable_regime_filter:
            # OPTIMAL ADX RANGE: 20-30 (based on backtest analysis)
            # Filter out: ADX < 20 (choppy) AND ADX > 30 (extreme volatility)
            market_conditions_sell = (
                ~signals_df['advanced_adx_choppy'] &  # Not choppy (ADX > 20)
                ~signals_df['advanced_adx_strong_trending'] &  # Not extreme (ADX < 30)
                signals_df['advanced_trending_market'] &  # Price action confirms trend
                signals_df['advanced_strong_bear_trend'] &  # Strong bearish trend
                signals_df['advanced_price_momentum_bear'] &  # Price momentum
                ~signals_df['advanced_high_volatility']  # Avoid high volatility periods
            )
        else:
            # Original filtering without regime filter
            market_conditions_sell = (
                signals_df['advanced_trending_market'] &  # Only trade in trending markets
                signals_df['advanced_strong_bear_trend'] &  # Strong bearish trend
                signals_df['advanced_price_momentum_bear'] &  # Price momentum
                ~signals_df['advanced_high_volatility']  # Avoid high volatility periods
            )
        
        # 5. Volume Confirmation
        volume_sell = signals_df['volume_vol_bear']
        
        # CONFLUENCE SELL SIGNAL: Requires ALL conditions
        professional_sell_trigger = (
            basic_sell_setup &
            rsi_sell_criteria &
            macd_sell_criteria &
            market_conditions_sell &
            volume_sell
        )
        
        # ============ QUALITY-FOCUSED ENTRY LOGIC - Research-Based Improvements ============
        # Use configuration to determine which signal logic to apply
        if self.config.require_confluence:
            # Use professional confluence signals
            buy_trigger = professional_buy_trigger
            sell_trigger = professional_sell_trigger
        else:
            # SIMPLIFIED ADAPTIVE TRADING STRATEGIES (No dependency on setup signals)
            regime = getattr(self, 'current_regime', 'mixed')
            adaptive_config = getattr(self, 'adaptive_config', {})

            adaptive_rsi_oversold = adaptive_config.get('rsi_oversold', 30)
            adaptive_rsi_overbought = adaptive_config.get('rsi_overbought', 75)
            
            # Check if we have required columns, create basic conditions if missing
            has_setup_signals = 'setup_buy_setup' in signals_df.columns and 'setup_sell_setup' in signals_df.columns
            has_volume_signals = 'volume_vol_bull' in signals_df.columns and 'volume_vol_bear' in signals_df.columns
            has_macd = 'macd_line' in signals_df.columns and 'signal_line' in signals_df.columns
            has_emas = 'ema_20' in signals_df.columns and 'ema_50' in signals_df.columns
            
            # Basic always-true conditions if setup signals missing
            if has_setup_signals:
                basic_buy_condition = signals_df['setup_buy_setup']
                basic_sell_condition = signals_df['setup_sell_setup']
            else:
                # Create simple EMA-based conditions or fallback to price action
                if has_emas:
                    basic_buy_condition = signals_df['close'] > signals_df['ema_20']
                    basic_sell_condition = signals_df['close'] < signals_df['ema_20']
                else:
                    # Last resort - simple price momentum
                    basic_buy_condition = signals_df['close'] > signals_df['close'].shift(1)
                    basic_sell_condition = signals_df['close'] < signals_df['close'].shift(1)
            
            # MACD conditions with fallbacks
            if has_macd:
                macd_bullish = signals_df['macd_line'] > signals_df['signal_line']
                macd_bearish = signals_df['macd_line'] < signals_df['signal_line']
            else:
                # Fallback to simple momentum
                macd_bullish = signals_df['close'] > signals_df['close'].rolling(5).mean()
                macd_bearish = signals_df['close'] < signals_df['close'].rolling(5).mean()
            
            # Volume conditions
            if has_volume_signals:
                volume_buy_condition = signals_df['volume_vol_bull']
                volume_sell_condition = signals_df['volume_vol_bear']
            else:
                volume_buy_condition = pd.Series(True, index=signals_df.index)
                volume_sell_condition = pd.Series(True, index=signals_df.index)
            
            # STRATEGY 1: BULL MARKET - Ultra Active Trend Following (maximum opportunities)  
            if regime == 'bull':
                buy_trigger = (
                    basic_buy_condition &
                    (
                        # VERY flexible RSI - almost all conditions accepted
                        (signals_df['rsi'] > 20) &  # Not in extreme panic
                        (signals_df['rsi'] < 85)    # Not in extreme euphoria
                    ) &
                    (  # Multiple MACD/trend options - at least ONE must be true
                        macd_bullish |  # MACD/momentum bullish OR
                        (signals_df['close'] > signals_df.get('ema_50', signals_df['close'] * 0.98)) |  # Above EMA50 OR
                        (signals_df['close'] > signals_df.get('ema_20', signals_df['close'] * 0.99)) |  # Above EMA20 OR
                        (signals_df['close'].pct_change(5) > 0.02) |  # 2%+ gain in 5 bars OR
                        (signals_df['close'].rolling(3).mean() > signals_df['close'].rolling(10).mean())  # 3-bar > 10-bar average
                    )
                    # No volume requirement for bull markets!
                )
                
                sell_trigger = (
                    basic_sell_condition &
                    (signals_df['rsi'] > 65) &
                    (signals_df['macd_line'] < signals_df['signal_line']) &
                    volume_sell_condition
                )
            
            # STRATEGY 2: BEAR MARKET - Ultra Conservative with Enhanced Quality (Live Trading Optimized)
            elif regime == 'bear':
                # Multi-layer volatility protection for live trading robustness
                extreme_conditions = (
                    (signals_df['close'].pct_change(5) < -0.08) |  # 8%+ crash in 5 bars (tighter)
                    (abs(signals_df['close'].pct_change()) > 0.05) |  # 5%+ single bar move (tighter)
                    (signals_df['rsi'].rolling(3).std() > 6) |  # RSI volatility (tighter)
                    (signals_df['close'].rolling(10).std() / signals_df['close'].rolling(10).mean() > 0.04)  # Price volatility check
                )
                
                # Enhanced market stress detection
                market_stress = (
                    (signals_df['close'] < signals_df.get('ema_200', signals_df['close'] * 1.05)) &  # Below 200 EMA
                    (signals_df['adx_adx'] > 30) &  # High ADX (was 35, now 30)
                    (signals_df['volume'] > signals_df['volume'].rolling(20).mean() * 1.5)  # High volume stress
                )
                
                # Momentum confluence requirement
                momentum_confluence = (
                    (signals_df['rsi'] > signals_df['rsi'].shift(3)) &  # RSI rising for 3+ bars
                    (signals_df['macd_line'] > signals_df['macd_line'].shift(2)) &  # MACD improving
                    (signals_df['close'] > signals_df['close'].rolling(5).mean())  # Above 5-bar average
                )

                # ULTRA conservative bear market buy: maximum quality filter
                buy_trigger = (
                    ~extreme_conditions &
                    ~market_stress &
                    basic_buy_condition &
                    momentum_confluence &
                    (signals_df['rsi'] > 20) & (signals_df['rsi'] < 40) &  # Very tight RSI (was 25-45)
                    (signals_df['close'] > signals_df.get('ema_20', signals_df['close'] * 0.99)) &  # Above 20 EMA
                    macd_bullish
                )

                # Ultra-selective shorts with quality focus
                sell_trigger = (
                    ~extreme_conditions &
                    (signals_df['close'] < signals_df.get('ema_50', signals_df['close'] * 1.02)) &  # Below 50 EMA (was 20)
                    (signals_df['rsi'] > 65) &  # Higher threshold (was 60)
                    macd_bearish &
                    volume_sell_condition &
                    (signals_df['adx_adx'] > 20) &  # Trending market
                    (signals_df['rsi'] < signals_df['rsi'].shift(2))  # RSI declining
                )
            
            # STRATEGY 3: VOLATILE MARKET - Ultra Selective Swing Trading
            elif regime == 'volatile':
                # Enhanced volatility filters for choppy markets
                volatility_conditions = (
                    # 1. RSI stability filter - avoid erratic RSI movements
                    (signals_df['rsi'].rolling(3).std() < 5) &  # RSI stable over 3 bars
                    # 2. Price action filter - avoid whipsaws
                    (abs(signals_df['close'].pct_change()) < 0.05) &  # No >5% single-bar moves
                    # 3. Trend consistency filter
                    (signals_df['ema_20'].diff().rolling(3).apply(lambda x: (x > 0).sum()) >= 2)  # EMA20 rising in 2/3 bars
                )
                
                buy_trigger = (
                    basic_buy_condition &
                    volatility_conditions &  # Must pass volatility filters
                    (signals_df['rsi'] < adaptive_rsi_oversold) &
                    macd_bullish &
                    volume_buy_condition
                )
                
                sell_trigger = (
                    basic_sell_condition &
                    volatility_conditions &  # Must pass volatility filters
                    (signals_df['rsi'] > adaptive_rsi_overbought) &
                    macd_bearish &
                    volume_sell_condition
                )
            
            # DEFAULT: All other regimes use balanced approach
            else:
                buy_trigger = (
                    basic_buy_condition &
                    (signals_df['rsi'] > adaptive_rsi_oversold) &
                    (signals_df['rsi'] < adaptive_rsi_overbought) &
                    macd_bullish &
                    volume_buy_condition
                )
                
                sell_trigger = (
                    basic_sell_condition &
                    (signals_df['rsi'] > adaptive_rsi_oversold) &
                    (signals_df['rsi'] < adaptive_rsi_overbought) &
                    macd_bearish &
                    volume_sell_condition
                )

        # Apply ADX filtering - relaxed for bull markets
        if self.config.enable_regime_filter:
            current_regime = getattr(self, 'current_regime', 'sideways')
            
            if current_regime == 'bull':
                # BULL MARKETS: Very relaxed ADX filtering - allow most conditions
                adx_filter_buy = pd.Series(True, index=signals_df.index)  # Allow all ADX conditions in bull
                adx_filter_sell = (
                    ~signals_df['advanced_adx_choppy'] &  # Not choppy (ADX > 18)
                    ~signals_df['advanced_adx_strong_trending']  # Not extreme (ADX < 35) for shorts
                )
            else:
                # BEAR/VOLATILE: Original restrictive filtering
                adx_filter_buy = (~signals_df['advanced_adx_choppy'])  # Only avoid choppy markets
                adx_filter_sell = (
                    ~signals_df['advanced_adx_choppy'] &  # Not choppy (ADX > 18)
                    ~signals_df['advanced_adx_strong_trending']  # Not extreme (ADX < 35) for shorts
                )
                
                buy_trigger = buy_trigger & adx_filter_buy
                sell_trigger = sell_trigger & adx_filter_sell
        
        # CONDITIONAL MARKET STRESS FILTER - Strict in Bear/Volatile, Relaxed in Bull
        # Get current regime for conditional filtering
        current_regime = getattr(self, 'current_regime', 'sideways')
        
        if current_regime == 'bear':
            # Moderate bear market filtering - avoid only catastrophic conditions
            market_stress_conditions = (
                # 1. Major price crash filter (>15% drop in 24 bars)
                (signals_df['close'].pct_change(24) < -0.15) |
                # 2. Extreme volatility filter (price swings >10% in single bar)
                (abs(signals_df['close'].pct_change()) > 0.10) |
                # 3. Severe RSI crash filter (RSI drops >35 points in 10 bars)
                (signals_df['rsi'].diff(10) < -35)
            )
        elif current_regime == 'volatile':
            # MODERATE volatile market filtering - avoid extreme spikes only
            market_stress_conditions = (
                # 1. Extreme single-bar moves only
                (abs(signals_df['close'].pct_change()) > 0.12) |
                # 2. Panic volume only  
                (signals_df.get('volume', pd.Series(0, index=signals_df.index)).rolling(1).mean() > 
                 signals_df.get('volume', pd.Series(1, index=signals_df.index)).rolling(20).mean() * 8) |
                # 3. Severe RSI crashes only
                (signals_df['rsi'].diff(5) < -40)
            )
        else:  # bull or sideways markets
            # MINIMAL bull market filtering - only avoid absolute catastrophes  
            market_stress_conditions = (
                # 1. Only filter catastrophic crashes (>20% single-bar drop)
                (signals_df['close'].pct_change() < -0.20) |
                # 2. Only filter extreme panic volume (>15x normal)
                (signals_df.get('volume', pd.Series(0, index=signals_df.index)).rolling(1).mean() > 
                 signals_df.get('volume', pd.Series(1, index=signals_df.index)).rolling(20).mean() * 15)
            )
        
        # Apply stress filter
        buy_trigger = buy_trigger & ~market_stress_conditions
        sell_trigger = sell_trigger & ~market_stress_conditions
        buy_signal = buy_trigger
        sell_signal = sell_trigger
        
        # Apply gap filter to prevent too frequent signals - DYNAMIC BASED ON REGIME
        buy_final = buy_signal.copy()
        sell_final = sell_signal.copy()

        # Dynamic gap based on market regime - optimized for live trading stability
        current_regime = getattr(self, 'current_regime', 'sideways')
        if current_regime == 'bear':
            min_gap = max(self.config.min_bars_gap, 20)  # Minimum 20 bars in bear markets (more selective)
        elif current_regime == 'volatile':
            min_gap = max(self.config.min_bars_gap, 15)  # Minimum 15 bars in volatile markets
        elif current_regime == 'bull':
            min_gap = max(1, self.config.min_bars_gap // 2)  # REDUCED gap in bull markets for more opportunities
        else:
            min_gap = self.config.min_bars_gap  # Normal gap for sideways markets
        
        if min_gap > 1:
            # Apply minimum gap between signals
            last_signal_idx = None

            for i in range(len(signals_df)):
                current_signal = buy_signal.iloc[i] or sell_signal.iloc[i]

                if current_signal:
                    if last_signal_idx is None or i - last_signal_idx >= min_gap:
                        last_signal_idx = i
                    else:
                        # Gap too small, filter out this signal
                        buy_final.iloc[i] = False
                        sell_final.iloc[i] = False
        
        # Store all signals for analysis and debugging
        signals_df['professional_buy_trigger'] = professional_buy_trigger
        signals_df['professional_sell_trigger'] = professional_sell_trigger
        signals_df['buy_trigger'] = buy_trigger
        signals_df['sell_trigger'] = sell_trigger  
        signals_df['buy_signal'] = buy_signal
        signals_df['sell_signal'] = sell_signal
        
        # Final confirmed signals
        signals_df['buy_confirmed'] = buy_final
        signals_df['sell_confirmed'] = sell_final
        
        return signals_df
    
    def _get_market_regime(self, row: pd.Series) -> str:
        """Determine market regime from signal row"""
        if not getattr(self.config, 'enable_adaptive_parameters', False):
            return 'normal'

        # Check regime flags in order of priority
        if row.get('advanced_regime_choppy', False):
            return 'choppy'
        elif row.get('advanced_regime_strong_trending', False):
            return 'strong_trending'
        elif row.get('advanced_regime_normal_trending', False):
            return 'normal'
        else:
            return 'normal'

    def run_backtest(self, start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> Dict[str, Any]:
        """Run complete backtest simulation with database integration"""
        if self.data is None:
            raise ValueError("No data available. Call fetch_data() first.")

        data = self.data.copy()
        if start_date:
            data = data[data.index >= pd.to_datetime(start_date)]
        if end_date:
            data = data[data.index <= pd.to_datetime(end_date)]

        self.position_manager.reset()

        buy_signals = []
        sell_signals = []
        exits = []

        print(f"[*] Running backtest on {len(data)} bars...")

        # Calculate intervals for periodic regime re-detection
        interval = getattr(self.config, 'interval', '1h')
        if interval.endswith('h'):
            bars_per_day = 24 // max(1, int(interval.replace('h', '')))
        elif interval.endswith('m'):
            bars_per_day = 1440 // max(1, int(interval.replace('m', '')))
        else:
            bars_per_day = 24
        regime_update_interval = bars_per_day * 7   # Re-detect weekly
        min_regime_bars = bars_per_day * 30          # Need 30 days minimum
        max_regime_lookback = bars_per_day * 60      # Use 60 days for detection

        # Use regime from signal calculation, or detect if missing
        if not hasattr(self, 'current_regime') or not hasattr(self, 'adaptive_config'):
            if start_date or end_date:
                if self.signals is None:
                    self.calculate_signals()
            else:
                full_data_regime = self.detect_market_regime(
                    self.data,
                    lookback_days=self.config.regime_lookback_days
                )
                self.current_regime = full_data_regime
                self.adaptive_config = self.get_adaptive_config(full_data_regime)

        current_regime = self.current_regime
        regime_changes = 0

        if self.signals is None:
            self.calculate_signals()

        # Filter signals to match backtest data range
        filtered_signals = self.signals.loc[data.index] if len(self.signals) > 0 else None

        for i, (timestamp, row) in enumerate(data.iterrows()):
            self.position_manager.update_bar(i)

            if i == 0:
                self.current_regime = current_regime
                self.adaptive_config = self.get_adaptive_config(current_regime)

            # Periodic regime re-detection with stability filtering (live trading optimized)
            if i > 0 and i % regime_update_interval == 0 and i >= min_regime_bars:
                past_data = data.iloc[max(0, i - max_regime_lookback):i + 1]
                new_regime = self.detect_market_regime(past_data, quiet=True)
                
                # STABILITY FILTER: Require regime to persist for multiple detection cycles
                min_regime_persistence = regime_update_interval * 2  # Must persist for 2 cycles (2 weeks)
                
                # Check if we're in a recent regime change period
                bars_since_last_change = i - getattr(self, 'last_regime_change_bar', 0)
                
                if new_regime != current_regime and bars_since_last_change >= min_regime_persistence:
                    # Additional confirmation: check if new regime is stable over shorter timeframe
                    shorter_data = data.iloc[max(0, i - regime_update_interval):i + 1]
                    confirmation_regime = self.detect_market_regime(shorter_data, quiet=True)
                    
                    # Only change if both long and short timeframes agree
                    if confirmation_regime == new_regime:
                        print(f"[*] Regime change at bar {i}: {current_regime.upper()} -> {new_regime.upper()}")
                        current_regime = new_regime
                        self.last_regime_change_bar = i
                        self.calculate_signals(regime_override=new_regime)
                        filtered_signals = self.signals.loc[data.index] if len(self.signals) > 0 else None
                        regime_changes += 1
                    # else: Skip regime change due to instability

            # Get current bar signals
            if filtered_signals is not None and timestamp in filtered_signals.index:
                current_bar_signals = filtered_signals.loc[timestamp]
            else:
                close_price = row.get('Close', row.get('close', 0))
                current_bar_signals = pd.Series({
                    'buy_confirmed': False, 'sell_confirmed': False,
                    'close': close_price, 'rsi': 50, 'atr': close_price * 0.02
                })
            
            # Check for exit conditions first
            if self.position_manager.is_in_trade():
                # Update trailing stop
                close_price = current_bar_signals.get('close', row.get('Close', row.get('close', 0)))
                current_atr = current_bar_signals.get('atr', close_price * 0.02)
                self.position_manager.update_trailing_stop(close_price, current_atr)
                
                # Check exit conditions using dynamic signals
                should_exit, exit_reason = self.position_manager.check_exit_conditions(
                    current_bar_signals['close'], timestamp, 
                    sell_signal=current_bar_signals.get('sell_confirmed', False),
                    buy_signal=current_bar_signals.get('buy_confirmed', False)
                )
                
                if should_exit:
                    trade = self.position_manager.exit_position(
                        current_bar_signals['close'], timestamp, exit_reason
                    )
                    if trade:  # Only add to exits if trade was successful
                        exits.append({
                            'timestamp': timestamp,
                            'price': current_bar_signals['close'],
                            'trade': trade
                        })
                        
                        # Log exit to database if available
                        if self.db:
                            self.db.save_signal(
                                symbol=getattr(self.config, 'symbol', 'BTCUSDT'),
                                signal_type='EXIT',
                                price=current_bar_signals['close'],
                                timestamp=timestamp,
                                exit_reason=exit_reason
                            )
            
            # Check for new entry signals (only when not in trade)
            if not self.position_manager.is_in_trade() and self.position_manager.can_enter_trade():
                buy_confirmed = current_bar_signals.get('buy_confirmed', False)

                if buy_confirmed:
                    market_regime = getattr(self, 'current_regime', 'sideways')
                    success = self.position_manager.enter_long_position(
                        current_bar_signals['close'], timestamp,
                        current_bar_signals.get('atr', current_bar_signals['close'] * 0.02),
                        market_regime=market_regime
                    )
                    if success:
                        buy_signals.append({
                            'timestamp': timestamp,
                            'price': current_bar_signals['close'],
                            'type': 'BUY',
                            'regime': market_regime
                        })
                        self._update_last_signal_info('BUY', i)

                        if self.db:
                            self.db.save_signal(
                                symbol=getattr(self.config, 'symbol', 'BTCUSDT'),
                                signal_type='BUY',
                                price=current_bar_signals['close'],
                                timestamp=timestamp,
                                rsi=current_bar_signals.get('rsi'),
                                macd_histogram=current_bar_signals.get('histogram')
                            )
                    
                elif current_bar_signals.get('sell_confirmed', False):
                    market_regime = getattr(self, 'current_regime', 'sideways')
                    success = self.position_manager.enter_short_position(
                        current_bar_signals['close'], timestamp,
                        current_bar_signals.get('atr', current_bar_signals['close'] * 0.02),
                        market_regime=market_regime
                    )
                    if success:
                        sell_signals.append({
                            'timestamp': timestamp,
                            'price': current_bar_signals['close'],
                            'type': 'SELL',
                            'regime': market_regime
                        })
                        self._update_last_signal_info('SELL', i)

                        if self.db:
                            self.db.save_signal(
                                symbol=getattr(self.config, 'symbol', 'BTCUSDT'),
                                signal_type='SELL',
                                price=current_bar_signals['close'],
                                timestamp=timestamp,
                                rsi=current_bar_signals.get('rsi'),
                                macd_histogram=current_bar_signals.get('histogram')
                            )
            
            # Update last signal bars ago
            self._update_signal_bars_ago(i)
        
        if regime_changes > 0:
            print(f"[*] Total regime changes during backtest: {regime_changes}")
            print(f"[*] Final regime: {current_regime.upper()}")

        # Force exit any remaining position
        if self.position_manager.is_in_trade():
            final_row = data.iloc[-1]
            final_close = final_row.get('Close', final_row.get('close', final_row.iloc[3]))  # Handle different column names
            trade = self.position_manager.exit_position(
                final_close, final_row.name, "End of Data"
            )
            if trade:
                exits.append({
                    'timestamp': final_row.name,
                    'price': final_close,
                    'trade': trade
                })
        
        results = {
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'exits': exits,
            'trades': self.position_manager.trade_history,
            'statistics': self.position_manager.get_trade_statistics(),
            'data': data,
            'symbol': getattr(self.config, 'symbol', 'BTCUSDT'),
            'config': self.config,
            'regime_changes': regime_changes,
            'final_regime': getattr(self, 'current_regime', 'unknown')
        }
        
        return results
    
    def _update_last_signal_info(self, signal_type: str, bar_index: int):
        """Update last signal information"""
        self.last_signal_info = {
            'type': signal_type,
            'bar_index': bar_index,
            'bars_ago': 0
        }
    
    def _update_signal_bars_ago(self, current_bar: int):
        """Update bars since last signal"""
        if 'bar_index' in self.last_signal_info:
            self.last_signal_info['bars_ago'] = current_bar - self.last_signal_info['bar_index']
    
    def get_current_market_status(self) -> Dict[str, Any]:
        """Get current market analysis status"""
        if self.signals is None or self.signals.empty:
            return {'error': 'No signals available'}
        
        latest = self.signals.iloc[-1]
        
        # Trend analysis
        trend_status = latest.get('trend_trend_status', 'Unknown')
        trend_percentage = (latest['ema_20'] / latest['ema_200'] - 1) * 100 if 'ema_20' in latest and 'ema_200' in latest else 0
        
        # RSI status with adaptive thresholds
        rsi_value = latest.get('rsi', 50)
        adaptive_rsi_oversold = getattr(self, 'adaptive_config', {}).get('rsi_oversold', self.config.rsi_oversold)
        adaptive_rsi_overbought = getattr(self, 'adaptive_config', {}).get('rsi_overbought', self.config.rsi_overbought)
        
        if rsi_value > adaptive_rsi_overbought:
            rsi_status = 'Overbought'
        elif rsi_value < adaptive_rsi_oversold:
            rsi_status = 'Oversold'
        else:
            rsi_status = 'Neutral'
        
        # MACD status
        macd_hist = latest.get('histogram', 0)
        if latest.get('momentum_macd_rising', False) and latest.get('macd_line', 0) > latest.get('signal_line', 0):
            macd_status = 'Bullish Rising'
        elif latest.get('macd_line', 0) > latest.get('signal_line', 0):
            macd_status = 'Bullish'
        elif latest.get('momentum_macd_falling', False) and latest.get('macd_line', 0) < latest.get('signal_line', 0):
            macd_status = 'Bearish Falling'
        else:
            macd_status = 'Bearish'
        
        # Setup status
        if latest.get('setup_buy_setup', False):
            setup_status = 'BUY ZONE'
        elif latest.get('setup_sell_setup', False):
            setup_status = 'SELL ZONE'
        else:
            setup_status = 'Neutral'
        
        # Position status
        position_status = self.position_manager.get_position_status()
        current_pnl = 0.0
        if self.position_manager.is_in_trade():
            current_pnl = self.position_manager.get_current_pnl(latest['close'])
            position_status['pnl_percent'] = current_pnl
        
        return {
            'timestamp': latest.name,
            'price': latest['close'],
            'trend': {
                'status': trend_status,
                'percentage': trend_percentage
            },
            'rsi': {
                'value': rsi_value,
                'status': rsi_status
            },
            'macd': {
                'histogram': macd_hist,
                'status': macd_status
            },
            'setup': {
                'status': setup_status
            },
            'position': position_status,
            'atr': latest.get('atr', latest['close'] * 0.02),
            'last_signal': self.last_signal_info
        }
    
    def get_live_signals(self) -> Dict[str, bool]:
        """Get current live trading signals"""
        if self.signals is None or self.signals.empty:
            return {'buy_signal': False, 'sell_signal': False, 'buy_setup': False, 'sell_setup': False, 'in_trade': False}
        
        latest = self.signals.iloc[-1]
        
        # Check if we can enter new trades
        can_trade = self.position_manager.can_enter_trade()
        
        return {
            'buy_signal': latest.get('buy_confirmed', False) and can_trade,
            'sell_signal': latest.get('sell_confirmed', False) and can_trade,
            'buy_setup': latest.get('setup_buy_setup', False),
            'sell_setup': latest.get('setup_sell_setup', False),
            'in_trade': self.position_manager.is_in_trade()
        }
    
    def export_results(self, results: Dict[str, Any], filename: str = "trading_results.csv"):
        """Export trading results to CSV"""
        if not results['trades']:
            print("No trades to export")
            return
        
        # Convert trades to DataFrame
        trades_data = []
        for trade in results['trades']:
            if trade is None:
                continue  # Skip None trades
            trades_data.append({
                'Entry Time': trade.entry_time,
                'Exit Time': trade.exit_time,
                'Type': trade.trade_type,
                'Entry Price': trade.entry_price,
                'Exit Price': trade.exit_price,
                'P&L %': trade.pnl_percent,
                'P&L Amount': trade.pnl_amount,
                'Exit Reason': trade.exit_reason,
                'Duration': trade.duration_bars,
                'Quantity': trade.quantity
            })
        
        trades_df = pd.DataFrame(trades_data)
        trades_df.to_csv(filename, index=False)
        print(f"Results exported to {filename}")
    
    def print_statistics(self, results: Dict[str, Any]):
        """Print comprehensive trading statistics"""
        stats = results['statistics']
        
        print("\n" + "="*60)
        print("PRO TRADER SYSTEM PERFORMANCE STATISTICS")
        print("="*60)
        
        print(f"Symbol: {results.get('symbol', 'Unknown')}")
        print(f"Period: {results['data'].index[0].date()} to {results['data'].index[-1].date()}")
        print(f"Total Bars: {len(results['data'])}")
        
        print(f"\n[*] Trade Statistics:")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Winning Trades: {stats['winning_trades']}")
        print(f"Losing Trades: {stats['losing_trades']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        
        print(f"\n[*] Performance Metrics:")
        print(f"Average Win: {stats['avg_win']:.2f}%")
        print(f"Average Loss: {stats['avg_loss']:.2f}%")
        print(f"Total P&L: {stats['total_pnl']:.2f}%")
        if 'total_amount_pnl' in stats:
            print(f"Total P&L Amount: ${stats['total_amount_pnl']:.2f}")
        print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")

        print("="*60)
    
    def start_live_trading(self, symbol: Optional[str] = None, 
                          interval: Optional[str] = None) -> bool:
        """Start live trading with real-time data and order execution"""
        if not self.live_system:
            print("❌ Live trading requires Binance integration")
            return False
        
        symbol = symbol or self.config.symbol
        interval = interval or self.config.interval
        
        print(f"[*] Starting live trading for {symbol} {interval}")
        
        # Check if live trading is enabled (API keys provided)
        if not self.binance_provider.is_live_trading:
            print("⚠️ Live trading not enabled - API keys required for order execution")
            return False
        
        return self.live_system.start_live_monitoring(symbol, interval)
    
    def stop_live_trading(self):
        """Stop live trading"""
        if self.live_system:
            self.live_system.stop_monitoring()
        print("[*] Live trading stopped")
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        if self.live_system:
            return self.live_system.get_portfolio_status()
        elif self.db:
            return self.db.get_portfolio_summary()
        else:
            return {'error': 'No portfolio data available'}