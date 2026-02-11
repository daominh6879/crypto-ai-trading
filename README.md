# Pro Trader System v3.0

A streamlined live trading application converted from TradingView Pine Script strategy, featuring Binance integration, SQLite database for position management, and automated backtesting.

## 🚀 Features

### ✅ Core Features
- **Live Trading**: Real Binance order execution with buy/sell signals
- **Database Integration**: SQLite storage for all positions, trades, and signals  
- **Backtesting**: Complete historical strategy testing with CSV export
- **TradingView Strategy**: Converted from original Pine Script with all indicators
- **Risk Management**: Stop losses, take profits, and trailing stops
- **Multiple Timeframes**: Support for various trading intervals
- **Portfolio Tracking**: Complete trade history and performance analytics
- **Lean Codebase**: Focused on core trading functionality without visualization bloat

### 📊 Trading Strategy (from TradingView)
Based on the original Pine Script with these components:

**Technical Indicators:**
- EMA (20, 50, 200) for trend analysis
- RSI (14) for momentum
- MACD for trend confirmation  
- ATR for volatility-based position sizing

**Entry Conditions:**
- **Buy Setup**: RSI oversold (< 30) + trend alignment
- **Buy Trigger**: Bullish reversal + MACD confirmation + volume confirmation
- **Sell Setup**: RSI overbought (> 70) + trend alignment  
- **Sell Trigger**: Bearish reversal + MACD confirmation

**Risk Management:**
- Stop Loss: 2x ATR (configurable)
- Take Profit 1: 3x ATR  
- Take Profit 2: 5x ATR
- Trailing Stop: Activated at 5% profit

## 🛠️ Installation

1. **Clone/Download** this repository
2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   Required packages:
   - pandas, numpy (data processing)
   - python-binance (market data & trading)
   - talib-binary, scipy (technical analysis)
   - colorama (console output)

3. **Setup Binance API** (for live trading):
   - Get API keys from Binance
   - Set environment variables:
     ```bash
     BINANCE_API_KEY=your_api_key
     BINANCE_API_SECRET=your_api_secret
     ```

## 📖 Usage

### Basic Commands

```bash
# Run crypto backtest with Binance data
python main.py --symbol BTCUSDT --mode backtest --interval 1h

# Monitor live signals (no orders)
python main.py --symbol BTCUSDT --mode monitor

# Live trading with real orders (⚠️ REAL MONEY!)
python main.py --symbol BTCUSDT --mode trade --position-size 100

# Show portfolio status
python main.py --mode portfolio

# Export trade data
python main.py --mode export --export-table trades
```

### Configuration Options

```bash
# Different trading configurations
--config default      # Balanced settings
--config scalping     # Short-term, smaller stops
--config swing        # Longer-term, bigger stops  
--config conservative # Stricter entry conditions

# Data sources
--interval 1h         # Trading timeframe
--period 2y           # Backtest period
```

## 📁 File Structure

```
├── main.py                 # Main application entry point
├── config.py              # Trading configuration settings  
├── trading_system.py      # Core trading system logic
├── database.py            # SQLite database management
├── position_manager.py    # Position and trade management
├── binance_provider.py    # Binance API integration
├── indicators.py          # Technical indicator calculations
├── requirements.txt       # Python dependencies
├── README.md              # This documentation
└── trading_system.db      # SQLite database (created automatically)
```

## 🎯 Key Components

### 1. Database System (`database.py`)
- **Positions Table**: Active trading positions
- **Trades Table**: Completed trade history  
- **Signals Table**: All generated signals for analysis
- **Performance Analytics**: Win rate, P&L, drawdown calculations
- **CSV Export**: Export data for external analysis

### 2. Live Trading (`binance_provider.py`)
- **Real Order Execution**: Market buy/sell orders
- **Account Management**: Balance checking, position limits
- **Order Tracking**: Order status monitoring
- **Error Handling**: Robust error handling for API issues
- **Position Size Calculation**: Automatic quantity calculation

