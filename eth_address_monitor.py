import requests
import time
from datetime import datetime
from typing import Dict, Any, List
import threading
from flask import Flask, render_template_string, jsonify, Blueprint
import logging
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os

# 设置日志级别
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# 配置重试策略
retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("http://", adapter)
http.mount("https://", adapter)

# 创建Blueprint
eth_bp = Blueprint('eth_monitor', __name__)

# 共享数据存储
eth_data = {
    'update_time': '',
    'transactions': [],
    'address': '0x3B2eb8CddE3bbCb184d418c0568De2Eb40C3BfE6'
}

# 获取Etherscan API密钥
# 尝试从api_keys.py加载API密钥，如果不存在则使用默认值
try:
    from api_keys import ETHERSCAN_API_KEY
except ImportError:
    # 默认占位符，上传到GitHub时使用
    ETHERSCAN_API_KEY = "YourEtherscanApiKey"  # 替换为您的API密钥

# HTML模板
ETH_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>ETH地址交易监控</title>
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
        .address-info {
            margin-bottom: 15px;
            font-size: 16px;
            color: #4CAF50;
            padding: 0 10px;
            word-break: break-all;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            white-space: nowrap;
            font-size: 16px;
            margin: 0 auto;
            table-layout: fixed;
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
        }
        tr:nth-child(even) {
            background-color: #2A2A2A;
        }
        .hash-cell {
            max-width: 120px;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .in {
            color: #4CAF50;
        }
        .out {
            color: #F44336;
        }
        
        @keyframes flash-new {
            0% { background-color: transparent; }
            50% { background-color: rgba(76, 175, 80, 0.3); }
            100% { background-color: transparent; }
        }
        
        .flash-new {
            animation: flash-new 1s ease-out;
        }
        
        .value-cell {
            text-align: right;
        }
        
        a {
            color: #64B5F6;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        /* 移动设备优化 */
        @media screen and (max-width: 768px) {
            table {
                font-size: 14px;
            }
            th, td {
                padding: 6px 4px;
            }
            .hash-cell {
                max-width: 80px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="update-time">最后更新: <span id="update-time">{{ update_time }}</span></div>
        <div class="address-info">监控地址: <span id="address">{{ address }}</span></div>
        <table>
            <thead>
                <tr>
                    <th>交易哈希</th>
                    <th>区块</th>
                    <th>时间</th>
                    <th>类型</th>
                    <th>金额 (ETH)</th>
                </tr>
            </thead>
            <tbody id="transactions-table">
                {% for tx in transactions %}
                <tr>
                    <td class="hash-cell"><a href="https://etherscan.io/tx/{{ tx.hash }}" target="_blank">{{ tx.hash }}</a></td>
                    <td>{{ tx.blockNumber }}</td>
                    <td>{{ tx.timeStamp }}</td>
                    <td class="{{ tx.direction }}">{{ tx.direction }}</td>
                    <td class="value-cell">{{ tx.value }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <script>
        // 自动刷新数据
        function refreshData() {
            fetch('/api/eth-transactions')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('update-time').textContent = data.update_time;
                    document.getElementById('address').textContent = data.address;
                    
                    const tableBody = document.getElementById('transactions-table');
                    const oldHashes = Array.from(tableBody.querySelectorAll('tr')).map(row => 
                        row.querySelector('td:first-child a').textContent
                    );
                    
                    // 清空表格
                    tableBody.innerHTML = '';
                    
                    // 添加新数据
                    data.transactions.forEach(tx => {
                        const row = document.createElement('tr');
                        
                        // 检查是否是新交易
                        if (!oldHashes.includes(tx.hash)) {
                            row.classList.add('flash-new');
                        }
                        
                        row.innerHTML = `
                            <td class="hash-cell"><a href="https://etherscan.io/tx/${tx.hash}" target="_blank">${tx.hash}</a></td>
                            <td>${tx.blockNumber}</td>
                            <td>${tx.timeStamp}</td>
                            <td class="${tx.direction}">${tx.direction}</td>
                            <td class="value-cell">${tx.value}</td>
                        `;
                        tableBody.appendChild(row);
                    });
                })
                .catch(error => console.error('Error fetching data:', error));
        }
        
        // 每30秒刷新一次数据
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
"""

def get_eth_transactions() -> List[Dict[str, Any]]:
    """获取指定ETH地址的交易记录"""
    try:
        address = eth_data['address']
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_API_KEY}"
        
        response = http.get(url, timeout=10)
        data = response.json()
        
        if data['status'] == '1':
            transactions = []
            # 只获取最近的5条交易
            for tx in data['result'][:5]:
                # 将Wei转换为ETH (1 ETH = 10^18 Wei)
                value_eth = float(tx['value']) / 10**18
                
                # 确定交易方向
                if tx['from'].lower() == address.lower():
                    direction = 'out'
                else:
                    direction = 'in'
                
                # 转换时间戳为可读格式
                timestamp = datetime.fromtimestamp(int(tx['timeStamp']))
                formatted_time = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                
                transactions.append({
                    'hash': tx['hash'],
                    'blockNumber': tx['blockNumber'],
                    'timeStamp': formatted_time,
                    'direction': direction,
                    'value': f"{value_eth:.6f}"
                })
            
            return transactions
        else:
            logger.error(f"Etherscan API error: {data['message']}")
            return []
    except Exception as e:
        logger.error(f"Error fetching ETH transactions: {str(e)}")
        return []

def update_eth_transactions():
    """更新ETH交易数据"""
    while True:
        try:
            transactions = get_eth_transactions()
            eth_data['transactions'] = transactions
            eth_data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.error(f"Error updating ETH transactions: {str(e)}")
        
        # 每30秒更新一次
        time.sleep(30)

@eth_bp.route('/eth')
def eth_index():
    """ETH交易监控页面"""
    return render_template_string(
        ETH_HTML_TEMPLATE,
        update_time=eth_data['update_time'],
        address=eth_data['address'],
        transactions=eth_data['transactions']
    )

@eth_bp.route('/api/eth-transactions')
def get_eth_data():
    """API端点，返回ETH交易数据"""
    return jsonify(eth_data)

# 启动ETH交易监控线程
def start_eth_monitor():
    eth_thread = threading.Thread(target=update_eth_transactions, daemon=True)
    eth_thread.start() 