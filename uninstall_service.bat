@echo off
echo 卸载加密货币价格监控服务

REM 检查是否以管理员权限运行
net session >nul 2>&1
if %errorLevel% == 0 (
    echo 正在以管理员权限运行...
) else (
    echo 请以管理员权限运行此脚本！
    pause
    exit /b 1
)

REM 停止服务
echo 停止服务...
python crypto_price_service.py stop

REM 移除服务
echo 移除服务...
python crypto_price_service.py remove

echo.
echo 服务已成功卸载！
echo.
pause