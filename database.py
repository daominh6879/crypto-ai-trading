"""
SQLite Database Manager for the Pro Trading System
Handles storage of positions, trades, and trading signals
"""

import sqlite3
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json
import os


@dataclass
class DatabasePosition:
    """Database representation of a trading position"""
    id: Optional[int] = None
    symbol: str = ""
    entry_price: float = 0.0
    entry_time: str = ""
    trade_type: str = ""  # "LONG" or "SHORT"
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    trailing_stop: Optional[float] = None
    quantity: float = 0.0
    is_active: bool = True
    binance_order_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class DatabaseTrade:
    """Database representation of a completed trade"""
    id: Optional[int] = None
    symbol: str = ""
    entry_price: float = 0.0
    exit_price: float = 0.0
    entry_time: str = ""
    exit_time: str = ""
    trade_type: str = ""
    pnl_percent: float = 0.0
    pnl_amount: float = 0.0
    quantity: float = 0.0
    exit_reason: str = ""
    duration_bars: int = 0
    entry_order_id: Optional[str] = None
    exit_order_id: Optional[str] = None
    fees: float = 0.0
    created_at: str = ""


class TradingDatabase:
    """
    SQLite database manager for trading system
    """
    
    def __init__(self, db_path: str = "trading_system.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                trade_type TEXT NOT NULL CHECK (trade_type IN ('LONG', 'SHORT')),
                stop_loss REAL NOT NULL,
                take_profit_1 REAL NOT NULL,
                take_profit_2 REAL NOT NULL,
                trailing_stop REAL,
                quantity REAL NOT NULL DEFAULT 0.0,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                binance_order_id TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT NOT NULL,
                trade_type TEXT NOT NULL CHECK (trade_type IN ('LONG', 'SHORT')),
                pnl_percent REAL NOT NULL,
                pnl_amount REAL NOT NULL DEFAULT 0.0,
                quantity REAL NOT NULL DEFAULT 0.0,
                exit_reason TEXT NOT NULL,
                duration_bars INTEGER NOT NULL DEFAULT 0,
                entry_order_id TEXT,
                exit_order_id TEXT,
                fees REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create signals table for analysis
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                signal_type TEXT NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'EXIT')),
                price REAL NOT NULL,
                rsi REAL,
                macd_histogram REAL,
                trend_status TEXT,
                confidence REAL,
                executed BOOLEAN NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_active ON positions(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(entry_time)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp)")
        
        conn.commit()
        conn.close()
    
    def save_position(self, position: DatabasePosition) -> int:
        """Save or update a position in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        position_dict = asdict(position)
        position_dict['updated_at'] = datetime.now().isoformat()
        
        if position.id is None:
            # Insert new position
            position_dict['created_at'] = datetime.now().isoformat()
            position_dict.pop('id')  # Remove id for insert
            
            columns = ', '.join(position_dict.keys())
            placeholders = ', '.join(['?' for _ in position_dict])
            
            cursor.execute(f"""
                INSERT INTO positions ({columns})
                VALUES ({placeholders})
            """, list(position_dict.values()))
            
            position_id = cursor.lastrowid
        else:
            # Update existing position
            position_dict.pop('created_at', None)  # Don't update created_at
            # Only proceed if there are fields to update
            updateable_fields = {k: v for k, v in position_dict.items() if k != 'id'}
            
            if updateable_fields:
                set_clause = ', '.join([f"{k} = ?" for k in updateable_fields.keys()])
                values = list(updateable_fields.values())
                values.append(position.id)
                
                cursor.execute(f"""
                    UPDATE positions 
                    SET {set_clause}
                    WHERE id = ?
                """, values)
            
            position_id = position.id
        
        conn.commit()
        conn.close()
        return position_id
    
    def get_active_position(self, symbol: str) -> Optional[DatabasePosition]:
        """Get active position for a symbol"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM positions 
            WHERE symbol = ? AND is_active = 1
            ORDER BY created_at DESC
            LIMIT 1
        """, (symbol,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            columns = [desc[0] for desc in cursor.description]
            position_dict = dict(zip(columns, result))
            return DatabasePosition(**position_dict)
        
        return None
    
    def close_position(self, position_id: int, exit_price: float, exit_time: datetime, 
                      exit_reason: str, exit_order_id: str = None) -> DatabaseTrade:
        """Close a position and create a trade record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get position details
            cursor.execute("SELECT * FROM positions WHERE id = ?", (position_id,))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError(f"Position {position_id} not found")
            
            columns = [desc[0] for desc in cursor.description]
            position_dict = dict(zip(columns, result))
            position = DatabasePosition(**position_dict)
            
            # Calculate P&L
            if position.trade_type == "LONG":
                pnl_percent = (exit_price - position.entry_price) / position.entry_price * 100
            else:  # SHORT
                pnl_percent = (position.entry_price - exit_price) / position.entry_price * 100
            
            pnl_amount = (pnl_percent / 100) * position.quantity * position.entry_price
            
            # Deactivate position
            cursor.execute("""
                UPDATE positions 
                SET is_active = 0, updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), position_id))
            
            # Create trade record
            trade = DatabaseTrade(
                symbol=position.symbol,
                entry_price=position.entry_price,
                exit_price=exit_price,
                entry_time=position.entry_time,
                exit_time=exit_time.isoformat(),
                trade_type=position.trade_type,
                pnl_percent=pnl_percent,
                pnl_amount=pnl_amount,
                quantity=position.quantity,
                exit_reason=exit_reason,
                entry_order_id=position.binance_order_id,
                exit_order_id=exit_order_id,
                created_at=datetime.now().isoformat()
            )
            
            trade_id = self.save_trade(trade)
            trade.id = trade_id
            
            conn.commit()
            return trade
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def save_trade(self, trade: DatabaseTrade) -> int:
        """Save a completed trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        trade_dict = asdict(trade)
        trade_dict.pop('id')  # Remove id for insert
        
        columns = ', '.join(trade_dict.keys())
        placeholders = ', '.join(['?' for _ in trade_dict])
        
        cursor.execute(f"""
            INSERT INTO trades ({columns})
            VALUES ({placeholders})
        """, list(trade_dict.values()))
        
        trade_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return trade_id
    
    def save_signal(self, symbol: str, signal_type: str, price: float, 
                   timestamp: datetime, **kwargs) -> int:
        """Save a trading signal to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert timestamp to datetime if needed
        if hasattr(timestamp, 'to_pydatetime'):
            # pandas Timestamp
            timestamp = timestamp.to_pydatetime()
        elif isinstance(timestamp, str):
            # String timestamp
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        cursor.execute("""
            INSERT INTO signals (symbol, timestamp, signal_type, price, rsi, 
                               macd_histogram, trend_status, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol,
            timestamp.isoformat(),
            signal_type,
            price,
            kwargs.get('rsi'),
            kwargs.get('macd_histogram'),
            kwargs.get('trend_status'),
            kwargs.get('confidence', 0.5),  # Default confidence
            datetime.now().isoformat()
        ))
        
        signal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return signal_id
    
    def get_trade_history(self, symbol: str = None, limit: int = 100) -> List[DatabaseTrade]:
        """Get trade history from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute("""
                SELECT * FROM trades 
                WHERE symbol = ?
                ORDER BY exit_time DESC 
                LIMIT ?
            """, (symbol, limit))
        else:
            cursor.execute("""
                SELECT * FROM trades 
                ORDER BY exit_time DESC 
                LIMIT ?
            """, (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        trades = []
        if results:
            columns = [desc[0] for desc in cursor.description]
            for result in results:
                trade_dict = dict(zip(columns, result))
                trades.append(DatabaseTrade(**trade_dict))
        
        return trades
    
    def get_statistics(self, symbol: str = None) -> Dict[str, Any]:
        """Get trading statistics from database"""
        conn = sqlite3.connect(self.db_path)
        
        if symbol:
            df = pd.read_sql_query("""
                SELECT * FROM trades 
                WHERE symbol = ?
                ORDER BY exit_time
            """, conn, params=[symbol])
        else:
            df = pd.read_sql_query("""
                SELECT * FROM trades 
                ORDER BY exit_time
            """, conn)
        
        conn.close()
        
        if df.empty:
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
        
        winning_trades = df[df['pnl_percent'] > 0]
        losing_trades = df[df['pnl_percent'] < 0]
        
        total_trades = len(df)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = winning_trades['pnl_percent'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['pnl_percent'].mean() if not losing_trades.empty else 0
        
        total_pnl = df['pnl_percent'].sum()
        total_amount_pnl = df['pnl_amount'].sum()
        
        # Calculate maximum drawdown
        cumulative_pnl = df['pnl_percent'].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = running_max - cumulative_pnl
        max_drawdown = drawdown.max() if not drawdown.empty else 0
        
        # Profit factor
        gross_profit = winning_trades['pnl_percent'].sum() if not winning_trades.empty else 0
        gross_loss = abs(losing_trades['pnl_percent'].sum()) if not losing_trades.empty else 0
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
    
    def export_to_csv(self, table_name: str, filename: str = None):
        """Export database table to CSV"""
        if filename is None:
            filename = f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        conn = sqlite3.connect(self.db_path)
        
        if table_name == 'trades':
            df = pd.read_sql_query("SELECT * FROM trades ORDER BY exit_time DESC", conn)
        elif table_name == 'positions':
            df = pd.read_sql_query("SELECT * FROM positions ORDER BY created_at DESC", conn)
        elif table_name == 'signals':
            df = pd.read_sql_query("SELECT * FROM signals ORDER BY timestamp DESC", conn)
        else:
            raise ValueError(f"Unknown table: {table_name}")
        
        conn.close()
        
        df.to_csv(filename, index=False)
        print(f"Exported {len(df)} records to {filename}")
        
        return filename
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old inactive positions and old signals"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - pd.Timedelta(days=days)).isoformat()
        
        # Remove old inactive positions
        cursor.execute("""
            DELETE FROM positions 
            WHERE is_active = 0 AND updated_at < ?
        """, (cutoff_date,))
        
        # Remove old signals
        cursor.execute("""
            DELETE FROM signals 
            WHERE timestamp < ? AND executed = 0
        """, (cutoff_date,))
        
        conn.commit()
        conn.close()
        
        print(f"Cleaned up data older than {days} days")
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get overall portfolio summary"""
        conn = sqlite3.connect(self.db_path)
        
        # Get active positions
        active_positions = pd.read_sql_query("""
            SELECT symbol, COUNT(*) as count, AVG(entry_price) as avg_entry
            FROM positions 
            WHERE is_active = 1
            GROUP BY symbol
        """, conn)
        
        # Get trade summary by symbol
        trade_summary = pd.read_sql_query("""
            SELECT symbol, 
                   COUNT(*) as total_trades,
                   SUM(pnl_amount) as total_pnl_amount,
                   AVG(pnl_percent) as avg_pnl_percent
            FROM trades 
            GROUP BY symbol
        """, conn)
        
        conn.close()
        
        return {
            'active_positions': active_positions.to_dict('records'),
            'trade_summary': trade_summary.to_dict('records'),
            'database_path': self.db_path,
            'last_updated': datetime.now().isoformat()
        }


# Singleton instance for global access
_database_instance = None

def get_database() -> TradingDatabase:
    """Get global database instance"""
    global _database_instance
    if _database_instance is None:
        _database_instance = TradingDatabase()
    return _database_instance