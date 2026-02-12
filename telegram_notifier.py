"""
Telegram Notifier for Pro Trading System
Sends real-time notifications about trades, signals, and portfolio updates
"""

import os
import requests
from typing import Optional, Dict, Any
from datetime import datetime
import json


class TelegramNotifier:
    """
    Send trading notifications via Telegram Bot API
    """

    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram bot token (get from @BotFather)
            chat_id: Your Telegram chat ID (get from @userinfobot)
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage" if self.bot_token else None

        if not self.enabled:
            print("⚠️  Telegram notifications disabled - set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        else:
            print("✅ Telegram notifications enabled")
            # Test connection
            self._test_connection()

    def _test_connection(self):
        """Test Telegram bot connection"""
        try:
            self.send_message("🤖 Pro Trader System connected!\nTelegram notifications are now active.")
        except Exception as e:
            print(f"⚠️  Telegram connection test failed: {e}")
            self.enabled = False

    def send_message(self, message: str, parse_mode: str = 'HTML', disable_notification: bool = False):
        """
        Send a text message to Telegram

        Args:
            message: Message text (supports HTML formatting)
            parse_mode: 'HTML' or 'Markdown'
            disable_notification: Send silently
        """
        if not self.enabled:
            return False

        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_notification': disable_notification
            }

            response = requests.post(self.api_url, json=payload, timeout=10)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send Telegram message: {e}")
            return False

    def notify_buy_signal(self, symbol: str, price: float, signal_data: Dict[str, Any]):
        """Send notification for BUY signal"""
        message = f"""
🟢 <b>BUY SIGNAL DETECTED</b>

📊 Symbol: <b>{symbol}</b>
💰 Price: <b>${price:,.4f}</b>

📈 Indicators:
  • RSI: {signal_data.get('rsi', 0):.1f}
  • MACD: {signal_data.get('macd_histogram', 0):.4f}
  • Trend: {signal_data.get('trend_status', 'Unknown')}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_sell_signal(self, symbol: str, price: float, signal_data: Dict[str, Any]):
        """Send notification for SELL signal"""
        message = f"""
🔴 <b>SELL SIGNAL DETECTED</b>

📊 Symbol: <b>{symbol}</b>
💰 Price: <b>${price:,.4f}</b>

📈 Indicators:
  • RSI: {signal_data.get('rsi', 0):.1f}
  • MACD: {signal_data.get('macd_histogram', 0):.4f}
  • Trend: {signal_data.get('trend_status', 'Unknown')}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_order_executed(self, order_type: str, symbol: str, quantity: float,
                             price: float, order_id: str, is_paper_trade: bool = False):
        """Send notification when order is executed"""
        trade_mode = "📋 PAPER TRADE" if is_paper_trade else "💰 LIVE TRADE"
        icon = "🟢" if order_type == "BUY" else "🔴"

        message = f"""
{icon} <b>{order_type} ORDER EXECUTED</b>
{trade_mode}

📊 Symbol: <b>{symbol}</b>
📦 Quantity: {quantity:.6f}
💵 Price: <b>${price:,.4f}</b>
💸 Value: <b>${quantity * price:,.2f}</b>
🔖 Order ID: <code>{order_id}</code>

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_order_failed(self, order_type: str, symbol: str, reason: str):
        """Send notification when order fails"""
        message = f"""
❌ <b>{order_type} ORDER FAILED</b>

📊 Symbol: <b>{symbol}</b>
⚠️ Reason: {reason}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_position_opened(self, symbol: str, trade_type: str, entry_price: float,
                              quantity: float, stop_loss: float, take_profit_1: float,
                              take_profit_2: float, is_paper_trade: bool = False):
        """Send notification when position is opened"""
        trade_mode = "📋 PAPER" if is_paper_trade else "💰 LIVE"

        sl_pct = abs((stop_loss - entry_price) / entry_price * 100)
        tp1_pct = abs((take_profit_1 - entry_price) / entry_price * 100)
        tp2_pct = abs((take_profit_2 - entry_price) / entry_price * 100)

        message = f"""
📍 <b>POSITION OPENED</b> {trade_mode}

📊 Symbol: <b>{symbol}</b>
📈 Type: <b>{trade_type}</b>
💰 Entry: <b>${entry_price:,.4f}</b>
📦 Quantity: {quantity:.6f}
💵 Position Value: <b>${quantity * entry_price:,.2f}</b>

🎯 Targets:
  • Stop Loss: ${stop_loss:,.4f} (-{sl_pct:.2f}%)
  • TP1: ${take_profit_1:,.4f} (+{tp1_pct:.2f}%)
  • TP2: ${take_profit_2:,.4f} (+{tp2_pct:.2f}%)

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_position_closed(self, symbol: str, trade_type: str, entry_price: float,
                              exit_price: float, quantity: float, pnl_percent: float,
                              pnl_amount: float, exit_reason: str, is_paper_trade: bool = False):
        """Send notification when position is closed"""
        trade_mode = "📋 PAPER" if is_paper_trade else "💰 LIVE"
        result_icon = "✅" if pnl_percent > 0 else "❌"

        message = f"""
{result_icon} <b>POSITION CLOSED</b> {trade_mode}

