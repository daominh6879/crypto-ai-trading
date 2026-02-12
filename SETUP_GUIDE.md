# 🚀 Quick Setup Guide

## Step-by-Step Setup for Live Trading Features

### 1️⃣ Install Dependencies (5 minutes)

```bash
# Install all required packages
pip install -r requirements.txt
```

**Required Packages:**
- pandas, numpy (data processing)
- python-binance (market data & trading)
- flask, flask-cors (web dashboard)
- requests (Telegram notifications)

---

### 2️⃣ Set Up Telegram Bot (10 minutes)

#### A. Create Telegram Bot

1. Open Telegram app
2. Search for `@BotFather`
3. Send command: `/newbot`
4. Follow prompts to name your bot
5. Copy the **bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrs...`)

#### B. Get Your Chat ID

1. Search for `@userinfobot` on Telegram
2. Send any message
3. Copy your **chat ID** (looks like: `987654321`)

#### C. Set Environment Variables

**Windows (Command Prompt):**
```cmd
set TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrs...
set TELEGRAM_CHAT_ID=987654321
```

**Windows (PowerShell):**
```powershell
$env:TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrs..."
$env:TELEGRAM_CHAT_ID="987654321"
```

**Linux/Mac:**
```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrs..."
export TELEGRAM_CHAT_ID="987654321"
```

#### D. Test Telegram Connection

```python
python
>>> from telegram_notifier import get_telegram_notifier
>>> notifier = get_telegram_notifier()
>>> notifier.send_message("🎉 Setup successful!")
```

You should receive a message in your Telegram!

---

### 3️⃣ Configure Trading Settings (5 minutes)

Edit `config.py`:

```python
# ==================== TRADING MODE ====================
paper_trading: bool = True  # TRUE = Paper trading (safe), FALSE = Real money
enable_telegram: bool = True  # Enable Telegram notifications
initial_paper_balance: float = 10000.0  # Starting balance for paper trading

# ==================== RISK MANAGEMENT ====================
max_position_size: float = 0.015  # 1.5% max position size
stop_loss_multiplier: float = 3.0  # Stop loss distance
take_profit_1_multiplier: float = 4.0  # First target
take_profit_2_multiplier: float = 8.0  # Second target
```

**Recommended for beginners:**
- Keep `paper_trading = True`
- Start with `max_position_size = 0.01` (1%)
- Keep default risk multipliers

---

### 4️⃣ Run Your First Backtest (2 minutes)

Test the strategy on historical data:

```bash
python main.py --mode backtest --symbol BTCUSDT --start-date 2025-01-01 --interval 1h
```

**Expected Output:**
```
✅ Backtest completed with 93 trades
📊 Total P&L: +31.92%
✅ Win Rate: 46.2%
📈 Profit Factor: 1.30
```

---

### 5️⃣ Start Paper Trading (3 minutes)

Run the system with paper money:

```bash
python main.py --mode trade --symbol BTCUSDT --interval 1h --position-size 100
```

**What Happens:**
- System monitors BTCUSDT in real-time
- Generates buy/sell signals
- Executes virtual orders
- Tracks positions in database
- Sends Telegram notifications
- No real money used! ✅

**Type 'START' when prompted to begin**

---

### 6️⃣ Open Web Dashboard (2 minutes)

Open a **new terminal/command prompt** and run:

```bash
python main.py --mode dashboard
```

Then open your browser: **http://127.0.0.1:5000**

**Dashboard Shows:**
- 📊 Total trades and win rate
- 💰 Total P&L
- 📍 Active positions
- 📋 Recent trade history
- Auto-refreshes every 5 seconds

---

### 7️⃣ View Portfolio Status (1 minute)

Check your trading stats anytime:

```bash
python main.py --mode portfolio
```

**Output:**
```
💼 PORTFOLIO STATUS
==================
📊 Active Positions: 1
  • BTCUSDT: 1 positions, Avg Entry: $42,350.50

📈 Trading Statistics:
Total Trades: 5
Win Rate: 60.0%
Total P&L: +8.50%
```

---

## 🎯 Complete Workflow Example

### Option A: Paper Trading + Dashboard

**Terminal 1 - Dashboard:**
```bash
python main.py --mode dashboard
# Opens at http://127.0.0.1:5000
```

**Terminal 2 - Paper Trading:**
```bash
python main.py --mode trade --symbol BTCUSDT --interval 1h --position-size 100
# Type 'START' when prompted
```

**Your Telegram - Notifications:**
- Real-time alerts for every signal and trade
- Position opened/closed notifications
- P&L updates

---

### Option B: Backtest → Monitor → Paper Trade

```bash
# 1. Run backtest
python main.py --mode backtest --symbol ETHUSDT --start-date 2025-01-01 --interval 1h

