"""
Main runner for the Pro Trader System
Live Trading Application based on TradingView Pine Script Strategy
"""

import pandas as pd
from datetime import datetime, timedelta
import argparse
import sys
import os
from typing import Optional
import warnings
warnings.filterwarnings('ignore')

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import configuration
from config import TradingConfig, DEFAULT_CONFIG, SCALPING_CONFIG, SWING_CONFIG, CONSERVATIVE_CONFIG

# Import core components
from binance_provider import BinanceDataProvider, LiveTradingSystem, PaperTradingProvider
from trading_system import ProTradingSystem
from database import get_database
from position_manager import EnhancedPositionManager
from telegram_notifier import get_telegram_notifier


def setup_api_keys():
    """Setup Binance API keys from environment or user input"""
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("\n[*] Binance API Configuration")
        print("="*40)
        print("For live trading, you need Binance API credentials.")
        print("You can set them as environment variables:")
        print("  BINANCE_API_KEY=your_api_key")
        print("  BINANCE_API_SECRET=your_api_secret")
        print("\nOr enter them now (they won't be saved):")
        
        if not api_key:
            api_key = input("Enter Binance API Key (or press Enter to skip): ").strip()
        if not api_secret and api_key:
            api_secret = input("Enter Binance API Secret: ").strip()
    
    return api_key, api_secret


