import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
from binance_btc_price import app, update_prices
from eth_address_monitor import update_eth_transactions
import threading
import logging

class CryptoPriceService(win32serviceutil.ServiceFramework):
    _svc_name_ = "CryptoPriceService"
    _svc_display_name_ = "Crypto Price Monitor Service"
    _svc_description_ = "显示加密货币实时价格的服务"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.running = True

    def SvcStop(self):
        """停止服务"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        """运行服务"""
        try:
            # 设置日志
            logging.basicConfig(
                filename='c:\\crypto_price_service.log',
                level=logging.ERROR,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            logger = logging.getLogger(__name__)

            # 启动Flask服务器
            flask_thread = threading.Thread(
                target=lambda: app.run(host='0.0.0.0', port=6000, debug=False),
                daemon=True
            )
            flask_thread.start()

            # 启动价格更新线程
            price_thread = threading.Thread(
                target=update_prices,
                daemon=True
            )
            price_thread.start()
            
            # 启动ETH地址监控线程
            eth_thread = threading.Thread(
                target=update_eth_transactions,
                daemon=True
            )
            eth_thread.start()

            # 保持服务运行
            while self.running:
                rc = win32event.WaitForSingleObject(self.stop_event, 1000)
                if rc == win32event.WAIT_OBJECT_0:
                    break

        except Exception as e:
            logger.error(f"Service error: {str(e)}")
            self.running = False

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(CryptoPriceService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(CryptoPriceService)