import ccxt
import time
from datetime import datetime
import sys
from typing import Dict, Any, List, Tuple
from collections import deque
from flask import Flask, render_template_string, jsonify
import threading
import json
from flask_cors import CORS
import logging
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
# 导入ETH地址监控模块
from eth_address_monitor import eth_bp, start_eth_monitor

# ANSI颜色代码
GREEN = '\033[32m'
RED = '\033[31m'
RESET = '\033[0m'

# HTML颜色代码
HTML_GREEN = '#4CAF50'
HTML_RED = '#F44336'

# 设置日志级别
logging.basicConfig(level=logging.ERROR)  # 改为ERROR级别
logger = logging.getLogger(__name__)
# 关闭Flask日志
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# 配置重试策略
retry_strategy = Retry(
    total=3,  # 最多重试3次
    backoff_factor=0.5,  # 重试间隔时间
    status_forcelist=[500, 502, 503, 504]  # 需要重试的HTTP状态码
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("http://", adapter)
http.mount("https://", adapter)

app = Flask(__name__)
app.logger.setLevel(logging.ERROR)  # 设置Flask日志级别
CORS(app)  # 启用CORS支持
# 注册ETH地址监控蓝图
app.register_blueprint(eth_bp)

# 共享数据存储
shared_data = {
    'update_time': '',
    'prices': []
}

# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>加密货币实时价格</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <style>
        body {
            font-family: monospace;
            background-color: #1E1E1E;
            color: #FFFFFF;
            padding: 0;
            margin: 0;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        .container {
            flex: 1;
            width: 100%;
            max-width: 100%;
            margin: 0;
            padding: 5px;
            display: flex;
            flex-direction: column;
            box-sizing: border-box;
            overflow-x: hidden;
        }
        .update-time {
            margin-bottom: 10px;
            font-size: 16px;
            color: #888;
            padding: 0 10px;
        }
        table {
            width: 1440px;
            min-width: 1440px;
            table-layout: fixed;
            border-collapse: collapse;
            white-space: nowrap;
            font-size: 18px;
            margin: 0 auto;
        }
        th, td {
            padding: 8px;
            border: 1px solid #333;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        th {
            background-color: #333;
            color: #CCC;
            position: sticky;
            top: 0;
            z-index: 1;
        }
        tr {
            background-color: #1E1E1E;
            transition: all 0.3s ease;
            height: 45px;
        }
        tr:nth-child(even) {
            background-color: #2A2A2A;
        }
        .up {
            color: #4CAF50;
        }
        .down {
            color: #F44336;
        }
        .price-cell {
            font-family: monospace;
            text-align: right;
            position: relative;
            padding-right: 5px;
        }
        
        @keyframes flash-green {
            0% { background-color: transparent; }
            50% { background-color: rgba(76, 175, 80, 0.3); }
            100% { background-color: transparent; }
        }
        
        @keyframes flash-red {
            0% { background-color: transparent; }
            50% { background-color: rgba(244, 67, 54, 0.3); }
            100% { background-color: transparent; }
        }
        
        .flash-green {
            animation: flash-green 1s ease-out;
        }
        
        .flash-red {
            animation: flash-red 1s ease-out;
        }
        
        /* 调整列宽比例 */
        th:nth-child(1), td:nth-child(1) { width: 100px; min-width: 100px; max-width: 100px; text-align: center; font-weight: bold; padding: 8px 0; }
        th:nth-child(2), td:nth-child(2) { width: 260px; min-width: 260px; max-width: 260px; text-align: center; font-weight: bold; padding: 8px 0; }
        th:nth-child(3), td:nth-child(3) { width: 200px; min-width: 200px; max-width: 200px; text-align: center; padding: 8px 0; }
        th:nth-child(4), td:nth-child(4) { width: 280px; min-width: 280px; max-width: 280px; text-align: center; padding: 8px 0; }
        
        .price-cell {
            font-family: monospace;
            text-align: center;
            position: relative;
            padding: 8px 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            letter-spacing: -0.2px;
            font-size: 18px;
        }
        
        /* 优化百分比显示间距 */
        td:nth-child(3) span {
            margin: 0 4px;
            font-size: 18px;
        }
        
        /* 移除箭头和数字之间的空格 */
        span[class^="up"], span[class^="down"] {
            margin: 0;
            padding: 0;
            font-size: 18px;
        }
        
        /* 移除箭头和数字之间的空格 */
        span[style*="color"] {
            margin: 0;
            padding: 0;
            font-size: 18px;
        }
        
        /* iPad mini 7 横屏优化 */
        @media screen and (max-width: 1488px) {
            table {
                width: 840px;
                min-width: 840px;
                font-size: 16px;
            }
            
            th:nth-child(1), td:nth-child(1) { 
                width: 100px; 
                min-width: 100px; 
                max-width: 100px;
                padding: 6px 0;
            }
            th:nth-child(2), td:nth-child(2) { 
                width: 260px; 
                min-width: 260px;
                max-width: 260px;
                padding: 6px 0;
            }
            th:nth-child(3), td:nth-child(3) { 
                width: 200px; 
                min-width: 200px;
                max-width: 200px;
                padding: 6px 0;
            }
            th:nth-child(4), td:nth-child(4) { 
                width: 280px; 
                min-width: 280px;
                max-width: 280px;
                padding: 6px 0;
            }
            
            .price-cell {
                font-size: 16px;
                letter-spacing: -0.2px;
                padding: 6px 0;
            }
            
            td:nth-child(3) span {
                font-size: 16px;
                margin: 0 3px;
            }
            
            tr {
                height: 40px;
            }
        }
        
        /* 较小屏幕的优化 */
        @media screen and (max-width: 768px) {
            table {
                min-width: 700px;
                font-size: 14px;
            }
            th, td {
                padding: 4px 1px;
            }
            .price-cell {
                font-size: 14px;
            }
            td:nth-child(3) span {
                font-size: 14px;
                margin: 0 2px;
            }
            tr {
                height: 35px;
            }
        }
    </style>
    <script>
        let previousPrices = {};
        
        function updateData() {
            fetch('/api/prices')
                .then(response => response.json())
                .then(data => {
                    document.querySelector('.update-time').textContent = '更新时间：' + data.update_time;
                    const tbody = document.querySelector('tbody');
                    tbody.innerHTML = '';
                    
                    data.prices.forEach(item => {
                        const row = document.createElement('tr');
                        const previousPrice = previousPrices[item.symbol];
                        
                        // 币种名称
                        const symbolCell = document.createElement('td');
                        symbolCell.textContent = item.symbol;
                        row.appendChild(symbolCell);
                        
                        // 最新价格
                        const priceCell = document.createElement('td');
                        priceCell.className = 'price-cell';
                        priceCell.textContent = item.price;
                        if (previousPrice && previousPrice !== item.price) {
                            priceCell.classList.add(parseFloat(item.price) > parseFloat(previousPrice) ? 'flash-green' : 'flash-red');
                        }
                        row.appendChild(priceCell);
                        
                        // 涨跌幅
                        const percentagesCell = document.createElement('td');
                        percentagesCell.innerHTML = item.percentages;
                        row.appendChild(percentagesCell);
                        
                        // 24H交易量
                        const volumeCell = document.createElement('td');
                        volumeCell.className = 'price-cell';
                        volumeCell.textContent = item.volume;
                        row.appendChild(volumeCell);
                        
                        tbody.appendChild(row);
                        previousPrices[item.symbol] = item.price;
                    });
                })
                .catch(error => console.error('Error:', error));
        }
        
        // 页面加载完成后立即更新一次
        document.addEventListener('DOMContentLoaded', updateData);
        
        // 每秒更新一次数据
        setInterval(updateData, 1000);
    </script>
</head>
<body>
    <div class="container">
        <div class="update-time">更新时间：</div>
        <table>
            <thead>
                <tr>
                    <th>币种名称</th>
                    <th>最新价格</th>
                    <th>1分/5分/15分/1时/4时/1天涨跌%</th>
                    <th>24H交易量</th>
                </tr>
            </thead>
            <tbody>
            </tbody>
        </table>
    </div>
</body>
</html>
"""

def format_volume(volume: float) -> str:
    """格式化交易量显示"""
    if volume >= 1_000_000_000:  # 十亿
        return f"{volume/1_000_000_000:.2f}B"
    elif volume >= 1_000_000:  # 百万
        return f"{volume/1_000_000:.2f}M"
    elif volume >= 1_000:  # 千
        return f"{volume/1_000:.2f}K"
    else:
        return f"{volume:.2f}"

def format_percentage(percentage: float) -> str:
    """格式化百分比显示"""
    if percentage > 0:
        return f'<span style="color: {HTML_GREEN}">↑{percentage:.2f}%</span>'
    elif percentage < 0:
        return f'<span style="color: {HTML_RED}">↓{abs(percentage):.2f}%</span>'
    else:
        return f'<span>0.00%</span>'

def get_price_data() -> List[Dict[str, Any]]:
    """获取价格数据"""
    try:
        exchange = ccxt.binance()
        symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'SOL/USDT',
                  'ADA/USDT', 'AVAX/USDT', 'DOGE/USDT', 'DOT/USDT', 'LINK/USDT']
        results = []

        for symbol in symbols:
            try:
                # 获取OHLCV数据
                timeframes = {
                    '1m': 1,
                    '5m': 5,
                    '15m': 15,
                    '1h': 60,
                    '4h': 240,
                    '1d': 1440
                }
                
                percentages = []
                for timeframe in timeframes.keys():
                    try:
                        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=2)
                        if len(ohlcv) >= 2:
                            open_price = ohlcv[-2][1]  # 使用前一个周期的开盘价
                            close_price = ohlcv[-1][4]  # 使用当前周期的收盘价
                            percentage = ((close_price - open_price) / open_price) * 100
                            percentages.append(format_percentage(percentage))
                        else:
                            percentages.append(format_percentage(0))
                    except Exception as e:
                        logger.error(f"Error fetching {timeframe} data for {symbol}: {str(e)}")
                        percentages.append(format_percentage(0))

                # 获取24小时交易量
                ticker = exchange.fetch_ticker(symbol)
                volume = ticker['quoteVolume'] if 'quoteVolume' in ticker else 0

                results.append({
                    'symbol': symbol.replace('/USDT', ''),
                    'price': f"{ticker['last']:.2f}",
                    'percentages': ' '.join(percentages),
                    'volume': format_volume(volume)
                })

            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                continue

        return results

    except Exception as e:
        logger.error(f"Error in get_price_data: {str(e)}")
        return []

def update_prices():
    """更新价格数据的线程函数"""
    while True:
        try:
            prices = get_price_data()
            shared_data['prices'] = prices
            shared_data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.error(f"Error updating prices: {str(e)}")
        time.sleep(5)  # 每5秒更新一次

@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE, update_time=shared_data['update_time'], prices=shared_data['prices'])

@app.route('/api/prices')
def get_prices():
    return jsonify(shared_data)

if __name__ == "__main__":
    # 启动价格更新线程
    price_thread = threading.Thread(target=update_prices, daemon=True)
    price_thread.start()
    
    # 启动ETH地址监控线程
    start_eth_monitor()
    
    # 启动Flask服务器
    app.run(host='0.0.0.0', port=8080, debug=False)
