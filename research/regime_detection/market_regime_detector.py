"""
Market Regime Detector - Automatically detect bull/bear/ranging markets
and dynamically adjust trading configuration
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple
from datetime import datetime, timedelta

class MarketRegimeDetector:
    """Detect market regime (bull/bear/ranging) based on price data"""

    def __init__(self, data: pd.DataFrame):
        """
        Initialize with OHLCV data

        Args:
            data: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data
        self.regime = None
        self.confidence = 0.0
        self.metrics = {}

    def detect_regime(self, lookback_days: int = None) -> Tuple[str, float, Dict]:
        """
        Detect current market regime

        Args:
            lookback_days: Number of days to analyze (default None = entire period)

        Returns:
            (regime, confidence, metrics)
            regime: 'BULL', 'BEAR', 'RANGING'
            confidence: 0.0 to 1.0
            metrics: dict with detailed analysis
        """
        close = self.data['Close']

        # Calculate lookback period (in bars)
        if lookback_days is None:
            # Use entire period for backtesting
            lookback_bars = len(close)
        else:
            lookback_bars = min(lookback_days * 24, len(close))  # Assuming 1h bars

        recent_data = close.iloc[-lookback_bars:]

        # 1. TREND ANALYSIS - Price direction
        start_price = recent_data.iloc[0]
        current_price = recent_data.iloc[-1]
        total_return = ((current_price - start_price) / start_price) * 100

        # 2. VOLATILITY ANALYSIS - Price stability
        returns = recent_data.pct_change().dropna()
        volatility = returns.std() * 100

        # 3. DRAWDOWN ANALYSIS - Peak to trough
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = ((cumulative - running_max) / running_max) * 100
        max_drawdown = drawdown.min()
        current_drawdown = drawdown.iloc[-1]

        # 4. MOMENTUM ANALYSIS - Recent acceleration
        last_30_days = min(30 * 24, len(close))
        recent_return = ((close.iloc[-1] - close.iloc[-last_30_days]) / close.iloc[-last_30_days]) * 100

        # 5. EMA ANALYSIS - Trend structure
        ema_20 = close.ewm(span=20).mean().iloc[-1]
        ema_50 = close.ewm(span=50).mean().iloc[-1]
        ema_200 = close.ewm(span=200).mean().iloc[-1]

        price_vs_ema200 = ((current_price - ema_200) / ema_200) * 100
        ema_alignment_bull = (ema_20 > ema_50) and (ema_50 > ema_200)
        ema_alignment_bear = (ema_20 < ema_50) and (ema_50 < ema_200)

        # 6. HIGHER HIGHS / LOWER LOWS
        highs = recent_data.rolling(window=20).max()
        lows = recent_data.rolling(window=20).min()
        higher_highs = (highs.iloc[-1] > highs.iloc[-40])
        lower_lows = (lows.iloc[-1] < lows.iloc[-40])

        # Store metrics
        self.metrics = {
            'total_return_pct': total_return,
            'volatility_pct': volatility,
            'max_drawdown_pct': max_drawdown,
            'current_drawdown_pct': current_drawdown,
            'recent_30d_return_pct': recent_return,
            'price_vs_ema200_pct': price_vs_ema200,
            'ema_alignment_bull': ema_alignment_bull,
            'ema_alignment_bear': ema_alignment_bear,
            'higher_highs': higher_highs,
            'lower_lows': lower_lows,
            'current_price': current_price,
            'ema_20': ema_20,
            'ema_50': ema_50,
            'ema_200': ema_200,
        }

        # REGIME DETECTION LOGIC
        bull_score = 0
        bear_score = 0
        ranging_score = 0

        # Scoring system (0-10 scale for each factor)

        # 1. Total return score
        if total_return > 20:
            bull_score += 3
        elif total_return > 10:
            bull_score += 2
        elif total_return > 0:
            bull_score += 1
        elif total_return < -20:
            bear_score += 3
        elif total_return < -10:
            bear_score += 2
        elif total_return < 0:
            bear_score += 1
        else:
            ranging_score += 1

        # 2. Recent momentum score
        if recent_return > 15:
            bull_score += 2
        elif recent_return > 5:
            bull_score += 1
        elif recent_return < -15:
            bear_score += 2
        elif recent_return < -5:
            bear_score += 1
        else:
            ranging_score += 1

        # 3. EMA alignment score
        if ema_alignment_bull:
            bull_score += 2
        elif ema_alignment_bear:
            bear_score += 2
        else:
            ranging_score += 1

        # 4. Price vs EMA200 score
        if price_vs_ema200 > 10:
            bull_score += 2
        elif price_vs_ema200 > 0:
            bull_score += 1
        elif price_vs_ema200 < -10:
            bear_score += 2
        elif price_vs_ema200 < 0:
            bear_score += 1
        else:
            ranging_score += 1

        # 5. Higher highs / Lower lows score
        if higher_highs and not lower_lows:
            bull_score += 1
        elif lower_lows and not higher_highs:
            bear_score += 1
        else:
            ranging_score += 1

        # 6. Drawdown severity score
        if max_drawdown < -30:
            bear_score += 2
        elif max_drawdown < -20:
            bear_score += 1
        elif max_drawdown > -10:
            bull_score += 1

        # 7. Volatility score (high volatility suggests ranging/choppy)
        if volatility > 4:
            ranging_score += 1
        elif volatility < 2:
            bull_score += 1

        # Normalize scores
        total_score = bull_score + bear_score + ranging_score
        if total_score > 0:
            bull_score_norm = bull_score / total_score
            bear_score_norm = bear_score / total_score
            ranging_score_norm = ranging_score / total_score
        else:
            bull_score_norm = bear_score_norm = ranging_score_norm = 0.33

        # Determine regime
        max_score = max(bull_score_norm, bear_score_norm, ranging_score_norm)

        if max_score == bull_score_norm:
            self.regime = 'BULL'
            self.confidence = bull_score_norm
        elif max_score == bear_score_norm:
            self.regime = 'BEAR'
            self.confidence = bear_score_norm
        else:
            self.regime = 'RANGING'
            self.confidence = ranging_score_norm

        # Store scores
        self.metrics['bull_score'] = bull_score
        self.metrics['bear_score'] = bear_score
        self.metrics['ranging_score'] = ranging_score
        self.metrics['bull_score_norm'] = bull_score_norm
        self.metrics['bear_score_norm'] = bear_score_norm
        self.metrics['ranging_score_norm'] = ranging_score_norm

        return self.regime, self.confidence, self.metrics

    def get_recommended_config(self) -> Dict:
        """
        Get recommended configuration based on detected regime

        Returns:
            dict with recommended config parameters
        """
        if self.regime is None:
            raise ValueError("Must call detect_regime() first")

        if self.regime == 'BULL':
            # Bull market: Standard trend-following
            return {
                'allow_long_trades': True,
                'allow_short_trades': True,  # Keep shorts for reversals
                'stop_loss_multiplier': 3.0,
                'take_profit_1_multiplier': 4.0,
                'take_profit_2_multiplier': 8.0,
                'min_bars_gap': 6,
                'enable_regime_filter': True,  # ADX 20-30 filter
                'strategy_bias': 'LONG_BIASED',
                'reason': 'Bull market detected - use standard trend-following'
            }
        elif self.regime == 'BEAR':
            # Bear market: Defensive with short bias
            return {
                'allow_long_trades': False,  # DISABLE LONGS (they lose -13.45% in bear)
                'allow_short_trades': True,   # ENABLE SHORTS (break-even to positive)
                'stop_loss_multiplier': 2.5,  # Tighter stops for shorts
                'take_profit_1_multiplier': 3.0,  # Smaller targets
                'take_profit_2_multiplier': 5.0,
                'min_bars_gap': 8,  # More selective
                'enable_regime_filter': True,
                'strategy_bias': 'SHORT_ONLY',
                'reason': 'Bear market detected - SHORT-ONLY mode to avoid long losses'
            }
        else:  # RANGING
            # Ranging market: Tight risk, high selectivity
            return {
                'allow_long_trades': True,
                'allow_short_trades': True,
                'stop_loss_multiplier': 2.0,  # Tight stops
                'take_profit_1_multiplier': 2.5,  # Small targets
                'take_profit_2_multiplier': 4.0,
                'min_bars_gap': 10,  # Very selective
                'enable_regime_filter': True,
                'strategy_bias': 'NEUTRAL',
                'reason': 'Ranging market detected - tight risk, high selectivity'
            }

    def print_analysis(self):
        """Print detailed regime analysis"""
        if self.regime is None:
            print("No analysis available. Call detect_regime() first.")
            return

        print("\n" + "="*80)
        print("MARKET REGIME ANALYSIS")
        print("="*80)

        print(f"\n[DETECTED REGIME]: {self.regime} (Confidence: {self.confidence*100:.1f}%)")

        print(f"\n[PRICE METRICS]")
        print(f"  Current Price: ${self.metrics['current_price']:.2f}")
        print(f"  Total Return (90d): {self.metrics['total_return_pct']:+.2f}%")
        print(f"  Recent Return (30d): {self.metrics['recent_30d_return_pct']:+.2f}%")
        print(f"  Price vs EMA200: {self.metrics['price_vs_ema200_pct']:+.2f}%")

        print(f"\n[RISK METRICS]")
        print(f"  Max Drawdown: {self.metrics['max_drawdown_pct']:.2f}%")
        print(f"  Current Drawdown: {self.metrics['current_drawdown_pct']:.2f}%")
        print(f"  Volatility: {self.metrics['volatility_pct']:.2f}%")

        print(f"\n[TREND STRUCTURE]")
        print(f"  EMA20: ${self.metrics['ema_20']:.2f}")
        print(f"  EMA50: ${self.metrics['ema_50']:.2f}")
        print(f"  EMA200: ${self.metrics['ema_200']:.2f}")
        print(f"  Bull Alignment: {'YES' if self.metrics['ema_alignment_bull'] else 'NO'}")
        print(f"  Bear Alignment: {'YES' if self.metrics['ema_alignment_bear'] else 'NO'}")
        print(f"  Higher Highs: {'YES' if self.metrics['higher_highs'] else 'NO'}")
        print(f"  Lower Lows: {'YES' if self.metrics['lower_lows'] else 'NO'}")

        print(f"\n[REGIME SCORES]")
        print(f"  Bull Score: {self.metrics['bull_score']} ({self.metrics['bull_score_norm']*100:.1f}%)")
        print(f"  Bear Score: {self.metrics['bear_score']} ({self.metrics['bear_score_norm']*100:.1f}%)")
        print(f"  Ranging Score: {self.metrics['ranging_score']} ({self.metrics['ranging_score_norm']*100:.1f}%)")

        # Recommended config
        config = self.get_recommended_config()
        print(f"\n[RECOMMENDED CONFIGURATION]")
        print(f"  Strategy Bias: {config['strategy_bias']}")
        print(f"  Allow LONG trades: {config['allow_long_trades']}")
        print(f"  Allow SHORT trades: {config['allow_short_trades']}")
        print(f"  Stop Loss: {config['stop_loss_multiplier']}x ATR")
        print(f"  Take Profit 1: {config['take_profit_1_multiplier']}x ATR")
        print(f"  Take Profit 2: {config['take_profit_2_multiplier']}x ATR")
        print(f"  Min Bars Gap: {config['min_bars_gap']}")
        print(f"  Reason: {config['reason']}")

        print("\n" + "="*80)