# 2. Check current market status
python main.py --mode monitor --symbol ETHUSDT --interval 1h

# 3. Start paper trading if conditions look good
python main.py --mode trade --symbol ETHUSDT --interval 1h --position-size 50
```

---

## ⚠️ Before Going Live with Real Money

### Prerequisites Checklist:

- [ ] Successful backtest with 30%+ annual return
- [ ] Paper trading for at least 1 month
- [ ] Understand all signals and indicators
- [ ] Telegram notifications working properly
- [ ] Comfortable with risk management settings
- [ ] Have Binance API keys ready
- [ ] Start with small position sizes (1-2%)

### Setting Up Real Trading:

1. **Get Binance API Keys:**
   - Go to Binance.com → Account → API Management
   - Create new API key
   - Enable "Reading" and "Spot & Margin Trading"
   - Save your API key and secret securely
   - ⚠️ Never share your API secret!

2. **Set API Environment Variables:**
   ```bash
   set BINANCE_API_KEY=your_api_key_here
   set BINANCE_API_SECRET=your_api_secret_here
   ```

3. **Update config.py:**
   ```python
   paper_trading: bool = False  # Enable real trading
   max_position_size: float = 0.01  # Start small (1%)
   ```

4. **Start with Small Position:**
   ```bash
   python main.py --mode trade --symbol BTCUSDT --interval 1h --position-size 20
   # Start with $20 USDT positions
   ```

---

## 🛠️ Troubleshooting

### Issue: Telegram Not Working

**Check:**
```bash
# Windows
echo %TELEGRAM_BOT_TOKEN%
echo %TELEGRAM_CHAT_ID%

# Linux/Mac
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID
```

**Fix:**
- Re-set environment variables
- Restart terminal/command prompt
- Verify bot token with BotFather
- Verify chat ID with userinfobot

---

### Issue: Dashboard Won't Load

**Check:**
```bash
# See if port 5000 is in use
netstat -ano | findstr :5000
```

**Fix:**
```bash
# Use different port
python main.py --mode dashboard --dashboard-port 8080
# Then open: http://127.0.0.1:8080
```

---

### Issue: "No data found for BTCUSDT"

**Check:**
- Internet connection
- Binance API is accessible
- Symbol is correct (use BTCUSDT not BTC/USDT)

**Fix:**
```bash
# Try different symbol
python main.py --mode backtest --symbol ETHUSDT --start-date 2025-01-01
```

---

### Issue: "Insufficient balance"

**Paper Trading:**
- Increase `initial_paper_balance` in config.py
- Reduce position size with `--position-size` flag

**Real Trading:**
- Check USDT balance on Binance
- Reduce position size
- Deposit more USDT to Binance spot wallet

---

## 📱 Telegram Notification Examples

### When You'll Get Notified:

**Buy Signal:**
```
🟢 BUY SIGNAL DETECTED

📊 Symbol: BTCUSDT
💰 Price: $42,350.50

📈 Indicators:
  • RSI: 58.5
  • MACD: 0.0024
  • Trend: Strong Bullish

⏰ Time: 2025-02-11 14:30:00
```

**Order Executed:**
```
🟢 BUY ORDER EXECUTED
📋 PAPER TRADE

📊 Symbol: BTCUSDT
📦 Quantity: 0.002360
💵 Price: $42,350.50
💸 Value: $100.00
🔖 Order ID: PAPER_1

⏰ Time: 2025-02-11 14:30:05
```

**Position Opened:**
```
📍 POSITION OPENED 📋 PAPER

📊 Symbol: BTCUSDT
📈 Type: LONG
💰 Entry: $42,350.50
📦 Quantity: 0.002360
💵 Position Value: $100.00

🎯 Targets:
  • Stop Loss: $41,000.00 (-3.19%)
  • TP1: $44,150.00 (+4.25%)
  • TP2: $45,950.00 (+8.50%)

⏰ Time: 2025-02-11 14:30:05
```

---

## 🎓 Next Steps

After completing setup:

1. **Week 1:** Run backtests on different symbols and intervals
2. **Week 2-4:** Paper trade and monitor dashboard daily
3. **Week 5:** Review all paper trades, analyze performance
4. **Week 6+:** If profitable, consider small real trading

**Remember:**
- 📋 Always start with paper trading
- 📱 Monitor Telegram notifications
- 🌐 Check dashboard regularly
- 💾 Export and review trades weekly
- 📊 Aim for 30%+ annual returns
- ⚠️ Never risk more than you can afford to lose

---

## 📞 Need Help?

1. Review the [FEATURES.md](FEATURES.md) documentation
2. Check troubleshooting section above
3. Verify all configuration settings
4. Review console logs for errors

**Happy Trading! 🚀📈**
