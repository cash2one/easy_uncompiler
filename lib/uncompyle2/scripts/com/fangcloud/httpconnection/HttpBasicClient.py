# 2016.10.21 16:38:39 CST
#Embedded file name: com/fangcloud/httpconnection/HttpBasicClient.pyc
import json
import os
from socks import ProxyConnectionError
import datetime
import requests
from requests.exceptions import ConnectionError, ReadTimeout
from requests_toolbelt import MultipartEncoderMonitor
from com.fangcloud.httpconnection.FangCloudUrls import FangCloudUrl
from com.fangcloud.httpconnection.HttpErrorMessage import HttpErrorMessage
from com.fangcloud.httpconnection.SyncingFileList import SyncingFileList
from com.fangcloud.httpconnection.statistic.HttpStatistic import HttpStatistic
from com.fangcloud.logging.LoggerFactory import LoggerFactory
from com.fangcloud.system.SyncConfiguration import SyncConfiguration
from com.fangcloud.utils import Utils
from com.fangcloud.utils.Exceptions import HttpQueryParameterError, UnAuthorizedException, RefreshTokenFailedException, StopSyncing, WebAPIException, EnterpriseExpired, OperationRetryInOneMinuteException, StopSyncingAndRestart, CheckSumExpiredException
from com.fangcloud.interface.SyncUiInterface import SyncUiInterface

class HttpTokenExitCode():
    DOWNLOAD_OK = 0
    DOWNLOAD_ACCESS_ERROR = 1
    DOWNLOAD_NET_ERROR = 2
    DOWNLOAD_TOKEN_EXPIRED = 3
    DOWNLOAD_RETRY_ERROR = 4


class StatusCode():
    Success = 200
    Created = 201
    Accepted = 202
    NoContent = 204
    PartialContent = 206
    Redirect = 302
    NotModified = 304
    BadRequest = 400
    UnAuthorized = 401
    Forbidden = 403
    NotFound = 404
    MethodNotAllowed = 405
    Conflict = 409
    TooManyRequests = 429
    InternalServerError = 500
    Unavailable = 503


def handleChunkFinish(monitor):
    if not SyncConfiguration.IsEnableSyncing or SyncConfiguration.IsFullSyncIniting:
        raise StopSyncing
    if monitor.filePath not in SyncingFileList.SyncingFileSet:
        raise StopSyncingAndRestart
    if not hasattr(monitor, 'last_read'):
        monitor.last_read = 0
    byte = monitor.bytes_read - monitor.last_read
    HttpStatistic.AddUploadByte(monitor.filePath, byte)
    monitor.last_read = monitor.bytes_read


class UploadInChunks(object):

    def __init__(self, filePath, tempPath, chunkSize, start, limit):
        self.filePath = filePath
        self.tempPath = tempPath
        self.chunkSize = chunkSize
        self.totalSize = limit
        self.start = start

    def __iter__(self):
        with open(self.tempPath, 'rb') as f:
            f.seek(self.start)
            readData = 0
            while True:
                if not SyncConfiguration.IsEnableSyncing or SyncConfiguration.IsFullSyncIniting:
                    raise StopSyncing
                if self.filePath not in SyncingFileList.SyncingFileSet:
                    raise StopSyncingAndRestart
                leftData = self.totalSize - readData
                if leftData > self.chunkSize:
                    data = f.read(self.chunkSize)
                    readData += self.chunkSize
                else:
                    data = f.read(leftData)
                    readData += leftData
                if not data:
                    break
                HttpStatistic.AddUploadByte(self.filePath, len(data))
                yield data

    def __len__(self):
        return self.totalSize


class IterableToFileAdapter(object):

    def __init__(self, iterable):
        self.iterator = iter(iterable)
        self.length = len(iterable)

    def read(self, size = 0):
        return next(self.iterator, '')

    def __len__(self):
        return self.length


