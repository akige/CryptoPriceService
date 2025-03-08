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
import urllib3
import asyncio
import concurrent.futures
import queue
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

# 优化Flask配置
app.config['JSON_SORT_KEYS'] = False  # 禁用JSON键排序，提高性能
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # 禁用JSON美化，减少数据大小
app.config['PROPAGATE_EXCEPTIONS'] = True  # 传播异常，便于调试

# 抑制不安全请求的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 共享数据存储
shared_data = {
    'update_time': '',
    'prices': [],
    'update_count': 0  # 更新计数器
}

# 设置Binance API限制
BINANCE_RATE_LIMIT = {
    'max_requests_per_second': 20,  # Binance允许的每秒最大请求数
    'max_requests_per_minute': 1200,  # Binance允许的每分钟最大请求数
    'update_interval': 0.05  # 每50毫秒更新一次，即每秒20次
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
        .update-info {
            margin-bottom: 10px;
            font-size: 16px;
            color: #888;
            padding: 0 10px;
            display: flex;
            justify-content: space-between;
        }
        .update-time {
            color: #64B5F6;
        }
        .update-count {
            color: #4CAF50;
        }
        .refresh-rate {
            color: #FF9800;
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
            50% { background-color: rgba(76, 175, 80, 0.6); }
            100% { background-color: transparent; }
        }
        
        @keyframes flash-red {
            0% { background-color: transparent; }
            50% { background-color: rgba(244, 67, 54, 0.6); }
            100% { background-color: transparent; }
        }
        
        .flash-green {
            animation: flash-green 0.3s ease-out;
        }
        
        .flash-red {
            animation: flash-red 0.3s ease-out;
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
        
        @supports (-webkit-overflow-scrolling: touch) {
            .container {
                -webkit-overflow-scrolling: touch;
                overflow-x: hidden;
                -webkit-overflow-style: -apple-system;
                width: 100%;
                max-width: 100vw;
                margin: 0;
                padding: 5px;
                -webkit-transform: translateZ(0);
            }
            
            table {
                transform: translateZ(0);
                backface-visibility: hidden;
            }
            
            .flash-green, .flash-red {
                -webkit-animation-duration: 1s;
                -webkit-animation-timing-function: ease-out;
                -webkit-animation-fill-mode: both;
            }
            
            /* iOS设备特定的滚动优化 */
            ::-webkit-scrollbar {
                -webkit-appearance: none;
                width: 3px;
                height: 3px;
            }
            
            ::-webkit-scrollbar-thumb {
                border-radius: 2px;
                background-color: rgba(255, 255, 255, .2);
            }
            
            /* iOS设备文字优化 */
            .price-cell {
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
            }
            
            /* 优化iOS设备上的性能 */
            * {
                -webkit-backface-visibility: hidden;
                -webkit-transform: translateZ(0);
            }
            
            body {
                overflow-x: hidden;
            }
        }
    </style>
    <script>
        let lastPrices = {};
        let flashTimeouts = {};
        let lastUpdateTime = Date.now();
        let updateCount = 0;
        
        function extractPrice(html) {
            const text = html.replace(/<[^>]*>/g, '').trim();
            const number = text.match(/[\d.]+/);
            return number ? parseFloat(number[0]) : null;
        }
        
        function flashRow(tr, isUp) {
            const symbol = tr.getAttribute('data-symbol');
            
            // 清除之前的超时
            if (flashTimeouts[symbol]) {
                clearTimeout(flashTimeouts[symbol]);
                tr.classList.remove('flash-green', 'flash-red');
            }
            
            // 强制重绘
            void tr.offsetWidth;
            
            // 添加新的闪烁类
            const flashClass = isUp ? 'flash-green' : 'flash-red';
            tr.classList.add(flashClass);
            
            // 设置新的超时
            flashTimeouts[symbol] = setTimeout(() => {
                tr.classList.remove(flashClass);
                delete flashTimeouts[symbol];
            }, 300);
        }
        
        function updateData() {
            fetch('/api/prices')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('update-time').textContent = data.update_time;
                    document.getElementById('update-count').textContent = data.update_count;
                    document.getElementById('refresh-rate').textContent = data.updates_per_second + "/秒";
                    
                    const tbody = document.getElementById('price-tbody');
                    
                    data.prices.forEach(row => {
                        let tr = tbody.querySelector(`tr[data-symbol="${row.symbol}"]`);
                        if (!tr) {
                            tr = document.createElement('tr');
                            tr.setAttribute('data-symbol', row.symbol);
                            tbody.appendChild(tr);
                        }
                        
                        // 获取当前价格
                        const currentPrice = extractPrice(row.price_html);
                        const lastPrice = lastPrices[row.symbol];
                        
                        // 如果价格发生变化，添加闪烁效果
                        if (lastPrice !== undefined && currentPrice !== null && currentPrice !== lastPrice) {
                            flashRow(tr, currentPrice > lastPrice);
                        }
                        
                        // 更新行内容
                        tr.innerHTML = `
                            <td>${row.symbol}</td>
                            <td class="price-cell">${row.price_html}</td>
                            <td class="price-cell">${row.percentage_changes}</td>
                            <td class="price-cell">${row.volume}</td>
                        `;
                        
                        // 保存当前价格用于下次比较
                        if (currentPrice !== null) {
                            lastPrices[row.symbol] = currentPrice;
                        }
                    });
                    
                    // 计算前端更新频率
                    updateCount++;
                    const now = Date.now();
                    if (now - lastUpdateTime >= 1000) {
                        const fps = updateCount / ((now - lastUpdateTime) / 1000);
                        document.getElementById('client-refresh-rate').textContent = fps.toFixed(1) + "/秒";
                        updateCount = 0;
                        lastUpdateTime = now;
                    }
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        }

        // 每100毫秒更新一次数据，提高刷新频率
        setInterval(updateData, 100);
        
        // 立即执行一次更新
        updateData();
    </script>
</head>
<body>
    <div class="container">
        <div class="update-info">
            <div>更新时间: <span id="update-time" class="update-time">{{ update_time }}</span></div>
            <div>更新计数: <span id="update-count" class="update-count">{{ update_count }}</span></div>
            <div>服务器刷新率: <span id="refresh-rate" class="refresh-rate">0/秒</span></div>
            <div>客户端刷新率: <span id="client-refresh-rate" class="refresh-rate">0/秒</span></div>
        </div>
        <table>
            <thead>
                <tr>
                    <th>币种名称</th>
                    <th>最新价格</th>
                    <th>24H涨跌%</th>
                    <th>24H交易量</th>
                </tr>
            </thead>
            <tbody id="price-tbody">
            {% for row in prices %}
                <tr data-symbol="{{ row.symbol }}">
                    <td>{{ row.symbol }}</td>
                    <td class="price-cell">{{ row.price_html | safe }}</td>
                    <td class="price-cell">{{ row.percentage_changes | safe }}</td>
                    <td class="price-cell">{{ row.volume | safe }}</td>
                </tr>
            {% endfor %}
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
        exchange = ccxt.binance({
            'enableRateLimit': False,  # 禁用CCXT内置的速率限制，最大化速度
            'timeout': 1500  # 减少超时时间为1.5秒
        })
        
        symbols = [
            'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT',
            'XRP/USDT', 'BNB/USDT', 'SHIB/USDT', 'ADA/USDT',
            'XLM/USDT', 'TRX/USDT'
        ]
        results = []

        # 使用线程池并行获取数据
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            def fetch_symbol_data(symbol):
                try:
                    # 获取24小时行情数据
                    ticker = exchange.fetch_ticker(symbol)
                    
                    # 获取24小时涨跌幅
                    percentage = ticker['percentage'] if 'percentage' in ticker else 0
                    
                    # 获取24小时交易量
                    volume = ticker['quoteVolume'] if 'quoteVolume' in ticker else 0

                    price = ticker['last']
                    price_str = f"{price:.2f}"
                    
                    # 创建HTML格式的价格显示
                    price_html = f'<span style="color: {HTML_GREEN}">{price_str}</span>'
                    
                    # 创建百分比变化的HTML
                    percentage_changes = format_percentage(percentage)

                    return {
                        'symbol': symbol.replace('/USDT', ''),
                        'price': price_str,
                        'price_html': price_html,
                        'raw_price': price,  # 保存原始价格用于比较
                        'percentage': percentage,
                        'percentage_changes': percentage_changes,
                        'volume': format_volume(volume),
                        'timestamp': time.time()  # 添加时间戳
                    }
                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    return None

            # 并行执行所有请求
            futures = [executor.submit(fetch_symbol_data, symbol) for symbol in symbols]
            
            # 收集结果
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)

        return results

    except Exception as e:
        logger.error(f"Error in get_price_data: {str(e)}")
        return []

# 单独获取单个币种的价格
def get_single_price(symbol):
    try:
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'rateLimit': 50
        })
        
        ticker = exchange.fetch_ticker(symbol)
        
        return {
            'symbol': symbol.replace('/USDT', ''),
            'price': f"{ticker['last']:.2f}",
            'raw_price': ticker['last'],
            'timestamp': time.time()
        }
    except Exception as e:
        logger.error(f"Error getting single price for {symbol}: {str(e)}")
        return None

