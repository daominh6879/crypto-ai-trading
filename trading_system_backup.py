"""
Streamlined Trading System for the Pro Trader System
Integrates indicators, signals, position management, and live trading
Converted from TradingView Pine Script with database integration
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
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
            self.binance_provider = None
            self.live_system = None
    
    def fetch_data(self, symbol: Optional[str] = None, 
                   interval: Optional[str] = None,
                   days: Optional[int] = None,
                   start_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch market data using Binance"""
        symbol = symbol or self.config.symbol
        interval = interval or self.config.interval
        
        if self.binance_provider:
            return self._fetch_binance_data(symbol, interval, days, start_date)
        else:
            raise ValueError("Binance provider not available")
    
    def _fetch_binance_data(self, symbol: str, interval: str, days: int = None) -> pd.DataFrame:
        """Fetch data from Binance"""
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
            
            # Limit to Binance API limits
            days = min(days, 365)  # Max 1 year for most intervals
            
            data = self.binance_provider.get_historical_data(
                symbol, interval, limit=min(1000, days * 24)
            )
            
            if data.empty:
                raise ValueError(f"No data found for symbol {symbol}")
            
            self.data = data
            return data
            
        except Exception as e:
            raise Exception(f"Error fetching data for {symbol}: {str(e)}")
    
    def calculate_signals(self) -> pd.DataFrame:
        """Calculate all trading signals"""
        if self.data is None:
            raise ValueError("No data available. Call fetch_data() first.")
        
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
        
        # Setup signals
        for name, series in setup_signals.items():
            signals_df[f'setup_{name}'] = series
        
        # Generate entry triggers
        signals_df = self._generate_entry_signals(signals_df)
        
        self.signals = signals_df
        return signals_df
    
    def _generate_entry_signals(self, signals_df: pd.DataFrame) -> pd.DataFrame:
        """Generate buy and sell entry signals matching TradingView Pine Script logic"""
        
        # Pine Script trigger conditions:
        # buyTrigger = (rsi > 50) and (macd > signal) and (hist > 0) and volBull
        buy_trigger = (
            (signals_df['rsi'] > 50) &
            (signals_df['macd_line'] > signals_df['signal_line']) &
            (signals_df['histogram'] > 0) &
            signals_df['volume_vol_bull']
        )
        
        # sellTrigger = (rsi < 50) and (macd < signal) and (hist < 0) and volBear  
        sell_trigger = (
            (signals_df['rsi'] < 50) &
            (signals_df['macd_line'] < signals_df['signal_line']) &
            (signals_df['histogram'] < 0) &
            signals_df['volume_vol_bear']
        )
        
        # Pine Script final signals:
        # buySignal = buySetup and buyTrigger and not inTrade
        # sellSignal = sellSetup and sellTrigger and not inTrade
        buy_signal = signals_df['setup_buy_setup'] & buy_trigger
        sell_signal = signals_df['setup_sell_setup'] & sell_trigger
        
        # Apply gap filter to prevent too frequent signals (from Pine Script gapControl)
        buy_final = buy_signal.copy()
        sell_final = sell_signal.copy()
        
        if self.config.min_bars_gap > 1:
            # Apply minimum gap between signals
            last_signal_idx = None
            
            for i in range(len(signals_df)):
                current_signal = buy_signal.iloc[i] or sell_signal.iloc[i]
                
                if current_signal:
                    if last_signal_idx is None or i - last_signal_idx >= self.config.min_bars_gap:
                        last_signal_idx = i
                    else:
                        # Gap too small, filter out this signal
                        buy_final.iloc[i] = False
                        sell_final.iloc[i] = False
        
        # Store intermediate signals for debugging
        signals_df['buy_trigger'] = buy_trigger
        signals_df['sell_trigger'] = sell_trigger  
        signals_df['buy_signal'] = buy_signal
        signals_df['sell_signal'] = sell_signal
        
        # Final confirmed signals
        signals_df['buy_confirmed'] = buy_final
        signals_df['sell_confirmed'] = sell_final
        
        return signals_df
    
    def run_backtest(self, start_date: Optional[str] = None, 
                    end_date: Optional[str] = None) -> Dict[str, Any]:
        """Run complete backtest simulation with database integration"""
        if self.signals is None:
            raise ValueError("No signals calculated. Call calculate_signals() first.")
        
        # Filter data by date range if specified
        data = self.signals.copy()
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        # Reset position manager for backtesting
        self.position_manager.reset()
        
        # Track signals and trades
        buy_signals = []
        sell_signals = []
        exits = []
        
        print(f"📊 Running backtest on {len(data)} bars...")
        
        # Iterate through each bar
        for i, (timestamp, row) in enumerate(data.iterrows()):
            self.position_manager.update_bar(i)
            
            # Check for exit conditions first
            if self.position_manager.is_in_trade():
                # Update trailing stop
                self.position_manager.update_trailing_stop(row['close'], row['atr'])
                
                # Check exit conditions
                should_exit, exit_reason = self.position_manager.check_exit_conditions(
                    row['close'], timestamp, 
                    sell_signal=row.get('sell_confirmed', False),
                    buy_signal=row.get('buy_confirmed', False)
                )
                
                if should_exit:
                    trade = self.position_manager.exit_position(
                        row['close'], timestamp, exit_reason
                    )
                    if trade:  # Only add to exits if trade was successful
                        exits.append({
                            'timestamp': timestamp,
                            'price': row['close'],
                            'trade': trade
                        })
                        
                        # Log exit to database if available
                        if self.db:
                            self.db.save_signal(
                                symbol=self.config.symbol,
                                signal_type='EXIT',
                                price=row['close'],
                                timestamp=timestamp,
                                exit_reason=exit_reason
                            )
            
            # Check for new entry signals (only when not in trade)
            elif self.position_manager.can_enter_trade():
                # Buy signal
                if row.get('buy_confirmed', False):
                    success = self.position_manager.enter_long_position(
                        row['close'], timestamp, row['atr']
                    )
                    if success:
                        buy_signals.append({
                            'timestamp': timestamp,
                            'price': row['close'],
                            'type': 'BUY'
                        })
                        self._update_last_signal_info('BUY', i)
                        
                        # Log to database
                        if self.db:
                            self.db.save_signal(
                                symbol=self.config.symbol,
                                signal_type='BUY',
                                price=row['close'],
                                timestamp=timestamp,
                                rsi=row.get('rsi'),
                                macd_histogram=row.get('histogram')
                            )
                
                # Sell signal (short position - if enabled)
                elif row.get('sell_confirmed', False):
                    success = self.position_manager.enter_short_position(
                        row['close'], timestamp, row['atr']
                    )
                    if success:
                        sell_signals.append({
                            'timestamp': timestamp,
                            'price': row['close'],
                            'type': 'SELL'
                        })
                        self._update_last_signal_info('SELL', i)
                        
                        # Log to database
                        if self.db:
                            self.db.save_signal(
                                symbol=self.config.symbol,
                                signal_type='SELL',
                                price=row['close'],
                                timestamp=timestamp,
                                rsi=row.get('rsi'),
                                macd_histogram=row.get('histogram')
                            )
            
            # Update last signal bars ago
            self._update_signal_bars_ago(i)
        
        # Force exit any remaining position
        if self.position_manager.is_in_trade():
            final_row = data.iloc[-1]
            trade = self.position_manager.exit_position(
                final_row['close'], final_row.name, "End of Data"
            )
            exits.append({
                'timestamp': final_row.name,
                'price': final_row['close'],
                'trade': trade
            })
        
        # Compile results
        results = {
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'exits': exits,
            'trades': self.position_manager.trade_history,
            'statistics': self.position_manager.get_trade_statistics(),
            'data': data,
            'symbol': self.config.symbol,
            'config': self.config
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
        
        # RSI status
        rsi_value = latest.get('rsi', 50)
        if rsi_value > self.config.rsi_overbought:
            rsi_status = 'Overbought'
        elif rsi_value < self.config.rsi_oversold:
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
        
        print(f"\n📊 Trade Statistics:")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Winning Trades: {stats['winning_trades']}")
        print(f"Losing Trades: {stats['losing_trades']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        
        print(f"\n💰 Performance Metrics:")
        print(f"Average Win: {stats['avg_win']:.2f}%")
        print(f"Average Loss: {stats['avg_loss']:.2f}%")
        print(f"Total P&L: {stats['total_pnl']:.2f}%")
        if 'total_amount_pnl' in stats:
            print(f"Total P&L Amount: ${stats['total_amount_pnl']:.2f}")
        print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")
        
        if results['trades']:
            print(f"\n📈 Recent Trades:")
            print("-" * 80)
            for trade in results['trades'][-5:]:
                if trade is None:
                    continue  # Skip None trades
                duration = f"{trade.duration_bars}bars"
                print(f"{trade.entry_time.strftime('%Y-%m-%d %H:%M')} | "
                      f"{trade.trade_type:5s} | "
                      f"${trade.entry_price:7.2f} → ${trade.exit_price:7.2f} | "
                      f"{trade.pnl_percent:6.2f}% | "
                      f"{duration:8s} | "
                      f"{trade.exit_reason}")
        
        print("="*60)
    
    def start_live_trading(self, symbol: Optional[str] = None, 
                          interval: Optional[str] = None) -> bool:
        """Start live trading with real-time data and order execution"""
        if not self.live_system:
            print("❌ Live trading requires Binance integration")
            return False
        
        symbol = symbol or self.config.symbol
        interval = interval or self.config.interval
        
        print(f"🚀 Starting live trading for {symbol} {interval}")
        
        # Check if live trading is enabled (API keys provided)
        if not self.binance_provider.is_live_trading:
            print("⚠️ Live trading not enabled - API keys required for order execution")
            return False
        
        return self.live_system.start_live_monitoring(symbol, interval)
    
    def stop_live_trading(self):
        """Stop live trading"""
        if self.live_system:
            self.live_system.stop_monitoring()
        print("🛑 Live trading stopped")
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        if self.live_system:
            return self.live_system.get_portfolio_status()
        elif self.db:
            return self.db.get_portfolio_summary()
        else:
            return {'error': 'No portfolio data available'}
    
    def fetch_data(self, symbol: Optional[str] = None, 
                   interval: Optional[str] = None,
                   days: Optional[int] = None,
                   start_date: Optional[str] = None) -> pd.DataFrame:
        """Fetch market data using Binance"""
        symbol = symbol or self.config.symbol
        interval = interval or self.config.interval
        
        if self.binance_provider:
            return self._fetch_binance_data(symbol, interval, days, start_date)
        else:
            raise ValueError("Binance provider not available")
    
    def _fetch_binance_data(self, symbol: str, interval: str, days: int = None) -> pd.DataFrame:
        """Fetch data from Binance"""
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
            
            # Limit to Binance API limits
            days = min(days, 365)  # Max 1 year for most intervals
            
            data = self.binance_provider.get_historical_data(
                symbol, interval, limit=min(1000, days * 24)
            )
            
            if data.empty:
                raise ValueError(f"No data found for symbol {symbol}")
            
            self.data = data
            return data
            
        except Exception as e:
            raise Exception(f"Error fetching data for {symbol}: {str(e)}")
    
    def calculate_signals(self) -> pd.DataFrame:
        """Calculate all trading signals"""
        if self.data is None:
            raise ValueError("No data available. Call fetch_data() first.")
        
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
        
        # Setup signals
        for name, series in setup_signals.items():
            signals_df[f'setup_{name}'] = series
        
        # Generate entry triggers
        signals_df = self._generate_entry_signals(signals_df)
        
        self.signals = signals_df
        return signals_df
    
    def _generate_entry_signals(self, signals_df: pd.DataFrame) -> pd.DataFrame:
        """Generate buy and sell entry signals"""
        # Buy trigger conditions
        buy_trigger = (
            signals_df['setup_buy_setup'].shift(1) &
            (signals_df['price_bullish_reversal'] | signals_df['price_strong_bull']) &
            (signals_df['momentum_macd_bull_cross'] | signals_df['momentum_macd_rising']) &
            signals_df['volume_vol_confirm_buy']
        )
        
        # Sell trigger conditions
        sell_trigger = (
            signals_df['setup_sell_setup'].shift(1) &
            (signals_df['price_bearish_reversal'] | signals_df['price_strong_bear'] | 
             signals_df['momentum_macd_bear_cross']) &
            signals_df['volume_vol_confirm_sell']
        )
        
        # Confirmation logic
        if self.config.require_confirmation:
            buy_confirmed = buy_trigger & signals_df['price_higher_low']
            sell_confirmed = sell_trigger & signals_df['price_lower_high']
        else:
            buy_confirmed = buy_trigger
            sell_confirmed = sell_trigger
        
        signals_df['buy_trigger'] = buy_trigger
        signals_df['sell_trigger'] = sell_trigger
        signals_df['buy_confirmed'] = buy_confirmed
        signals_df['sell_confirmed'] = sell_confirmed
        
        return signals_df
    
    def run_backtest(self, start_date: Optional[str] = None, 
                    end_date: Optional[str] = None) -> Dict[str, Any]:
        """Run complete backtest simulation"""
        if self.signals is None:
            raise ValueError("No signals calculated. Call calculate_signals() first.")
        
        # Filter data by date range if specified
        data = self.signals.copy()
        if start_date:
            data = data[data.index >= start_date]
        if end_date:
            data = data[data.index <= end_date]
        
        # Reset position manager
        self.position_manager.reset()
        
        # Track signals and trades
        buy_signals = []
        sell_signals = []
        exits = []
        
        # Iterate through each bar
        for i, (timestamp, row) in enumerate(data.iterrows()):
            self.position_manager.update_bar(i)
            
            # Check for exit conditions first
            if self.position_manager.is_in_trade():
                # Update trailing stop
                self.position_manager.update_trailing_stop(row['close'], row['atr'])
                
                # Check exit conditions
                should_exit, exit_reason = self.position_manager.check_exit_conditions(
                    row['close'], timestamp, 
                    sell_signal=row.get('sell_confirmed', False),
                    buy_signal=row.get('buy_confirmed', False)
                )
                
                if should_exit:
                    trade = self.position_manager.exit_position(
                        row['close'], timestamp, exit_reason
                    )
                    if trade:  # Only add to exits if trade was successful
                        exits.append({
                            'timestamp': timestamp,
                            'price': row['close'],
                            'trade': trade
                        })
            elif self.position_manager.can_enter_trade():
                # Buy signal
                if row.get('buy_confirmed', False):
                    success = self.position_manager.enter_long_position(
                        row['close'], timestamp, row['atr']
                    )
                    if success:
                        buy_signals.append({
                            'timestamp': timestamp,
                            'price': row['close'],
                            'type': 'BUY'
                        })
                        self._update_last_signal_info('BUY', i)
                
                # Sell signal
                elif row.get('sell_confirmed', False):
                    success = self.position_manager.enter_short_position(
                        row['close'], timestamp, row['atr']
                    )
                    if success:
                        sell_signals.append({
                            'timestamp': timestamp,
                            'price': row['close'],
                            'type': 'SELL'
                        })
                        self._update_last_signal_info('SELL', i)
            
            # Update last signal bars ago
            self._update_signal_bars_ago(i)
        
        # Force exit any remaining position
        if self.position_manager.is_in_trade():
            final_row = data.iloc[-1]
            trade = self.position_manager.exit_position(
                final_row['close'], final_row.name, "End of Data"
            )
            exits.append({
                'timestamp': final_row.name,
                'price': final_row['close'],
                'trade': trade
            })
        
        # Compile results
        results = {
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'exits': exits,
            'trades': self.position_manager.trade_history,
            'statistics': self.position_manager.get_trade_statistics(),
            'data': data
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
        trend_status = latest['trend_trend_status']
        if latest['trend_strong_bullish']:
            trend_color = 'green'
        elif latest['trend_strong_bearish']:
            trend_color = 'red'
        elif latest['trend_above_ema_200']:
            trend_color = 'yellow'
        else:
            trend_color = 'orange'
        
        trend_percentage = (latest['ema_20'] / latest['ema_200'] - 1) * 100
        
        # RSI status
        rsi_value = latest['rsi']
        rsi_status = latest['momentum_rsi_status']
        if latest['momentum_rsi_overbought']:
            rsi_color = 'red'
        elif latest['momentum_rsi_oversold']:
            rsi_color = 'lime'
        else:
            rsi_color = 'yellow'
        
        # MACD status
        macd_hist = latest['histogram']
        macd_status = latest['momentum_macd_status']
        if latest['momentum_macd_rising'] and latest['macd_line'] > latest['signal_line']:
            macd_color = 'lime'
        elif latest['macd_line'] > latest['signal_line']:
            macd_color = 'green'
        elif latest['momentum_macd_falling'] and latest['macd_line'] < latest['signal_line']:
            macd_color = 'red'
        else:
            macd_color = 'orange'
        
        # Setup status
        setup_status = latest['setup_setup_status']
        if latest['setup_buy_setup']:
            setup_color = 'lime'
        elif latest['setup_sell_setup']:
            setup_color = 'red'
        else:
            setup_color = 'gray'
        
        # Candle status
        candle_status = latest['price_candle_status']
        candle_color = 'lime' if latest['price_bull_candle'] else 'red'
        
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
                'percentage': trend_percentage,
                'color': trend_color
            },
            'rsi': {
                'value': rsi_value,
                'status': rsi_status,
                'color': rsi_color
            },
            'macd': {
                'histogram': macd_hist,
                'status': macd_status,
                'color': macd_color
            },
            'setup': {
                'status': setup_status,
                'color': setup_color
            },
            'candle': {
                'status': candle_status,
                'color': candle_color
            },
            'position': position_status,
            'atr': latest['atr'],
            'last_signal': self.last_signal_info
        }
    
    def get_live_signals(self) -> Dict[str, bool]:
        """Get current live trading signals"""
        if self.signals is None or self.signals.empty:
            return {'buy_signal': False, 'sell_signal': False}
        
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
    
    def update_with_new_data(self, new_bar: Dict[str, float]) -> Dict[str, Any]:
        """Update system with new real-time bar data"""
        if self.data is None:
            raise ValueError("No historical data loaded")
        
        # Convert new bar to DataFrame row
        timestamp = datetime.now()
        new_row = pd.DataFrame([new_bar], index=[timestamp])
        
        # Append to existing data
        self.data = pd.concat([self.data, new_row])
        
        # Recalculate signals for the new data
        self.calculate_signals()
        
        # Get current status
        return self.get_current_market_status()
    
    def export_results(self, results: Dict[str, Any], filename: str = "trading_results.csv"):
        """Export trading results to CSV"""
        if not results['trades']:
            print("No trades to export")
            return
        
        # Convert trades to DataFrame
        trades_data = []
        for trade in results['trades']:
            trades_data.append({
                'Entry Time': trade.entry_time,
                'Exit Time': trade.exit_time,
                'Type': trade.trade_type,
                'Entry Price': trade.entry_price,
                'Exit Price': trade.exit_price,
                'P&L %': trade.pnl_percent,
                'Exit Reason': trade.exit_reason,
                'Duration': trade.duration_bars
            })
        
        trades_df = pd.DataFrame(trades_data)
        trades_df.to_csv(filename, index=False)
        print(f"Results exported to {filename}")
    
    def print_statistics(self, results: Dict[str, Any]):
        """Print comprehensive trading statistics"""
        stats = results['statistics']
        
        print("\n" + "="*50)
        print("TRADING SYSTEM PERFORMANCE STATISTICS")
        print("="*50)
        
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Winning Trades: {stats['winning_trades']}")
        print(f"Losing Trades: {stats['losing_trades']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        print(f"Average Win: {stats['avg_win']:.2f}%")
        print(f"Average Loss: {stats['avg_loss']:.2f}%")
        print(f"Total P&L: {stats['total_pnl']:.2f}%")
        print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")
        
        if results['trades']:
            print(f"\nLast 5 Trades:")
            print("-" * 80)
            for trade in results['trades'][-5:]:
                print(f"{trade.entry_time.strftime('%Y-%m-%d %H:%M')} | "
                      f"{trade.trade_type:5s} | "
                      f"Entry: ${trade.entry_price:7.2f} | "
                      f"Exit: ${trade.exit_price:7.2f} | "
                      f"P&L: {trade.pnl_percent:6.2f}% | "
                      f"{trade.exit_reason}")
        
        print("="*50)
    
    def start_live_trading(self, symbol: Optional[str] = None, 
                          interval: Optional[str] = None) -> bool:
        """Start live trading with real-time data"""
        if not self.live_system:
            print("❌ Live trading requires Binance integration")
            return False
        
        symbol = symbol or self.config.symbol
        interval = interval or self.config.interval
        
        print(f"🚀 Starting live trading for {symbol} {interval}")
        
        # Fetch initial historical data
        initial_data = self.live_system.fetch_initial_data(symbol, interval, days=30)
        if initial_data is None:
            return False
        
        self.data = initial_data
        self.calculate_signals()
        
        # Setup live update callback
        def handle_live_update(kline_data, new_row):
            try:
                # Update data with new bar
                self.data = self.live_system.get_combined_data()
                
                # Recalculate signals
                self.calculate_signals()
                
                # Check for new trading signals
                current_signals = self.get_live_signals()
                
                if current_signals['buy_signal']:
                    print(f"🟢 BUY SIGNAL DETECTED at ${kline_data['close']:.4f}!")
                elif current_signals['sell_signal']:
                    print(f"🔴 SELL SIGNAL DETECTED at ${kline_data['close']:.4f}!")
                
                # Update position management
                if self.position_manager.is_in_trade():
                    self.position_manager.update_trailing_stop(
                        kline_data['close'], 
                        self.signals['atr'].iloc[-1] if len(self.signals) > 0 else 0
                    )
                    
                    # Check exit conditions
                    should_exit, exit_reason = self.position_manager.check_exit_conditions(
                        kline_data['close'], 
                        kline_data['timestamp'],
                        sell_signal=current_signals['sell_signal'],
                        buy_signal=current_signals['buy_signal']
                    )
                    
                    if should_exit:
                        trade = self.position_manager.exit_position(
                            kline_data['close'], 
                            kline_data['timestamp'], 
                            exit_reason
                        )
                        if trade:
                            print(f"📊 TRADE CLOSED: {trade.trade_type} | P&L: {trade.pnl_percent:+.2f}% | Reason: {exit_reason}")
                        else:
                            print(f"📊 TRADE CLOSED | Reason: {exit_reason}")
                
            except Exception as e:
                print(f"Error in live update: {e}")
        
        # Add callback and start monitoring
        self.live_system.add_update_callback(handle_live_update)
        success = self.live_system.start_live_monitoring(symbol, interval)
        
        if success:
            print(f"✅ Live trading started for {symbol}")
            print("💡 Press Ctrl+C to stop live trading")
        
        return success
    
    def stop_live_trading(self):
        """Stop live trading"""
        if self.live_system:
            self.live_system.stop_monitoring()
            print("🛑 Live trading stopped")
    
    def get_binance_market_info(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get additional Binance market information"""
        if not self.binance_provider:
            return {}
        
        symbol = symbol or self.config.symbol
        
        try:
            ticker_24hr = self.binance_provider.get_24hr_ticker(symbol)
            latest_price = self.binance_provider.get_latest_price(symbol)
            
            return {
                'current_price': latest_price,
                'price_change_24h': float(ticker_24hr.get('priceChange', 0)),
                'price_change_percent_24h': float(ticker_24hr.get('priceChangePercent', 0)),
                'high_24h': float(ticker_24hr.get('highPrice', 0)),
                'low_24h': float(ticker_24hr.get('lowPrice', 0)),
                'volume_24h': float(ticker_24hr.get('volume', 0)),
                'quote_volume_24h': float(ticker_24hr.get('quoteVolume', 0)),
                'trade_count_24h': int(ticker_24hr.get('count', 0))
            }
            
        except Exception as e:
            print(f"Error getting market info: {e}")
            return {}
    
    def get_popular_symbols(self) -> List[str]:
        """Get list of popular trading symbols"""
        if self.binance_provider:
            return self.binance_provider.get_popular_symbols()
        else:
            return ['AAPL', 'TSLA', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'SPY', 'QQQ', 'BTC-USD']
