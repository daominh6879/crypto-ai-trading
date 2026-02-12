"""
Simple Regime Detector - Conservative threshold-based detection
Only acts on EXTREME signals to avoid misclassification
"""
import pandas as pd
from typing import Dict, Tuple

class SimpleRegimeDetector:
    """
    Simple, robust regime detector focusing on overall period performance
    Only triggers regime-specific actions in EXTREME market conditions
    """

    def __init__(self, data: pd.DataFrame):
        """
        Initialize with OHLCV data

        Args:
            data: DataFrame with columns ['Open', 'High', 'Low', 'Close', 'Volume']
        """
        self.data = data
        self.metrics = {}

    def analyze_period(self) -> Dict:
        """
        Analyze the entire period to determine market characteristics

        Returns:
            dict with analysis metrics
        """
        close = self.data['Close']

        # 1. TOTAL RETURN - Overall trend direction
        start_price = close.iloc[0]
        end_price = close.iloc[-1]
        total_return = ((end_price - start_price) / start_price) * 100

        # 2. MAX DRAWDOWN - Severity of decline
        cumulative = close / close.iloc[0]
        running_max = cumulative.cummax()
        drawdown = ((cumulative - running_max) / running_max) * 100
        max_drawdown = drawdown.min()
        current_drawdown = drawdown.iloc[-1]

        # 3. VOLATILITY - Price stability
        returns = close.pct_change().dropna()
        volatility = returns.std() * np.sqrt(252) * 100  # Annualized

        # 4. TREND CONSISTENCY - How steady is the trend
        positive_days = (returns > 0).sum()
        negative_days = (returns < 0).sum()
        trend_consistency = abs(positive_days - negative_days) / len(returns) * 100

        # 5. RECENT MOMENTUM (last 30 days)
        lookback = min(30 * 24, len(close))  # 30 days in 1h bars
        recent_return = ((close.iloc[-1] - close.iloc[-lookback]) / close.iloc[-lookback]) * 100

        self.metrics = {
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'current_drawdown': current_drawdown,
            'volatility': volatility,
            'trend_consistency': trend_consistency,
            'recent_momentum': recent_return,
            'start_price': start_price,
            'end_price': end_price,
            'period_days': len(close) / 24,  # Assuming 1h bars
        }

        return self.metrics

    def detect_severe_bear(self) -> Tuple[bool, Dict]:
        """
        Detect if this is a SEVERE bear market requiring defensive action

        Conservative thresholds to avoid false positives:
        - Total return < -30% (significant decline)
        - Max drawdown < -40% (severe drawdown)

        Returns:
            (is_severe_bear, info_dict)
        """
        if not self.metrics:
            self.analyze_period()

        total_return = self.metrics['total_return']
        max_drawdown = self.metrics['max_drawdown']

        # CONSERVATIVE THRESHOLDS - only trigger in extreme conditions
        is_severe = (total_return < -30) and (max_drawdown < -40)

        info = {
            'is_severe_bear': is_severe,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'threshold_return': -30,
            'threshold_drawdown': -40,
            'action': 'DISABLE_LONGS' if is_severe else 'NONE',
            'reason': self._get_reason(is_severe, total_return, max_drawdown)
        }

        return is_severe, info

    def _get_reason(self, is_severe: bool, total_return: float, max_dd: float) -> str:
        """Generate human-readable reason"""
        if is_severe:
            return f"Severe bear market: {total_return:.1f}% return, {max_dd:.1f}% max drawdown"
        elif total_return < -30:
            return f"Declining market but drawdown manageable ({max_dd:.1f}%)"
        elif max_dd < -40:
            return f"High drawdown but recovering (current return {total_return:.1f}%)"
        else:
            return "Normal market conditions"

    def get_recommended_config(self) -> Dict:
        """
        Get configuration adjustments based on regime

        Returns:
            dict with config parameters to adjust
        """
        is_severe, info = self.detect_severe_bear()

        base_config = {
            'enable_regime_filter': True,  # Always keep ADX 20-30
            'stop_loss_multiplier': 3.0,
            'take_profit_1_multiplier': 4.0,
            'take_profit_2_multiplier': 8.0,
            'min_bars_gap': 6,
        }

        if is_severe:
            # SEVERE BEAR: Disable longs, defensive params
            base_config.update({
                'allow_long_trades': False,  # KEY: Disable longs
                'allow_short_trades': True,
                'stop_loss_multiplier': 2.5,  # Tighter for shorts
                'take_profit_1_multiplier': 3.0,
                'take_profit_2_multiplier': 5.0,
                'min_bars_gap': 8,  # More selective
                'regime': 'SEVERE_BEAR',
                'info': info
            })
        else:
            # NORMAL: Standard config
            base_config.update({
                'allow_long_trades': True,
                'allow_short_trades': True,
                'regime': 'NORMAL',
                'info': info
            })

        return base_config

    def print_analysis(self):
        """Print detailed analysis"""
        if not self.metrics:
            self.analyze_period()

        is_severe, info = self.detect_severe_bear()

        print("\n" + "="*80)
        print("SIMPLE REGIME DETECTION ANALYSIS")
        print("="*80)

        print(f"\n[PERIOD ANALYSIS]")
        print(f"  Period: {self.metrics['period_days']:.0f} days")
        print(f"  Start Price: ${self.metrics['start_price']:.2f}")
        print(f"  End Price: ${self.metrics['end_price']:.2f}")
        print(f"  Total Return: {self.metrics['total_return']:+.2f}%")

        print(f"\n[RISK METRICS]")
        print(f"  Max Drawdown: {self.metrics['max_drawdown']:.2f}%")
        print(f"  Current Drawdown: {self.metrics['current_drawdown']:.2f}%")
        print(f"  Volatility (annualized): {self.metrics['volatility']:.1f}%")

        print(f"\n[MOMENTUM]")
        print(f"  Recent 30d Return: {self.metrics['recent_momentum']:+.2f}%")
        print(f"  Trend Consistency: {self.metrics['trend_consistency']:.1f}%")

        print(f"\n[REGIME DETECTION]")
        print(f"  Severe Bear Market: {'YES' if is_severe else 'NO'}")
        print(f"  Thresholds: Return < -30% AND Drawdown < -40%")
        print(f"  Current: Return {self.metrics['total_return']:.1f}%, Drawdown {self.metrics['max_drawdown']:.1f}%")

        config = self.get_recommended_config()
        print(f"\n[RECOMMENDED ACTION]")
        print(f"  Regime: {config['regime']}")
        print(f"  Action: {info['action']}")
        print(f"  Reason: {info['reason']}")
        print(f"  Allow LONG trades: {config['allow_long_trades']}")
        print(f"  Allow SHORT trades: {config['allow_short_trades']}")
        print(f"  Stop Loss: {config['stop_loss_multiplier']}x ATR")
        print(f"  Min Bars Gap: {config['min_bars_gap']}")

        print("\n" + "="*80)

# Add numpy import at top of file
import numpy as np
