# CryptoPriceService

一个基于Python的加密货币价格监控Windows服务。
实时显示比特币等加密货币的价格、涨跌幅和交易量，支持系统启动自动运行。同时提供以太坊地址交易监控功能。

## 功能特点

- 实时监控多个加密货币的价格
- 轻量化，适合第二屏监控价格
- 显示24小时的价格涨跌幅
- 显示24小时交易量
- 作为 Windows 服务运行，支持开机自启
- 优化的 iPad mini 7 显示支持
- 自动数据刷新(涨跌闪烁效果)
- 日志记录功能
- **新功能：实时监控指定ETH地址的链上交易**
- **新功能：支持监控多个ETH地址，可随时切换查看**

## 系统要求

- Windows 10/11
- Python 3.8+
- 必需的 Python 包：
  - pywin32
  - flask
  - ccxt
  - flask-cors
  - requests

## 安装说明

1. 安装必需的 Python 包：
```bash
pip install pywin32 flask ccxt flask-cors requests
```

2. 将以下文件放在同一目录下：
- binance_btc_price.py（主程序）
- crypto_price_service.py（服务程序）
- eth_address_monitor.py（ETH地址监控程序）
- install_service.bat（安装脚本）
- uninstall_service.bat（卸载脚本）

3. **配置API密钥和ETH地址：** 创建 api_keys.py 文件，内容如下：
   ```python
   # Etherscan API密钥
   ETHERSCAN_API_KEY = "您的API密钥"
   
   # 要监控的ETH地址列表
   ETH_ADDRESSES = [
       "0x3B2eb8CddE3bbCb184d418c0568De2Eb40C3BfE6",  # 主要监控地址
       # 可以添加更多地址，例如：
       # "0x123456789abcdef123456789abcdef123456789a",
       # "0xabcdef123456789abcdef123456789abcdef1234",
   ]
   ```
   - 您可以在 https://etherscan.io/myapikey 免费注册获取API密钥
   - 您可以添加多个ETH地址进行监控，程序会提供地址切换功能

4. 以管理员权限运行 install_service.bat 安装服务

## 服务管理

### 启动服务
1. 打开 Windows 服务管理器（services.msc）
2. 找到 "CryptoPriceService"
3. 点击 "启动" 按钮

### 停止服务
1. 在服务管理器中找到 "CryptoPriceService"
2. 点击 "停止" 按钮

### 设置自动启动
1. 在服务管理器中双击 "CryptoPriceService"
2. 将 "启动类型" 设置为 "自动"
3. 点击 "确定" 保存设置

## 使用说明

1. 服务启动后，打开浏览器访问：http://localhost:6000
2. 页面会自动显示并更新加密货币的价格信息
3. 服务日志位于：C:\crypto_price_service.log
4. **ETH地址监控：** 
   - 访问 http://localhost:6000/eth 查看ETH地址的最近5条交易
   - 如果配置了多个ETH地址，可以通过页面上的下拉菜单切换不同的地址

## 卸载说明

1. 以管理员权限运行 uninstall_service.bat
2. 删除程序相关文件

## 常见问题

1. 服务无法启动
   - 检查 Python 环境是否正确安装
   - 确认所有必需的包都已安装
   - 查看日志文件了解详细错误信息

2. 页面无法访问
   - 确认服务是否正在运行
   - 检查端口 6000 是否被其他程序占用
   - 检查防火墙设置

3. ETH交易监控不显示数据
   - 确认您已经设置了有效的 Etherscan API 密钥
   - 检查监控的地址是否有交易记录
   - 查看日志文件了解详细错误信息

## 贡献

欢迎提交 Issues 和 Pull Requests 来改进这个项目。

## 许可证

MIT License