"""
Binance Live Trading Provider for the Pro Trader System
Provides historical data, live streaming, and order execution capabilities
"""

import pandas as pd
import numpy as np
import time
import threading
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Callable, Any
import warnings
warnings.filterwarnings('ignore')

try:
    from binance import Client, BinanceSocketManager
    from binance.enums import SIDE_BUY, SIDE_SELL, ORDER_TYPE_MARKET, ORDER_TYPE_LIMIT
    from binance.exceptions import BinanceAPIException, BinanceOrderException
    import websocket
    HAS_BINANCE = True
except ImportError:
    HAS_BINANCE = False
    print("Warning: python-binance not found. Install with: pip install python-binance")

from config import TradingConfig


class BinanceDataProvider:
    """
    Enhanced Binance provider for historical data, live streaming, and order execution
    """
    
    def __init__(self, config: TradingConfig, api_key: str = "", api_secret: str = ""):
        self.config = config
        self.client = None
        self.socket_manager = None
        self.live_data_callback = None
        self.is_streaming = False
        self.latest_kline = None
        self.is_live_trading = False
        self.account_info = None
        self.symbol_info = {}
        
        # Get API keys from environment if not provided
        if not api_key:
            api_key = os.getenv('BINANCE_API_KEY', '')
        if not api_secret:
            api_secret = os.getenv('BINANCE_API_SECRET', '')
        
        self.api_key = api_key
        self.api_secret = api_secret
        
        if HAS_BINANCE:
            try:
                # Initialize client
                if api_key and api_secret:
                    self.client = Client(api_key, api_secret, testnet=False)
                    self.is_live_trading = True
                    print("✅ Binance client initialized with API credentials for LIVE trading")
                    
                    # Test connection and get account info
                    try:
                        self.account_info = self.client.get_account()
                        print("✅ Binance account connection verified")
                    except Exception as e:
                        print(f"⚠️ Warning: API key verification failed: {e}")
                        print("[*] Falling back to data-only mode")
                        self.is_live_trading = False
                        self.client = Client()
                else:
                    self.client = Client()
                    print("[*] Binance client initialized for data access only (no API keys)")
                    
            except Exception as e:
                print(f"Warning: Could not initialize Binance client: {e}")
                print("Continuing with public data access only...")
                if HAS_BINANCE:
                    self.client = Client()
    
    def get_account_balance(self, asset: str = 'USDT') -> float:
        """Get account balance for specific asset"""
        if not self.is_live_trading or not self.client:
            return 0.0
        
        try:
            account = self.client.get_account()
            for balance in account['balances']:
                if balance['asset'] == asset:
                    return float(balance['free'])
            return 0.0
        except Exception as e:
            print(f"Error getting balance: {e}")
            return 0.0
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information for order precision"""
        if symbol in self.symbol_info:
            return self.symbol_info[symbol]
        
        try:
            info = self.client.get_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    # Extract important order parameters
                    symbol_data = {
                        'symbol': symbol,
                        'status': s['status'],
                        'base_asset': s['baseAsset'],
                        'quote_asset': s['quoteAsset'],
                        'min_qty': 0.0,
                        'max_qty': 0.0,
                        'step_size': 0.0,
                        'min_notional': 0.0,
                        'tick_size': 0.0
                    }
                    
                    # Parse filters
                    for f in s['filters']:
                        if f['filterType'] == 'LOT_SIZE':
                            symbol_data['min_qty'] = float(f['minQty'])
                            symbol_data['max_qty'] = float(f['maxQty'])
                            symbol_data['step_size'] = float(f['stepSize'])
                        elif f['filterType'] == 'MIN_NOTIONAL':
                            symbol_data['min_notional'] = float(f['minNotional'])
                        elif f['filterType'] == 'PRICE_FILTER':
                            symbol_data['tick_size'] = float(f['tickSize'])
                    
                    self.symbol_info[symbol] = symbol_data
                    return symbol_data
            
            return {}
        except Exception as e:
            print(f"Error getting symbol info: {e}")
            return {}
    
    def calculate_quantity(self, symbol: str, price: float, usdt_amount: float) -> float:
        """Calculate appropriate quantity for order"""
        info = self.get_symbol_info(symbol)
        if not info:
            return 0.0
        
        # Calculate base quantity
        quantity = usdt_amount / price
        
        # Adjust for step size
        step_size = info['step_size']
        if step_size > 0:
            quantity = round(quantity / step_size) * step_size
        
        # Check minimum quantity
        min_qty = info['min_qty']
        if quantity < min_qty:
            print(f"⚠️ Quantity {quantity} below minimum {min_qty}")
            return 0.0
        
        # Check maximum quantity
        max_qty = info['max_qty']
        if max_qty > 0 and quantity > max_qty:
            quantity = max_qty
        
        # Check minimum notional value
        notional = quantity * price
        min_notional = info['min_notional']
        if notional < min_notional:
            print(f"⚠️ Order value {notional} below minimum {min_notional}")
            return 0.0
        
        return quantity
    
    def place_buy_order(self, symbol: str, quantity: float = None, price: float = None, 
                       order_type: str = 'MARKET', usdt_amount: float = None) -> Dict[str, Any]:
        """Place a buy order on Binance"""
        if not self.is_live_trading:
            return {'error': 'Live trading not enabled', 'orderId': None}
        
        try:
            # Get current price if not provided
            if price is None:
                price = self.get_latest_price(symbol)
            
            # Calculate quantity if USDT amount provided
            if quantity is None and usdt_amount is not None:
                quantity = self.calculate_quantity(symbol, price, usdt_amount)
            
            if quantity <= 0:
                return {'error': 'Invalid quantity', 'orderId': None}
            
            print(f"[*] Placing BUY order: {quantity} {symbol} at ${price}")
            
            if order_type == 'MARKET':
                order = self.client.order_market_buy(
                    symbol=symbol,
                    quantity=quantity
                )
            else:  # LIMIT order
                order = self.client.order_limit_buy(
                    symbol=symbol,
                    quantity=quantity,
                    price=str(price)
                )
            
            print(f"✅ BUY order placed successfully: Order ID {order['orderId']}")
            return {
                'success': True,
                'orderId': order['orderId'],
                'symbol': symbol,
                'side': 'BUY',
                'quantity': float(order['executedQty']) if 'executedQty' in order else quantity,
                'price': float(order['fills'][0]['price']) if 'fills' in order and order['fills'] else price,
                'status': order['status'],
                'order': order
            }
            
        except BinanceAPIException as e:
            error_msg = f"Binance API Error: {e}"
            print(f"❌ {error_msg}")
            return {'error': error_msg, 'orderId': None}
        except BinanceOrderException as e:
            error_msg = f"Binance Order Error: {e}"
            print(f"❌ {error_msg}")
            return {'error': error_msg, 'orderId': None}
        except Exception as e:
            error_msg = f"Unexpected error placing buy order: {e}"
            print(f"❌ {error_msg}")
            return {'error': error_msg, 'orderId': None}
    
    def place_sell_order(self, symbol: str, quantity: float, price: float = None, 
                        order_type: str = 'MARKET') -> Dict[str, Any]:
        """Place a sell order on Binance"""
        if not self.is_live_trading:
            return {'error': 'Live trading not enabled', 'orderId': None}
        
        try:
            # Get current price if not provided
            if price is None:
                price = self.get_latest_price(symbol)
            
            print(f"[*] Placing SELL order: {quantity} {symbol} at ${price}")
            
            if order_type == 'MARKET':
                order = self.client.order_market_sell(
                    symbol=symbol,
                    quantity=quantity
                )
            else:  # LIMIT order
                order = self.client.order_limit_sell(
                    symbol=symbol,
                    quantity=quantity,
                    price=str(price)
                )
            
            print(f"✅ SELL order placed successfully: Order ID {order['orderId']}")
            return {
                'success': True,
                'orderId': order['orderId'],
                'symbol': symbol,
                'side': 'SELL',
                'quantity': float(order['executedQty']) if 'executedQty' in order else quantity,
                'price': float(order['fills'][0]['price']) if 'fills' in order and order['fills'] else price,
                'status': order['status'],
                'order': order
            }
            
        except BinanceAPIException as e:
            error_msg = f"Binance API Error: {e}"
            print(f"❌ {error_msg}")
            return {'error': error_msg, 'orderId': None}
        except BinanceOrderException as e:
            error_msg = f"Binance Order Error: {e}"
            print(f"❌ {error_msg}")
            return {'error': error_msg, 'orderId': None}
        except Exception as e:
            error_msg = f"Unexpected error placing sell order: {e}"
            print(f"❌ {error_msg}")
            return {'error': error_msg, 'orderId': None}
    
    def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Get order status from Binance"""
        if not self.is_live_trading:
            return {'error': 'Live trading not enabled'}
        
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            return {
                'orderId': order['orderId'],
                'symbol': order['symbol'],
                'status': order['status'],
                'side': order['side'],
                'quantity': float(order['origQty']),
                'executed_qty': float(order['executedQty']),
                'price': float(order['price']) if order['price'] != '0.00000000' else None,
                'avg_price': float(order['cummulativeQuoteQty']) / float(order['executedQty']) if float(order['executedQty']) > 0 else 0
            }
        except Exception as e:
            return {'error': f"Error getting order status: {e}"}
    
    def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an open order"""
        if not self.is_live_trading:
            return {'error': 'Live trading not enabled'}
        
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            print(f"✅ Order {order_id} cancelled successfully")
            return {'success': True, 'orderId': order_id, 'result': result}
        except Exception as e:
            error_msg = f"Error cancelling order: {e}"
            print(f"❌ {error_msg}")
            return {'error': error_msg}
    
    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Get all open orders"""
        if not self.is_live_trading:
            return []
        
        try:
            if symbol:
                orders = self.client.get_open_orders(symbol=symbol)
            else:
                orders = self.client.get_open_orders()
            
            formatted_orders = []
            for order in orders:
                formatted_orders.append({
                    'orderId': order['orderId'],
                    'symbol': order['symbol'],
                    'side': order['side'],
                    'quantity': float(order['origQty']),
                    'price': float(order['price']) if order['price'] != '0.00000000' else None,
                    'status': order['status'],
                    'type': order['type'],
                    'time': datetime.fromtimestamp(order['time'] / 1000)
                })
            
            return formatted_orders
        except Exception as e:
            print(f"Error getting open orders: {e}")
            return []
    
    def get_historical_data(self, symbol: str, interval: str, 
                          limit: int = 1000, start_str: str = None) -> pd.DataFrame:
        """Fetch historical kline data from Binance"""
        if not HAS_BINANCE or not self.client:
            raise Exception("Binance client not available")
        
        try:
            # Convert interval format
            binance_interval = self._convert_interval(interval)
            
            # Fetch klines
            if start_str:
                klines = self.client.get_historical_klines(
                    symbol, binance_interval, start_str, limit=limit
                )
            else:
                klines = self.client.get_klines(
                    symbol=symbol, interval=binance_interval, limit=limit
                )
            
            if not klines:
                raise ValueError(f"No data found for {symbol}")
            
            # Convert to DataFrame
            df = self._klines_to_dataframe(klines)
            
            return df
            
        except Exception as e:
            raise Exception(f"Error fetching data from Binance: {str(e)}")
    
    def _convert_interval(self, interval: str) -> str:
        """Convert interval format to Binance format"""
        interval_map = {
            '1m': Client.KLINE_INTERVAL_1MINUTE,
            '3m': Client.KLINE_INTERVAL_3MINUTE,
            '5m': Client.KLINE_INTERVAL_5MINUTE,
            '15m': Client.KLINE_INTERVAL_15MINUTE,
            '30m': Client.KLINE_INTERVAL_30MINUTE,
            '1h': Client.KLINE_INTERVAL_1HOUR,
            '2h': Client.KLINE_INTERVAL_2HOUR,
            '4h': Client.KLINE_INTERVAL_4HOUR,
            '6h': Client.KLINE_INTERVAL_6HOUR,
            '8h': Client.KLINE_INTERVAL_8HOUR,
            '12h': Client.KLINE_INTERVAL_12HOUR,
            '1d': Client.KLINE_INTERVAL_1DAY,
            '3d': Client.KLINE_INTERVAL_3DAY,
            '1w': Client.KLINE_INTERVAL_1WEEK,
            '1M': Client.KLINE_INTERVAL_1MONTH
        }
        
        return interval_map.get(interval, Client.KLINE_INTERVAL_1HOUR)
    
    def _klines_to_dataframe(self, klines: List) -> pd.DataFrame:
        """Convert Binance klines to pandas DataFrame"""
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Convert to numeric
        numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col])
        
        # Keep only OHLCV data
        df = df[numeric_columns]
        
        return df
    
    def start_live_stream(self, symbol: str, interval: str, 
                         callback: Callable[[Dict], None]):
        """Start live kline data stream (simplified version)"""
        if not HAS_BINANCE or not self.client:
            print("Binance client not available for live streaming")
            return False
        
        print(f"[*] Live stream simulation for {symbol} {interval}")
        print("Note: Using polling method instead of WebSocket for compatibility")
        
        self.live_data_callback = callback
        self.is_streaming = True
        
        def polling_stream():
            """Simple polling-based stream simulation"""
            import time
            last_kline = None
            
            while self.is_streaming:
                try:
                    # Get latest kline data
                    binance_interval = self._convert_interval(interval)
                    klines = self.client.get_klines(
                        symbol=symbol, interval=binance_interval, limit=2
                    )
                    
                    if klines and len(klines) >= 2:
                        # Use the completed kline (second to last)
                        current_kline = klines[-2]
                        
                        # Check if this is a new kline
                        if last_kline is None or current_kline[0] != last_kline:
                            kline_info = {
                                'symbol': symbol,
                                'open_time': current_kline[0],
                                'close_time': current_kline[6],
                                'open': float(current_kline[1]),
                                'high': float(current_kline[2]),
                                'low': float(current_kline[3]),
                                'close': float(current_kline[4]),
                                'volume': float(current_kline[5]),
                                'is_closed': True,
                                'timestamp': datetime.fromtimestamp(current_kline[0] / 1000)
                            }
                            
                            self.latest_kline = kline_info
                            
                            if self.live_data_callback:
                                self.live_data_callback(kline_info)
                            
                            last_kline = current_kline[0]
                            
                            print(f"[*] {kline_info['timestamp'].strftime('%H:%M:%S')} | {symbol} | ${kline_info['close']:,.2f}")
                    
                    # Wait before next poll (adjust based on interval)
                    interval_seconds = self._get_interval_seconds(interval)
                    time.sleep(min(60, interval_seconds // 10))  # Poll every minute or 1/10th of interval
                    
                except Exception as e:
                    print(f"Polling error: {e}")
                    time.sleep(30)  # Wait 30 seconds on error
        
        # Start polling thread
        import threading
        stream_thread = threading.Thread(target=polling_stream, daemon=True)
        stream_thread.start()
        
        return True
    
    def _get_interval_seconds(self, interval: str) -> int:
        """Convert interval to seconds"""
        interval_map = {
            '1m': 60, '3m': 180, '5m': 300, '15m': 900, '30m': 1800,
            '1h': 3600, '2h': 7200, '4h': 14400, '6h': 21600, 
            '8h': 28800, '12h': 43200, '1d': 86400, '3d': 259200,
            '1w': 604800, '1M': 2592000
        }
        return interval_map.get(interval, 3600)
    
    def _process_kline_data(self, kline_data: Dict):
        """Process incoming kline data"""
        try:
            # Extract kline information
            kline_info = {
                'symbol': kline_data['s'],
                'open_time': kline_data['t'],
                'close_time': kline_data['T'],
                'open': float(kline_data['o']),
                'high': float(kline_data['h']),
                'low': float(kline_data['l']),
                'close': float(kline_data['c']),
                'volume': float(kline_data['v']),
                'is_closed': kline_data['x'],  # True if kline is closed
                'timestamp': datetime.fromtimestamp(kline_data['t'] / 1000)
            }
            
            self.latest_kline = kline_info
            
            # Call user callback if kline is closed (completed)
            if kline_info['is_closed'] and self.live_data_callback:
                self.live_data_callback(kline_info)
                
        except Exception as e:
            print(f"Error processing kline data: {e}")
    
    def stop_live_stream(self):
        """Stop live data stream"""
        self.is_streaming = False
        if self.socket_manager:
            try:
                self.socket_manager.close()
            except:
                pass
        print("[*] Live stream stopped")
    
    def get_latest_price(self, symbol: str) -> float:
        """Get latest price for symbol"""
        if not HAS_BINANCE or not self.client:
            return 0.0
        
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except:
            return 0.0
    
    def get_24hr_ticker(self, symbol: str) -> Dict:
        """Get 24hr ticker statistics"""
        if not HAS_BINANCE or not self.client:
            return {}
        
        try:
            return self.client.get_24hr_ticker(symbol=symbol)
        except:
            return {}
    
    def is_symbol_valid(self, symbol: str) -> bool:
        """Check if symbol is valid on Binance"""
        if not HAS_BINANCE or not self.client:
            return False
        
        try:
            info = self.client.get_exchange_info()
            symbols = [s['symbol'] for s in info['symbols'] if s['status'] == 'TRADING']
            return symbol.upper() in symbols
        except:
            return False
    
    def get_popular_symbols(self) -> List[str]:
        """Get list of popular trading symbols"""
        popular = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT',
            'XRPUSDT', 'LTCUSDT', 'LINKUSDT', 'BCHUSDT', 'XLMUSDT',
            'SOLUSDT', 'MATICUSDT', 'AVAXUSDT', 'DOGEUSDT', 'SHIBUSDT'
        ]
        
        # Filter valid symbols
        valid_symbols = []
        for symbol in popular:
            if self.is_symbol_valid(symbol):
                valid_symbols.append(symbol)
        
        return valid_symbols[:10]  # Return top 10
    
    def format_volume(self, volume: float) -> str:
        """Format volume for display"""
        if volume > 1_000_000_000:
            return f"{volume/1_000_000_000:.2f}B"
        elif volume > 1_000_000:
            return f"{volume/1_000_000:.2f}M"
        elif volume > 1_000:
            return f"{volume/1_000:.2f}K"
        else:
            return f"{volume:.2f}"


class LiveTradingSystem:
    """
    Enhanced live trading system with real Binance order execution and database integration
    """
    
    def __init__(self, config: TradingConfig, binance_provider: BinanceDataProvider, telegram_notifier=None):
        self.config = config
        self.binance = binance_provider
        self.telegram = telegram_notifier
        self.historical_data = None
        self.live_data_buffer = []
        self.max_buffer_size = 1000
        self.update_callbacks = []
        self.position_size_usdt = 100.0  # Default position size in USDT
        self.max_positions = 3  # Maximum concurrent positions
        self.is_paper_trading = not binance_provider.is_live_trading

        # Import database here to avoid circular imports
        try:
            from database import get_database
            self.db = get_database()
        except ImportError:
            print("Warning: Database module not available")
            self.db = None
    
    def set_position_size(self, usdt_amount: float):
        """Set position size for trades"""
        self.position_size_usdt = usdt_amount
        print(f"[*] Position size set to ${usdt_amount} USDT")
    
    def add_update_callback(self, callback: Callable):
        """Add callback for live updates"""
        self.update_callbacks.append(callback)
    
    def fetch_initial_data(self, symbol: str, interval: str, days: int = 30):
        """Fetch initial historical data"""
        try:
            # Calculate start time
            start_time = datetime.now() - pd.Timedelta(days=days)
            start_str = start_time.strftime("%d %b %Y")
            
            # Fetch data
            self.historical_data = self.binance.get_historical_data(
                symbol, interval, limit=min(1000, days * 24), start_str=start_str
            )
            
            print(f"✅ Loaded {len(self.historical_data)} bars of historical data")
            return self.historical_data
            
        except Exception as e:
            print(f"❌ Error fetching initial data: {e}")
            return None
    
    def execute_buy_signal(self, symbol: str, price: float, signal_data: Dict) -> Dict[str, Any]:
        """Execute a buy signal with real Binance order"""
        try:
            # Send Telegram notification for signal detection
            if self.telegram:
                self.telegram.notify_buy_signal(symbol, price, signal_data)

            # Check if we can open new position
            if not self._can_open_position(symbol):
                reason = 'Position limit reached or position exists'
                if self.telegram:
                    self.telegram.notify_order_failed('BUY', symbol, reason)
                return {'success': False, 'reason': reason}

            # Place buy order
            order_result = self.binance.place_buy_order(
                symbol=symbol,
                usdt_amount=self.position_size_usdt,
                price=price
            )

            if 'error' in order_result:
                if self.telegram:
                    self.telegram.notify_order_failed('BUY', symbol, order_result['error'])
                return {'success': False, 'reason': order_result['error']}

            # Send order executed notification
            if self.telegram and order_result.get('success'):
                self.telegram.notify_order_executed(
                    'BUY', symbol, order_result['quantity'], order_result['price'],
                    str(order_result['orderId']), self.is_paper_trading
                )

            # Save position to database
            if self.db and order_result.get('success'):
                from database import DatabasePosition

                # Calculate levels based on ATR (simplified for now)
                atr = signal_data.get('atr', price * 0.02)  # 2% fallback

                position = DatabasePosition(
                    symbol=symbol,
                    entry_price=order_result['price'],
                    entry_time=datetime.now().isoformat(),
                    trade_type="LONG",
                    stop_loss=order_result['price'] - (atr * self.config.stop_loss_multiplier),
                    take_profit_1=order_result['price'] + (atr * self.config.take_profit_1_multiplier),
                    take_profit_2=order_result['price'] + (atr * self.config.take_profit_2_multiplier),
                    quantity=order_result['quantity'],
                    binance_order_id=str(order_result['orderId'])
                )

                position_id = self.db.save_position(position)
                print(f"[*] Position saved to database with ID: {position_id}")

                # Send position opened notification
                if self.telegram:
                    self.telegram.notify_position_opened(
                        symbol, "LONG", position.entry_price, position.quantity,
                        position.stop_loss, position.take_profit_1, position.take_profit_2,
                        self.is_paper_trading
                    )

                # Save signal to database
                self.db.save_signal(
                    symbol=symbol,
                    signal_type='BUY',
                    price=price,
                    timestamp=datetime.now(),
                    **signal_data
                )

            return {
                'success': True,
                'order_id': order_result['orderId'],
                'price': order_result['price'],
                'quantity': order_result['quantity'],
                'type': 'BUY'
            }

        except Exception as e:
            error_msg = f"Error executing buy signal: {e}"
            print(f"❌ {error_msg}")
            if self.telegram:
                self.telegram.notify_error('BUY_SIGNAL_ERROR', str(e))
            return {'success': False, 'reason': error_msg}
    
    def execute_sell_signal(self, symbol: str, price: float, signal_data: Dict) -> Dict[str, Any]:
        """Execute a sell signal (close position)"""
        try:
            # Send Telegram notification for signal detection
            if self.telegram:
                self.telegram.notify_sell_signal(symbol, price, signal_data)

            # Get active position from database
            if not self.db:
                return {'success': False, 'reason': 'Database not available'}

            position = self.db.get_active_position(symbol)
            if not position:
                reason = 'No active position found'
                if self.telegram:
                    self.telegram.notify_order_failed('SELL', symbol, reason)
                return {'success': False, 'reason': reason}

            # Place sell order
            order_result = self.binance.place_sell_order(
                symbol=symbol,
                quantity=position.quantity,
                price=price
            )

            if 'error' in order_result:
                if self.telegram:
                    self.telegram.notify_order_failed('SELL', symbol, order_result['error'])
                return {'success': False, 'reason': order_result['error']}

            # Send order executed notification
            if self.telegram and order_result.get('success'):
                self.telegram.notify_order_executed(
                    'SELL', symbol, order_result['quantity'], order_result['price'],
                    str(order_result['orderId']), self.is_paper_trading
                )

            # Close position in database
            if order_result.get('success'):
                trade = self.db.close_position(
                    position_id=position.id,
                    exit_price=order_result['price'],
                    exit_time=datetime.now(),
                    exit_reason="Signal Exit",
                    exit_order_id=str(order_result['orderId'])
                )

                print(f"[*] Position closed. P&L: {trade.pnl_percent:+.2f}%")

                # Send position closed notification
                if self.telegram:
                    self.telegram.notify_position_closed(
                        symbol, position.trade_type, position.entry_price,
                        order_result['price'], position.quantity, trade.pnl_percent,
                        trade.pnl_amount, "Signal Exit", self.is_paper_trading
                    )

                # Save exit signal
                self.db.save_signal(
                    symbol=symbol,
                    signal_type='SELL',
                    price=price,
                    timestamp=datetime.now(),
                    **signal_data
                )

            return {
                'success': True,
                'order_id': order_result['orderId'],
                'price': order_result['price'],
                'quantity': order_result['quantity'],
                'type': 'SELL'
            }

        except Exception as e:
            error_msg = f"Error executing sell signal: {e}"
            print(f"❌ {error_msg}")
            if self.telegram:
                self.telegram.notify_error('SELL_SIGNAL_ERROR', str(e))
            return {'success': False, 'reason': error_msg}
    
    def check_exit_conditions(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Check if any positions should be exited based on stop loss or take profit"""
        if not self.db:
            return {'should_exit': False}
        
        try:
            position = self.db.get_active_position(symbol)
            if not position:
                return {'should_exit': False}
            
            should_exit = False
            exit_reason = ""
            
            if position.trade_type == "LONG":
                if current_price <= position.stop_loss:
                    should_exit = True
                    exit_reason = "Stop Loss"
                elif current_price >= position.take_profit_2:
                    should_exit = True
                    exit_reason = "Take Profit 2"
                elif position.trailing_stop and current_price <= position.trailing_stop:
                    should_exit = True
                    exit_reason = "Trailing Stop"
            else:  # SHORT positions
                if current_price >= position.stop_loss:
                    should_exit = True
                    exit_reason = "Stop Loss"
                elif current_price <= position.take_profit_2:
                    should_exit = True
                    exit_reason = "Take Profit 2"
                elif position.trailing_stop and current_price >= position.trailing_stop:
                    should_exit = True
                    exit_reason = "Trailing Stop"
            
            if should_exit:
                # Execute the exit
                exit_result = self.binance.place_sell_order(
                    symbol=symbol,
                    quantity=position.quantity
                )
                
                if exit_result.get('success'):
                    trade = self.db.close_position(
                        position_id=position.id,
                        exit_price=exit_result['price'],
                        exit_time=datetime.now(),
                        exit_reason=exit_reason,
                        exit_order_id=str(exit_result['orderId'])
                    )
                    
                    print(f"[*] {exit_reason} hit! Position closed. P&L: {trade.pnl_percent:+.2f}%")
                    
                    return {
                        'should_exit': True,
                        'exit_reason': exit_reason,
                        'trade': trade,
                        'order_result': exit_result
                    }
            
            return {'should_exit': False}
            
        except Exception as e:
            print(f"Error checking exit conditions: {e}")
            return {'should_exit': False}
    
    def update_trailing_stops(self, symbol: str, current_price: float, atr: float):
        """Update trailing stops for active positions"""
        if not self.db:
            return
        
        try:
            position = self.db.get_active_position(symbol)
            if not position:
                return
            
            updated = False
            
            if position.trade_type == "LONG":
                # Activate trailing stop at 5% profit
                profit_pct = (current_price - position.entry_price) / position.entry_price
                if profit_pct >= self.config.trailing_activation:
                    new_trail = current_price - (atr * self.config.stop_loss_multiplier * self.config.trailing_stop_factor)
                    
                    if position.trailing_stop is None or new_trail > position.trailing_stop:
                        position.trailing_stop = new_trail
                        updated = True
            
            else:  # SHORT
                profit_pct = (position.entry_price - current_price) / position.entry_price
                if profit_pct >= self.config.trailing_activation:
                    new_trail = current_price + (atr * self.config.stop_loss_multiplier * self.config.trailing_stop_factor)
                    
                    if position.trailing_stop is None or new_trail < position.trailing_stop:
                        position.trailing_stop = new_trail
                        updated = True
            
            if updated:
                self.db.save_position(position)
                print(f"[*] Trailing stop updated for {symbol}: ${position.trailing_stop:.4f}")
                
        except Exception as e:
            print(f"Error updating trailing stops: {e}")
    
    def _can_open_position(self, symbol: str) -> bool:
        """Check if we can open a new position"""
        if not self.db:
            return True  # Allow if no database
        
        # Check if position already exists for this symbol
        existing_position = self.db.get_active_position(symbol)
        if existing_position:
            print(f"⚠️ Active position already exists for {symbol}")
            return False
        
        # Check maximum positions limit
        # This would require a database query to count active positions
        # For now, we'll allow it
        return True
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status"""
        if not self.db:
            return {'error': 'Database not available'}
        
        try:
            summary = self.db.get_portfolio_summary()
            stats = self.db.get_statistics()
            
            # Get current balances
            usdt_balance = self.binance.get_account_balance('USDT')
            
            return {
                'account_balance_usdt': usdt_balance,
                'active_positions': summary['active_positions'],
                'trade_summary': summary['trade_summary'],
                'statistics': stats,
                'position_size_usdt': self.position_size_usdt,
                'live_trading_enabled': self.binance.is_live_trading
            }
            
        except Exception as e:
            return {'error': f'Error getting portfolio status: {e}'}
    
    def start_live_monitoring(self, symbol: str, interval: str):
        """Start live monitoring with enhanced trading logic"""
        def live_update_handler(kline_data):
            """Enhanced live update handler with trading logic"""
            try:
                # Convert to DataFrame row format
                new_row = pd.DataFrame([{
                    'Open': kline_data['open'],
                    'High': kline_data['high'],
                    'Low': kline_data['low'],
                    'Close': kline_data['close'],
                    'Volume': kline_data['volume']
                }], index=[kline_data['timestamp']])
                
                # Add to buffer
                self.live_data_buffer.append(new_row)
                
                # Maintain buffer size
                if len(self.live_data_buffer) > self.max_buffer_size:
                    self.live_data_buffer.pop(0)
                
                # Update trailing stops for active positions
                current_price = kline_data['close']
                atr = current_price * 0.02  # Simplified ATR calculation
                self.update_trailing_stops(symbol, current_price, atr)
                
                # Check exit conditions
                exit_check = self.check_exit_conditions(symbol, current_price)
                if exit_check['should_exit']:
                    print(f"[*] Position automatically closed: {exit_check['exit_reason']}")
                
                # Notify callbacks with trading context
                for callback in self.update_callbacks:
                    try:
                        callback(kline_data, new_row)
                    except Exception as e:
                        print(f"Callback error: {e}")
                
                # Print enhanced live update
                self._print_live_update(kline_data, symbol)
                
            except Exception as e:
                print(f"Error handling live update: {e}")
        
        # Start live stream
        success = self.binance.start_live_stream(symbol, interval, live_update_handler)
        
        if success:
            print(f"[*] LIVE: Started monitoring {symbol} {interval}")
            if self.binance.is_live_trading:
                print("[*] Live trading is ENABLED - Orders will be executed automatically")
            else:
                print("[*] Data monitoring only - No orders will be placed")
        else:
            print(f"❌ Failed to start live monitoring for {symbol}")
            
        return success
    
    def _print_live_update(self, kline_data, symbol: str):
        """Print enhanced live update with position info"""
        timestamp = kline_data['timestamp'].strftime('%H:%M:%S')
        price = kline_data['close']
        volume = self.binance.format_volume(kline_data['volume'])
        
        status_icon = "[*]"
        extra_info = ""
        
        # Add position info if available
        if self.db:
            position = self.db.get_active_position(symbol)
            if position:
                pnl = ((price - position.entry_price) / position.entry_price * 100) if position.trade_type == "LONG" else ((position.entry_price - price) / position.entry_price * 100)
                status_icon = "[*]" if pnl > 0 else "[*]"
                extra_info = f" | {position.trade_type} P&L: {pnl:+.2f}%"
        
        print(f"{status_icon} {timestamp} | {symbol} | ${price:,.4f} | Vol: {volume}{extra_info}")
    
    def get_combined_data(self) -> Optional[pd.DataFrame]:
        """Get historical data combined with live buffer"""
        if self.historical_data is None:
            return None
        
        if not self.live_data_buffer:
            return self.historical_data
        
        # Combine historical with live data
        try:
            live_df = pd.concat(self.live_data_buffer, ignore_index=False)
            combined = pd.concat([self.historical_data, live_df])
            
            # Remove duplicates and sort
            combined = combined[~combined.index.duplicated(keep='last')]
            combined = combined.sort_index()
            
            return combined
            
        except Exception as e:
            print(f"Error combining data: {e}")
            return self.historical_data
    
    def stop_monitoring(self):
        """Stop live monitoring"""
        self.binance.stop_live_stream()
        self.live_data_buffer.clear()
        print("[*] Live monitoring stopped")


class PaperTradingProvider:
    """
    Paper trading provider that simulates order execution without real trades
    """

    def __init__(self, initial_balance: float = 10000.0):
        self.balance_usdt = initial_balance
        self.initial_balance = initial_balance
        self.positions = {}  # symbol -> {quantity, entry_price}
        self.orders = []
        self.order_counter = 1
        self.is_live_trading = False  # Paper trading flag
        print(f"[*] Paper Trading Mode Initialized - Starting Balance: ${initial_balance:,.2f}")

    def get_account_balance(self, asset: str = 'USDT') -> float:
        """Get paper trading balance"""
        if asset == 'USDT':
            return self.balance_usdt
        # For other assets, calculate from positions
        total = 0.0
        for symbol, pos in self.positions.items():
            if asset in symbol:
                total += pos['quantity']
        return total

    def place_buy_order(self, symbol: str, quantity: float = None, price: float = None,
                       order_type: str = 'MARKET', usdt_amount: float = None) -> Dict[str, Any]:
        """Simulate buy order execution"""
        try:
            # Calculate quantity if USDT amount provided
            if quantity is None and usdt_amount is not None:
                quantity = usdt_amount / price

            # Check if we have enough balance
            cost = quantity * price
            if cost > self.balance_usdt:
                return {
                    'error': f'Insufficient balance. Required: ${cost:.2f}, Available: ${self.balance_usdt:.2f}',
                    'orderId': None
                }

            # Simulate order execution
            order_id = f"PAPER_{self.order_counter}"
            self.order_counter += 1

            # Deduct from balance (assume 0.1% trading fee)
            fee = cost * 0.001
            self.balance_usdt -= (cost + fee)

            # Add to positions
            if symbol in self.positions:
                # Average in
                existing = self.positions[symbol]
                total_qty = existing['quantity'] + quantity
                avg_price = ((existing['quantity'] * existing['entry_price']) + (quantity * price)) / total_qty
                self.positions[symbol] = {
                    'quantity': total_qty,
                    'entry_price': avg_price
                }
            else:
                self.positions[symbol] = {
                    'quantity': quantity,
                    'entry_price': price
                }

            # Record order
            order = {
                'orderId': order_id,
                'symbol': symbol,
                'side': 'BUY',
                'type': order_type,
                'quantity': quantity,
                'price': price,
                'cost': cost,
                'fee': fee,
                'status': 'FILLED',
                'timestamp': datetime.now()
            }
            self.orders.append(order)

            print(f"[*] [PAPER] BUY: {quantity:.6f} {symbol} @ ${price:.4f} | Balance: ${self.balance_usdt:.2f}")

            return {
                'success': True,
                'orderId': order_id,
                'symbol': symbol,
                'side': 'BUY',
                'quantity': quantity,
                'price': price,
                'status': 'FILLED',
                'order': order
            }

        except Exception as e:
            error_msg = f"Paper trading buy error: {e}"
            print(f"❌ {error_msg}")
            return {'error': error_msg, 'orderId': None}

    def place_sell_order(self, symbol: str, quantity: float, price: float = None,
                        order_type: str = 'MARKET') -> Dict[str, Any]:
        """Simulate sell order execution"""
        try:
            # Check if we have the position
            if symbol not in self.positions:
                return {
                    'error': f'No position found for {symbol}',
                    'orderId': None
                }

            position = self.positions[symbol]
            if quantity > position['quantity']:
                return {
                    'error': f'Insufficient quantity. Have: {position["quantity"]}, Trying to sell: {quantity}',
                    'orderId': None
                }

            # Simulate order execution
            order_id = f"PAPER_{self.order_counter}"
            self.order_counter += 1

            # Calculate proceeds (assume 0.1% trading fee)
            proceeds = quantity * price
            fee = proceeds * 0.001
            self.balance_usdt += (proceeds - fee)

            # Update position
            position['quantity'] -= quantity
            if position['quantity'] <= 0:
                del self.positions[symbol]

            # Record order
            order = {
                'orderId': order_id,
                'symbol': symbol,
                'side': 'SELL',
                'type': order_type,
                'quantity': quantity,
                'price': price,
                'proceeds': proceeds,
                'fee': fee,
                'status': 'FILLED',
                'timestamp': datetime.now()
            }
            self.orders.append(order)

            print(f"[*] [PAPER] SELL: {quantity:.6f} {symbol} @ ${price:.4f} | Balance: ${self.balance_usdt:.2f}")

            return {
                'success': True,
                'orderId': order_id,
                'symbol': symbol,
                'side': 'SELL',
                'quantity': quantity,
                'price': price,
                'status': 'FILLED',
                'order': order
            }

        except Exception as e:
            error_msg = f"Paper trading sell error: {e}"
            print(f"❌ {error_msg}")
            return {'error': error_msg, 'orderId': None}

    def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Get paper trade order status"""
        for order in self.orders:
            if order['orderId'] == order_id:
                return {
                    'orderId': order['orderId'],
                    'symbol': order['symbol'],
                    'status': order['status'],
                    'side': order['side'],
                    'quantity': order['quantity'],
                    'executed_qty': order['quantity'],
                    'price': order['price'],
                    'avg_price': order['price']
                }
        return {'error': 'Order not found'}

    def get_open_orders(self, symbol: str = None) -> list:
        """Get open orders (always empty for paper trading as orders fill immediately)"""
        return []

    def get_portfolio_value(self, current_prices: Dict[str, float]) -> float:
        """Calculate total portfolio value"""
        total_value = self.balance_usdt
        for symbol, position in self.positions.items():
            if symbol in current_prices:
                total_value += position['quantity'] * current_prices[symbol]
        return total_value

    def get_portfolio_pnl(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """Calculate overall P&L"""
        current_value = self.get_portfolio_value(current_prices)
        pnl_amount = current_value - self.initial_balance
        pnl_percent = (pnl_amount / self.initial_balance) * 100

        return {
            'initial_balance': self.initial_balance,
            'current_value': current_value,
            'pnl_amount': pnl_amount,
            'pnl_percent': pnl_percent,
            'balance_usdt': self.balance_usdt,
            'positions_count': len(self.positions)
        }

    def reset(self):
        """Reset paper trading account"""
        self.balance_usdt = self.initial_balance
        self.positions.clear()
        self.orders.clear()
        self.order_counter = 1
        print(f"[*] Paper Trading Account Reset - Balance: ${self.initial_balance:,.2f}")