class HttpBasicClient(object):
    UserAuthToken = None
    UserRefreshToken = None
    ExpireDate = None

    def __init__(self):
        self.logger = LoggerFactory().getLoggerInstance()

    def getHeaders(self, additional = None):
        if HttpBasicClient.UserAuthToken is not None:
            headers = {'Egeio-Client-Info': SyncConfiguration.ClientInfo,
             'Auth-Token': HttpBasicClient.UserAuthToken,
             'Device-Token': SyncConfiguration.DeviceToken,
             'X-Custom-Productid': '%s' % Utils.getSyncProductId()}
        else:
            headers = {'Egeio-Client-Info': SyncConfiguration.ClientInfo}
        if additional is not None:
            headers.update(additional)
        self.logger.debug('[HttpBasicClient] http header = %s', headers)
        return headers

    def getProxies(self):
        if SyncConfiguration.EnableProxy:
            return SyncConfiguration.ProxySetting
        else:
            return {}

    def handleFailedResponseStatus(self, url, status, content):
        result = False
        if status == StatusCode.BadRequest:
            self.logger.info('[HTTP] Response of ' + url + '. Receive bad request response')
            if url == FangCloudUrl.URL['RERRESH_AUTH_TOKEN']:
                raise RefreshTokenFailedException
            try:
                content = json.loads(content)
                if content['error'] == HttpErrorMessage.InvalidateLoginInfo:
                    result = False
                elif content['error'] == HttpErrorMessage.ErrorEnterpriseExpired:
                    raise EnterpriseExpired(content['message'])
                elif content['error'] in [HttpErrorMessage.AuthTokenExpired, HttpErrorMessage.CurrentVersionUnavailable]:
                    raise UnAuthorizedException
                elif content['error'] == HttpErrorMessage.UploadTokenExpired:
                    raise CheckSumExpiredException
                else:
                    content['success'] = False
                    result = content
            except (EnterpriseExpired, UnAuthorizedException, CheckSumExpiredException) as exception:
                raise exception
            except Exception:
                result = False

        elif status == StatusCode.UnAuthorized:
            self.logger.info('[HTTP] Response of ' + url + '. Receive unauthorized response')
            raise UnAuthorizedException
        else:
            self.logger.info('[HTTP] Response of ' + url + '. Receive status code = ' + str(status))
        return result

    def prepareParams(self, params):
        prepared = {}
        for name, value in params.iteritems():
            if value is True:
                value = 1
            elif value is False:
                value = 0
            prepared[name] = value

        return prepared

    def get(self, url, query = None, logData = True):
        """
        @return: False if failed, json structure if success
        """
        response = None
        httpSession = requests.Session()
        bConnectError = False
        try:
            if query is not None:
                query = self.prepareParams(query)
            self.logger.debug('[HTTP] GET Url: ' + url)
            while True:
                try:
                    if SyncConfiguration.EnableProxy:
                        response = httpSession.get(url, params=query, headers=self.getHeaders(), timeout=600, proxies=self.getProxies(), verify=False)
                    elif Utils.isMacOS():
                        response = httpSession.get(url, params=query, headers=self.getHeaders(), timeout=600, proxies=self.getProxies(), verify=Utils.getCertFile())
                    else:
                        response = httpSession.get(url, params=query, headers=self.getHeaders(), timeout=600, proxies=self.getProxies())
                    break
                except requests.exceptions.Timeout:
                    self.logger.warning('[HTTP] time out and try the request again')

            if logData:
                self.logger.debug('[HTTP] Response status [%s] and content: %s', str(response.status_code), response.content)
            else:
                self.logger.debug('[HTTP] Response status [%s]', str(response.status_code))
            if response.status_code == StatusCode.Success:
                responseJson = json.loads(response.content)
                if responseJson.get('success') == True:
                    return responseJson
                else:
                    return False
            else:
                return self.handleFailedResponseStatus(response.url, response.status_code, response.content)
        except (ProxyConnectionError, ConnectionError) as exception:
            bConnectError = True
            self.logger.error(exception, exc_info=1)
            raise exception
        except (UnAuthorizedException, RefreshTokenFailedException, HttpQueryParameterError) as exception:
            self.logger.error(exception, exc_info=1)
            raise exception
        except Exception as exception:
            if response is not None:
                self.logger.error('[HTTP] Error response content from server: %s', response.content)
            self.logger.error(exception, exc_info=1)
            raise WebAPIException
        finally:
            SyncUiInterface.SetNetworkAvailable(not bConnectError)
            httpSession.close()

    def getFileForUpdate(self, url, localPath, query = None):
        """
        @return: False if failed, json structure if success
        """
        response = None
        httpSession = requests.Session()
        try:
            if query is not None:
                query = self.prepareParams(query)
            self.logger.debug('[HTTP] GET Url: %s; file path: %s', url, localPath)
            if SyncConfiguration.EnableProxy:
                response = httpSession.get(url, params=query, headers=self.getHeaders(), stream=True, proxies=self.getProxies(), verify=False)
            elif Utils.isMacOS():
                response = httpSession.get(url, params=query, headers=self.getHeaders(), stream=True, proxies=self.getProxies(), verify=Utils.getCertFile())
            else:
                response = httpSession.get(url, params=query, headers=self.getHeaders(), stream=True, proxies=self.getProxies())
            self.logger.debug('[HTTP] Response status [%s]', str(response.status_code))
            if response.status_code == StatusCode.Success:
                with open(localPath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)

                return True
            return self.handleFailedResponseStatus(response.url, response.status_code, response.content)
        except IOError as exception:
            self.logger.error(exception, exc_info=1)
            raise exception
        except (UnAuthorizedException,
         RefreshTokenFailedException,
         HttpQueryParameterError,
         StopSyncing,
         ConnectionError) as exception:
            raise exception
        except Exception as exception:
            if response is not None:
                self.logger.error('[HTTP] Error response content from server: %s', response.content)
            self.logger.error(exception, exc_info=1)
            raise WebAPIException
        finally:
            httpSession.close()

    def getFileWithToken(self, url, localPath, token, query = None):
        """
        @return: False if failed, json structure if success
        """
        response = None
        httpSession = requests.Session()
        try:
            if query is not None:
                query = self.prepareParams(query)
            self.logger.debug('[HTTP] GET Url: %s; file path: %s', url, localPath)
            if None != token:
                headersToken = {'Auth-Token': token}
            else:
                headersToken = {}
            if SyncConfiguration.EnableProxy:
                response = httpSession.get(url, params=query, headers=headersToken, timeout=600, stream=True, verify=False)
            elif Utils.isMacOS():
                response = httpSession.get(url, params=query, headers=headersToken, timeout=600, stream=True, verify=Utils.getCertFile())
            else:
                response = httpSession.get(url, params=query, headers=headersToken, timeout=600, stream=True)
            self.logger.debug('[HTTP] Response status [%s]', str(response.status_code))
            if response.status_code == StatusCode.Success:
                with open(localPath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)

                return (True, None, HttpTokenExitCode.DOWNLOAD_OK)
            errorCode = HttpTokenExitCode.DOWNLOAD_RETRY_ERROR
            strError = '\xe8\xaf\xb7\xe9\x87\x8d\xe8\xaf\x95'
            if 400 == StatusCode.Success:
                errorCode = HttpTokenExitCode.DOWNLOAD_ACCESS_ERROR
                strError = u'\u6743\u9650\u4e0d\u8db3\u65e0\u6cd5\u5b8c\u6210\u8be5\u64cd\u4f5c\uff0c\u8bf7\u68c0\u67e5\u60a8\u7684\u534f\u4f5c\u8005\u7b49\u7ea7'
            elif 500 == StatusCode.Success:
                errorCode = HttpTokenExitCode.DOWNLOAD_NET_ERROR
                strError = u'\u60a8\u7684\u7f51\u7edc\u53ef\u80fd\u5b58\u5728\u95ee\u9898\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5'
            elif 401 == StatusCode.Success:
                errorCode = HttpTokenExitCode.DOWNLOAD_TOKEN_EXPIRED
                strError = u'\u7528\u6237\u5df2\u6ce8\u9500'
            return (False, strError, errorCode)
        except Exception as exception:
            if response is not None:
                self.logger.error('[HTTP] Error response content from server: %s', response.content)
            self.logger.error(exception, exc_info=1)
        finally:
            httpSession.close()

        return (False, '\xe8\xaf\xb7\xe9\x87\x8d\xe8\xaf\x95', HttpTokenExitCode.DOWNLOAD_RETRY_ERROR)

    def getFile(self, url, localPath, desPath, query = None):
        """
        @localPath: the file that need to be upload, this maybe temp file
        @desPath: destination position
        @return: False if failed, json structure if success
        """
        response = None
        httpSession = requests.Session()
        bConnectError = False
        try:
            if query is not None:
                query = self.prepareParams(query)
            self.logger.debug('[HTTP] GET Url: %s; file path: %s', url, localPath)
            headers = self.getHeaders()
            if os.path.exists(localPath):
                bytePos = os.path.getsize(localPath)
                headers['RANGE'] = 'bytes=%d-' % bytePos
            else:
                bytePos = 0
            if SyncConfiguration.EnableProxy:
                response = httpSession.get(url, params=query, headers=headers, timeout=600, stream=True, proxies=self.getProxies(), verify=False)
            elif Utils.isMacOS():
                response = httpSession.get(url, params=query, headers=headers, timeout=600, stream=True, proxies=self.getProxies(), verify=Utils.getCertFile())
            else:
                response = httpSession.get(url, params=query, headers=headers, timeout=600, stream=True, proxies=self.getProxies())
            self.logger.debug('[HTTP] Response status [%s]', str(response.status_code))
            if response.status_code == StatusCode.Success or response.status_code == StatusCode.PartialContent:
                try:
                    if bytePos > 0:
                        openTag = 'ab'
                    else:
                        openTag = 'wb'
                    openfile = open(localPath, openTag)
                    for chunk in response.iter_content(chunk_size=10240):
                        if chunk:
                            openfile.write(chunk)
                            HttpStatistic.AddDownloadByte(localPath, 10240)
                            if not SyncConfiguration.IsEnableSyncing or SyncConfiguration.IsFullSyncIniting:
                                raise StopSyncing
                            if desPath not in SyncingFileList.SyncingFileSet:
                                raise StopSyncingAndRestart

                finally:
                    if locals().has_key('openfile'):
                        openfile.close()

                if response.status_code == StatusCode.PartialContent and long(response.headers.get('Content-Range').split('/')[1]) != os.path.getsize(localPath):
                    self.logger.debug('[HTTP] More data should be transfer, status code = %d', response.status_code)
                    result = False
                elif response.status_code == StatusCode.Success:
                    if response.headers.get('Transfer-Encoding') != 'chunked' and long(response.headers.get('Content-Length')) != os.path.getsize(localPath):
                        self.logger.debug('[HTTP] More data should be transfer, status code = %d', response.status_code)
                        result = False
                    elif response.headers.get('Transfer-Encoding') == 'chunked' and response.headers.get('X-Decrypt-Content-Length') is not None and long(response.headers.get('X-Decrypt-Content-Length')) != os.path.getsize(localPath):
                        self.logger.debug('[HTTP] More data should be transfer, status code = %d', response.status_code)
                        result = False
                    else:
                        result = True
                else:
                    self.logger.debug('[HTTP] File download successfully')
                    result = True
                return result
            if response.status_code == StatusCode.NotFound:
                result = {'success': False,
                 'error': HttpErrorMessage.UnavailableFileOnServer}
                return result
            return self.handleFailedResponseStatus(response.url, response.status_code, response.content)
        except (ProxyConnectionError, ConnectionError) as exception:
            self.logger.error(exception, exc_info=1)
            bConnectError = True
            raise exception
        except ReadTimeout as exception:
            self.logger.error(exception, exc_info=1)
            raise OperationRetryInOneMinuteException
        except IOError as exception:
            self.logger.error(exception, exc_info=1)
            raise exception
        except (UnAuthorizedException,
         RefreshTokenFailedException,
         HttpQueryParameterError,
         StopSyncing) as exception:
            self.logger.error(exception, exc_info=1)
            raise exception
        except Exception as exception:
            self.logger.error(exception, exc_info=1)
            raise WebAPIException
        finally:
            SyncUiInterface.SetNetworkAvailable(not bConnectError)
            httpSession.close()

    def post(self, url, query = None, jsonData = None, data = None, logData = True, header = {}):
        """
        @return: False if failed, json structure if success
        """
        response = None
        httpSession = requests.Session()
        bConnectError = False
        try:
            if query is not None:
                query = self.prepareParams(query)
            header = self.getHeaders(header)
            self.logger.debug('[HTTP] POST Url: ' + url)
            if jsonData is not None:
                if logData:
                    self.logger.debug('[HTTP] POST Json: ' + json.dumps(jsonData))
                while True:
                    try:
                        if SyncConfiguration.EnableProxy:
                            response = httpSession.post(url, params=query, json=jsonData, headers=header, timeout=600, proxies=self.getProxies(), verify=False)
                        elif Utils.isMacOS():
                            response = httpSession.post(url, params=query, json=jsonData, headers=header, timeout=600, proxies=self.getProxies(), verify=Utils.getCertFile())
                        else:
                            response = httpSession.post(url, params=query, json=jsonData, headers=header, timeout=600, proxies=self.getProxies())
                        break
                    except requests.exceptions.Timeout:
                        self.logger.warning('[HTTP] time out and try the request again')

            else:
                if logData and data is not None:
                    self.logger.debug('[HTTP] POST Data: ' + data)
                while True:
                    try:
                        if SyncConfiguration.EnableProxy:
                            response = httpSession.post(url, params=query, data=data, headers=header, timeout=600, proxies=self.getProxies(), verify=False)
                        elif Utils.isMacOS():
                            response = httpSession.post(url, params=query, data=data, headers=header, timeout=600, proxies=self.getProxies(), verify=Utils.getCertFile())
                        else:
                            response = httpSession.post(url, params=query, data=data, headers=header, timeout=600, proxies=self.getProxies())
                        break
                    except requests.exceptions.Timeout as exception:
                        pass

            if logData:
                self.logger.debug('[HTTP] Response status [%s] and content: %s', str(response.status_code), response.content)
            else:
                self.logger.debug('[HTTP] Response status [%s]', str(response.status_code))
            if response.status_code == StatusCode.Success:
                responseJson = response.json()
                if responseJson.get('success') == True:
                    return responseJson
                else:
                    return False
            else:
                return self.handleFailedResponseStatus(response.url, response.status_code, response.content)
        except (ProxyConnectionError, ConnectionError) as exception:
            self.logger.error(exception, exc_info=1)
            bConnectError = True
            raise exception
        except (UnAuthorizedException,
         RefreshTokenFailedException,
         HttpQueryParameterError,
         StopSyncing,
         CheckSumExpiredException) as exception:
            self.logger.error(exception, exc_info=1)
            raise exception
        except Exception as exception:
            if response is not None:
                self.logger.error('[HTTP] Error response content from server: %s', response.content)
            self.logger.error(exception, exc_info=1)
            raise WebAPIException
        finally:
            SyncUiInterface.SetNetworkAvailable(not bConnectError)
            httpSession.close()

    def postFileWithToken(self, url, localPath, tempPath, token, appName, query = None):
        """
        @return: False if failed, json structure if success
        """
        response = None
        httpSession = requests.Session()
        try:
            if Utils.isWindowsOS():
                fileName = Utils.getNameFromPath(localPath)
                tempFileHanlder = open(tempPath, 'rb')
            else:
                fileName = Utils.getNameFromPath(localPath)
                tempFileHanlder = open(tempPath, 'rb')
            files = {'file': (fileName, tempFileHanlder, {'Expires': '0'})}
            if query is not None:
                query = self.prepareParams(query)
            if self.logger is not None:
                self.logger.debug('[HTTP] POST Url: ' + url)
            multipartMonitor = MultipartEncoderMonitor.from_fields(fields=files, callback=None)
            multipartMonitor.filePath = localPath
            headersToken = {'Content-Type': multipartMonitor.content_type,
             'Auth-Token': token}
            if SyncConfiguration.EnableProxy:
                response = httpSession.post(url, params=query, data=multipartMonitor, headers=headersToken, timeout=600, verify=False)
            elif Utils.isMacOS():
                response = httpSession.post(url, params=query, data=multipartMonitor, headers=headersToken, timeout=600, verify=Utils.getCertFile())
            else:
                response = httpSession.post(url, params=query, data=multipartMonitor, headers=headersToken, timeout=600, proxies=self.getProxies())
            self.logger.debug('[HTTP] Response status [%s] and content: %s', str(response.status_code), response.content)
            if response.status_code == StatusCode.Success:
                responseJson = response.json()
                if responseJson.get('success') == True:
                    return (responseJson, None)
                else:
                    return (False, '\xe8\xaf\xb7\xe9\x87\x8d\xe8\xaf\x95')
            else:
                errorMsg = '\xe8\xaf\xb7\xe9\x87\x8d\xe8\xaf\x95'
                if 400 == response.status_code or 500 == response.status_code:
                    responseJson = response.json()
                    if -1 != responseJson.find('failed_to_process_request'):
                        errorMsg = u'\u4e91\u7aef\u6587\u4ef6\u4e0d\u5b58\u5728'
                    elif 500 == response.status_code:
                        errorMsg = u'\u60a8\u7684\u7f51\u7edc\u53ef\u80fd\u5b58\u5728\u95ee\u9898\uff0c\u8bf7\u7a0d\u540e\u518d\u8bd5'
                    else:
                        errorMsg = u'\u6743\u9650\u4e0d\u8db3\u65e0\u6cd5\u5b8c\u6210\u8be5\u64cd\u4f5c\uff0c\u8bf7\u68c0\u67e5\u60a8\u7684\u534f\u4f5c\u8005\u7b49\u7ea7'
                elif 401 == response.status_code:
                    errorMsg = u'\u7528\u6237\u5df2\u9000\u51fa' + appName
                return (False, errorMsg)
        except Exception as exception:
            self.logger.error(exception, exc_info=1)
        finally:
            httpSession.close()
            if locals().has_key('tempFileHanlder'):
                tempFileHanlder.close()

        return (False, '\xe8\xaf\xb7\xe9\x87\x8d\xe8\xaf\x95')

    def postStreamFile(self, url, filePath, tempPath, start, limit, query = None, header = {}, resetUploadedByte = False):
        response = None
        httpSession = requests.Session()
        bConnectError = False
        try:
            if query is not None:
                query = self.prepareParams(query)
            if self.logger is not None:
                self.logger.debug('[HTTP] POST Url: ' + url)
            header = self.getHeaders(header)
            it = UploadInChunks(filePath, tempPath, 10240, start, limit)
            if SyncConfiguration.EnableProxy:
                response = httpSession.post(url, params=query, data=IterableToFileAdapter(it), headers=header, timeout=600, proxies=self.getProxies(), verify=False)
            elif Utils.isMacOS():
                response = httpSession.post(url, params=query, data=IterableToFileAdapter(it), headers=header, timeout=600, proxies=self.getProxies(), verify=Utils.getCertFile())
            else:
                response = httpSession.post(url, params=query, data=IterableToFileAdapter(it), headers=header, timeout=600, proxies=self.getProxies())
            self.logger.debug('[HTTP] Response status [%s] and content: %s', str(response.status_code), response.content)
            if response.status_code == StatusCode.Success:
                responseJson = response.json()
                if responseJson.get('success'):
                    return responseJson
                else:
                    return False
            else:
                return self.handleFailedResponseStatus(response.url, response.status_code, response.content)
        except (ProxyConnectionError, ConnectionError) as exception:
            self.logger.debug('[HTTP] post file stopped because connection abort')
            self.logger.error(exception, exc_info=1)
            bConnectError = True
            raise exception
        except (StopSyncing, StopSyncingAndRestart) as exception:
            self.logger.debug('[HTTP] stop send file to server and clear upload byte')
            HttpStatistic.FinishedUploadByte(filePath)
            raise exception
        except (UnAuthorizedException,
         RefreshTokenFailedException,
         HttpQueryParameterError,
         CheckSumExpiredException) as exception:
            self.logger.debug('[HTTP] stop send file to server')
            raise exception
        except Exception as exception:
            if response is not None:
                self.logger.error('[HTTP] Error response content from server: %s', response.content)
            self.logger.error(exception, exc_info=1)
            raise WebAPIException
        finally:
            SyncUiInterface.SetNetworkAvailable(not bConnectError)
            if resetUploadedByte:
                HttpStatistic.FinishedUploadByte(filePath)
            httpSession.close()

    def postFile(self, url, localPath, tempPath, query = None):
        """
        @return: False if failed, json structure if success
        """
        response = None
        httpSession = requests.Session()
        bConnectError = False
        try:
            fileName = Utils.getNameFromPath(localPath)
            tempFileHanlder = open(tempPath, 'rb')
            files = {'file': (fileName, tempFileHanlder, {'Expires': '0'})}
            if query is not None:
                query = self.prepareParams(query)
            if self.logger is not None:
                self.logger.debug('[HTTP] POST Url: ' + url)
            multipartMonitor = MultipartEncoderMonitor.from_fields(fields=files, callback=handleChunkFinish)
            multipartMonitor.filePath = localPath
            headers = self.getHeaders()
            headers['Content-Type'] = multipartMonitor.content_type
            if SyncConfiguration.EnableProxy:
                response = httpSession.post(url, params=query, data=multipartMonitor, headers=headers, timeout=600, proxies=self.getProxies(), verify=False)
            elif Utils.isMacOS():
                response = httpSession.post(url, params=query, data=multipartMonitor, headers=headers, timeout=600, proxies=self.getProxies(), verify=Utils.getCertFile())
            else:
                response = httpSession.post(url, params=query, data=multipartMonitor, headers=headers, timeout=600, proxies=self.getProxies())
            self.logger.debug('[HTTP] Response status [%s] and content: %s', str(response.status_code), response.content)
            if response.status_code == StatusCode.Success:
                responseJson = response.json()
                if responseJson.get('success') == True:
                    return responseJson
                else:
                    return False
            else:
                return self.handleFailedResponseStatus(response.url, response.status_code, response.content)
        except (ProxyConnectionError, ConnectionError) as exception:
            self.logger.debug('[HTTP] post file stopped because connection abort')
            bConnectError = True
            self.logger.error(exception, exc_info=1)
            raise exception
        except (UnAuthorizedException,
         RefreshTokenFailedException,
         HttpQueryParameterError,
         StopSyncing) as exception:
            self.logger.debug('[HTTP] stop send file to server')
            raise exception
        except Exception as exception:
            if response is not None:
                self.logger.error('[HTTP] Error response content from server: %s', response.content)
            self.logger.error(exception, exc_info=1)
            raise WebAPIException
        finally:
            SyncUiInterface.SetNetworkAvailable(not bConnectError)
            HttpStatistic.FinishedUploadByte(localPath)
            httpSession.close()
            if locals().has_key('tempFileHanlder'):
                tempFileHanlder.close()

    def postLogFile(self, url, localPath, tempFile, query = None):
        response = None
        self.logger.debug('[HTTP] post log file, the path is %s', localPath)
        httpSession = requests.Session()
        try:
            if query is not None:
                query = self.prepareParams(query)
            fileName = Utils.getNameFromPath(localPath)
            files = {'log_file': (fileName, open(tempFile, 'rb'), {'Expires': '0'})}
            headers = self.getHeaders()
            if SyncConfiguration.EnableProxy:
                response = httpSession.post(url, params=query, files=files, timeout=600, headers=headers, proxies=self.getProxies(), verify=False)
            elif Utils.isMacOS():
                response = httpSession.post(url, params=query, files=files, timeout=600, headers=headers, proxies=self.getProxies(), verify=Utils.getCertFile())
            else:
                response = httpSession.post(url, params=query, files=files, timeout=600, headers=headers, proxies=self.getProxies())
            if response.status_code == StatusCode.Success:
                responseJson = response.json()
                if responseJson.get('success') == True:
                    return True
            raise WebAPIException
        except Exception as exception:
            if response is not None:
                self.logger.error('[HTTP] Error response content from server: %s', response.content)
            self.logger.error(exception, exc_info=1)
            raise WebAPIException
        finally:
            httpSession.close()


if __name__ == '__main__':
    payload = {'login': 'linrenjun@egeio.com',
     'password': ''}
    r = requests.post('https://www.fangcloud.com/api/v1/user/auth?api_key=37e359bba6b45e2cd91ac2ca2c7adb47', json=payload)
+++ okay decompyling HttpBasicClient.pyc 
# decompiled 1 files: 1 okay, 0 failed, 0 verify failed
# 2016.10.21 16:38:42 CST
