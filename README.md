# CryptoPriceService

一个基于 Python 的加密货币价格监控 Windows 服务。实时显示比特币等加密货币的价格、涨跌幅和交易量，支持系统启动自动运行。

## 功能特点

- 实时监控多个加密货币的价格
- 显示24小时的价格涨跌幅
- 显示24小时交易量
- 作为 Windows 服务运行，支持开机自启
- 优化的 iPad mini 7 显示支持
- 自动数据刷新(涨跌闪烁效果)
- 日志记录功能

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
- install_service.bat（安装脚本）
- uninstall_service.bat（卸载脚本）

3. 以管理员权限运行 install_service.bat 安装服务

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

1. 服务启动后，打开浏览器访问：http://localhost:5000
2. 页面会自动显示并更新加密货币的价格信息
3. 服务日志位于：C:\crypto_price_service.log

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
   - 检查端口 5000 是否被其他程序占用
   - 检查防火墙设置

## 贡献

欢迎提交 Issues 和 Pull Requests 来改进这个项目。

## 许可证

MIT License