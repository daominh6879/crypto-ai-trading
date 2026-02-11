"""
Technical Indicators for the Pro Trader System
Converted from TradingView Pine Script
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from config import TradingConfig

# Try to import talib, fallback to pandas if unavailable
try:
    import talib
    HAS_TALIB = True
except ImportError:
    HAS_TALIB = False
    print("Warning: TA-Lib not found, using pandas fallback functions")


class TechnicalIndicators:
    """
    Technical indicator calculations for the trading system
    """
    
    def __init__(self, config: TradingConfig):
        self.config = config
    
    def calculate_ema(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate Exponential Moving Averages"""
        close = data['Close']
        
        if HAS_TALIB:
            return {
                'ema_20': talib.EMA(close, timeperiod=self.config.ema_20_length),
                'ema_50': talib.EMA(close, timeperiod=self.config.ema_50_length),
                'ema_200': talib.EMA(close, timeperiod=self.config.ema_200_length)
            }
        else:
            # Pandas fallback
            return {
                'ema_20': close.ewm(span=self.config.ema_20_length).mean(),
                'ema_50': close.ewm(span=self.config.ema_50_length).mean(),
                'ema_200': close.ewm(span=self.config.ema_200_length).mean()
            }
    
    def calculate_rsi(self, data: pd.DataFrame) -> pd.Series:
        """Calculate RSI"""
        close = data['Close']
        
        if HAS_TALIB:
            return talib.RSI(close, timeperiod=self.config.rsi_length)
        else:
            # Pandas fallback RSI calculation
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.config.rsi_length).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.config.rsi_length).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
    
    def calculate_macd(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate MACD"""
        close = data['Close']
        
        if HAS_TALIB:
            macd_line, signal_line, histogram = talib.MACD(
                close,
                fastperiod=self.config.macd_fast,
                slowperiod=self.config.macd_slow,
                signalperiod=self.config.macd_signal
            )
        else:
            # Pandas fallback MACD calculation
            ema_fast = close.ewm(span=self.config.macd_fast).mean()
            ema_slow = close.ewm(span=self.config.macd_slow).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=self.config.macd_signal).mean()
            histogram = macd_line - signal_line
        
        return {
            'macd_line': macd_line,
            'signal_line': signal_line,
            'histogram': histogram
        }
    
    def calculate_atr(self, data: pd.DataFrame) -> pd.Series:
        """Calculate Average True Range"""
        if HAS_TALIB:
            return talib.ATR(
                data['High'], 
                data['Low'], 
                data['Close'], 
                timeperiod=self.config.atr_length
            )
        else:
            # Pandas fallback ATR calculation
            high = data['High']
            low = data['Low']
            close = data['Close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.rolling(window=self.config.atr_length).mean()
            return atr
    
    def calculate_trend_analysis(self, ema_data: Dict[str, pd.Series], 
                               close: pd.Series) -> Dict[str, pd.Series]:
        """Analyze trend conditions"""
        ema_20 = ema_data['ema_20']
        ema_50 = ema_data['ema_50']
        ema_200 = ema_data['ema_200']
        
        above_ema_200 = close > ema_200
        below_ema_200 = close < ema_200
        strong_bullish = (ema_20 > ema_50) & (ema_50 > ema_200)
        strong_bearish = (ema_20 < ema_50) & (ema_50 < ema_200)
        
        # Trend status
        trend_status = pd.Series(index=close.index, dtype=str)
        trend_status[strong_bullish] = "STRONG UP"
        trend_status[strong_bearish] = "STRONG DOWN"
        trend_status[above_ema_200 & ~strong_bullish] = "UP"
        trend_status[below_ema_200 & ~strong_bearish] = "DOWN"
        
        return {
            'above_ema_200': above_ema_200,
            'below_ema_200': below_ema_200,
            'strong_bullish': strong_bullish,
            'strong_bearish': strong_bearish,
            'trend_status': trend_status
        }
    
    def calculate_momentum_analysis(self, rsi: pd.Series, 
                                  macd_data: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
        """Analyze momentum conditions"""
        # RSI conditions
        rsi_oversold = rsi < self.config.rsi_oversold
        rsi_overbought = rsi > self.config.rsi_overbought
        rsi_recovering = (rsi.shift(1) < self.config.rsi_oversold) & (rsi > rsi.shift(1))
        rsi_weakening = (rsi.shift(1) > self.config.rsi_overbought) & (rsi < rsi.shift(1))
        
        # RSI status
        rsi_status = pd.Series(index=rsi.index, dtype=str)
        rsi_status[rsi_overbought] = "Overbought"
        rsi_status[rsi_oversold] = "Oversold"
        rsi_status[~(rsi_overbought | rsi_oversold)] = "Neutral"
        
        # MACD conditions
        macd_line = macd_data['macd_line']
        signal_line = macd_data['signal_line']
        histogram = macd_data['histogram']
        
        macd_bull_cross = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
        macd_bear_cross = (macd_line < signal_line) & (macd_line.shift(1) >= signal_line.shift(1))
        macd_rising = histogram > histogram.shift(1)
        macd_falling = histogram < histogram.shift(1)
        
        # MACD status
        macd_status = pd.Series(index=macd_line.index, dtype=str)
        bull_rising = (macd_line > signal_line) & macd_rising
        bull_not_rising = (macd_line > signal_line) & ~macd_rising
        bear_falling = (macd_line < signal_line) & macd_falling
        bear_not_falling = (macd_line < signal_line) & ~macd_falling
        
        macd_status[bull_rising] = "Bullish↑"
        macd_status[bull_not_rising] = "Bullish"
        macd_status[bear_falling] = "Bearish↓"
        macd_status[bear_not_falling] = "Bearish"
        
        return {
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'rsi_recovering': rsi_recovering,
            'rsi_weakening': rsi_weakening,
            'rsi_status': rsi_status,
            'macd_bull_cross': macd_bull_cross,
            'macd_bear_cross': macd_bear_cross,
            'macd_rising': macd_rising,
            'macd_falling': macd_falling,
            'macd_status': macd_status
        }
    
    def calculate_price_action(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Analyze price action patterns"""
        open_price = data['Open']
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        # Candle analysis
        bull_candle = close > open_price
        bear_candle = close < open_price
        body_size = abs(close - open_price)
        avg_body = body_size.rolling(window=20).mean()
        
        # Reversal patterns
        bullish_reversal = (
            bull_candle & 
            (body_size > avg_body * 1.3) & 
            (close > high.shift(1))
        )
        bearish_reversal = (
            bear_candle & 
            (body_size > avg_body * 1.3) & 
            (close < low.shift(1))
        )
        
        # Strong candles
        strong_bull = bull_candle & (body_size > avg_body)
        strong_bear = bear_candle & (body_size > avg_body)
        
        # Support/Resistance patterns
        higher_low = (low > low.shift(1)) & (low > low.shift(2))
        lower_high = (high < high.shift(1)) & (high < high.shift(2))
        
        # Candle status
        candle_status = pd.Series(index=close.index, dtype=str)
        candle_status[bullish_reversal] = "Strong↑"
        candle_status[bearish_reversal] = "Strong↓"
        candle_status[strong_bull & ~bullish_reversal] = "Bullish"
        candle_status[strong_bear & ~bearish_reversal] = "Bearish"
        candle_status[
            ~(bullish_reversal | bearish_reversal | strong_bull | strong_bear)
        ] = "Weak"
        
        return {
            'bull_candle': bull_candle,
            'bear_candle': bear_candle,
            'body_size': body_size,
            'avg_body': avg_body,
            'bullish_reversal': bullish_reversal,
            'bearish_reversal': bearish_reversal,
            'strong_bull': strong_bull,
            'strong_bear': strong_bear,
            'higher_low': higher_low,
            'lower_high': lower_high,
            'candle_status': candle_status
        }
    
    def calculate_volume_analysis(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Analyze volume conditions matching TradingView Pine Script"""
        volume = data.get('Volume', pd.Series(index=data.index, dtype=float))
        has_volume = volume > 0
        
        if has_volume.any():
            # Volume SMA (20 periods like Pine Script)
            vol_sma = volume.rolling(window=20).mean()
            
            # Pine Script volume conditions:
            # volBull = volume > sma(volume, 20) * 1.2 (20% above average)
            vol_bull = volume > vol_sma * 1.2
            
            # volBear = volume > sma(volume, 20) * 1.1 (10% above average)  
            vol_bear = volume > vol_sma * 1.1
            
            # For compatibility with existing code
            vol_confirm_buy = ~has_volume | vol_bull
            vol_confirm_sell = ~has_volume | vol_bear
        else:
            vol_sma = pd.Series(index=data.index, dtype=float)
            vol_bull = pd.Series(False, index=data.index)
            vol_bear = pd.Series(False, index=data.index)
            vol_confirm_buy = pd.Series(True, index=data.index)
            vol_confirm_sell = pd.Series(True, index=data.index)
        
        return {
            'has_volume': has_volume,
            'vol_sma': vol_sma,
            'vol_bull': vol_bull,
            'vol_bear': vol_bear,
            'vol_confirm_buy': vol_confirm_buy,
            'vol_confirm_sell': vol_confirm_sell
        }
    
    def calculate_all_indicators(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate all technical indicators"""
        # Basic indicators
        ema_data = self.calculate_ema(data)
        rsi = self.calculate_rsi(data)
        macd_data = self.calculate_macd(data)
        atr = self.calculate_atr(data)
        
        # Analysis
        trend_analysis = self.calculate_trend_analysis(ema_data, data['Close'])
        momentum_analysis = self.calculate_momentum_analysis(rsi, macd_data)
        price_action = self.calculate_price_action(data)
        volume_analysis = self.calculate_volume_analysis(data)
        
        # Create base indicators dict
        indicators_base = {
            'ema': ema_data,
            'rsi': rsi,
            'macd': macd_data,
            'atr': atr,
            'trend': trend_analysis,
            'momentum': momentum_analysis,
            'price_action': price_action,
            'volume': volume_analysis
        }
        
        # Add advanced conditions
        try:
            advanced_conditions = self.calculate_advanced_conditions(indicators_base, data)
            indicators_base['advanced'] = advanced_conditions
        except Exception as e:
            print(f"❌ Error calculating advanced conditions: {e}")
            # Provide fallback empty advanced conditions
            indicators_base['advanced'] = {}
        
        return indicators_base
    
    def calculate_advanced_conditions(self, indicators: Dict[str, Any], data: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate advanced market conditions for professional trading"""
        close = data['Close']
        high = data['High']
        low = data['Low']
        atr = indicators['atr']
        ema_20 = indicators['ema']['ema_20']
        ema_50 = indicators['ema']['ema_50']
        ema_200 = indicators['ema']['ema_200']
        rsi = indicators['rsi']
        macd_line = indicators['macd']['macd_line']
        signal_line = indicators['macd']['signal_line']
        
        # 1. TREND STRENGTH ANALYSIS
        # EMA separation as % of price (stronger trends have wider separation)
        ema_separation_bull = ((ema_20 - ema_50) / close) * 100
        ema_separation_bear = ((ema_50 - ema_20) / close) * 100
        strong_bull_trend = ema_separation_bull > 0.5  # 0.5% minimum separation
        strong_bear_trend = ema_separation_bear > 0.5
        
        # Price momentum (price distance from EMAs)
        price_above_ema20 = ((close - ema_20) / close) * 100
        price_momentum_bull = price_above_ema20 > 1.0  # Price 1%+ above EMA20
        price_momentum_bear = price_above_ema20 < -1.0  # Price 1%+ below EMA20
        
        # 2. VOLATILITY FILTERING
        # ATR-based volatility classification
        atr_pct = (atr / close) * 100
        atr_sma = atr_pct.rolling(window=20).mean()
        high_volatility = atr_pct > atr_sma * 1.5  # 50% above average volatility
        low_volatility = atr_pct < atr_sma * 0.7   # 30% below average volatility
        normal_volatility = ~(high_volatility | low_volatility)
        
        # 3. MARKET PHASE DETECTION
        # Trending vs Ranging market detection
        price_range_20 = high.rolling(20).max() - low.rolling(20).min()
        price_movement = abs(close - close.shift(20))
        trending_market = price_movement > (price_range_20 * 0.6)  # 60% of range covered
        ranging_market = ~trending_market
        
        # 4. RSI MOMENTUM QUALITY
        # RSI slope for momentum confirmation
        rsi_slope = rsi - rsi.shift(3)
        rsi_bull_momentum = (rsi > 45) & (rsi < 75) & (rsi_slope > 2)  # Rising RSI in good range
        rsi_bear_momentum = (rsi < 55) & (rsi > 25) & (rsi_slope < -2)  # Falling RSI in good range
        
        # 5. MACD QUALITY
        # MACD histogram acceleration
        histogram = indicators['macd']['histogram']
        histogram_slope = histogram - histogram.shift(2)
        macd_accelerating_bull = (macd_line > signal_line) & (histogram_slope > 0)
        macd_accelerating_bear = (macd_line < signal_line) & (histogram_slope < 0)
        
        return {
            'strong_bull_trend': strong_bull_trend,
            'strong_bear_trend': strong_bear_trend,
            'price_momentum_bull': price_momentum_bull,
            'price_momentum_bear': price_momentum_bear,
            'high_volatility': high_volatility,
            'low_volatility': low_volatility,
            'normal_volatility': normal_volatility,
            'trending_market': trending_market,
            'ranging_market': ranging_market,
            'rsi_bull_momentum': rsi_bull_momentum,
            'rsi_bear_momentum': rsi_bear_momentum,
            'macd_accelerating_bull': macd_accelerating_bull,
            'macd_accelerating_bear': macd_accelerating_bear,
            'ema_separation_bull': ema_separation_bull,
            'ema_separation_bear': ema_separation_bear,
            'atr_pct': atr_pct
        }

    def get_setup_signals(self, indicators: Dict[str, Any]) -> Dict[str, pd.Series]:
        """Generate setup signals based on TradingView Pine Script logic"""
        # Get EMAs
        ema_20 = indicators['ema']['ema_20']
        ema_50 = indicators['ema']['ema_50'] 
        ema_200 = indicators['ema']['ema_200']
        
        # Pine Script setup conditions - EMA alignment only
        # buySetup = (e20 > e50) and (e50 > e200)
        buy_setup = (ema_20 > ema_50) & (ema_50 > ema_200)
        
        # sellSetup = (e20 < e50) and (e50 < e200)  
        sell_setup = (ema_20 < ema_50) & (ema_50 < ema_200)
        
        # Setup status
        rsi = indicators['rsi']
        setup_status = pd.Series(index=rsi.index, dtype=str)
        setup_status[buy_setup] = "BUY SETUP"
        setup_status[sell_setup] = "SELL SETUP"
        setup_status[~(buy_setup | sell_setup)] = "Neutral"
        
        return {
            'buy_setup': buy_setup,
            'sell_setup': sell_setup,
            'setup_status': setup_status
        }
    
    def validate_signal_quality(self, indicators: Dict[str, Any], index: int) -> Dict[str, bool]:
        """Professional signal quality validation for individual trade setups"""
        try:
            # Extract current values
            atr_pct = indicators['advanced']['atr_pct'].iloc[index]
            trending = indicators['advanced']['trending_market'].iloc[index]
            high_vol = indicators['advanced']['high_volatility'].iloc[index]
            
            # EMA separation strength
            ema_sep_bull = indicators['advanced']['ema_separation_bull'].iloc[index]
            ema_sep_bear = indicators['advanced']['ema_separation_bear'].iloc[index]
            
            # Market condition validations
            volatility_ok = not high_vol and atr_pct < self.config.max_volatility_threshold
            trend_strong = trending and (ema_sep_bull > self.config.min_trend_strength or 
                                       ema_sep_bear > self.config.min_trend_strength)
            
            return {
                'volatility_acceptable': volatility_ok,
                'trend_strength_ok': trend_strong,
                'overall_quality': volatility_ok and trend_strong
            }
        except (IndexError, KeyError):
            # Fallback for missing data
            return {
                'volatility_acceptable': True,
                'trend_strength_ok': True,
                'overall_quality': True
            }