📊 Symbol: <b>{symbol}</b>
📈 Type: <b>{trade_type}</b>
💰 Entry: ${entry_price:,.4f}
💸 Exit: ${exit_price:,.4f}
📦 Quantity: {quantity:.6f}

📊 Result:
  • P&L: <b>{pnl_percent:+.2f}%</b>
  • Amount: <b>${pnl_amount:+.2f}</b>
  • Reason: {exit_reason}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_stop_loss_hit(self, symbol: str, trade_type: str, entry_price: float,
                            exit_price: float, pnl_percent: float, is_paper_trade: bool = False):
        """Send notification when stop loss is hit"""
        trade_mode = "📋 PAPER" if is_paper_trade else "💰 LIVE"

        message = f"""
🛑 <b>STOP LOSS HIT</b> {trade_mode}

📊 Symbol: <b>{symbol}</b>
📈 Type: {trade_type}
💰 Entry: ${entry_price:,.4f}
💸 Exit: ${exit_price:,.4f}

📉 Loss: <b>{pnl_percent:.2f}%</b>

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message, disable_notification=False)

    def notify_take_profit_hit(self, symbol: str, trade_type: str, tp_level: int,
                               entry_price: float, exit_price: float, pnl_percent: float,
                               is_paper_trade: bool = False):
        """Send notification when take profit is hit"""
        trade_mode = "📋 PAPER" if is_paper_trade else "💰 LIVE"

        message = f"""
🎯 <b>TAKE PROFIT {tp_level} HIT</b> {trade_mode}

📊 Symbol: <b>{symbol}</b>
📈 Type: {trade_type}
💰 Entry: ${entry_price:,.4f}
💸 Exit: ${exit_price:,.4f}

📈 Profit: <b>+{pnl_percent:.2f}%</b>

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_trailing_stop_updated(self, symbol: str, new_stop: float, profit_pct: float):
        """Send notification when trailing stop is updated"""
        message = f"""
📈 <b>TRAILING STOP UPDATED</b>

📊 Symbol: <b>{symbol}</b>
🎯 New Stop: <b>${new_stop:,.4f}</b>
💰 Current Profit: <b>+{profit_pct:.2f}%</b>

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message, disable_notification=True)

    def notify_portfolio_summary(self, balance: float, active_positions: int,
                                total_trades: int, win_rate: float, total_pnl: float,
                                is_paper_trading: bool = False):
        """Send daily portfolio summary"""
        trade_mode = "📋 PAPER TRADING" if is_paper_trading else "💰 LIVE TRADING"

        message = f"""
💼 <b>PORTFOLIO SUMMARY</b>
{trade_mode}

💵 Balance: <b>${balance:,.2f}</b>
📍 Active Positions: {active_positions}
📊 Total Trades: {total_trades}
✅ Win Rate: <b>{win_rate:.1f}%</b>
💰 Total P&L: <b>{total_pnl:+.2f}%</b>

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_error(self, error_type: str, error_message: str):
        """Send error notification"""
        message = f"""
⚠️ <b>ERROR ALERT</b>

❌ Type: {error_type}
📝 Message: {error_message}

⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_system_start(self, symbol: str, mode: str, config_name: str):
        """Send notification when system starts"""
        message = f"""
🚀 <b>TRADING SYSTEM STARTED</b>

📊 Symbol: <b>{symbol}</b>
⚙️ Mode: <b>{mode.upper()}</b>
🔧 Config: {config_name}

⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)

    def notify_system_stop(self):
        """Send notification when system stops"""
        message = f"""
🛑 <b>TRADING SYSTEM STOPPED</b>

⏰ Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()

        return self.send_message(message)


# Singleton instance
_notifier_instance = None

def get_telegram_notifier(bot_token: str = None, chat_id: str = None) -> TelegramNotifier:
    """Get global Telegram notifier instance"""
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = TelegramNotifier(bot_token, chat_id)
    return _notifier_instance
