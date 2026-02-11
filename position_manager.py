"""
Position Management for the Pro Trader System
Handles trade entries, exits, and risk management with SQLite database integration
Converted from TradingView Pine Script
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, Any, List
from dataclasses import dataclass
from datetime import datetime
from config import TradingConfig

# Import database components
try:
    from database import TradingDatabase, DatabasePosition, DatabaseTrade, get_database
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    print("Warning: Database module not available")


@dataclass
class Position:
    """Represents an active trading position (legacy compatibility)"""
    entry_price: float
    entry_time: datetime
    trade_type: str  # "LONG" or "SHORT"
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    trailing_stop: Optional[float] = None
    entry_bar: int = 0
    is_active: bool = True
    quantity: float = 0.0
    db_id: Optional[int] = None  # Database ID


@dataclass
class Trade:
    """Represents a completed trade for record keeping (legacy compatibility)"""
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    trade_type: str
    pnl_percent: float
    exit_reason: str
    duration_bars: int
    quantity: float = 0.0
    pnl_amount: float = 0.0
    fees: float = 0.0


class EnhancedPositionManager:
    """
    Enhanced position manager with SQLite database integration
    """
    
    def __init__(self, config: TradingConfig, symbol: str = "BTCUSDT"):
        self.config = config
        self.symbol = symbol
        self.current_position: Optional[Position] = None
        self.trade_history: List[Trade] = []
        self.last_buy_bar = -999
        self.last_sell_bar = -999
        self.current_bar = 0
        self.backtesting_mode = False  # Initialize backtesting mode flag
        
        # Database integration
        if HAS_DATABASE:
            self.db = get_database()
            self._load_active_position()
        else:
            self.db = None
    
    def _load_active_position(self):
        """Load active position from database if exists"""
        if not self.db:
            return
        
        try:
            db_position = self.db.get_active_position(self.symbol)
            if db_position and hasattr(db_position, 'trade_type') and db_position.trade_type:
                # Validate required fields before creating position
                required_fields = ['entry_price', 'entry_time', 'trade_type', 'stop_loss', 
                                 'take_profit_1', 'take_profit_2', 'quantity']
                
                if all(hasattr(db_position, field) and getattr(db_position, field) is not None 
                       for field in required_fields):
                    # Convert database position to internal position
                    self.current_position = Position(
                        entry_price=db_position.entry_price,
                        entry_time=datetime.fromisoformat(db_position.entry_time),
                        trade_type=db_position.trade_type,
                        stop_loss=db_position.stop_loss,
                        take_profit_1=db_position.take_profit_1,
                        take_profit_2=db_position.take_profit_2,
                        trailing_stop=getattr(db_position, 'trailing_stop', db_position.stop_loss),
                        quantity=db_position.quantity,
                        db_id=db_position.id,
                        is_active=db_position.is_active
                    )
                    print(f"📊 Loaded active {db_position.trade_type} position from database")
                else:
                    print("⚠️  Incomplete position found in database, skipping")
        except Exception as e:
            print(f"Warning: Could not load active position: {e}")
            self.current_position = None
    
    def reset(self):
        """Reset position manager state (for backtesting)"""
        self.current_position = None
        self.trade_history = []
        self.last_buy_bar = -999
        self.last_sell_bar = -999
        self.current_bar = 0
        self.backtesting_mode = True  # Enable backtesting mode to ignore database
        print("🔄 Position manager reset for backtesting")
    
    def enable_live_mode(self):
        """Enable live trading mode (disable backtesting isolation)"""
        self.backtesting_mode = False
        print("📡 Live trading mode enabled")
    
    def is_in_trade(self) -> bool:
        """Check if currently in a trade"""
        # In backtesting mode, only check local position
        if hasattr(self, 'backtesting_mode') and self.backtesting_mode:
            return self.current_position is not None and self.current_position.is_active
        
        # Check local position first (important for backtesting)
        if self.current_position is not None and self.current_position.is_active:
            return True
            
        # If no local position, check database for live trading
        if self.db and self.current_position is None:
            db_position = self.db.get_active_position(self.symbol)
            if db_position and db_position.is_active:
                return True
        
        return False
    
    def can_enter_trade(self) -> bool:
        """Check if new trade entry is allowed"""
        if self.is_in_trade():
            return False
        
        # Check minimum gap between signals
        gap_ok = (
            (self.current_bar - self.last_buy_bar >= self.config.min_bars_gap) and
            (self.current_bar - self.last_sell_bar >= self.config.min_bars_gap)
        )
        
        return gap_ok
    
    def calculate_position_levels(self, entry_price: float, trade_type: str, 
                                atr: float) -> Tuple[float, float, float]:
        """Calculate stop loss and take profit levels"""
        if trade_type == "LONG":
            stop_loss = entry_price - (atr * self.config.stop_loss_multiplier)
            take_profit_1 = entry_price + (atr * self.config.take_profit_1_multiplier)
            take_profit_2 = entry_price + (atr * self.config.take_profit_2_multiplier)
        else:  # SHORT
            stop_loss = entry_price + (atr * self.config.stop_loss_multiplier)
            take_profit_1 = entry_price - (atr * self.config.take_profit_1_multiplier)
            take_profit_2 = entry_price - (atr * self.config.take_profit_2_multiplier)
        
        return stop_loss, take_profit_1, take_profit_2
    
    def enter_position(self, trade_type: str, price: float, timestamp: datetime, 
                      atr: float, quantity: float = 0.0, order_id: str = None) -> bool:
        """Enter a new position (universal method for LONG/SHORT)"""
        if not self.can_enter_trade():
            return False
        
        stop_loss, tp1, tp2 = self.calculate_position_levels(price, trade_type, atr)
        
        # Create position object
        position = Position(
            entry_price=price,
            entry_time=timestamp,
            trade_type=trade_type,
            stop_loss=stop_loss,
            take_profit_1=tp1,
            take_profit_2=tp2,
            entry_bar=self.current_bar,
            quantity=quantity
        )
        
        # Save to database if available (skip in backtesting mode)
        if self.db and not getattr(self, 'backtesting_mode', False):
            db_position = DatabasePosition(
                symbol=self.symbol,
                entry_price=price,
                entry_time=timestamp.isoformat(),
                trade_type=trade_type,
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2,
                quantity=quantity,
                binance_order_id=order_id,
                is_active=True
            )
            
            db_id = self.db.save_position(db_position)
            position.db_id = db_id
            print(f"💾 Position saved to database with ID: {db_id}")
        elif getattr(self, 'backtesting_mode', False):
            print(f"📝 Position created (backtesting mode - not saved to database)")
        
        self.current_position = position
        
        # Update signal tracking
        if trade_type == "LONG":
            self.last_buy_bar = self.current_bar
        else:
            self.last_sell_bar = self.current_bar
        
        return True
    
    def enter_long_position(self, price: float, timestamp: datetime, atr: float, 
                           quantity: float = 0.0, order_id: str = None) -> bool:
        """Enter a long position"""
        return self.enter_position("LONG", price, timestamp, atr, quantity, order_id)
    
    def enter_short_position(self, price: float, timestamp: datetime, atr: float,
                            quantity: float = 0.0, order_id: str = None) -> bool:
        """Enter a short position"""
        return self.enter_position("SHORT", price, timestamp, atr, quantity, order_id)
    
    def update_trailing_stop(self, current_price: float, atr: float):
        """Update trailing stop loss with dynamic trailing based on profit level"""
        if not self.is_in_trade() or not self.current_position:
            return

        position = self.current_position
        updated = False

        if position.trade_type == "LONG":
            # Calculate current profit
            current_profit_pct = (current_price - position.entry_price) / position.entry_price

            # Dynamic trailing based on profit level (professional technique)
            if getattr(self.config, 'dynamic_trailing', False):
                if current_profit_pct > 0.06:  # 6%+ profit: very tight trail (40% of initial stop)
                    trail_factor = 0.40
                elif current_profit_pct > 0.04:  # 4-6% profit: tight trail (50% of initial stop)
                    trail_factor = 0.50
                elif current_profit_pct > 0.02:  # 2-4% profit: normal trail (60% of initial stop)
                    trail_factor = 0.60
                else:  # Below 2%: use configured trail factor
                    trail_factor = self.config.trailing_stop_factor
            else:
                trail_factor = self.config.trailing_stop_factor

            # Activate trailing stop at configured profit level
            if current_profit_pct > self.config.trailing_activation:
                new_trail = current_price - (atr * self.config.stop_loss_multiplier * trail_factor)
                if position.trailing_stop is None or new_trail > position.trailing_stop:
                    position.trailing_stop = new_trail
                    updated = True

        else:  # SHORT
            # Calculate current profit
            current_profit_pct = (position.entry_price - current_price) / position.entry_price

            # Dynamic trailing based on profit level
            if getattr(self.config, 'dynamic_trailing', False):
                if current_profit_pct > 0.06:
                    trail_factor = 0.40
                elif current_profit_pct > 0.04:
                    trail_factor = 0.50
                elif current_profit_pct > 0.02:
                    trail_factor = 0.60
                else:
                    trail_factor = self.config.trailing_stop_factor
            else:
                trail_factor = self.config.trailing_stop_factor

            # Activate trailing stop
            if current_profit_pct > self.config.trailing_activation:
                new_trail = current_price + (atr * self.config.stop_loss_multiplier * trail_factor)
                if position.trailing_stop is None or new_trail < position.trailing_stop:
                    position.trailing_stop = new_trail
                    updated = True
        
        # Update in database
        if updated and self.db and position.db_id:
            try:
                db_position = DatabasePosition(
                    id=position.db_id,
                    symbol=self.symbol,
                    entry_price=position.entry_price,
                    entry_time=position.entry_time.isoformat(),
                    trade_type=position.trade_type,
                    stop_loss=position.stop_loss,
                    take_profit_1=position.take_profit_1,
                    take_profit_2=position.take_profit_2,
                    trailing_stop=position.trailing_stop,
                    quantity=position.quantity,
                    is_active=position.is_active
                )
                self.db.save_position(db_position)
            except Exception as e:
                print(f"Warning: Could not update trailing stop in database: {e}")
    
    def check_exit_conditions(self, current_price: float, timestamp: datetime,
                            sell_signal: bool = False, buy_signal: bool = False) -> Tuple[bool, str]:
        """Check if position should be exited and return exit reason"""
        if not self.is_in_trade() or not self.current_position:
            return False, ""
        
        position = self.current_position
        
        # Additional safety check
        if not hasattr(position, 'trade_type') or position.trade_type is None:
            return False, ""
        
        if position.trade_type == "LONG":
            # Exit conditions for long positions
            if sell_signal:
                return True, "Opposite Signal"
            elif current_price <= position.stop_loss:
                return True, "Stop Loss"
            elif current_price >= position.take_profit_2:
                return True, "Take Profit 2"
            elif position.trailing_stop and current_price <= position.trailing_stop:
                return True, "Trailing Stop"
        
        else:  # SHORT
            # Exit conditions for short positions
            if buy_signal:
                return True, "Opposite Signal"
            elif current_price >= position.stop_loss:
                return True, "Stop Loss"
            elif current_price <= position.take_profit_2:
                return True, "Take Profit 2"
            elif position.trailing_stop and current_price >= position.trailing_stop:
                return True, "Trailing Stop"
        
        return False, ""
    
    def exit_position(self, exit_price: float, exit_time: datetime, exit_reason: str,
                     exit_order_id: str = None) -> Optional[Trade]:
        """Exit current position and record the trade"""
        if not self.is_in_trade() or not self.current_position:
            print(f"⚠️  Cannot exit - no active position (exit_reason: {exit_reason})")
            return None
        
        position = self.current_position
        
        # Validate position has required attributes
        if not hasattr(position, 'trade_type') or position.trade_type is None:
            print(f"⚠️  Cannot exit - position missing trade_type (exit_reason: {exit_reason})")
            return None
        
        # Calculate P&L
        if position.trade_type == "LONG":
            pnl_percent = (exit_price - position.entry_price) / position.entry_price * 100
        else:  # SHORT
            pnl_percent = (position.entry_price - exit_price) / position.entry_price * 100
        
        pnl_amount = (pnl_percent / 100) * position.quantity * position.entry_price if position.quantity > 0 else 0
        
        # Create trade record
        trade = Trade(
            entry_price=position.entry_price,
            exit_price=exit_price,
            entry_time=position.entry_time,
            exit_time=exit_time,
            trade_type=position.trade_type,
            pnl_percent=pnl_percent,
            exit_reason=exit_reason,
            duration_bars=self.current_bar - position.entry_bar,
            quantity=position.quantity,
            pnl_amount=pnl_amount
        )
        
        # Close position in database (skip in backtesting mode)
        if self.db and position.db_id and not getattr(self, 'backtesting_mode', False):
            try:
                db_trade = self.db.close_position(
                    position_id=position.db_id,
                    exit_price=exit_price,
                    exit_time=exit_time,
                    exit_reason=exit_reason,
                    exit_order_id=exit_order_id
                )
                print(f"💾 Position closed in database. P&L: {db_trade.pnl_percent:+.2f}%")
            except Exception as e:
                print(f"Warning: Could not close position in database: {e}")
        elif getattr(self, 'backtesting_mode', False):
            print(f"📝 Position closed (backtesting mode - not saved to database)")
        
        # Add to local trade history
        self.trade_history.append(trade)
        
        # Clear position
        self.current_position = None
        
        return trade
    
    def get_current_pnl(self, current_price: float) -> float:
        """Get current unrealized P&L percentage"""
        if not self.is_in_trade() or not self.current_position:
            return 0.0
        
        position = self.current_position
        
        if position.trade_type == "LONG":
            return (current_price - position.entry_price) / position.entry_price * 100
        else:  # SHORT
            return (position.entry_price - current_price) / position.entry_price * 100
    
    def get_risk_reward_ratio(self) -> float:
        """Get current position's risk-reward ratio"""
        if not self.is_in_trade() or not self.current_position:
            return 0.0
        
        position = self.current_position
        
        if position.trade_type == "LONG":
            profit_potential = abs(position.take_profit_1 - position.entry_price)
            risk = abs(position.entry_price - position.stop_loss)
        else:  # SHORT
            profit_potential = abs(position.entry_price - position.take_profit_1)
            risk = abs(position.stop_loss - position.entry_price)
        
        return profit_potential / risk if risk > 0 else 0.0
    
    def get_position_status(self) -> Dict[str, Any]:
        """Get current position status information"""
        if not self.is_in_trade():
            return {
                'status': 'None',
                'type': '',
                'pnl_percent': 0.0,
                'risk_reward': 0.0,
                'entry_price': None,
                'stop_loss': None,
                'take_profit_1': None,
                'take_profit_2': None,
                'trailing_stop': None,
                'quantity': 0.0
            }
        
        position = self.current_position
        
        return {
            'status': 'Running',
            'type': position.trade_type,
            'pnl_percent': 0.0,  # Will be updated in main loop
            'risk_reward': self.get_risk_reward_ratio(),
            'entry_price': position.entry_price,
            'stop_loss': position.stop_loss,
            'take_profit_1': position.take_profit_1,
            'take_profit_2': position.take_profit_2,
            'trailing_stop': position.trailing_stop,
            'quantity': position.quantity
        }
    
    def get_trade_statistics(self) -> Dict[str, Any]:
        """Get trading performance statistics (enhanced with database)"""
        # In backtesting mode, always use local statistics
        if hasattr(self, 'backtesting_mode') and self.backtesting_mode:
            # Use local statistics for backtest
            pass
        # Get statistics from database if available (live mode only)
        elif self.db:
            return self.db.get_statistics(self.symbol)
        
        # Fallback to local statistics
        if not self.trade_history:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'total_pnl': 0.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0,
                'total_amount_pnl': 0.0
            }
        
        pnls = [trade.pnl_percent for trade in self.trade_history if trade is not None]
        winning_trades = [pnl for pnl in pnls if pnl > 0]
        losing_trades = [pnl for pnl in pnls if pnl < 0]
        
        total_trades = len([trade for trade in self.trade_history if trade is not None])
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        
        total_pnl = sum(pnls)
        total_amount_pnl = sum([trade.pnl_amount for trade in self.trade_history if trade is not None])
        
        # Calculate maximum drawdown
        cumulative_pnl = np.cumsum(pnls)
        running_max = np.maximum.accumulate(cumulative_pnl)
        drawdown = running_max - cumulative_pnl
        max_drawdown = max(drawdown) if len(drawdown) > 0 else 0
        
        # Profit factor
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'total_pnl': total_pnl,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'total_amount_pnl': total_amount_pnl
        }
    
    def update_bar(self, bar_index: int):
        """Update current bar index"""
        self.current_bar = bar_index
    
    def export_trades(self, filename: str = None) -> str:
        """Export trades to CSV file"""
        if self.db:
            return self.db.export_to_csv('trades', filename)
        else:
            # Fallback to local export
            if filename is None:
                filename = f"trades_{self.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            trades_data = []
            for trade in self.trade_history:
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
            
            df = pd.DataFrame(trades_data)
            df.to_csv(filename, index=False)
            print(f"Exported {len(df)} trades to {filename}")
            return filename


# Create alias for compatibility
PositionManager = EnhancedPositionManager