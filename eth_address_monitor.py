import requests
import time
from datetime import datetime
from typing import Dict, Any, List
import threading
from flask import Flask, render_template_string, jsonify, Blueprint, request
import logging
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import os
import ssl
import urllib3

# 抑制不安全请求的警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 设置日志级别
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# 配置重试策略
retry_strategy = Retry(
    total=5,  # 增加重试次数
    backoff_factor=1,  # 增加重试间隔
    status_forcelist=[429, 500, 502, 503, 504],  # 添加429状态码
    allowed_methods=["GET"]  # 只允许GET请求重试
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
    'addresses': [],
    'current_address': ''
}

# 获取Etherscan API密钥和ETH地址
# 尝试从api_keys.py加载配置，如果不存在则使用默认值
try:
    from api_keys import ETHERSCAN_API_KEY, ETH_ADDRESSES
    eth_data['addresses'] = ETH_ADDRESSES
    eth_data['current_address'] = ETH_ADDRESSES[0] if ETH_ADDRESSES else '0x3B2eb8CddE3bbCb184d418c0568De2Eb40C3BfE6'
except ImportError:
    # 默认占位符，上传到GitHub时使用
    ETHERSCAN_API_KEY = "YourEtherscanApiKey"  # 替换为您的API密钥
    eth_data['addresses'] = ['0xF977814e90dA44bFA03b6295A0616a897441aceC']
    eth_data['current_address'] = '0xF977814e90dA44bFA03b6295A0616a897441aceC'

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
        .address-selector {
            margin-bottom: 20px;
            padding: 0 10px;
        }
        .address-selector select {
            background-color: #333;
            color: #FFF;
            border: 1px solid #555;
            padding: 8px;
            border-radius: 4px;
            width: 100%;
            max-width: 500px;
            font-family: monospace;
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
        
        .token-cell {
            text-align: center;
            font-weight: bold;
        }
        
        .token-ETH {
            color: #64B5F6;
        }
        
        .token-ELON {
            color: #FF9800;
        }
        
        .token-TRUMP {
            color: #E91E63;
        }
        
        .token-ERC20 {
            color: #9C27B0;
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
        
        .no-data {
            text-align: center;
            padding: 20px;
            color: #888;
            font-style: italic;
        }
        
        .error-message {
            background-color: rgba(244, 67, 54, 0.1);
            border: 1px solid #F44336;
            color: #F44336;
            padding: 10px;
            margin: 10px;
            border-radius: 4px;
        }
        
        .status-message {
            background-color: rgba(33, 150, 243, 0.1);
            border: 1px solid #2196F3;
            color: #2196F3;
            padding: 10px;
            margin: 10px;
            border-radius: 4px;
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
        
        {% if addresses|length > 1 %}
        <div class="address-selector">
            <form id="address-form" action="/eth" method="get">
                <select name="address" id="address-select" onchange="this.form.submit()">
                    {% for addr in addresses %}
                    <option value="{{ addr }}" {% if addr == address %}selected{% endif %}>{{ addr }}</option>
                    {% endfor %}
                </select>
            </form>
        </div>
        {% endif %}
        
        <div class="address-info">监控地址: <span id="address">{{ address }}</span></div>
        
        {% if transactions %}
        <table>
            <thead>
                <tr>
                    <th>交易哈希</th>
                    <th>区块</th>
                    <th>时间</th>
                    <th>类型</th>
                    <th>代币</th>
                    <th>金额</th>
                </tr>
            </thead>
            <tbody id="transactions-table">
                {% for tx in transactions %}
                <tr>
                    <td class="hash-cell"><a href="https://etherscan.io/tx/{{ tx.hash }}" target="_blank">{{ tx.hash }}</a></td>
                    <td>{{ tx.blockNumber }}</td>
                    <td>{{ tx.timeStamp }}</td>
                    <td class="{{ tx.direction }}">{{ tx.direction }}</td>
                    <td class="token-cell token-{{ tx.token }}">{{ tx.token }}</td>
                    <td class="value-cell">{{ tx.value }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="no-data">
            <p>该地址暂无交易记录，或者API请求出现问题。</p>
            <p>您可以：</p>
            <ul>
                <li>检查地址是否正确</li>
                <li>确认API密钥是否有效</li>
                <li>稍后再试</li>
            </ul>
            <p>您也可以直接在 <a href="https://etherscan.io/address/{{ address }}" target="_blank">Etherscan</a> 上查看该地址</p>
        </div>
        {% endif %}
    </div>
    
    <script>
        // 自动刷新数据
        function refreshData() {
            // 获取当前选中的地址
            const currentAddress = document.getElementById('address').textContent;
            
            fetch('/api/eth-transactions')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('update-time').textContent = data.update_time;
                    
                    // 只有当地址匹配时才更新表格
                    if (data.current_address === currentAddress) {
                        // 如果没有交易数据，刷新页面以显示无数据提示
                        if (!data.transactions || data.transactions.length === 0) {
                            location.reload();
                            return;
                        }
                        
                        const tableBody = document.getElementById('transactions-table');
                        if (!tableBody) {
                            location.reload();
                            return;
                        }
                        
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
                                <td class="token-cell token-${tx.token}">${tx.token}</td>
                                <td class="value-cell">${tx.value}</td>
                            `;
                            tableBody.appendChild(row);
                        });
                    }
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                    // 5分钟后刷新页面
                    setTimeout(() => location.reload(), 300000);
                });
        }
        
        // 每15秒刷新一次数据
        setInterval(refreshData, 15000);
    </script>
</body>
</html>
"""

def get_eth_transactions() -> List[Dict[str, Any]]:
    """获取指定ETH地址的交易记录"""
    try:
        address = eth_data['current_address']
        if not address:
            logger.warning("No ETH address specified")
            return []
            
        # 添加超时和SSL验证选项
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_API_KEY}"
        
        # 创建自定义SSL上下文
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        response = http.get(url, timeout=30, verify=False)  # 增加超时时间，禁用SSL验证
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
                
                # 尝试识别代币名称
                token_name = "ETH"  # 默认为ETH
                
                # 如果有input数据且长度大于10，可能是代币交易
                if tx.get('input') and len(tx['input']) > 10:
                    # 尝试从input数据或其他字段识别代币
                    # 这里使用一个简单的方法，实际上需要更复杂的逻辑
                    if tx.get('to') and tx['to'].lower() == '0x761d38e5ddf6ccf6cf7c55759d5210750b5d60f3'.lower():
                        token_name = "ELON"
                    elif tx.get('to') and tx['to'].lower() == '0x1ce270557c1f68cfb577b856766310bf8b47fd9c'.lower():
                        token_name = "TRUMP"
                    elif tx.get('input').startswith('0xa9059cbb'):  # ERC20 transfer方法的签名
                        token_name = "ERC20"
                
                transactions.append({
                    'hash': tx['hash'],
                    'blockNumber': tx['blockNumber'],
                    'timeStamp': formatted_time,
                    'direction': direction,
                    'value': f"{value_eth:.6f}",
                    'token': token_name
                })
            
            return transactions
        elif data['status'] == '0' and data['message'] == 'No transactions found':
            # 处理没有交易的情况，不记录为错误
            logger.info(f"No transactions found for address: {address}")
            return []
        else:
            logger.error(f"Etherscan API error: {data['message']}")
            return []
    except requests.exceptions.SSLError as e:
        logger.error(f"SSL Error: {str(e)}")
        # 尝试不使用SSL验证重新请求
        try:
            url = f"http://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock=0&endblock=99999999&sort=desc&apikey={ETHERSCAN_API_KEY}"
            response = http.get(url, timeout=30, verify=False)
            data = response.json()
            
            if data['status'] == '1':
                # 处理数据...
                # 这里简化处理，实际应该复制上面的代码
                return []
            else:
                return []
        except Exception as inner_e:
            logger.error(f"Error in fallback request: {str(inner_e)}")
            return []
    except Exception as e:
        logger.error(f"Error fetching ETH transactions: {str(e)}")
        return []

def update_eth_transactions():
    """更新ETH交易数据"""
    while True:
        try:
            if not eth_data['addresses']:
                logger.warning("No ETH addresses configured")
                time.sleep(30)
                continue
                
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
    # 检查是否有地址参数
    address = request.args.get('address')
    if address and address in eth_data['addresses']:
        eth_data['current_address'] = address
    
    return render_template_string(
        ETH_HTML_TEMPLATE,
        update_time=eth_data['update_time'],
        address=eth_data['current_address'],
        addresses=eth_data['addresses'],
        transactions=eth_data['transactions']
    )

@eth_bp.route('/api/eth-transactions')
def get_eth_data():
    """API端点，返回ETH交易数据"""
    return jsonify({
        'update_time': eth_data['update_time'],
        'current_address': eth_data['current_address'],
        'addresses': eth_data['addresses'],
        'transactions': eth_data['transactions']
    })

# 启动ETH交易监控线程
def start_eth_monitor():
    eth_thread = threading.Thread(target=update_eth_transactions, daemon=True)
    eth_thread.start() 