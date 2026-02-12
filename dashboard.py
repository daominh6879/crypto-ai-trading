"""
Web-based Dashboard for Pro Trading System
Provides real-time visualization of trades, positions, and performance
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
from datetime import datetime, timedelta
from database import get_database
from config import TradingConfig, DEFAULT_CONFIG
import os

app = Flask(__name__)
CORS(app)

# Global state
dashboard_state = {
    'last_update': None,
    'live_price': 0.0,
    'symbol': 'BTCUSDT',
    'is_running': False,
    'mode': 'Paper Trading'
}


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/status')
def get_status():
    """Get current system status"""
    try:
        db = get_database()
        portfolio = db.get_portfolio_summary()
        stats = db.get_statistics()

        # Get active positions with current P&L
        active_positions = []
        for pos_data in portfolio['active_positions']:
            symbol = pos_data['symbol']
            position = db.get_active_position(symbol)
            if position:
                # Calculate current P&L (would need live price in real implementation)
                active_positions.append({
                    'symbol': symbol,
                    'type': position.trade_type,
                    'entry_price': position.entry_price,
                    'quantity': position.quantity,
                    'stop_loss': position.stop_loss,
                    'take_profit_1': position.take_profit_1,
                    'take_profit_2': position.take_profit_2,
                    'entry_time': position.entry_time
                })

        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'system': {
                'is_running': dashboard_state['is_running'],
                'mode': dashboard_state['mode'],
                'symbol': dashboard_state['symbol'],
                'live_price': dashboard_state['live_price']
            },
            'portfolio': {
                'active_positions': active_positions,
                'positions_count': len(active_positions)
            },
            'statistics': stats
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trades')
def get_trades():
    """Get recent trades"""
    try:
        db = get_database()
        limit = request.args.get('limit', 50, type=int)
        symbol = request.args.get('symbol', None)

        trades = db.get_trade_history(symbol, limit)

        trades_data = []
        for trade in trades:
            trades_data.append({
                'id': trade.id,
                'symbol': trade.symbol,
                'type': trade.trade_type,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'pnl_percent': trade.pnl_percent,
                'pnl_amount': trade.pnl_amount,
                'exit_reason': trade.exit_reason,
                'quantity': trade.quantity
            })

        return jsonify({
            'success': True,
            'trades': trades_data,
            'count': len(trades_data)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/performance')
def get_performance():
    """Get performance metrics and equity curve"""
    try:
        db = get_database()
        stats = db.get_statistics()
        trades = db.get_trade_history(limit=1000)

        # Build equity curve
        equity_curve = []
        cumulative_pnl = 0.0

        for trade in reversed(trades):
            cumulative_pnl += trade.pnl_percent
            equity_curve.append({
                'timestamp': trade.exit_time,
                'cumulative_pnl': cumulative_pnl,
                'trade_pnl': trade.pnl_percent
            })

        # Calculate additional metrics
        winning_trades = [t for t in trades if t.pnl_percent > 0]
        losing_trades = [t for t in trades if t.pnl_percent < 0]

        avg_win_amount = sum(t.pnl_amount for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss_amount = sum(t.pnl_amount for t in losing_trades) / len(losing_trades) if losing_trades else 0

        # Recent performance (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        recent_trades = [t for t in trades if t.exit_time >= thirty_days_ago]
        recent_pnl = sum(t.pnl_percent for t in recent_trades)

        return jsonify({
            'success': True,
            'statistics': stats,
            'equity_curve': equity_curve,
            'additional_metrics': {
                'avg_win_amount': avg_win_amount,
                'avg_loss_amount': avg_loss_amount,
                'total_winning_amount': sum(t.pnl_amount for t in winning_trades),
                'total_losing_amount': sum(t.pnl_amount for t in losing_trades),
                'recent_30d_pnl': recent_pnl,
                'recent_30d_trades': len(recent_trades)
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/positions')
def get_positions():
    """Get all active positions"""
    try:
        db = get_database()
        portfolio = db.get_portfolio_summary()

        positions = []
        for pos_data in portfolio['active_positions']:
            symbol = pos_data['symbol']
            position = db.get_active_position(symbol)
            if position:
                positions.append({
                    'id': position.id,
                    'symbol': symbol,
                    'type': position.trade_type,
                    'entry_price': position.entry_price,
                    'quantity': position.quantity,
                    'stop_loss': position.stop_loss,
                    'take_profit_1': position.take_profit_1,
                    'take_profit_2': position.take_profit_2,
                    'trailing_stop': position.trailing_stop,
                    'entry_time': position.entry_time,
                    'order_id': position.binance_order_id
                })

        return jsonify({
            'success': True,
            'positions': positions,
            'count': len(positions)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/update_price', methods=['POST'])
def update_price():
    """Update live price (called by trading system)"""
    try:
        data = request.get_json()
        dashboard_state['live_price'] = data.get('price', 0.0)
        dashboard_state['symbol'] = data.get('symbol', 'BTCUSDT')
        dashboard_state['last_update'] = datetime.now().isoformat()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system/start', methods=['POST'])
def start_system():
    """Signal that trading system has started"""
    data = request.get_json()
    dashboard_state['is_running'] = True
    dashboard_state['mode'] = data.get('mode', 'Paper Trading')
    dashboard_state['symbol'] = data.get('symbol', 'BTCUSDT')
    return jsonify({'success': True})


@app.route('/api/system/stop', methods=['POST'])
def stop_system():
    """Signal that trading system has stopped"""
    dashboard_state['is_running'] = False
    return jsonify({'success': True})


def create_html_template():
    """Create the HTML template for the dashboard"""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)

    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pro Trader Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0f1419;
            color: #e0e0e0;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #fff; margin-bottom: 20px; font-size: 28px; }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding: 20px;
            background: #1a1f26;
            border-radius: 10px;
        }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }
        .status-running { background: #10b981; color: white; }
        .status-stopped { background: #ef4444; color: white; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .card {
            background: #1a1f26;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .card h3 { color: #fff; margin-bottom: 15px; font-size: 16px; }
        .metric { margin-bottom: 10px; }
        .metric-label { color: #9ca3af; font-size: 13px; }
        .metric-value { color: #fff; font-size: 24px; font-weight: bold; }
        .positive { color: #10b981; }
        .negative { color: #ef4444; }
        .table-container { background: #1a1f26; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #2d3748; color: #fff; padding: 12px; text-align: left; font-size: 13px; }
        td { padding: 12px; border-bottom: 1px solid #2d3748; font-size: 13px; }
        tr:hover { background: #2d3748; }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            font-size: 14px;
        }
        .btn-refresh { background: #3b82f6; color: white; }
        .btn-refresh:hover { background: #2563eb; }
        .live-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #10b981;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🎯 Pro Trader Dashboard</h1>
                <p style="color: #9ca3af;">Real-time Trading System Monitor</p>
            </div>
            <div>
                <span id="systemStatus" class="status-badge status-stopped">⚫ Stopped</span>
                <button class="btn btn-refresh" onclick="refreshData()">🔄 Refresh</button>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h3>📊 Total Trades</h3>
                <div class="metric">
                    <div class="metric-value" id="totalTrades">-</div>
                    <div class="metric-label">All time</div>
                </div>
            </div>
            <div class="card">
                <h3>✅ Win Rate</h3>
                <div class="metric">
                    <div class="metric-value" id="winRate">-</div>
                    <div class="metric-label">Success rate</div>
                </div>
            </div>
            <div class="card">
                <h3>💰 Total P&L</h3>
                <div class="metric">
                    <div class="metric-value" id="totalPnl">-</div>
                    <div class="metric-label">Cumulative</div>
                </div>
            </div>
            <div class="card">
                <h3>📈 Profit Factor</h3>
                <div class="metric">
                    <div class="metric-value" id="profitFactor">-</div>
                    <div class="metric-label">Risk/Reward ratio</div>
                </div>
            </div>
        </div>

        <div class="table-container">
            <h3 style="color: #fff; margin-bottom: 15px;">📍 Active Positions</h3>
            <div id="activePositions">Loading...</div>
        </div>

        <div class="table-container">
            <h3 style="color: #fff; margin-bottom: 15px;">📋 Recent Trades</h3>
            <div id="recentTrades">Loading...</div>
        </div>
    </div>

    <script>
        function formatNumber(num, decimals = 2) {
            return parseFloat(num).toFixed(decimals);
        }

        function formatPercent(num) {
            const val = parseFloat(num);
            const sign = val >= 0 ? '+' : '';
            const color = val >= 0 ? 'positive' : 'negative';
            return `<span class="${color}">${sign}${val.toFixed(2)}%</span>`;
        }

        async function refreshData() {
            try {
                // Fetch status
                const statusRes = await fetch('/api/status');
                const status = await statusRes.json();

                if (status.success) {
                    const stats = status.statistics;
                    document.getElementById('totalTrades').textContent = stats.total_trades;
                    document.getElementById('winRate').innerHTML = formatPercent(stats.win_rate);
                    document.getElementById('totalPnl').innerHTML = formatPercent(stats.total_pnl);
                    document.getElementById('profitFactor').textContent = formatNumber(stats.profit_factor);

                    // Update system status
                    const statusBadge = document.getElementById('systemStatus');
                    if (status.system.is_running) {
                        statusBadge.className = 'status-badge status-running';
                        statusBadge.innerHTML = '<span class="live-indicator"></span>Running - ' + status.system.mode;
                    } else {
                        statusBadge.className = 'status-badge status-stopped';
                        statusBadge.textContent = '⚫ Stopped';
                    }
                }

                // Fetch positions
                const posRes = await fetch('/api/positions');
                const posData = await posRes.json();

                if (posData.success) {
                    const positions = posData.positions;
                    let posHtml = '';

                    if (positions.length === 0) {
                        posHtml = '<p style="color: #9ca3af;">No active positions</p>';
                    } else {
                        posHtml = '<table><thead><tr><th>Symbol</th><th>Type</th><th>Entry</th><th>Quantity</th><th>Stop Loss</th><th>TP1</th><th>TP2</th><th>Time</th></tr></thead><tbody>';
                        positions.forEach(pos => {
                            posHtml += `<tr>
                                <td><strong>${pos.symbol}</strong></td>
                                <td><span class="${pos.type === 'LONG' ? 'positive' : 'negative'}">${pos.type}</span></td>
                                <td>$${formatNumber(pos.entry_price, 4)}</td>
                                <td>${formatNumber(pos.quantity, 6)}</td>
                                <td>$${formatNumber(pos.stop_loss, 4)}</td>
                                <td>$${formatNumber(pos.take_profit_1, 4)}</td>
                                <td>$${formatNumber(pos.take_profit_2, 4)}</td>
                                <td>${new Date(pos.entry_time).toLocaleString()}</td>
                            </tr>`;
                        });
                        posHtml += '</tbody></table>';
                    }
                    document.getElementById('activePositions').innerHTML = posHtml;
                }

                // Fetch trades
                const tradesRes = await fetch('/api/trades?limit=20');
                const tradesData = await tradesRes.json();

                if (tradesData.success) {
                    const trades = tradesData.trades;
                    let tradesHtml = '<table><thead><tr><th>Symbol</th><th>Type</th><th>Entry</th><th>Exit</th><th>P&L %</th><th>P&L $</th><th>Reason</th><th>Exit Time</th></tr></thead><tbody>';

                    trades.forEach(trade => {
                        tradesHtml += `<tr>
                            <td><strong>${trade.symbol}</strong></td>
                            <td><span class="${trade.type === 'LONG' ? 'positive' : 'negative'}">${trade.type}</span></td>
                            <td>$${formatNumber(trade.entry_price, 4)}</td>
                            <td>$${formatNumber(trade.exit_price, 4)}</td>
                            <td>${formatPercent(trade.pnl_percent)}</td>
                            <td class="${trade.pnl_amount >= 0 ? 'positive' : 'negative'}">$${formatNumber(trade.pnl_amount)}</td>
                            <td>${trade.exit_reason}</td>
                            <td>${new Date(trade.exit_time).toLocaleString()}</td>
                        </tr>`;
                    });
                    tradesHtml += '</tbody></table>';
                    document.getElementById('recentTrades').innerHTML = tradesHtml;
                }

            } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }

        // Initial load
        refreshData();

        // Auto-refresh every 5 seconds
        setInterval(refreshData, 5000);
    </script>
</body>
</html>"""

    with open(os.path.join(template_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("✅ Dashboard template created")


def start_dashboard(host='127.0.0.1', port=5000, debug=False):
    """Start the web dashboard server"""
    create_html_template()
    print(f"🌐 Starting dashboard server at http://{host}:{port}")
    print("📊 Open this URL in your browser to view the dashboard")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    start_dashboard(debug=True)
