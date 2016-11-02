# 2016.10.21 16:41:38 CST
#Embedded file name: com/fangcloud/httpconnection/statistic/HttpStatisticManager.pyc
"""
Created on 2015-6-1

@author: renjun
"""
import threading
from com.fangcloud.httpconnection.statistic.HttpStatisticWatcher import HttpStatisticWatcher
from com.fangcloud.logging.LoggerFactory import LoggerFactory
from com.fangcloud.utils.Utils import Singleton

class HttpStatisticThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self, name='HttpStatisticThread')
        self.logger = LoggerFactory().getLoggerInstance()

    def run(self):
        HttpStatisticWatcher().startWatcherLoop()


class HttpStatisticManager(Singleton):
    StaticLock = threading.RLock()

    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = LoggerFactory().getLoggerInstance()

    def startWatcher(self):
        if not hasattr(self, 'httpStatisticThread') or self.httpStatisticThread is None or not self.httpStatisticThread.is_alive():
            try:
                HttpStatisticManager.StaticLock.acquire()
                if not hasattr(self, 'httpStatisticThread') or self.httpStatisticThread is None or not self.httpStatisticThread.is_alive():
                    self.httpStatisticThread = HttpStatisticThread()
                    self.httpStatisticThread.setDaemon(True)
                    self.httpStatisticThread.start()
            finally:
                HttpStatisticManager.StaticLock.release()

        self.logger.debug('[Resource Watcher] file watcher process started')
+++ okay decompyling HttpStatisticManager.pyc 
# decompiled 1 files: 1 okay, 0 failed, 0 verify failed
# 2016.10.21 16:41:38 CST
