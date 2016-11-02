# 2016.10.21 16:37:51 CST
#Embedded file name: com/fangcloud/httpconnection/FangCloudHttpClient.pyc
"""
Created on 2014-10-16

@author: renjun
"""
import datetime
import threading
import os
import hashlib
from requests.exceptions import ConnectionError
from com.fangcloud.database.UserDatabaseManager import UserDatabaseManager
from com.fangcloud.httpconnection.FangCloudUrls import FangCloudUrl
from com.fangcloud.httpconnection.HttpBasicClient import HttpBasicClient
from com.fangcloud.httpconnection.SyncingFileList import SyncingFileList
from com.fangcloud.httpconnection.statistic.HttpStatistic import HttpStatistic
from com.fangcloud.logging.LoggerFactory import LoggerFactory
from com.fangcloud.utils import Utils
from com.fangcloud.utils.Exceptions import UnAuthorizedException, DeleteParameterException, WebAPIException, CheckSumExpiredException
from com.fangcloud.utils.Utils import API_KEY, FILE_TYPE, INVALID_RESOURCE_ID, TEST_SECURITY_KEY, INVALID_SEQUENCE_ID
TOKEN_REFRESH_LOCK = threading.RLock()

class HttpResponseResult:
    Failed = False
    RepeatRightNow = 'RepeatRightNow'
    RefreshTokenIgnore = 'RefreshTokenIgnore'


class FangCloudHttpCallBackHandler(object):

    def __init__(self):
        self.logger = LoggerFactory().getLoggerInstance()

    def handleHttpResponse(self, response):
        pass