# 价格更新线程函数
def price_updater(symbol):
    """单独更新一个币种的价格"""
    while True:
        try:
            price_data = get_single_price(symbol)
            if price_data:
                shared_data['price_queue'].put(price_data)
        except Exception as e:
            logger.error(f"Error in price updater for {symbol}: {str(e)}")
        
        # 随机延迟50-150毫秒，避免所有请求同时发送
        time.sleep(0.05 + (hash(symbol) % 10) * 0.01)

def update_prices():
    """更新价格数据的线程函数"""
    last_update_time = time.time()
    updates_count = 0
    
    while True:
        try:
            # 获取价格数据
            prices = get_price_data()
            
            # 更新共享数据
            shared_data['prices'] = prices
            shared_data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            shared_data['update_count'] += 1
            
            # 计算更新频率
            current_time = time.time()
            time_diff = current_time - last_update_time
            if time_diff >= 1.0:  # 每秒计算一次
                updates_per_second = updates_count / time_diff
                shared_data['updates_per_second'] = f"{updates_per_second:.1f}"
                updates_count = 0
                last_update_time = current_time
            else:
                updates_count += 1
                
        except Exception as e:
            logger.error(f"Error updating prices: {str(e)}")
        
        # 最小化延迟以提高刷新速度
        time.sleep(0.01)  # 10毫秒延迟，每秒最多100次更新

@app.route('/')
def index():
    """主页"""
    return render_template_string(HTML_TEMPLATE, update_time=shared_data['update_time'], prices=shared_data['prices'], update_count=shared_data['update_count'])

@app.route('/api/prices')
def get_prices():
    """API端点，返回价格数据"""
    return jsonify({
        'update_time': shared_data['update_time'],
        'prices': shared_data['prices'],
        'update_count': shared_data['update_count'],
        'updates_per_second': shared_data.get('updates_per_second', '0.0')
    })

if __name__ == "__main__":
    # 启动价格更新线程
    price_thread = threading.Thread(target=update_prices, daemon=True)
    price_thread.start()
    
    # 启动ETH地址监控线程
    start_eth_monitor()
    
    # 启动Flask服务器
    app.run(host='0.0.0.0', port=8888, debug=False, threaded=True)
