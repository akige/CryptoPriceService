@echo off
echo 安装加密货币价格监控服务

REM 检查是否以管理员权限运行
net session >nul 2>&1
if %errorLevel% == 0 (
    echo 正在以管理员权限运行...
) else (
    echo 请以管理员权限运行此脚本！
    pause
    exit /b 1
)

REM 安装必要的Python包
echo 安装必要的包...
pip install pywin32 flask ccxt flask-cors requests

REM 停止服务（如果已存在）
echo 停止现有服务（如果存在）...
python crypto_price_service.py stop

REM 移除服务（如果已存在）
echo 移除现有服务（如果存在）...
python crypto_price_service.py remove

REM 安装服务
echo 安装服务...
python crypto_price_service.py install

REM 启动服务
echo 启动服务...
python crypto_price_service.py start

echo.
echo 服务安装完成！
echo 服务已经安装并启动。
echo 您可以在服务管理器中查看"Crypto Price Monitor Service"服务。
echo.
pause