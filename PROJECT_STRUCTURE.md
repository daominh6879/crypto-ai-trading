# Project Structure

## Production Code (Root Directory)

### Core Trading System

**config.py** - Trading configuration and parameters
- Strategy parameters (stops, targets, position sizing)
- ADX 20-30 filter enabled by default
- Trade direction controls (long/short)
- Risk management settings

**trading_system.py** - Main trading system implementation
- Signal generation with ADX 20-30 filter
- Trade execution logic
- Backtesting functionality
- Position management integration

**position_manager.py** - Position and trade management
- Open/close positions
- Risk management (stops, targets)
- Trailing stop logic
- Trade history tracking

**indicators.py** - Technical indicator calculations
- RSI, MACD, Stochastic
- ADX (Average Directional Index)
- Bollinger Bands
- Signal generation helpers

**binance_provider.py** - Market data provider
- Fetch historical OHLCV data from Binance
- Real-time price data
- Comprehensive data fetching with chunking
- Data validation and cleaning

**database.py** - Persistent storage
- SQLite database operations
- Trade history storage
- Performance metrics tracking
- Position logging

### User Interface & Notifications

**main.py** - Command-line interface
- Interactive trading dashboard
- Manual trade entry
- Real-time monitoring
- System control (start/stop/status)

**dashboard.py** - Terminal dashboard UI
- Real-time P&L display
- Open positions view
- Recent trades
- Performance statistics

**telegram_notifier.py** - Telegram notifications
- Trade entry/exit alerts
- P&L updates
- System status notifications
- Error alerts

### Documentation

**README.md** - Main project documentation
- Project overview
- Features and capabilities
- Quick start guide
- Basic usage instructions

**SETUP_GUIDE.md** - Installation and setup
- Requirements
- API key configuration
- Database setup
- First-time usage

**FEATURES.md** - Feature documentation
- Detailed feature descriptions
- Configuration options
- Advanced usage
- Examples

**PROJECT_STRUCTURE.md** (this file) - Code organization
- File structure
- Module descriptions
- Dependencies

## Research Archive (`/research`)

Analysis scripts, experimental code, and detailed documentation from the optimization project. See [research/README.md](research/README.md) for details.

**Not required for production.** Can be deleted if disk space needed, but recommended to keep for reference.

### Subdirectories:
- `/analysis` - One-time analysis scripts
- `/regime_detection` - Experimental features (not implemented)
- `/documentation` - Detailed analysis reports and findings

## Tests (`/tests` - if exists)

Unit tests and integration tests for the trading system.

## Configuration Files

**.env** - Environment variables (gitignored)
- API keys (Binance, Telegram)
- Database path
- Feature flags

**requirements.txt** - Python dependencies
- pandas, numpy, ta-lib
- python-binance
- python-telegram-bot
- Other dependencies

## Database Files

**trading.db** - SQLite database (gitignored)
- Trade history
- Position records
- Performance metrics

## File Count Summary

### Production Code: ~12 files
- 6 core system files
- 3 UI/notification files
- 3 documentation files

### Research Archive: ~15 files
- 9 analysis scripts
- 2 regime detection systems
- 4 documentation files

**Total codebase is clean and focused on production functionality.**

## Import Dependencies

```
main.py
  ├── trading_system.py
  │   ├── config.py
  │   ├── position_manager.py
  │   │   └── database.py
  │   ├── indicators.py
  │   └── binance_provider.py
  ├── dashboard.py
  └── telegram_notifier.py
```

## Key Design Principles

1. **Separation of Concerns**: Each module has a single, clear responsibility
2. **Configuration-Driven**: All parameters in config.py, no hardcoded values
3. **Clean Research Archive**: Analysis code separated from production code
4. **Minimal Dependencies**: Only essential libraries required
5. **Database Persistence**: All trades and positions logged for analysis

## Optimization Status

**Current Implementation**: ADX 20-30 filter enabled by default

**Performance**:
- 2022 (Bear): -12.66% (60% loss reduction from baseline)
- 2024 (Bull): +20.93% (14% gain increase from baseline)
- Combined: +8.27% (vs baseline -13.40%)

**Further optimization**: See research/documentation/OPTIMIZATION_JOURNEY_COMPLETE.md

## Adding New Features

1. **New Indicator**: Add to `indicators.py`
2. **New Signal Logic**: Modify `trading_system.py`
3. **New Risk Management**: Modify `position_manager.py`
4. **New Parameters**: Add to `config.py`

Always test changes on historical data before live trading.

---

**Last Updated**: 2026-02-12
**Status**: Production ready
**Optimization**: Complete (ADX 20-30 filter implemented)