### 3. Position Management (`position_manager.py`)
- **Risk Management**: Stop loss and take profit automation
- **Trailing Stops**: Dynamic stop loss adjustment
- **Database Integration**: Automatic position persistence
- **Multiple Positions**: Support for multiple concurrent positions
- **Exit Conditions**: Comprehensive exit logic

### 4. Trading Signals (`trading_system.py`)  
- **Indicator Calculation**: All technical indicators
- **Signal Generation**: Buy/sell trigger logic
- **Confirmation Logic**: Multi-factor confirmation
- **Market Analysis**: Real-time market status
- **Historical Testing**: Complete backtesting framework

## ⚠️ Important Notes

### Live Trading Safety
- **Start Small**: Begin with small position sizes
- **Test First**: Run backtests and monitoring before live trading
- **API Keys**: Keep API keys secure, use IP restrictions
- **Risk Management**: Never risk more than you can afford to lose

### Database
- All positions and trades are automatically saved
- Database file: `trading_system.db`  
- Backup your database regularly for important data
- Use `--mode portfolio` to check current status

### Binance Integration
- Supports spot trading only
- Requires verified Binance account
- API keys need trading permissions
- Respects Binance rate limits

## 📊 Sample Output

### Backtest Results
```
PRO TRADER SYSTEM PERFORMANCE STATISTICS
============================================================
Symbol: BTCUSDT
Period: 2024-02-11 to 2026-02-11
Total Bars: 730

📊 Trade Statistics:
Total Trades: 45
Winning Trades: 28
Losing Trades: 17
Win Rate: 62.2%

💰 Performance Metrics:
Average Win: 4.85%
Average Loss: -2.31%
Total P&L: 23.45%
Total P&L Amount: $2,345.67
Max Drawdown: 8.92%
Profit Factor: 2.1
```

### Live Trading
```
🔴 LIVE TRADING for BTCUSDT 1h
💰 USDT Balance: $1,000.00
🟢 BUY SIGNAL TRIGGERED at $43,250.50
✅ BUY ORDER EXECUTED: 0.002314 BTCUSDT
📊 Position saved to database with ID: 1
```

## 🧪 Testing

Verify installation with these commands:

```bash
# Test crypto backtest
python main.py --symbol BTCUSDT --mode backtest

# Test with crypto monitoring (no trading)
python main.py --symbol BTCUSDT --mode monitor

# Check portfolio status
python main.py --mode portfolio
```

## 🔧 Troubleshooting

### Common Issues
1. **ModuleNotFoundError**: Install missing packages with pip
2. **API Errors**: Check Binance API key permissions
3. **Database Errors**: Delete `trading_system.db` to reset
4. **No Trades in Backtest**: Adjust configuration parameters
5. **TA-Lib Warning**: "TA-Lib not found, using pandas fallback functions" is normal and doesn't affect functionality

### Debug Mode
Use monitoring mode to see signals without trading:
```bash
python main.py --symbol BTCUSDT --mode monitor
```

## 📈 Strategy Performance

This strategy is based on proven technical analysis concepts:
- **Trend Following**: EMA alignment for trend direction
- **Mean Reversion**: RSI extremes for entry timing  
- **Momentum Confirmation**: MACD for signal validation
- **Volume Confirmation**: Volume analysis for signal strength
- **Risk Management**: ATR-based position sizing and stops

The original TradingView strategy has been fully converted to Python with additional enhancements:
- Database persistence for all trades and positions
- Live order execution with Binance API
- Portfolio management and performance tracking
- Advanced backtesting with detailed statistics
- Multiple configuration presets for different trading styles
- Lean, focused codebase without visualization dependencies

## 📄 License

This project is for educational and personal use. Please ensure compliance with your local trading regulations and exchange terms of service.

## ⚠️ Disclaimer

**Trading involves significant risk of loss. Past performance does not guarantee future results. This software is provided for educational purposes only. Users are responsible for their own trading decisions and any resulting profits or losses.**

---

**Happy Trading! 🚀📈**