def run_backtest_demo(symbol: str = "BTCUSDT", config: TradingConfig = None, 
                      start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Run a complete backtest demonstration"""
    if config is None:
        config = DEFAULT_CONFIG
    
    # Validate date formats if provided
    def validate_date(date_str, date_name):
        if date_str:
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                return True
            except ValueError:
                print(f"❌ Invalid {date_name} format: {date_str}")
                print("   Expected format: YYYY-MM-DD (e.g., 2024-01-01)")
                return False
        return True
    
    if not validate_date(start_date, "start date") or not validate_date(end_date, "end date"):
        return
    
    print(f"\n[*] Starting Pro Trader System Backtest for {symbol}")
    print("="*60)
    
    # Initialize system
    trading_system = ProTradingSystem(config)
    
    try:
        # Fetch data
        print("[*] Fetching market data...")
        data = trading_system.fetch_data(symbol, start_date=start_date, end_date=end_date)
        print(f"✅ Loaded {len(data)} bars of data from {data.index[0].date()} to {data.index[-1].date()}")
        
        # Show warning if requested start date differs from actual data start
        if start_date and data.index[0].strftime('%Y-%m-%d') != start_date:
            print(f"⚠️  Note: You requested start date {start_date}, but actual data starts from {data.index[0].date()}")
            print(f"    This is due to Binance API limits (max 1000 bars for {config.interval} interval)")
            print(f"    The backtest will run on the available data range: {data.index[0].date()} to {data.index[-1].date()}")
        
        # Calculate signals with proper date range for regime detection
        print("[*] Calculating technical indicators and signals...")
        # Calculate signals
        signals = trading_system.calculate_signals()
        print("✅ Signals calculated successfully")
        
        # Run backtest with date range if specified
        print("⚡ Running backtest simulation...")
        if start_date or end_date:
            date_info = f" (from {start_date or 'start'} to {end_date or 'end'})"
            print(f"[*] Date range specified{date_info}")
        results = trading_system.run_backtest(start_date=start_date, end_date=end_date)
        print(f"✅ Backtest completed with {len(results['trades'])} trades")
        
        # Show actual date range of the backtest data
        if len(results['data']) > 0:
            actual_start = results['data'].index[0].date()
            actual_end = results['data'].index[-1].date()
            print(f"[*] Actual backtest period: {actual_start} to {actual_end}")
        
        # Print statistics
        trading_system.print_statistics(results)
        
        # Get current market status
        market_status = trading_system.get_current_market_status()
        
        # Export results
        trading_system.export_results(results, f"{symbol}_trading_results.csv")
        
        # Show current signals
        current_signals = trading_system.get_live_signals()
        print("\n[*] CURRENT LIVE SIGNALS:")
        print("-" * 30)
        if current_signals['buy_signal']:
            print("[*] BUY SIGNAL DETECTED!")
        elif current_signals['sell_signal']:
            print("[*] SELL SIGNAL DETECTED!")
        elif current_signals['buy_setup']:
            print("[*] BUY SETUP - Waiting for trigger")
        elif current_signals['sell_setup']:
            print("[*] SELL SETUP - Waiting for trigger")
        else:
            print("⚪ No active signals")
        
        if current_signals['in_trade']:
            print("[*] Currently in trade")
        
        # Show market status summary
        print(f"\n[*] CURRENT MARKET STATUS:")
        print("-" * 30)
        print(f"Price: ${market_status['price']:.2f}")
        print(f"Trend: {market_status['trend']['status']} ({market_status['trend']['percentage']:+.1f}%)")
        print(f"RSI: {market_status['rsi']['value']:.1f} ({market_status['rsi']['status']})")
        print(f"MACD: {market_status['macd']['status']}")
        print(f"Setup: {market_status['setup']['status']}")
        
        position = market_status['position']
        if position['status'] == 'Running':
            print(f"Position: {position['type']} - P&L: {position['pnl_percent']:+.2f}%")
        
        return trading_system, results
        
    except Exception as e:
        print(f"❌ Error during backtest: {str(e)}")
        return None, None


def run_live_monitoring(symbol: str = "BTCUSDT", config: TradingConfig = None):
    """Run live market monitoring (simulated with latest data)"""
    if config is None:
        config = DEFAULT_CONFIG
        
    print(f"\n[*] Starting Live Monitoring for {symbol}")
    print("="*60)
    print("Note: This is monitoring using the latest available data")
    
    trading_system = ProTradingSystem(config)
    
    try:
        # Fetch recent data
        data = trading_system.fetch_data(symbol)
        signals = trading_system.calculate_signals()
        
        # Show live status
        market_status = trading_system.get_current_market_status()
        current_signals = trading_system.get_live_signals()
        
        print(f"\n[*] LIVE MARKET STATUS for {symbol}")
        print(f"Time: {market_status['timestamp']}")
        print(f"Price: ${market_status['price']:.2f}")
        print("-" * 40)
        
        # Status table
        print(f"Trend:     {market_status['trend']['status']:15s} ({market_status['trend']['percentage']:+6.1f}%)")
        print(f"RSI:       {market_status['rsi']['value']:6.1f} ({market_status['rsi']['status']})")
        print(f"MACD:      {market_status['macd']['status']}")
        print(f"Setup:     {market_status['setup']['status']}")
        
        last_signal = market_status['last_signal']
        print(f"Last Sig:  {last_signal['type']} ({last_signal['bars_ago']} bars ago)")
        
        print(f"ATR:       {market_status['atr']:.4f}")
        
        position = market_status['position']
        print("-" * 40)
        print(f"Position:  {position['status']}")
        if position['status'] == 'Running':
            print(f"Type:      {position['type']}")
            print(f"P&L:       {position['pnl_percent']:+.2f}%")
            print(f"R:R Ratio: {position['risk_reward']:.1f}")
        
        print("\n[*] SIGNAL STATUS:")
        if current_signals['buy_signal']:
            print("[*] STRONG BUY SIGNAL - Enter Long Position!")
        elif current_signals['sell_signal']:
            print("[*] STRONG SELL SIGNAL - Enter Short Position!")
        elif current_signals['buy_setup']:
            print("[*] BUY SETUP DETECTED - Watch for trigger...")
        elif current_signals['sell_setup']:
            print("[*] SELL SETUP DETECTED - Watch for trigger...")
        else:
            print("⚪ No active signals - Wait for setup")
        
        return trading_system
        
    except Exception as e:
        print(f"❌ Error in live monitoring: {e}")
        return None


def run_live_trading(symbol: str = "BTCUSDT", config: TradingConfig = None, position_size: float = 100.0):
    """Run live trading with real-time execution"""
    if config is None:
        config = DEFAULT_CONFIG

    # Determine trading mode
    is_paper_trading = config.paper_trading
    trading_mode = "PAPER TRADING" if is_paper_trading else "LIVE TRADING"

    print(f"\n[*] Starting {trading_mode} for {symbol}")
    print("="*60)

    if not is_paper_trading:
        print("⚠️  WARNING: This is LIVE TRADING with real market orders!")
        print("[*] Make sure you understand the risks before proceeding.")
    else:
        print("[*] Paper Trading Mode - No real orders will be placed")
        print(f"[*] Starting with ${config.initial_paper_balance:,.2f} virtual balance")

    # Initialize Telegram notifications
    telegram = None
    if config.enable_telegram:
        telegram = get_telegram_notifier()
        if telegram.enabled:
            telegram.notify_system_start(symbol, trading_mode, "DEFAULT")

    # Setup trading provider based on mode
    if is_paper_trading:
        # Paper trading mode
        trading_provider = PaperTradingProvider(config.initial_paper_balance)
        # Still need Binance for market data
        binance_data = BinanceDataProvider(config)
    else:
        # Real trading mode - setup API keys
        api_key, api_secret = setup_api_keys()

        if not api_key or not api_secret:
            print("❌ API credentials required for live trading")
            if telegram:
                telegram.notify_error('STARTUP_ERROR', 'API credentials missing for live trading')
            return None

        trading_provider = BinanceDataProvider(config, api_key, api_secret)
        binance_data = trading_provider

        if not trading_provider.is_live_trading:
            print("❌ Could not initialize live trading - check API credentials")
            if telegram:
                telegram.notify_error('STARTUP_ERROR', 'Failed to initialize live trading API')
            return None

    # Confirm trading
    print(f"\n[*] Trading Configuration:")
    print(f"Mode: {trading_mode}")
    print(f"Symbol: {symbol}")
    print(f"Position Size: ${position_size} USDT")
    print(f"Interval: {config.interval}")
    print(f"Stop Loss: {config.stop_loss_multiplier}x ATR")
    print(f"Take Profit: {config.take_profit_1_multiplier}x / {config.take_profit_2_multiplier}x ATR")
    print(f"Telegram Notifications: {'Enabled' if telegram and telegram.enabled else 'Disabled'}")

    confirm = input("\nType 'START' to begin trading: ")
    if confirm.upper() != 'START':
        print("❌ Trading cancelled by user")
        if telegram:
            telegram.notify_system_stop()
        return None
    
    try:
        # Initialize live trading system with provider and Telegram
        live_system = LiveTradingSystem(config, trading_provider, telegram)
        live_system.set_position_size(position_size)

        # Check account balance
        balance = trading_provider.get_account_balance('USDT')
        print(f"\n[*] USDT Balance: ${balance:.2f}")

        if not is_paper_trading and balance < position_size:
            print(f"⚠️ Warning: Balance (${balance:.2f}) is less than position size (${position_size})")
            confirm_low_balance = input("Continue anyway? (type 'YES'): ")
            if confirm_low_balance.upper() != 'YES':
                print("❌ Trading cancelled due to insufficient balance")
                if telegram:
                    telegram.notify_system_stop()
                return None

        # Fetch initial data using binance_data for market data
        print("[*] Fetching initial data...")
        data = live_system.fetch_initial_data(symbol, config.interval, days=30)


        if data is None:
            print("❌ Could not fetch initial data")
            if telegram:
                telegram.notify_error('DATA_ERROR', 'Could not fetch initial market data')
            return None

        # Initialize trading system
        trading_system = ProTradingSystem(config)
        trading_system.data = data
        trading_system.calculate_signals()

        def trading_callback(kline_data, new_row):
            """Handle trading signals from live data"""
            try:
                # Update trading system with new data
                current_price = kline_data['close']
                timestamp = kline_data['timestamp']
                
                # Recalculate signals with new data
                combined_data = live_system.get_combined_data()
                if combined_data is not None:
                    trading_system.data = combined_data
                    trading_system.calculate_signals()
                    
                    # Get current signals
                    signals = trading_system.get_live_signals()
                    
                    # Calculate ATR for position sizing
                    atr = trading_system.signals['atr'].iloc[-1] if len(trading_system.signals) > 0 else current_price * 0.02
                    
                    # Prepare signal data
                    signal_data = {
                        'atr': atr,
                        'rsi': trading_system.signals['rsi'].iloc[-1] if len(trading_system.signals) > 0 else 50,
                        'macd_histogram': trading_system.signals.get('histogram', pd.Series([0])).iloc[-1],
                        'trend_status': 'Unknown'
                    }
                    
                    # Execute buy signals
                    if signals['buy_signal'] and not signals['in_trade']:
                        print(f"\n[*] BUY SIGNAL TRIGGERED at ${current_price:.4f}")
                        result = live_system.execute_buy_signal(symbol, current_price, signal_data)
                        
                        if result['success']:
                            print(f"✅ BUY ORDER EXECUTED: {result['quantity']:.6f} {symbol}")
                        else:
                            print(f"❌ BUY ORDER FAILED: {result['reason']}")
                    
                    # Execute sell signals (position exits)  
                    elif signals['sell_signal'] and signals['in_trade']:
                        print(f"\n[*] SELL SIGNAL TRIGGERED at ${current_price:.4f}")
                        result = live_system.execute_sell_signal(symbol, current_price, signal_data)
                        
                        if result['success']:
                            print(f"✅ SELL ORDER EXECUTED: {result['quantity']:.6f} {symbol}")
                        else:
                            print(f"❌ SELL ORDER FAILED: {result['reason']}")
                
            except Exception as e:
                print(f"❌ Error in trading callback: {e}")
        
        # Add trading callback
        live_system.add_update_callback(trading_callback)
        
        # Start live monitoring with trading
        success = live_system.start_live_monitoring(symbol, config.interval)
        
        if success:
            print(f"\n✨ Live trading active for {symbol}")
            print("[*] Monitor your positions carefully!")
            print("[*] Press Ctrl+C to stop live trading")
            
            # Show portfolio status
            portfolio = live_system.get_portfolio_status()
            if 'error' not in portfolio:
                print(f"\n[*] Portfolio Status:")
                print(f"Balance: ${portfolio['account_balance_usdt']:.2f} USDT")
                print(f"Active Positions: {len(portfolio['active_positions'])}")
            
            # Keep running until interrupted
            try:
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[*] Stopping live trading...")
                live_system.stop_monitoring()

                # Show final portfolio status
                portfolio = live_system.get_portfolio_status()
                if 'statistics' in portfolio:
                    stats = portfolio['statistics']
                    print(f"\n[*] Final Statistics:")
                    print(f"Total Trades: {stats['total_trades']}")
                    print(f"Win Rate: {stats['win_rate']:.1f}%")
                    print(f"Total P&L: ${stats['total_amount_pnl']:.2f}")

                    # Send final summary via Telegram
                    if telegram:
                        telegram.notify_portfolio_summary(
                            balance, len(portfolio['active_positions']),
                            stats['total_trades'], stats['win_rate'],
                            stats['total_pnl'], is_paper_trading
                        )
                        telegram.notify_system_stop()

        return live_system

    except Exception as e:
        print(f"❌ Error in live trading: {str(e)}")
        if telegram:
            telegram.notify_error('LIVE_TRADING_ERROR', str(e))
        return None


def show_portfolio_status():
    """Show current portfolio status from database"""
    try:
        db = get_database()
        portfolio = db.get_portfolio_summary()
        stats = db.get_statistics()
        
        print("\n[*] PORTFOLIO STATUS")
        print("="*50)
        
        print(f"[*] Active Positions: {len(portfolio['active_positions'])}")
        for pos in portfolio['active_positions']:
            print(f"  • {pos['symbol']}: {pos['count']} positions, Avg Entry: ${pos['avg_entry']:.4f}")
        
        print(f"\n[*] Trading Statistics:")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Win Rate: {stats['win_rate']:.1f}%")
        print(f"Total P&L: {stats['total_pnl']:+.2f}%")
        print(f"Total P&L Amount: ${stats['total_amount_pnl']:+.2f}")
        print(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")
        
        print(f"\n[*] Trade Summary by Symbol:")
        for trade in portfolio['trade_summary']:
            print(f"  • {trade['symbol']}: {trade['total_trades']} trades, "
                  f"${trade['total_pnl_amount']:+.2f}, "
                  f"{trade['avg_pnl_percent']:+.2f}% avg")
    
    except Exception as e:
        print(f"❌ Error getting portfolio status: {e}")


def export_data(table: str = 'trades'):
    """Export database data to CSV"""
    try:
        db = get_database()
        filename = db.export_to_csv(table)
        print(f"✅ Exported {table} to {filename}")
    except Exception as e:
        print(f"❌ Error exporting data: {e}")


def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description="Pro Trader System - Live Trading Application")
    parser.add_argument('--symbol', '-s', default='BTCUSDT', help='Trading symbol (default: BTCUSDT)')
    parser.add_argument('--mode', '-m', choices=['backtest', 'monitor', 'trade', 'portfolio', 'export', 'dashboard'],
                       default='backtest', help='Running mode')
    parser.add_argument('--config', '-c', choices=['default', 'scalping', 'swing', 'conservative'],
                       default='default', help='Trading configuration')
    parser.add_argument('--period', '-p', default='2y', help='Data period (default: 2y)')
    parser.add_argument('--interval', '-i', help='Trading interval (1m, 5m, 1h, 1d, etc.)')
    parser.add_argument('--position-size', type=float, default=100.0, help='Position size in USDT for live trading')
    parser.add_argument('--export-table', choices=['trades', 'positions', 'signals'], default='trades',
                       help='Table to export (for export mode)')
    parser.add_argument('--start-date', help='Backtest start date (YYYY-MM-DD format), e.g., 2024-01-01')
    parser.add_argument('--end-date', help='Backtest end date (YYYY-MM-DD format), e.g., 2024-12-31')
    parser.add_argument('--dashboard-port', type=int, default=5000, help='Dashboard server port (default: 5000)')
    
    args = parser.parse_args()
    
    # Select configuration
    config_map = {
        'default': DEFAULT_CONFIG,
        'scalping': SCALPING_CONFIG,
        'swing': SWING_CONFIG,
        'conservative': CONSERVATIVE_CONFIG
    }
    
    selected_config = config_map[args.config]
    selected_config.symbol = args.symbol
    selected_config.lookback_period = args.period
    
    # Override interval if specified
    if args.interval:
        selected_config.interval = args.interval
    
    print("PRO TRADER SYSTEM v3.0")
    print("Live Trading Application based on TradingView Pine Script")
    print(f"Mode: {args.mode.upper()}")
    print(f"Symbol: {args.symbol}")
    print(f"Configuration: {args.config.upper()}")
    print("Data Source: Binance")
    
    try:
        if args.mode == 'backtest':
            run_backtest_demo(args.symbol, selected_config, args.start_date, args.end_date)
            
        elif args.mode == 'monitor':
            run_live_monitoring(args.symbol, selected_config)
            
        elif args.mode == 'trade':
            run_live_trading(args.symbol, selected_config, args.position_size)
            
        elif args.mode == 'portfolio':
            show_portfolio_status()
            
        elif args.mode == 'export':
            export_data(args.export_table)

        elif args.mode == 'dashboard':
            from dashboard import start_dashboard
            print("[*] Starting web dashboard...")
            print(f"[*] Access at: http://127.0.0.1:{args.dashboard_port}")
            start_dashboard(port=args.dashboard_port)

        print(f"\n✅ {args.mode.upper()} completed successfully!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())