class FangCloudHttpClient(HttpBasicClient):

    def __init__(self, callbackHandler):
        super(FangCloudHttpClient, self).__init__()
        self.callbackHandler = callbackHandler

    def login(self, username, password):
        """
            @return: return false if exception or failed. return the following user structure if success.
        
                 {
                     "auth_token": "a8f5f167f44f4964e6c998dee827110c",
                     "refresh_token": "964e6c998dee827110ca8f5f167f44f4",
                     "auth_success": true,
                     "expires_at": "1401698962",
                     "user": {
                         "type": "user",
                         "id": "12312311",
                         "name": "Yuan Cheng",
                         "login": "yuan@egeio.com",
                         "phone": "123123",
                         "space_total": "123123",
                         "space_used": "1123123",
                         "name_first_letter": "a",
                         "profile_pic_key" : "ksui667f44f4964e6c998dee8245s61",
                     },
                 }
        """
        try:
            urlQuery = {'api_key': API_KEY}
            postBody = {'login': username,
             'password': password}
            response = self.post(FangCloudUrl.URL['USER_LOGIN'], query=urlQuery, jsonData=postBody, logData=False)
            if response != False:
                HttpBasicClient.UserAuthToken = response['auth_token']
                HttpBasicClient.UserRefreshToken = response['refresh_token']
                HttpBasicClient.ExpireDate = datetime.datetime.fromtimestamp(int(response['expires_at']))
                Utils.storeAuthToken(HttpBasicClient.UserAuthToken)
            else:
                self.logger.info('[HTTP] User login failed!')
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return HttpResponseResult.Failed
        except ConnectionError:
            return HttpResponseResult.Failed

    def refreshAuthToken(self, forceRereshToken = False):
        """
            Response:
            {
                "auth_token": "a8f5f167f44f4964e6c998dee827110c",
                "refresh_token": "964e6c998dee827110ca8f5f167f44f4",
                "expires_at": "1401698962",
            }
        
            @return: False if failed, json structure if success
        
        """
        try:
            TOKEN_REFRESH_LOCK.acquire()
            if HttpBasicClient.UserRefreshToken is None:
                self.logger.warning('[HTTP] refresh token stored in cache is invalidate')
                return HttpResponseResult.RefreshTokenIgnore
            if type(HttpBasicClient.ExpireDate) == int:
                self.logger.warning('[HTTP] error of expire date: %d', HttpBasicClient.ExpireDate)
            currentTime = self.getServerCurrentTime()
            if HttpBasicClient.ExpireDate is not None and currentTime < HttpBasicClient.ExpireDate - datetime.timedelta(seconds=60) and not forceRereshToken:
                self.logger.debug('[HTTP] do not need to refresh token because other thread have finished it, the expire date is %s', HttpBasicClient.ExpireDate)
                return HttpResponseResult.RefreshTokenIgnore
            postBody = {'refresh_token': HttpBasicClient.UserRefreshToken}
            response = self.post(FangCloudUrl.URL['RERRESH_AUTH_TOKEN'], jsonData=postBody, logData=True)
            if response != False:
                HttpBasicClient.UserAuthToken = response['auth_token']
                HttpBasicClient.UserRefreshToken = response['refresh_token']
                HttpBasicClient.ExpireDate = datetime.datetime.fromtimestamp(int(response['expires_at']))
                Utils.storeAuthToken(HttpBasicClient.UserAuthToken)
                UserDatabaseManager().refreshAuthToken(response['auth_token'], response['refresh_token'], response['expires_at'])
            else:
                self.logger.info('[HTTP] Refresh user token failed')
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return HttpResponseResult.Failed
        except ConnectionError:
            return HttpResponseResult.Failed
        finally:
            TOKEN_REFRESH_LOCK.release()

    def logout(self):
        try:
            postBody = {}
            response = self.post(FangCloudUrl.URL['USER_LOGOUT'], jsonData=postBody)
            self.callbackHandler.handleHttpResponse(response)
            if type(response) == dict:
                return response['success']
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return True
        except ConnectionError:
            return HttpResponseResult.Failed

    def getUserAccountInfo(self):
        try:
            response = self.get(FangCloudUrl.URL['USER_ACCOUNT_INFO'])
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getFileSyncInfo(self, fileId):
        try:
            response = self.get(FangCloudUrl.URL['FILE_SYNC_INFO'] % fileId)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getFolderSyncInfo(self, folderId):
        try:
            response = self.get(FangCloudUrl.URL['FOLDER_SYNC_INFO'] % int(folderId))
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getFileOwnerInfo(self, fileId):
        try:
            response = self.get(FangCloudUrl.URL['FILE_OWNER_INFO'] % int(fileId))
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getFolderOwnerInfo(self, folderId):
        try:
            response = self.get(FangCloudUrl.URL['FOLDER_OWNER_INFO'] % int(folderId))
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getResourceShareLink(self, serverId, resourceType):
        try:
            currentTime = self.getServerCurrentTime()
            self.logger.debug('[HTTP] get server current time %s', currentTime)
            dueTime = currentTime + datetime.timedelta(days=7)
            postBody = {'access': 'public',
             'disable_download': False,
             'password_protected': False,
             'password': None,
             'need_update': False,
             'due_time': dueTime.strftime('%Y-%m-%d')}
            if resourceType == FILE_TYPE:
                response = self.post(FangCloudUrl.URL['FILE_SHARE'] % serverId, jsonData=postBody)
            else:
                response = self.post(FangCloudUrl.URL['FOLDER_SHARE'] % serverId, jsonData=postBody)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def folderChildren(self, folderId):
        """
        this is a temp function
        """
        try:
            urlQuery = {'fields': 'size,created_at,modified_at,parent_folder_id,shared,in_trash,permissions,extension_category'}
            response = self.get(FangCloudUrl.URL['FOLDER_CHILDREN'] % folderId, urlQuery)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def createNewFolder(self, name, parentFolderId, merge = False, description = 'None Description'):
        """
            Create new folder on server
        """
        try:
            postBody = {'name': name,
             'description ': description,
             'parent_id': parentFolderId,
             'merge_folder': merge}
            response = self.post(FangCloudUrl.URL['CREATE_FOLDER'], jsonData=postBody)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def updateFolder(self, name, resourceId, sequenceId):
        """
        Description: update the folder information. Currently, we only support update name.
        """
        try:
            postBody = {'name': name,
             'sequence_id': sequenceId}
            response = self.post(FangCloudUrl.URL['FOLDER_UPDATE_WITH_RESOURCE'] % resourceId, jsonData=postBody)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def updateFile(self, name, resourceId, sequenceId):
        """
        Description: update the file information (not include the content). Currently, we only support update name.
        """
        try:
            postBody = {'name': name,
             'sequence_id': sequenceId}
            response = self.post(FangCloudUrl.URL['FILE_UPDATE_WITH_RESOURCE'] % resourceId, jsonData=postBody)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def checkFileExistsOnServerAtTheSameDirWithTheSameName(self, localPath, parentFolderId, sha1, description = None):
        try:
            _, filename = os.path.split(localPath)
            urlQuery = {'folder_id': parentFolderId,
             'file_name': filename,
             'unencrypted_sha1': sha1,
             'modified_at': Utils.getModifyTime(localPath)}
            if description is not None:
                urlQuery['description'] = description
            response = self.post(FangCloudUrl.URL['FILE_UPLOAD_CHECK_FILE_EXISTS_IN_SAME_DIR_IN_SAME_NAME'], None, urlQuery)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def uploadNewFilePresign(self, parentFolderId, localPath, description = None):
        try:
            postBody = {'folder_id': parentFolderId,
             'file_name': Utils.getNameFromPath(localPath),
             'file_size': str(os.path.getsize(localPath)),
             'modified_at': Utils.getModifyTime(localPath)}
            if description is not None:
                postBody['description'] = description
            response = self.post(FangCloudUrl.URL['FILE_PRESIGN_UPLOAD'], jsonData=postBody, logData=True)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def uploadNewFile(self, url, localPath, tempPath):
        try:
            SyncingFileList.SyncingFileSet.add(localPath)
            response = self.postFile(url, localPath, tempPath)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def startMultiUploadNewFile(self, localPath, folderId, sha1):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x8f\x91\xe9\x80\x81\xe5\xbc\x80\xe5\xa7\x8b\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe8\xaf\xb7\xe6\xb1\x82-\xe9\x92\x88\xe5\xaf\xb9\xe6\x96\xb0\xe6\x96\x87\xe4\xbb\xb6
        @param localPath:
        @param folderId:
        @param sha1:
        @return:
        """
        try:
            startPostBody = {'sha1': sha1,
             'file_size': str(os.path.getsize(localPath)),
             'file_name': os.path.basename(localPath),
             'sequence_id': INVALID_SEQUENCE_ID,
             'remark': '',
             'folder_id': folderId,
             'modified_at': Utils.getModifyTime(localPath)}
            url = FangCloudUrl.URL['FILE_MULTI_UPLOAD']
            response = self.post(url, jsonData=startPostBody, logData=True)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def startMultiUploadNewFileVersion(self, localPath, fileId, sequenceId, sha1):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x8f\x91\xe9\x80\x81\xe5\xbc\x80\xe5\xa7\x8b\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe8\xaf\xb7\xe6\xb1\x82-\xe9\x92\x88\xe5\xaf\xb9\xe6\x96\x87\xe4\xbb\xb6\xe6\x96\xb0\xe7\x89\x88\xe6\x9c\xac
        @param localPath:
        @param fileId:
        @param sequenceId:
        @param sha1:
        @return:
        """
        try:
            startPostBody = {'sha1': sha1,
             'file_size': str(os.path.getsize(localPath)),
             'file_name': os.path.basename(localPath),
             'sequence_id': sequenceId,
             'remark': '',
             'folder_id': '',
             'modified_at': Utils.getModifyTime(localPath)}
            print startPostBody
            url = FangCloudUrl.URL['FILE_MULTI_UPLOAD_WITH_FILE_ID'] % fileId
            response = self.post(url, jsonData=startPostBody, logData=True)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getChecksumNewFile(self, uploadId, folderId):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x8f\x91\xe9\x80\x81\xe8\x8e\xb7\xe5\x8f\x96\xe6\x9b\xb4\xe6\x96\xb0checksum\xe8\xaf\xb7\xe6\xb1\x82-\xe9\x92\x88\xe5\xaf\xb9\xe6\x96\xb0\xe6\x96\x87\xe4\xbb\xb6
        @param uploadId:
        @param folderId:
        @return:
        """
        try:
            postBody = {'upload_id': uploadId,
             'folder_id': folderId}
            url = FangCloudUrl.URL['FILE_MULTI_UPLOAD_GET_CHECKSUM']
            response = self.post(url, jsonData=postBody, logData=True)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getChecksumNewVersion(self, uploadId, fileId):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x8f\x91\xe9\x80\x81\xe8\x8e\xb7\xe5\x8f\x96\xe6\x9b\xb4\xe6\x96\xb0checksum\xe8\xaf\xb7\xe6\xb1\x82-\xe9\x92\x88\xe5\xaf\xb9\xe6\x96\x87\xe4\xbb\xb6\xe6\x96\xb0\xe7\x89\x88\xe6\x9c\xac
        @param uploadId:
        @param fileId:
        @return:
        """
        try:
            postBody = {'upload_id': uploadId,
             'folder_id': 0}
            url = FangCloudUrl.URL['FILE_MULTI_UPLOAD_GET_CHECKSUM_WITH_FILE_ID']
            response = self.post(url % fileId, jsonData=postBody, logData=True)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def multiUploadNewFile(self, url, filePath, tempPath, blockIndex, uploadId, uploadToken, checkSum, start, limit, sha1ForBlock):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe9\x80\x9a\xe8\xbf\x87\xe6\xb5\x81\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x8e\xa5\xe5\x8f\xa3\xe4\xbc\xa0\xe8\xbe\x93\xe6\x96\x87\xe4\xbb\xb6\xe5\x9d\x97
        @param url:
        @param filePath:
        @param tempPath:
        @param blockIndex:
        @param uploadId:
        @param uploadToken:
        @param checkSum:
        @param start:
        @param limit:
        @param sha1ForBlock:
        @return:
        """
        try:
            query = {'block_index': blockIndex,
             'upload_id': uploadId,
             'upload_token': uploadToken,
             'checksum': checkSum,
             'sha1': sha1ForBlock}
            response = self.postStreamFile(url, filePath, tempPath, start, limit, query=query)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def multiUploadFinish(self, localPath, url, uploadId, uploadToken, checkSum, uploadParts, sha1):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x8f\x91\xe9\x80\x81\xe5\xb7\xb2\xe7\xbb\x8f\xe4\xb8\x8a\xe4\xbc\xa0\xe5\xae\x8c\xe6\xaf\x95\xe8\xaf\xb7\xe6\xb1\x82
        @param localPath:
        @param url:
        @param uploadId:
        @param uploadToken:
        @param checkSum:
        @param uploadParts:
        @param sha1:
        @return:
        """
        try:
            query = {'upload_id': uploadId,
             'upload_token': uploadToken,
             'checksum': checkSum}
            postBody = {'sha1': sha1,
             'upload_parts': uploadParts}
            response = self.post(url, jsonData=postBody, logData=True, query=query)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed
        finally:
            HttpStatistic.FinishedUploadByte(localPath)

    def multiUploadGet(self, url, uploadId, uploadToken, checkSum):
        """
        \xe8\x8e\xb7\xe5\x8f\x96\xe5\xb7\xb2\xe7\xbb\x8f\xe4\xb8\x8a\xe4\xbc\xa0\xe7\x9a\x84\xe4\xbf\xa1\xe6\x81\xaf
        @param url:
        @param uploadId:
        @param uploadToken:
        @param checkSum:
        @return:
        """
        try:
            query = {'upload_id': uploadId,
             'upload_token': uploadToken,
             'checksum': checkSum}
            response = self.post(url, logData=True, query=query)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def multiUploadAbort(self, url, uploadId, uploadToken, checkSum):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe7\xbb\x88\xe6\xad\xa2\xe6\x96\x87\xe4\xbb\xb6\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0
        @param url:
        @param uploadId:
        @param uploadToken:
        @param checkSum:
        @return:
        """
        try:
            query = {'upload_id': uploadId,
             'upload_token': uploadToken,
             'checksum': checkSum}
            response = self.post(url, logData=True, query=query)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def uploadNewFileVersionPresign(self, fileId, sequenceId, size, name, modifiedAt):
        try:
            postBody = {'target_file_id': fileId,
             'sequence_id': sequenceId,
             'file_size': str(size),
             'file_name': name,
             'modified_at': modifiedAt}
            response = self.post(FangCloudUrl.URL['FILE_PRESIGN_UPLOAD'], jsonData=postBody, logData=True)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def uploadNewFileVersion(self, url, localPath, tempPath, description = None):
        """
        @resourceId: it means uploading a new version of a file, then folder_id is not required
        """
        try:
            SyncingFileList.SyncingFileSet.add(localPath)
            response = self.postFile(url, localPath, tempPath)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def downloadFile(self, fileId, tempPath, fileLocalPathToStore):
        """
            @fileId: int
            @fileLocalPathToStore: string
            @return: True if success, False if failed
        """
        try:
            SyncingFileList.SyncingFileSet.add(fileLocalPathToStore)
            if type(fileId) != int:
                fileId = int(fileId)
            response = self.getFile(FangCloudUrl.URL['FILE_DOWNLOAD_WITH_RESOURCE'] % fileId, tempPath, fileLocalPathToStore)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def deleteFilesAndDirectories(self, fileIds, directoryIds, unsyncFileIds, unsyncDirectoryIds, enableCheckUnsync, forceDelete):
        """
            Description: delete files or directories from fang cloud server
            @fileIds: int list, file ids to delete
            @directoryIds: int list, directory ids to delete
            @return: {'success': True}
        """
        try:
            deleteItem = None
            if fileIds is not None and type(fileIds) == list and len(fileIds) > 0:
                for fileId in fileIds:
                    deleteItem = 'file_' + str(fileId)

            if directoryIds is not None and type(directoryIds) == list and len(directoryIds) > 0:
                for directoryId in directoryIds:
                    deleteItem = 'folder_' + str(directoryId)

            if deleteItem is None:
                raise DeleteParameterException
            unsyncItem = []
            if unsyncFileIds is not None and type(unsyncFileIds) == list and len(unsyncFileIds) > 0:
                for fileId in unsyncFileIds:
                    unsyncItem.append('file_' + str(fileId))

            if unsyncDirectoryIds is not None and type(unsyncDirectoryIds) == list and len(unsyncDirectoryIds) > 0:
                for directoryId in unsyncDirectoryIds:
                    unsyncItem.append('folder_' + str(directoryId))

            postBody = {'item': deleteItem,
             'unsync_items': unsyncItem,
             'check_enabled': enableCheckUnsync,
             'force_delete': forceDelete}
            response = self.post(FangCloudUrl.URL['ITEM_DELETE'], jsonData=postBody)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def moveFilesAndDirectories(self, targetFoldId, sequenceId, fileId = INVALID_RESOURCE_ID, directoryId = INVALID_RESOURCE_ID):
        try:
            if fileId != INVALID_RESOURCE_ID:
                resourceKey = 'file_' + str(fileId)
            elif directoryId != INVALID_RESOURCE_ID:
                resourceKey = 'folder_' + str(directoryId)
            else:
                raise WebAPIException
            postBody = {'target_folder_id': targetFoldId,
             'skip_collab_limit': True,
             'items_sequence_ids': {resourceKey: sequenceId}}
            response = self.post(FangCloudUrl.URL['ITEM_MOVE'], jsonData=postBody, logData=False)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getSyncedFolders(self):
        try:
            response = self.get(FangCloudUrl.URL['GET_SYNCED_FOLDERS'])
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getSyncedFiles(self):
        try:
            response = self.get(FangCloudUrl.URL['GET_SYNCED_FILES'])
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getPagedSyncedFiles(self, pageId):
        try:
            urlQuery = {'page': pageId}
            response = self.get(FangCloudUrl.URL['GET_PAGED_SYNCED_FILES'], urlQuery)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getSyncedBulkInfo(self, folders, files, secureToken):
        folderStr = ','.join((str(folderCur) for folderCur in folders))
        fileStr = ','.join((str(fileCur) for fileCur in files))
        signalToken = '%s %s %s' % (folderStr, secureToken, fileStr)
        tokenMd5 = hashlib.md5(signalToken).hexdigest()
        bodySet = {'folder_ids': folders,
         'file_ids': files,
         'secure_token': tokenMd5}
        response = self.post(FangCloudUrl.URL['GET_SYNCED_BULK_INFO'], jsonData=bodySet, logData=False)
        self.callbackHandler.handleHttpResponse(response)
        return response

    def getSynedFolderChildrenIds(self, folderId, isSyncedFolder = True):
        urlQuery = {'is_sync_folder': isSyncedFolder}
        response = self.get(FangCloudUrl.URL['GET_SYNCED_FOLDERS_CHILDREN_IDS'] % folderId, urlQuery, logData=False)
        self.callbackHandler.handleHttpResponse(response)
        return response

    def markFolderAsSynced(self, folderId):
        try:
            postBody = {'folder_ids': [folderId]}
            response = self.post(FangCloudUrl.URL['MARK_FOLDER_AS_SYNCED'], jsonData=postBody)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def markFolderAsUnSynced(self, folderId):
        try:
            postBody = {'folder_ids': [folderId]}
            response = self.post(FangCloudUrl.URL['MARK_FOLDER_AS_UNSYNCED'], jsonData=postBody)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getAliyunAccessLog(self, fileNameList):
        try:
            postBody = {'file_names': fileNameList}
            response = self.post(FangCloudUrl.URL['ALIYUN_ACCESS_CRASH_LOG'], jsonData=postBody)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def uploadCrashLogCallBack(self, objectKey):
        try:
            postBody = {'object_key': objectKey}
            response = self.post(FangCloudUrl.URL['CRASH_LOG_UPLOADED_CALL_BACK'], jsonData=postBody)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def downloadUpdateFile(self, url, localPath):
        """
        Description: download sync app update file to local
        @url: file url to be downloaded
        @localPath: file path to store
        """
        try:
            return self.getFileForUpdate(url, localPath)
        except ConnectionError:
            return HttpResponseResult.Failed

    def __refreshTokenWhenUnAuthorized(self):
        result = self.refreshAuthToken()
        if result == HttpResponseResult.RefreshTokenIgnore:
            return HttpResponseResult.RefreshTokenIgnore
        else:
            return HttpResponseResult.Failed

    def clearResourceOnServer(self):
        try:
            response = self.get(FangCloudUrl.URL['DELETE_ALL_ITEMS'] % TEST_SECURITY_KEY)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getAllServerItems(self):
        try:
            response = self.get(FangCloudUrl.URL['GET_ALL_ITEMS'] % TEST_SECURITY_KEY)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getRealTimeUri(self):
        try:
            response = self.get(FangCloudUrl.REALTIME_FETCH_ADDRESS_URL)
            self.callbackHandler.handleHttpResponse(response)
            return response['uri']
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed

    def getServerCurrentTime(self):
        try:
            response = self.get(FangCloudUrl.URL['USER_TIMESTAMP'])
            if type(response) == dict and response.get('success', False) and response.has_key('timestamp'):
                return datetime.datetime.fromtimestamp(response['timestamp'])
            return datetime.datetime.now()
        except Exception:
            return datetime.datetime.now()

    def clientVersionCheck(self):
        try:
            response = self.get(FangCloudUrl.URL['CLIENT_VERSION_CHECK'])
            return response
        except UnAuthorizedException:
            return {'success': False}
        except Exception:
            return {'success': True}

    def lockResource(self, serverId):
        urlQuery = {'item_id': serverId}
        response = self.get(FangCloudUrl.URL['LOCK_ITEM'], query=urlQuery)
        self.callbackHandler.handleHttpResponse(response)
        return response

    def unlockResource(self, serverId):
        urlQuery = {'item_id': serverId}
        response = self.get(FangCloudUrl.URL['UNLOCK_ITEM'], query=urlQuery)
        self.callbackHandler.handleHttpResponse(response)
        return response

    def invite(self, folderId, inviteUsers):
        try:
            userStr = ''
            for user in inviteUsers:
                if userStr != '':
                    userStr += ';'
                userStr += userStr + str(user['id']) + ':' + user['level']

            postBody = {'invitation_message': '',
             'resend': False,
             'folder_id': folderId,
             'invited_users': userStr}
            response = self.post(FangCloudUrl.URL['INVITE'], jsonData=postBody)
            self.callbackHandler.handleHttpResponse(response)
            return response
        except UnAuthorizedException as exception:
            self.logger.error(exception, exc_info=1)
            return self.__refreshTokenWhenUnAuthorized()
        except ConnectionError:
            return HttpResponseResult.Failed
+++ okay decompyling FangCloudHttpClient.pyc 
# decompiled 1 files: 1 okay, 0 failed, 0 verify failed
# 2016.10.21 16:37:53 CST
