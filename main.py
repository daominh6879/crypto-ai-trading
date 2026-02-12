"""
Main runner for the Pro Trader System
Live Trading Application based on TradingView Pine Script Strategy
"""

import pandas as pd
from datetime import datetime, timedelta
import argparse
import sys
import os
from typing import Optional, List, Tuple, Dict, Any
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


def run_historical_backtest(symbol: str = "BTCUSDT", config: TradingConfig = None, 
                          years: Optional[List[int]] = None, 
                          start_year: int = 2017, end_year: int = 2025) -> List[Dict]:
    """
    Run historical backtests across multiple years and generate comprehensive analysis
    
    Args:
        symbol: Trading symbol to test
        config: Trading configuration
        years: List of specific years to test (overrides start_year/end_year)
        start_year: Starting year for range (default 2017)
        end_year: Ending year for range (default 2025)
    
    Returns:
        List of yearly results with comprehensive statistics
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Ensure we're using 1h interval for historical analysis
    config.interval = '1h'
    
    # Determine years to test
    if years is None:
        years = list(range(start_year, end_year + 1))
    
    print(f"\n[*] HISTORICAL BACKTEST ANALYSIS for {symbol}")
    print("="*80)
    print(f"Years to test: {years}")
    print(f"Configuration: {config.__class__.__name__}")
    print(f"Interval: {config.interval}")
    
    # Data availability info
    if symbol == 'BTCUSDT':
        print(f"\n📋 DATA AVAILABILITY NOTE:")
        print(f"   • Binance BTCUSDT data starts from August 17, 2017")
        print(f"   • Years 2010-2016: No data available (Binance didn't exist)")
        print(f"   • Bitcoin trading before 2017 was on different exchanges")
        early_years = [y for y in years if y < 2017]
        if early_years:
            print(f"   • Will skip years: {early_years} (no data available)")
            years = [y for y in years if y >= 2017]
            print(f"   • Adjusted years to test: {years}")
    
    results_summary = []
    
    for year in years:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        print(f"\n[*] Testing {year}...")
        print("-" * 60)
        
        try:
            # Initialize fresh system for each year to avoid data contamination
            trading_system = ProTradingSystem(config)
            
            # Fetch data using the same method as regular backtest
            print("[*] Fetching market data...")
            data = trading_system.fetch_data(symbol, start_date=start_date, end_date=end_date)
            
            if len(data) == 0:
                print(f"⚠️  No data available for {year} (Binance data starts August 2017)")
                continue
            
            print(f"✅ Loaded {len(data)} bars of data from {data.index[0].date()} to {data.index[-1].date()}")
            
            # Show actual data range if different from requested
            if data.index[0].strftime('%Y-%m-%d') != start_date:
                print(f"⚠️  Note: Requested {start_date}, actual data starts from {data.index[0].date()}")
                print(f"    This is due to Binance API limits (max 1000 bars for {config.interval} interval)")
            
            # Calculate signals
            print("[*] Calculating technical indicators and signals...")
            signals = trading_system.calculate_signals()
            print("✅ Signals calculated successfully")
            
            # Run backtest
            print("⚡ Running backtest simulation...")
            results = trading_system.run_backtest(start_date=start_date, end_date=end_date)
            stats = results['statistics']
            
            # Show actual backtest period
            if len(results['data']) > 0:
                actual_start = results['data'].index[0].date()
                actual_end = results['data'].index[-1].date()
                print(f"[*] Actual backtest period: {actual_start} to {actual_end}")
            
            print(f"✅ Backtest completed with {len(results['trades'])} trades")
            
            # Determine market context based on performance and volatility
            market_context = determine_market_context(year, stats, results)
            
            # Calculate additional metrics
            actual_start = results['data'].index[0].date() if len(results['data']) > 0 else start_date
            actual_end = results['data'].index[-1].date() if len(results['data']) > 0 else end_date
            
            # Store comprehensive results
            year_result = {
                'year': year,
                'trades': stats['total_trades'],
                'pnl_percent': stats['total_pnl'],
                'win_rate': stats['win_rate'],
                'max_drawdown': stats['max_drawdown'],
                'profit_factor': stats.get('profit_factor', 0),
                'market_context': market_context,
                'actual_start': actual_start,
                'actual_end': actual_end,
                'avg_win': stats.get('avg_win_pct', 0),
                'avg_loss': stats.get('avg_loss_pct', 0),
                'regime_changes': results.get('regime_changes', 0),
                'final_regime': results.get('final_regime', 'Unknown'),
                'total_bars': len(results['data']),
                'winning_trades': stats.get('winning_trades', 0),
                'losing_trades': stats.get('losing_trades', 0)
            }
            
            results_summary.append(year_result)
            
            # Print year summary
            print(f"📊 {year}: {stats['total_trades']} trades, {stats['total_pnl']:+.2f}% P&L, "
                  f"{stats['win_rate']:.1f}% win rate, {stats['max_drawdown']:.2f}% max DD")
            
        except Exception as e:
            print(f"❌ Error testing {year}: {str(e)}")
            continue
    
    # Show summary of what was actually tested
    if results_summary:
        tested_years = [r['year'] for r in results_summary]
        original_years = list(range(start_year, end_year + 1)) if years is None else years
        skipped_years = [y for y in original_years if y not in tested_years]
        
        print(f"\n📊 TESTING SUMMARY:")
        print(f"   • Requested years: {len(original_years if years is None else years)}")
        print(f"   • Successfully tested: {len(tested_years)} ({tested_years})")
        if skipped_years:
            print(f"   • Skipped (no data): {len(skipped_years)} ({skipped_years})")
    
    # Print comprehensive summary table
    print_historical_summary(results_summary, symbol)
    
    # Calculate and print aggregate statistics
    print_aggregate_statistics(results_summary)
    
    return results_summary


def determine_market_context(year: int, stats: Dict, results: Dict) -> str:
    """Determine market context based on year and performance characteristics"""
    pnl = stats['total_pnl']
    max_dd = stats['max_drawdown']
    vol_regime_changes = results.get('regime_changes', 0)
    
    # Historical context mapping
    context_map = {
        2017: "Bull Market (partial data)" if pnl > 20 else "Early Bull Market",
        2018: "Major Bear Market" if pnl < -30 else "Bear Market",
        2019: "Recovery Year" if pnl > 30 else "Sideways Recovery",
        2020: "Strong Bull Market" if pnl > 80 else "Bull Market",
        2021: "Volatile Bull Market" if vol_regime_changes > 10 else "Bull Market",
        2022: "Bear Market" if pnl < 0 else "Resilient Market",
        2023: "Recovery/Sideways" if 10 < pnl < 40 else ("Bull Recovery" if pnl > 40 else "Sideways"),
        2024: "Moderate Bull" if pnl > 15 else "Sideways Market",
        2025: "Mixed/Volatile" if vol_regime_changes > 10 else "Stable Market"
    }
    
    base_context = context_map.get(year, "Unknown Market")
    
    # Add performance qualifiers
    if max_dd > 50:
        base_context += " (High Vol)"
    elif max_dd < 20:
        base_context += " (Low Vol)"
    
    return base_context


def print_historical_summary(results: List[Dict], symbol: str):
    """Print formatted historical summary table"""
    if not results:
        print("❌ No results to display")
        print("\n💡 NOTE: BTCUSDT data on Binance is only available from August 2017 onwards")
        print("   For earlier Bitcoin price history, you would need data from other sources")
        return
    
    print(f"\n{'='*100}")
    print(f"COMPREHENSIVE HISTORICAL BACKTEST SUMMARY - {symbol}")
    print(f"{'='*100}")
    
    # Add data availability note for BTCUSDT
    if symbol == 'BTCUSDT':
        earliest_year = min(r['year'] for r in results)
        if earliest_year >= 2017:
            print(f"📋 Data Source: Binance exchange (available from Aug 2017)")
            print(f"   Note: Earlier Bitcoin data (2009-2016) not available on Binance")
    
    # Header
    header = f"{'Year':<6}{'Trades':<8}{'P&L (%)':<12}{'Win Rate (%)':<13}{'Max DD (%)':<12}{'Profit Factor':<14}{'Market Context':<25}"
    print(header)
    print("-" * 100)
    
    # Data rows
    for result in results:
        pnl_str = f"{result['pnl_percent']:+.2f}%"
        row = (f"{result['year']:<6}"
               f"{result['trades']:<8}"
               f"{pnl_str:<12}"
               f"{result['win_rate']:.1f}%{'':<8}"
               f"{result['max_drawdown']:.2f}%{'':<7}"
               f"{result['profit_factor']:.2f}{'':<10}"
               f"{result['market_context']:<25}")
        print(row)
    
    print("-" * 100)


def print_aggregate_statistics(results: List[Dict]):
    """Print aggregate performance statistics"""
    if not results:
        return
    
    print(f"\n{'='*60}")
    print("AGGREGATE PERFORMANCE ANALYSIS")
    print(f"{'='*60}")
    
    # Calculate aggregates
    total_years = len(results)
    profitable_years = len([r for r in results if r['pnl_percent'] > 0])
    total_trades = sum(r['trades'] for r in results)
    
    # Cumulative returns (compound)
    cumulative_return = 1.0
    for result in results:
        cumulative_return *= (1 + result['pnl_percent'] / 100)
    cumulative_return = (cumulative_return - 1) * 100
    
    # Average metrics
    avg_annual_return = sum(r['pnl_percent'] for r in results) / total_years
    avg_win_rate = sum(r['win_rate'] for r in results) / total_years
    avg_max_dd = sum(r['max_drawdown'] for r in results) / total_years
    avg_profit_factor = sum(r['profit_factor'] for r in results if r['profit_factor'] > 0) / max(1, len([r for r in results if r['profit_factor'] > 0]))
    
    # Best and worst years
    best_year = max(results, key=lambda x: x['pnl_percent'])
    worst_year = min(results, key=lambda x: x['pnl_percent'])
    
    # Risk metrics
    annual_returns = [r['pnl_percent'] for r in results]
    volatility = pd.Series(annual_returns).std() if len(annual_returns) > 1 else 0
    sharpe_ratio = avg_annual_return / volatility if volatility > 0 else 0
    
    print(f"📊 PERFORMANCE METRICS:")
    print(f"   Total Years Tested: {total_years}")
    print(f"   Profitable Years: {profitable_years} ({profitable_years/total_years*100:.1f}%)")
    print(f"   Total Trades: {total_trades:,}")
    print(f"   Cumulative Return: {cumulative_return:+.2f}% ({((cumulative_return/100 + 1)**(1/total_years) - 1)*100:.2f}% CAGR)")
    
    print(f"\n📈 ANNUAL AVERAGES:")
    print(f"   Average Annual Return: {avg_annual_return:+.2f}%")
    print(f"   Average Win Rate: {avg_win_rate:.1f}%")
    print(f"   Average Max Drawdown: {avg_max_dd:.2f}%")
    print(f"   Average Profit Factor: {avg_profit_factor:.2f}")
    
    print(f"\n⚡ RISK METRICS:")
    print(f"   Annual Volatility: {volatility:.2f}%")
    print(f"   Sharpe Ratio: {sharpe_ratio:.2f}")
    
    print(f"\n🏆 BEST & WORST:")
    print(f"   Best Year: {best_year['year']} ({best_year['pnl_percent']:+.2f}%) - {best_year['market_context']}")
    print(f"   Worst Year: {worst_year['year']} ({worst_year['pnl_percent']:+.2f}%) - {worst_year['market_context']}")
    
    print(f"\n💡 SYSTEM INSIGHTS:")
    bull_years = [r for r in results if 'Bull' in r['market_context']]
    bear_years = [r for r in results if 'Bear' in r['market_context']]
    sideways_years = [r for r in results if 'Sideways' in r['market_context'] or 'Recovery' in r['market_context']]
    
    if bull_years:
        bull_avg = sum(r['pnl_percent'] for r in bull_years) / len(bull_years)
        print(f"   Bull Market Avg: {bull_avg:+.2f}% ({len(bull_years)} years)")
    
    if bear_years:
        bear_avg = sum(r['pnl_percent'] for r in bear_years) / len(bear_years)
        print(f"   Bear Market Avg: {bear_avg:+.2f}% ({len(bear_years)} years)")
    
    if sideways_years:
        sideways_avg = sum(r['pnl_percent'] for r in sideways_years) / len(sideways_years)
        print(f"   Sideways Market Avg: {sideways_avg:+.2f}% ({len(sideways_years)} years)")
    
    # Risk assessment
    max_consecutive_losses = calculate_max_consecutive_losses(results)
    print(f"\n🛡️  RISK ASSESSMENT:")
    print(f"   Max Consecutive Loss Years: {max_consecutive_losses}")
    print(f"   Worst Drawdown Year: {max(results, key=lambda x: x['max_drawdown'])['year']} ({max(results, key=lambda x: x['max_drawdown'])['max_drawdown']:.2f}%)")
    
    # Overall grade
    grade = calculate_system_grade(cumulative_return, volatility, profitable_years, total_years, avg_max_dd)
    print(f"\n📋 OVERALL SYSTEM GRADE: {grade}")


def calculate_max_consecutive_losses(results: List[Dict]) -> int:
    """Calculate maximum consecutive losing years"""
    max_consecutive = 0
    current_consecutive = 0
    
    for result in results:
        if result['pnl_percent'] < 0:
            current_consecutive += 1
            max_consecutive = max(max_consecutive, current_consecutive)
        else:
            current_consecutive = 0
    
    return max_consecutive


def calculate_system_grade(cumulative_return: float, volatility: float, 
                         profitable_years: int, total_years: int, avg_max_dd: float) -> str:
    """Calculate overall system performance grade"""
    # Scoring components
    return_score = min(100, max(0, cumulative_return / 5))  # 5% per point up to 100
    consistency_score = (profitable_years / total_years) * 100
    risk_score = max(0, 100 - avg_max_dd * 2)  # Penalize high drawdowns
    sharpe_score = min(100, max(0, (cumulative_return / total_years / volatility if volatility > 0 else 0) * 50))
    
    overall_score = (return_score * 0.3 + consistency_score * 0.3 + risk_score * 0.25 + sharpe_score * 0.15)
    
    if overall_score >= 85:
        return "A+ (Excellent)"
    elif overall_score >= 75:
        return "A (Very Good)"
    elif overall_score >= 65:
        return "B+ (Good)"
    elif overall_score >= 55:
        return "B (Above Average)"
    elif overall_score >= 45:
        return "C+ (Average)"
    elif overall_score >= 35:
        return "C (Below Average)"
    else:
        return "D (Poor)"


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
    parser.add_argument('--mode', '-m', choices=['backtest', 'historical', 'monitor', 'trade', 'portfolio', 'export', 'dashboard'],
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
    parser.add_argument('--start-year', type=int, default=2017, help='Historical backtest start year (default: 2017)')
    parser.add_argument('--end-year', type=int, default=2025, help='Historical backtest end year (default: 2025)')
    parser.add_argument('--years', nargs='+', type=int, help='Specific years to test (e.g., --years 2020 2021 2022)')
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
            
        elif args.mode == 'historical':
            run_historical_backtest(
                symbol=args.symbol, 
                config=selected_config, 
                years=args.years,
                start_year=args.start_year, 
                end_year=args.end_year
            )
            
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