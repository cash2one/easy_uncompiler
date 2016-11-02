# 2016.10.21 16:41:17 CST
#Embedded file name: com/fangcloud/httpconnection/statistic/HttpStatistic.pyc
"""
Created on 2015-1-20

@author: renjun
"""
import datetime
import threading
from time import sleep
from com.fangcloud.logging.LoggerFactory import LoggerFactory
from com.fangcloud.system.SyncConfiguration import SyncConfiguration
from com.fangcloud.utils.Utils import SpeedLimitMode
HTTP_STATISTIC_UPLOAD_LOCK = threading.RLock()
HTTP_STATISTIC_DOWNLOAD_LOCK = threading.RLock()
HTTP_STATISTIC_LAN_DOWNLOAD_LOCK = threading.RLock()

class HttpStatistic(object):
    Logger = LoggerFactory().getLoggerInstance()
    UploadByte = 0
    DownloadByte = 0
    LanDownloadByte = 0
    CalculateTime = None
    TotalUploadedByte = {}
    TotalDownloadedByte = {}
    SmoothWindowSize = 20
    SmoothUploadSpeed = []
    SmoothDownloadSpeed = []
    SmoothIndex = 0
    SmoothIgnore = 0
    SmoothResetCount = 0

    @staticmethod
    def AddUploadByte(path, byte):
        try:
            HTTP_STATISTIC_UPLOAD_LOCK.acquire()
            HttpStatistic.UploadByte += byte
            if not HttpStatistic.TotalUploadedByte.has_key(path):
                HttpStatistic.TotalUploadedByte[path] = 0
            HttpStatistic.TotalUploadedByte[path] += byte
            if SyncConfiguration.SyncSpeedLimitMode == SpeedLimitMode.Customer and HttpStatistic.UploadByte > SyncConfiguration.SyncSpeedLimitUpload:
                sleep(0.5)
        finally:
            HTTP_STATISTIC_UPLOAD_LOCK.release()

    @staticmethod
    def AddUploadByteSkipSpeed(path, byte):
        try:
            HTTP_STATISTIC_UPLOAD_LOCK.acquire()
            if not HttpStatistic.TotalUploadedByte.has_key(path):
                HttpStatistic.TotalUploadedByte[path] = 0
            HttpStatistic.TotalUploadedByte[path] += byte
        finally:
            HTTP_STATISTIC_UPLOAD_LOCK.release()

    @staticmethod
    def AddDownloadByte(path, byte):
        try:
            HTTP_STATISTIC_DOWNLOAD_LOCK.acquire()
            HttpStatistic.DownloadByte += byte
            if SyncConfiguration.SyncSpeedLimitMode == SpeedLimitMode.Customer and HttpStatistic.DownloadByte > SyncConfiguration.SyncSpeedLimitDownload:
                sleep(1)
        finally:
            HTTP_STATISTIC_DOWNLOAD_LOCK.release()

    @staticmethod
    def AddLanDownloadByte(path, byte):
        try:
            HTTP_STATISTIC_LAN_DOWNLOAD_LOCK.acquire()
            HttpStatistic.LanDownloadByte += byte
        finally:
            HTTP_STATISTIC_LAN_DOWNLOAD_LOCK.release()

    @staticmethod
    def FinishedUploadByte(path):
        try:
            HTTP_STATISTIC_UPLOAD_LOCK.acquire()
            if HttpStatistic.TotalUploadedByte.has_key(path):
                del HttpStatistic.TotalUploadedByte[path]
        finally:
            HTTP_STATISTIC_UPLOAD_LOCK.release()

    @staticmethod
    def GetNetSpeed():
        if HttpStatistic.CalculateTime is None:
            HttpStatistic.CalculateTime = datetime.datetime.now()
            return (0, 0)
        deltatime = datetime.datetime.now() - HttpStatistic.CalculateTime
        interval = deltatime.seconds + deltatime.microseconds / 1000000.0
        if interval > 0:
            uploadSpeed = HttpStatistic.UploadByte / 1024.0 / interval
            downloadSpeed = HttpStatistic.DownloadByte / 1024.0 / interval
            lanDownloadSpeed = HttpStatistic.LanDownloadByte / 1024.0 / interval
            HttpStatistic.CalculateTime = datetime.datetime.now()
            HttpStatistic.UploadByte = 0
            HttpStatistic.DownloadByte = 0
            HttpStatistic.LanDownloadByte = 0
            return (uploadSpeed, downloadSpeed + lanDownloadSpeed)
        else:
            return (0, 0)

    @staticmethod
    def GetSmoothSpeed():
        smoothUploadSpeed, smoothDownloadSpeed = (0, 0)
        uploadSpeed, downloadSpeed = HttpStatistic.GetNetSpeed()
        if uploadSpeed == 0 and downloadSpeed == 0:
            HttpStatistic.SmoothResetCount += 1
        HttpStatistic.SmoothUploadSpeed[HttpStatistic.SmoothIndex % HttpStatistic.SmoothWindowSize] = uploadSpeed
        HttpStatistic.SmoothDownloadSpeed[HttpStatistic.SmoothIndex % HttpStatistic.SmoothWindowSize] = downloadSpeed
        count = 1
        for i in range(0, HttpStatistic.SmoothWindowSize):
            if HttpStatistic.SmoothUploadSpeed[i] != HttpStatistic.SmoothIgnore or HttpStatistic.SmoothDownloadSpeed[i] != HttpStatistic.SmoothIgnore:
                smoothUploadSpeed += HttpStatistic.SmoothUploadSpeed[i]
                smoothDownloadSpeed += HttpStatistic.SmoothDownloadSpeed[i]
                count += 1

        HttpStatistic.SmoothIndex += 1
        return (smoothUploadSpeed / count, smoothDownloadSpeed / count)

    @staticmethod
    def ResetSmoothSpeed():
        HttpStatistic.SmoothDownloadSpeed = []
        HttpStatistic.SmoothUploadSpeed = []
        for i in range(0, HttpStatistic.SmoothWindowSize):
            HttpStatistic.SmoothDownloadSpeed.append(HttpStatistic.SmoothIgnore)
            HttpStatistic.SmoothUploadSpeed.append(HttpStatistic.SmoothIgnore)


HttpStatistic.ResetSmoothSpeed()
+++ okay decompyling HttpStatistic.pyc 
# decompiled 1 files: 1 okay, 0 failed, 0 verify failed
# 2016.10.21 16:41:18 CST
