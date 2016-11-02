# 2016.10.21 16:41:56 CST
#Embedded file name: com/fangcloud/httpconnection/statistic/HttpStatisticWatcher.pyc
"""
Created on 2015-6-1

@author: renjun
"""
from time import sleep
from com.fangcloud.httpconnection.statistic.HttpStatistic import HttpStatistic
from com.fangcloud.logging.LoggerFactory import LoggerFactory
from com.fangcloud.utils.Utils import Singleton

class HttpStatisticWatcher(Singleton):
    UploadSpeed = 0
    DownloadSpeed = 0

    def __init__(self):
        if not hasattr(self, 'logger'):
            self.logger = LoggerFactory().getLoggerInstance()

    def startWatcherLoop(self):
        self.logger.info('[Resource Watcher] start http statistic watcher loop...')
        while True:
            try:
                HttpStatisticWatcher.UploadSpeed, HttpStatisticWatcher.DownloadSpeed = HttpStatistic.GetSmoothSpeed()
                sleep(1)
            except Exception as exception:
                self.logger.error(exception, exc_info=1)
+++ okay decompyling HttpStatisticWatcher.pyc 
# decompiled 1 files: 1 okay, 0 failed, 0 verify failed
# 2016.10.21 16:41:56 CST
