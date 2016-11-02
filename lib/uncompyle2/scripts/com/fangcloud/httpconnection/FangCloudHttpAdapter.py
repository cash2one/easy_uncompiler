# 2016.10.21 16:37:02 CST
#Embedded file name: com/fangcloud/httpconnection/FangCloudHttpAdapter.pyc
"""
Created on 2014-10-23

@author: renjun
"""
import os
import shutil
import oss2
import math
from time import sleep, time
from com.fangcloud.controller.TempResourceController import TempResourceController
from com.fangcloud.controller.status.ServerResourceAttribute import ServerResourceAttribute
from com.fangcloud.httpconnection.FangCloudHttpClient import FangCloudHttpClient, FangCloudHttpCallBackHandler, HttpResponseResult
from com.fangcloud.httpconnection.FangCloudUrls import FangCloudUrl
from com.fangcloud.httpconnection.SyncingFileList import SyncingFileList
from com.fangcloud.httpconnection.statistic.HttpStatistic import HttpStatistic
from com.fangcloud.interface.SyncUiInterface import SyncUiInterface
from com.fangcloud.localfile.LocalFileSystemAdapter import LocalFileSystemAdapter
from com.fangcloud.logging.LoggerFactory import LoggerFactory
from com.fangcloud.utils.Exceptions import AutoRepeatQueryException, WebAPIException, RefreshTokenFailedException, EnterpriseExpired, OperationRetryException, WaitingOtherResourceException, OperationRetryInOneMinuteException, CheckSumExpiredException
from com.fangcloud.utils.Utils import DIRECTORY_TYPE, FILE_TYPE, INVALID_RESOURCE_ID, INVALID_SEQUENCE_ID
from com.fangcloud.utils import Utils
from com.fangcloud.international.SyncInternational import trsl
from com.fangcloud.database.MultiUploadRecordManager import MultiUploadRecordManager
from com.fangcloud.database.TreeDatabaseManager import TreeDatabaseManager

class FangCloudHttpAdapter(object):
    """
    This class is used as adapter of FangCloudHttpClient.
    """

    def __init__(self, checkAuthToken = True, responseHandler = None):
        self.logger = LoggerFactory().getLoggerInstance()
        self.responseHandler = responseHandler
        self.checkAuthToken = checkAuthToken
        self.multiUploadRecordDatabase = MultiUploadRecordManager()
        self.treeDatabase = TreeDatabaseManager()
        self.localFileSystem = LocalFileSystemAdapter().getFileSystem()

    def getFangCloudHttpClient(self):
        if self.responseHandler is None:
            client = FangCloudHttpClient(FangCloudHttpCallBackHandler())
        else:
            client = FangCloudHttpClient(self.responseHandler)
        return client

    def autoRepeatQuery(self, function, parameters):
        try:
            response = HttpResponseResult.Failed
            refreshTokenCount = 0
            requestCount = 0
            while response in [HttpResponseResult.Failed, HttpResponseResult.RefreshTokenIgnore]:
                response = function(*parameters)
                if response == HttpResponseResult.Failed:
                    if requestCount < 1:
                        requestCount += 1
                        sleep(5)
                    else:
                        raise AutoRepeatQueryException
                elif response == HttpResponseResult.RefreshTokenIgnore:
                    refreshTokenCount += 1
                    if refreshTokenCount > 1:
                        raise RefreshTokenFailedException

            return response
        except RefreshTokenFailedException:
            SyncUiInterface.PopBubble(trsl(u'\u7528\u6237\u767b\u5f55\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u767b\u5f55'))
            SyncUiInterface.ReLogin(True, True)
            return False
        except EnterpriseExpired as exception:
            SyncUiInterface.PopBubble(trsl(u'\u7528\u6237\u4f7f\u7528\u6743\u9650\u8fc7\u671f\uff0c\u8bf7\u91cd\u65b0\u7eed\u8d39'))
            SyncUiInterface.EnterpriseExpired(exception.error_message)
            return False
        except OperationRetryInOneMinuteException as exception:
            raise exception
        except CheckSumExpiredException as exception:
            raise exception
        except (WebAPIException, IOError) as exception:
            self.logger.error(exception, exc_info=1)
            raise exception
        except Exception as exception:
            self.logger.error(exception, exc_info=1)
            raise WebAPIException

    def getUserAccountInfo(self):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getUserAccountInfo, [])

    def login(self, username, password):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().login, [username, password])

    def refreshAuthToken(self, forceRereshToken = False):
        """
        Description:user refresh auth token
        @return: True if success, False if failed
        """
        return self.autoRepeatQuery(self.getFangCloudHttpClient().refreshAuthToken, [forceRereshToken])

    def logout(self):
        """
        Description:user logout
        @return: True if success, False if failed
        """
        return self.getFangCloudHttpClient().logout()

    def getFileSyncInfo(self, fileId):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getFileSyncInfo, [-fileId])

    def getFolderSyncInfo(self, folderId):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getFolderSyncInfo, [folderId])

    def getFileOwnerInfo(self, fileId):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getFileOwnerInfo, [-fileId])

    def getFolderOwnerInfo(self, folderId):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getFolderOwnerInfo, [folderId])

    def getResourceShareLink(self, serverId, resourceType):
        if resourceType == FILE_TYPE:
            serverId = -serverId
        response = self.autoRepeatQuery(self.getFangCloudHttpClient().getResourceShareLink, [serverId, resourceType])
        if response == False:
            raise RefreshTokenFailedException
        if response.has_key('unique_name'):
            return FangCloudUrl.URL['SHARE'] % response['unique_name']
        else:
            return None

    def createNewFolder(self, name, parentFolderId, mergeFolder = False, description = 'None Description'):
        response = self.autoRepeatQuery(self.getFangCloudHttpClient().createNewFolder, [name,
         parentFolderId,
         mergeFolder,
         description])
        if response['success'] == False:
            result = response
        else:
            result = {'id': response['id'],
             'parentId': response['parent_folder_id'],
             'name': response['name'],
             'type': DIRECTORY_TYPE,
             'size': response['size'],
             'success': True,
             'is_synced': response['is_synced']}
        return result

    def updateFolder(self, name, resourceId, sequenceId):
        response = self.autoRepeatQuery(self.getFangCloudHttpClient().updateFolder, [name, resourceId, sequenceId])
        if response['success'] == False:
            result = response
        else:
            result = {'id': response['id'],
             'parentId': response['parent_folder_id'] if type(response['parent_folder_id']) == int else int(response['parent_folder_id']),
             'name': response['name'],
             'type': FILE_TYPE,
             'size': response['size'],
             'sequenceId': response['sequence_id'],
             'success': True}
        return result

    def updateFile(self, name, resourceId, sequenceId):
        response = self.autoRepeatQuery(self.getFangCloudHttpClient().updateFile, [name, -resourceId, sequenceId])
        if response['success'] == False:
            result = response
        else:
            result = {'id': -response['id'],
             'parentId': response['parent_folder_id'] if type(response['parent_folder_id']) == int else int(response['parent_folder_id']),
             'name': response['name'],
             'type': FILE_TYPE,
             'size': response['size'],
             'sequenceId': response['sequence_id'],
             'success': True}
        return result

    def uploadNewFile(self, localPath, tempFilePath, parentFolderId, description = None):
        if os.path.exists(localPath):
            if localPath != tempFilePath:
                self.logger.debug('[Adapter] Copy local file (%s) to temp file (%s)', localPath, tempFilePath)
                shutil.copyfile(localPath, tempFilePath)
        else:
            raise WaitingOtherResourceException
        sha1 = Utils.sha1ForFile(localPath)
        checkExistResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().checkFileExistsOnServerAtTheSameDirWithTheSameName, [localPath,
         parentFolderId,
         sha1,
         description])
        if checkExistResponse['success'] == False or not checkExistResponse['is_file_existed']:
            presignResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().uploadNewFilePresign, [parentFolderId, localPath, description])
            if presignResponse.get('success', False):
                uploadURL = presignResponse['upload_url']
                response = self.autoRepeatQuery(self.getFangCloudHttpClient().uploadNewFile, [uploadURL, localPath, tempFilePath])
            else:
                response = presignResponse
            if response['success'] == False:
                result = response
            else:
                result = self.__formatUploadNewFileResponse(response)
            return result
        else:
            self.logger.debug('[Adapter] File (%s) exist on server', localPath)
            checkExistResponse['file_info']['success'] = checkExistResponse['success']
            checkExistResponse['file_info']['is_synced'] = checkExistResponse['is_synced']
            checkExistResponse['file_info']['unencrypted_sha1'] = Utils.sha1ForFile(localPath)
            response = checkExistResponse['file_info']
            return self.__formatUploadNewFileResponse(response)

    def __uploadNewFileWithoutPresign(self, localPath, tempFilePath, startMultiUploadResponse):
        """
        \xe8\xaf\xb4\xe6\x98\x8e:
        @param localPath:
        @param tempFilePath:
        @param startMultiUploadResponse:
        @return:
        """
        if os.path.exists(localPath):
            if localPath != tempFilePath:
                self.logger.debug('[Adapter] Copy local file (%s) to temp file (%s)', localPath, tempFilePath)
                shutil.copyfile(localPath, tempFilePath)
        else:
            raise WaitingOtherResourceException
        if startMultiUploadResponse.get('success', False):
            uploadURL = startMultiUploadResponse['upload_url']
            response = self.autoRepeatQuery(self.getFangCloudHttpClient().uploadNewFile, [uploadURL, localPath, tempFilePath])
        else:
            response = startMultiUploadResponse
        if response['success']:
            result = self.__formatUploadNewFileResponse(response)
        else:
            result = response
        return result

    def __uploadNewFileVersionWithoutPresign(self, localPath, tempFilePath, startMultiUploadResponse, description = 'UpdateNewVersion'):
        """
        \xe8\xaf\xb4\xe6\x98\x8e:
        @param localPath:
        @param tempFilePath:
        @param startMultiUploadResponse:
        @param description:
        @return:
        """
        if os.path.exists(localPath):
            if localPath != tempFilePath:
                shutil.copyfile(unicode(localPath), tempFilePath)
        else:
            raise WaitingOtherResourceException
        if startMultiUploadResponse.get('success', False):
            uploadURL = startMultiUploadResponse['upload_url']
            response = self.autoRepeatQuery(self.getFangCloudHttpClient().uploadNewFileVersion, [uploadURL,
             localPath,
             tempFilePath,
             description])
        else:
            response = startMultiUploadResponse
        if response['success']:
            result = self.__formatUploadNewFileResponse(response)
        else:
            result = response
        return result

    @staticmethod
    def __formatUploadNewFileResponse(response):
        return {'id': -response['id'],
         'parentId': response['parent_folder_id'],
         'name': response['name'],
         'type': FILE_TYPE,
         'size': response['size'] if type(response['size']) == int else int(response['size']),
         'sequenceId': response['sequence_id'],
         'success': True,
         'is_synced': response['is_synced'],
         'unencrypted_sha1': response['unencrypted_sha1'],
         'exist': response.get('exist', False)}

    def uploadNewFileV2(self, localPath, tempFilePath, parentFolderId, description = None):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x8a\xa0\xe4\xb8\x8a\xe4\xba\x86\xe6\x96\x87\xe4\xbb\xb6\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe5\xa4\x84\xe7\x90\x86,\xe7\xbb\xbc\xe5\x90\x88\xe4\xba\x86\xe6\x96\x87\xe4\xbb\xb6\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe5\x92\x8c\xe6\x96\x87\xe4\xbb\xb6\xe6\x99\xae\xe9\x80\x9a\xe4\xbc\xa0\xe8\xbe\x93\xe5\x8a\x9f\xe8\x83\xbd
        @param localPath:
        @param tempFilePath:
        @param parentFolderId:
        @param description:
        @return:
        """
        try:
            self.logger.debug('[Adapter] enter multiupload new file main process, file (%s)', localPath)
            if os.path.exists(localPath):
                if localPath != tempFilePath:
                    self.logger.debug('[Adapter] Copy local file (%s) to temp file (%s)', localPath, tempFilePath)
                    shutil.copyfile(localPath, tempFilePath)
            else:
                raise WaitingOtherResourceException
            sha1 = Utils.sha1ForFile(localPath)
            checkExistResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().checkFileExistsOnServerAtTheSameDirWithTheSameName, [localPath,
             parentFolderId,
             sha1,
             description])
            if checkExistResponse['success'] == False or not checkExistResponse['is_file_existed']:
                localId1, localId2 = self.localFileSystem.getResourceIndex(localPath)
                self.__checkFileSha1(localId1, localId2, sha1)
                isInterruptUpload, uploadGetResponse = self.__isInterruptUpload(localId1, localId2)
                if isInterruptUpload:
                    if uploadGetResponse.get('success', False):
                        return self.__multiInterruptUploadNewFile(localPath, tempFilePath, localId1, localId2, uploadGetResponse, sha1)
                    else:
                        return uploadGetResponse
                else:
                    isMultiUpLoadNewFile, response = self.__isMultiUploadNewFile(localPath, parentFolderId, sha1)
                    if response.get('success', False) and isMultiUpLoadNewFile:
                        return self.__multiUploadNewFile(localPath, tempFilePath, response, sha1)
                    elif response.get('success', False) and not isMultiUpLoadNewFile:
                        self.logger.debug('[Adapter] upload file in original way file (%s)', localPath)
                        return self.__uploadNewFileWithoutPresign(localPath, tempFilePath, response)
                    else:
                        return response
            else:
                self.logger.debug('[Adapter] File (%s) exist on server', localPath)
                fileId = -checkExistResponse['file_info']['id']
                checkExistResponse['file_info']['success'] = checkExistResponse['success']
                checkExistResponse['file_info']['exist'] = True
                checkExistResponse['file_info']['is_synced'] = checkExistResponse['is_synced']
                checkExistResponse['file_info']['unencrypted_sha1'] = Utils.sha1ForFile(localPath)
                ServerResourceAttribute.CreateTime[fileId] = checkExistResponse.get('created_at', time())
                ServerResourceAttribute.ModifyTime[fileId] = checkExistResponse.get('modified_at', time())
                response = checkExistResponse['file_info']
                return self.__formatUploadNewFileResponse(response)
        except CheckSumExpiredException:
            self.__checkSumExpiredRecovery(localId1, localId2)
            raise OperationRetryException

    def uploadNewFileVersionV2(self, localPath, tempFilePath, resourceId, sequenceId, description = 'UpdateNewVersion'):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe4\xb8\x8a\xe4\xbc\xa0\xe6\x96\x87\xe4\xbb\xb6\xe6\x96\xb0\xe7\x89\x88\xe6\x9c\xac\xe6\x8e\xa5\xe5\x8f\xa3,\xe7\xbb\xbc\xe5\x90\x88\xe4\xba\x86\xe6\x96\x87\xe4\xbb\xb6\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe5\x92\x8c\xe6\x96\x87\xe4\xbb\xb6\xe6\x99\xae\xe9\x80\x9a\xe4\xb8\x8a\xe4\xbc\xa0
        @param localPath:
        @param tempFilePath:
        @param resourceId:
        @param sequenceId:
        @param description:
        @return:
        """
        try:
            self.logger.debug('[Adapter] enter multiupload new version main process, file (%s)', localPath)
            self.treeDatabase.getResourceByServerId(resourceId)
            if os.path.exists(localPath):
                if localPath != tempFilePath:
                    self.logger.debug('[Adapter] Copy local file (%s) to temp file (%s)', localPath, tempFilePath)
                    shutil.copyfile(localPath, tempFilePath)
            else:
                raise WaitingOtherResourceException
            sha1 = Utils.sha1ForFile(localPath)
            treeResource = self.treeDatabase.getResourceByServerId(resourceId)
            localId1 = treeResource.local_id1
            localId2 = treeResource.local_id2
            self.__checkFileSha1(localId1, localId2, sha1)
            isInterruptUploadOrNot, uploadGetResponse = self.__isInterruptUpload(localId1, localId2)
            if isInterruptUploadOrNot:
                if uploadGetResponse.get('success', False):
                    return self.__multiInterruptUploadNewFile(localPath, tempFilePath, localId1, localId2, uploadGetResponse, sha1)
                else:
                    return uploadGetResponse
            else:
                isMultiUpLoadNewFileOrNot, response = self.__isMultiUploadNewVersionOrNot(localPath, -resourceId, sequenceId, sha1)
                if response.get('success', False) and isMultiUpLoadNewFileOrNot:
                    return self.__multiUploadNewFileVersion(localPath, tempFilePath, resourceId, sequenceId, response, sha1)
                if response.get('success', False) and not isMultiUpLoadNewFileOrNot:
                    self.logger.debug('[Adapter] upload new version in original way file (%s)', localPath)
                    return self.__uploadNewFileVersionWithoutPresign(localPath, tempFilePath, response, description)
                return response
        except CheckSumExpiredException:
            self.__checkSumExpiredRecovery(localId1, localId2)
            raise OperationRetryException

    def multiUploadAbort(self, localId1, localId2):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe4\xb8\xad\xe6\x96\xad\xe5\x88\x86\xe5\x9d\x97\xe4\xbc\xa0\xe8\xbe\x93\xe6\x8e\xa5\xe5\x8f\xa3
        @param localId1:
        @param localId2:
        @return:
        """
        try:
            multiUploadRecord = self.multiUploadRecordDatabase.getMultiUploadRecord(localId1, localId2)
            if multiUploadRecord is not None:
                abortUrl = multiUploadRecord['server_url'] + '/abort_upload'
                self.autoRepeatQuery(self.getFangCloudHttpClient().multiUploadAbort, [abortUrl,
                 multiUploadRecord['upload_id'],
                 multiUploadRecord['upload_token'],
                 multiUploadRecord['checksum']])
                self.clearLocalMultiUploadData(localId1, localId2)
        except CheckSumExpiredException as exception:
            self.__checkSumExpiredRecovery(localId1, localId2)
            raise OperationRetryException

    def clearLocalMultiUploadData(self, localId1, localId2):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe6\xb8\x85\xe9\x99\xa4\xe6\x9c\xac\xe5\x9c\xb0\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x95\xb0\xe6\x8d\xae
        @param localId1:
        @param localId2:
        @return:
        """
        localPath = self.treeDatabase.getLocalPathByLocalId(localId1, localId2)
        HttpStatistic.FinishedUploadByte(localPath)
        self.multiUploadRecordDatabase.removeMultiUploadRecordByLocalId(localId1, localId2)
        self.__delSha1CacheById(localId1, localId2)

    def __updateChecksumNewFile(self, localId1, localId2, folderId):
        """
        \xe6\x9b\xb4\xe6\x96\xb0checksum-\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x96\xb0\xe6\x96\x87\xe4\xbb\xb6\xe6\x97\xb6\xe4\xbd\xbf\xe7\x94\xa8
        @param localId1:
        @param localId2:
        @param folderId:
        @return:
        """
        multiUploadRecord = self.multiUploadRecordDatabase.getMultiUploadRecord(localId1, localId2)
        if multiUploadRecord is not None:
            checkSumGetResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().getChecksumNewFile, [multiUploadRecord['upload_id'], folderId])
            if checkSumGetResponse.get('success', False):
                self.multiUploadRecordDatabase.updateChecksumByLocalId(localId1, localId2, checkSumGetResponse['checksum'], checkSumGetResponse['upload_token'])

    def __updateChecksumNewVersion(self, localId1, localId2, resourseId):
        """
        \xe6\x9b\xb4\xe6\x96\xb0checksum-\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x96\x87\xe4\xbb\xb6\xe6\x96\xb0\xe7\x89\x88\xe6\x9c\xac\xe6\x97\xb6\xe4\xbd\xbf\xe7\x94\xa8
        @param localId1:
        @param localId2:
        @param resourseId:
        @return:
        """
        multiUploadRecord = self.multiUploadRecordDatabase.getMultiUploadRecord(localId1, localId2)
        if multiUploadRecord is not None:
            checkSumGetResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().getChecksumNewVersion, [multiUploadRecord['upload_id'], resourseId])
            if checkSumGetResponse.get('success', False):
                self.multiUploadRecordDatabase.updateChecksumByLocalId(localId1, localId2, checkSumGetResponse['checksum'], checkSumGetResponse['upload_token'])

    def __checkFileSha1(self, localId1, localId2, sha1):
        """
        \xe8\xaf\xb4\xe6\x98\x8e:\xe6\xa3\x80\xe6\x9f\xa5\xe6\x96\x87\xe4\xbb\xb6sha1\xe4\xb8\x8e\xe6\x95\xb0\xe6\x8d\xae\xe5\xba\x93sha1\xe7\x9a\x84\xe4\xb8\x80\xe8\x87\xb4\xe6\x80\xa7
        @param localId2:
        @return:
        """
        multiUploadRecord = self.multiUploadRecordDatabase.getMultiUploadRecord(localId1, localId2)
        if multiUploadRecord is not None:
            if sha1 != multiUploadRecord['sha1']:
                self.logger.debug('[Adapter] File has changed and multiupload abort')
                self.multiUploadAbort(localId1, localId2)

    def __checkSumExpiredRecovery(self, localId1, localId2):
        """
        \xe8\xaf\xb4\xe6\x98\x8e:checksum\xe8\xbf\x87\xe6\x9c\x9f\xe4\xbf\xae\xe5\xa4\x8d\xe7\xa8\x8b\xe5\xba\x8f
        @param localId1:
        @param localId2:
        @return:
        """
        treeRecord = self.treeDatabase.getResourceByLocalId(localId1, localId2)
        if treeRecord is not None:
            if treeRecord.server_id != INVALID_RESOURCE_ID:
                self.__updateChecksumNewVersion(localId1, localId2, -treeRecord.server_id)
            else:
                parentRecord = self.treeDatabase.getResourceByLocalId(treeRecord.local_parent_id1, treeRecord.local_parent_id2)
                self.__updateChecksumNewFile(localId1, localId2, parentRecord.server_id)

    def __isInterruptUpload(self, localId1, localId2):
        """
        \xe5\x88\xa4\xe6\x96\xad\xe6\x98\xaf\xe6\x96\xad\xe7\x82\xb9\xe7\xbb\xad\xe4\xbc\xa0\xe8\xbf\x98\xe6\x98\xaf\xe9\x87\x8d\xe6\x96\xb0\xe7\x94\xb3\xe8\xaf\xb7\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0
        @param localId1:
        @param localId2:
        @return:
        """
        multiUploadRecord = self.multiUploadRecordDatabase.getMultiUploadRecord(localId1, localId2)
        if multiUploadRecord is not None:
            multiUploadGetResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().multiUploadGet, [multiUploadRecord['server_url'] + '/get_uploads',
             multiUploadRecord['upload_id'],
             multiUploadRecord['upload_token'],
             multiUploadRecord['checksum']])
            return (True, multiUploadGetResponse)
        else:
            return (False, None)

    def __isMultiUploadNewFile(self, localPath, folderId, sha1):
        """
        \xe4\xb8\x8a\xe4\xbc\xa0\xe6\x96\xb0\xe6\x96\x87\xe4\xbb\xb6\xe6\x97\xb6,\xe5\x88\xa4\xe6\x96\xad\xe6\x98\xaf\xe5\x90\xa6\xe9\x9c\x80\xe8\xa6\x81\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0
        @param localPath:
        @param folderId:
        @param sha1:
        @return:
        """
        startMultiUploadResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().startMultiUploadNewFile, [localPath, folderId, sha1])
        if startMultiUploadResponse.get('success', False):
            if startMultiUploadResponse.get('multi', False):
                return (True, startMultiUploadResponse)
            else:
                return (False, startMultiUploadResponse)
        else:
            startMultiUploadResponse['success'] = False
            return (False, startMultiUploadResponse)

    def __isMultiUploadNewVersionOrNot(self, localPath, fileId, sequenceId, sha1):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x88\xa4\xe6\x96\xad\xe6\x98\xaf\xe5\x90\xa6\xe9\x9c\x80\xe8\xa6\x81\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x96\x87\xe4\xbb\xb6-\xe5\xaf\xb9\xe6\x96\x87\xe4\xbb\xb6\xe6\x96\xb0\xe7\x89\x88\xe6\x9c\xac\xe6\x97\xb6\xe6\x9c\x89\xe6\x95\x88
        @param localPath:
        @param fileId:
        @param sequenceId:
        @param sha1:
        @return:
        """
        startMultiUploadResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().startMultiUploadNewFileVersion, [localPath,
         fileId,
         sequenceId,
         sha1])
        if startMultiUploadResponse.get('success', False):
            if startMultiUploadResponse.get('multi', False):
                return (True, startMultiUploadResponse)
            else:
                return (False, startMultiUploadResponse)
        else:
            startMultiUploadResponse['success'] = False
            return (False, startMultiUploadResponse)

    def __multiInterruptUploadNewFile(self, localPath, tempPath, localId1, localId2, mutiUploadGetResponse, sha1):
        """
        \xe5\x88\x86\xe5\x9d\x97\xe6\x96\xad\xe7\x82\xb9\xe7\xbb\xad\xe4\xbc\xa0\xe6\x8e\xa5\xe5\x8f\xa3
        @param localPath:
        @param localId1:
        @param localId2:
        @param mutiUploadGetResponse:
        @param sha1:
        @return:
        """
        self.logger.debug('[Adapter] Start Interrupt multiupload file (%s)', localPath)
        multiUploadRecord = self.multiUploadRecordDatabase.getMultiUploadRecord(localId1, localId2)
        if multiUploadRecord is not None:
            uploadId = multiUploadRecord['upload_id']
            uploadToken = multiUploadRecord['upload_token']
            checkSum = multiUploadRecord['checksum']
            blockSize = multiUploadRecord['block_size']
            if mutiUploadGetResponse.get('success', False):
                uploadParts = mutiUploadGetResponse.get('upload_parts')
                blockNum = multiUploadRecord['block_num']
                blockTransState = {}
                for i in range(1, blockNum + 1, 1):
                    blockTransState[i] = False

                SyncingFileList.SyncingFileSet.add(localPath)
                self.__computeSha1ForAllBlocks(localPath, localId1, localId2, blockNum, blockSize)
                alreadyUploadByteNumer = 0
                for items in uploadParts:
                    curBlockId = items['id']
                    if blockTransState.has_key(curBlockId) and items['sha1'] == self.__getSha1ByIdAndIndex(localId1, localId2, curBlockId):
                        alreadyUploadByteNumer += items['size']
                        blockTransState[curBlockId] = True

                HttpStatistic.AddUploadByteSkipSpeed(localPath, alreadyUploadByteNumer)
                return self.__multiUploadCoreProcess(localId1, localId2, localPath, tempPath, multiUploadRecord['server_url'], uploadId, uploadToken, checkSum, blockTransState, uploadParts, blockNum, blockSize)

    @staticmethod
    def __getFileStartPosAndBlockSize(fileSize, blockNum, blockSize, blockIndex):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe8\x8e\xb7\xe5\x8f\x96\xe6\x96\x87\xe4\xbb\xb6\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe7\x9a\x84\xe6\x8c\x87\xe5\xae\x9a\xe5\x9d\x97\xe7\x9a\x84\xe5\xbc\x80\xe5\xa7\x8b\xe4\xbd\x8d\xe7\xbd\xae\xe5\x92\x8c\xe5\x9d\x97\xe5\xa4\xa7\xe5\xb0\x8f
        @param localPath:
        @param blockNum:
        @param blockSize:
        @param blockIndex:
        @return:
        """
        start = (blockIndex - 1) * blockSize
        if blockIndex == blockNum:
            realBlockSize = fileSize - (blockIndex - 1) * blockSize
        else:
            realBlockSize = blockSize
        return (start, realBlockSize)

    def __computeSha1ForAllBlocks(self, localPath, localId1, localId2, blockNum, blockSize):
        """
        \xe8\xae\xa1\xe7\xae\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x96\x87\xe4\xbb\xb6\xe6\xaf\x8f\xe5\x9d\x97\xe7\x9a\x84sha1
        @param localPath:
        @param blockNum:
        @param blockSize:
        @return:
        """
        if not os.path.exists(localPath):
            return
        try:
            fileSize = os.path.getsize(localPath)
            fileToRead = open(localPath, 'rb')
            keyForFile = str(localId1) + '_' + str(localId2)
            SyncingFileList.SyncingSha1ForFileBlocks[keyForFile] = {}
            for i in range(1, blockNum + 1, 1):
                start, realBlockSize = self.__getFileStartPosAndBlockSize(fileSize, blockNum, blockSize, i)
                sha1ForBlock = Utils.sha1ForBlock(fileToRead, start, realBlockSize)
                SyncingFileList.SyncingSha1ForFileBlocks[keyForFile][i] = sha1ForBlock

        except IOError as exception:
            return
        finally:
            if locals().has_key('fileToRead'):
                fileToRead.close()

    @staticmethod
    def __getSha1ByIdAndIndex(localId1, localId2, index):
        """
        \xe4\xbb\x8e\xe5\x86\x85\xe5\xad\x98\xe4\xb8\xad\xe8\x8e\xb7\xe5\x8f\x96\xe6\x8c\x87\xe5\xae\x9a\xe5\x9d\x97\xe7\x9a\x84sha1
        @param localId1:
        @param localId2:
        @param index:
        @return:
        """
        keyForFile = str(localId1) + '_' + str(localId2)
        try:
            if keyForFile in SyncingFileList.SyncingSha1ForFileBlocks:
                return SyncingFileList.SyncingSha1ForFileBlocks[keyForFile][index]
        except ValueError:
            return None

    @staticmethod
    def __delSha1CacheById(localId1, localId2):
        keyForFile = str(localId1) + '_' + str(localId2)
        if keyForFile in SyncingFileList.SyncingSha1ForFileBlocks:
            del SyncingFileList.SyncingSha1ForFileBlocks[keyForFile]

    @staticmethod
    def __isMultiUploadFinish(blockTransState):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x88\xa4\xe6\x96\xad\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x98\xaf\xe5\x90\xa6\xe5\xae\x8c\xe6\x88\x90
        @param blockTransState:
        @return:
        """
        for key in blockTransState.keys():
            if not blockTransState[key]:
                return False

        return True

    def __multiUploadProcess(self, localPath, tempFilePath, localId1, localId2, sequenceId, startMutiUploadResponse, sha1):
        """
        \xe6\x8a\xbd\xe8\xb1\xa1\xe5\x87\xba\xe6\x9d\xa5\xe7\x9a\x84\xe5\x88\x86\xe5\x9d\x97\xe4\xbc\xa0\xe8\xbe\x93\xe5\x85\xac\xe5\x85\xb1\xe9\x80\xbb\xe8\xbe\x91
        @param localPath:
        @param tempFilePath:
        @param localId1:
        @param localId2:
        @param startMutiUploadResponse:
        @param sha1:
        @return:
        """
        self.logger.debug('[Adapter] multiupload file (%s)', localPath)
        if startMutiUploadResponse.get('success', False) and startMutiUploadResponse.get('multi', False):
            uploadServer = startMutiUploadResponse['upload_server']
            uploadId = startMutiUploadResponse['upload_id']
            uploadToken = startMutiUploadResponse['upload_token']
            checkSum = startMutiUploadResponse['checksum']
            fileSize = os.path.getsize(tempFilePath)
            blockSize = startMutiUploadResponse['block_size']
            blockNum = int(math.ceil(fileSize / float(blockSize)))
            record = {'local_id1': localId1,
             'local_id2': localId2,
             'local_sequence_id': sequenceId,
             'server_url': uploadServer,
             'block_num': blockNum,
             'upload_id': uploadId,
             'upload_token': uploadToken,
             'checksum': checkSum,
             'block_size': blockSize,
             'sha1': sha1}
            self.multiUploadRecordDatabase.insertMultiUploadRecord(record)
            blockTransState = {}
            blockTransPart = []
            for i in range(1, blockNum + 1, 1):
                blockTransState[i] = False

            SyncingFileList.SyncingFileSet.add(localPath)
            self.__computeSha1ForAllBlocks(localPath, localId1, localId2, blockNum, blockSize)
            return self.__multiUploadCoreProcess(localId1, localId2, localPath, tempFilePath, uploadServer, uploadId, uploadToken, checkSum, blockTransState, blockTransPart, blockNum, blockSize)

    def __multiUploadCoreProcess(self, localId1, localId2, localPath, tempFilePath, uploadServer, uploadId, uploadToken, checkSum, blockTransState, blockTransPart, blockNum, blockSize):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe4\xb8\xba\xe4\xba\x86\xe5\x87\x8f\xe5\xb0\x91\xe4\xbb\xa3\xe7\xa0\x81\xe9\x87\x8d\xe5\xa4\x8d\xe5\xa2\x9e\xe5\x8a\xa0\xe7\x9a\x84\xe6\x8e\xa5\xe5\x8f\xa3
        @param localId1:
        @param localId2:
        @param localPath:
        @param tempFilePath:
        @param uploadServer:
        @param uploadId:
        @param checkSum:
        @param blockTransState:
        @param blockTransPart:
        @param blockNum:
        @param blockSize:
        @return:
        """
        fileSize = os.path.getsize(localPath)
        uploadUrl = uploadServer + '/multi_upload'
        while not self.__isMultiUploadFinish(blockTransState):
            for i in range(1, blockNum + 1):
                if not blockTransState.get(i):
                    start, realBlockSize = self.__getFileStartPosAndBlockSize(fileSize, blockNum, blockSize, i)
                    blockSha1 = self.__getSha1ByIdAndIndex(localId1, localId2, i)
                    blockUploadResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().multiUploadNewFile, [uploadUrl,
                     localPath,
                     tempFilePath,
                     i,
                     uploadId,
                     uploadToken,
                     checkSum,
                     start,
                     realBlockSize,
                     blockSha1])
                    if blockUploadResponse.get('success', False):
                        blockTransPart.append(blockUploadResponse['upload_part'])
                        blockTransState[i] = True
                    else:
                        self.logger.debug('[FangCloudHttpAdapter] failed to multi upload file')
                        return blockUploadResponse

        return self.__multiUploadFileFinish(localPath, localId1, localId2, blockTransPart)

    def __multiUploadNewFile(self, localPath, tempFilePath, startMutiUploadResponse, sha1):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x96\xb0\xe6\x96\x87\xe4\xbb\xb6
        @param localPath:
        @param tempFilePath:
        @param startMutiUploadResponse:
        @param sha1:
        @return:
        """
        localId1, localId2 = self.localFileSystem.getResourceIndex(localPath)
        return self.__multiUploadProcess(localPath, tempFilePath, localId1, localId2, INVALID_SEQUENCE_ID, startMutiUploadResponse, sha1)

    def __multiUploadNewFileVersion(self, localPath, tempFilePath, fileId, sequenceId, startMutiUploadResponse, sha1):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x96\x87\xe4\xbb\xb6-\xe6\x96\xb0\xe7\x89\x88\xe6\x9c\xac
        @param localPath:
        @param tempFilePath:
        @param fileId:
        @param sequenceId:
        @param startMutiUploadResponse:
        @param sha1:
        @return:
        """
        treeResource = self.treeDatabase.getResourceByServerId(fileId)
        localId1 = treeResource.local_id1
        localId2 = treeResource.local_id2
        return self.__multiUploadProcess(localPath, tempFilePath, localId1, localId2, sequenceId, startMutiUploadResponse, sha1)

    def __multiUploadFileFinish(self, localPath, localId1, localId2, blockTransPart):
        """
        \xe8\xaf\xb4\xe6\x98\x8e: \xe9\x80\x9a\xe7\x9f\xa5\xe5\x88\x86\xe5\x9d\x97\xe4\xb8\x8a\xe4\xbc\xa0\xe6\x9c\x8d\xe5\x8a\xa1\xe5\x99\xa8\xe5\x88\x86\xe5\x9d\x97\xe4\xbc\xa0\xe8\xbe\x93\xe5\xae\x8c\xe6\x88\x90
        @param localPath:
        @param localId1:
        @param localId2:
        @param blockTransPart:
        @return:
        """
        multiUploadRecord = self.multiUploadRecordDatabase.getMultiUploadRecord(localId1, localId2)
        uploadServer = multiUploadRecord['server_url']
        uploadFinishUrl = uploadServer + '/finish_upload'
        uploadId = multiUploadRecord['upload_id']
        uploadToken = multiUploadRecord['upload_token']
        checkSum = multiUploadRecord['checksum']
        sha1 = multiUploadRecord['sha1']
        finishUploadResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().multiUploadFinish, [localPath,
         uploadFinishUrl,
         uploadId,
         uploadToken,
         checkSum,
         blockTransPart,
         sha1])
        if finishUploadResponse.get('success', False):
            self.clearLocalMultiUploadData(localId1, localId2)
            result = {'id': -finishUploadResponse['id'],
             'parentId': finishUploadResponse['parent_folder_id'],
             'name': finishUploadResponse['name'],
             'type': finishUploadResponse['type'],
             'size': finishUploadResponse['size'] if type(finishUploadResponse['size']) == int else int(finishUploadResponse['size']),
             'sequenceId': finishUploadResponse['sequence_id'],
             'success': True,
             'is_synced': finishUploadResponse['is_synced'],
             'unencrypted_sha1': finishUploadResponse['unencrypted_sha1']}
        else:
            result = finishUploadResponse
        return result

    def uploadNewFileVersion(self, localPath, tempFilePath, resourceId, sequenceId, description = 'UpdateNewVersion'):
        if os.path.exists(localPath):
            if localPath != tempFilePath:
                shutil.copyfile(unicode(localPath), tempFilePath)
        else:
            raise WaitingOtherResourceException
        size = os.path.getsize(localPath)
        name = Utils.getNameFromPath(localPath)
        modifiedAt = Utils.getModifyTime(localPath)
        presignResponse = self.autoRepeatQuery(self.getFangCloudHttpClient().uploadNewFileVersionPresign, [-resourceId,
         sequenceId,
         size,
         name,
         modifiedAt])
        if presignResponse.get('success', False):
            uploadURL = presignResponse['upload_url']
            response = self.autoRepeatQuery(self.getFangCloudHttpClient().uploadNewFileVersion, [uploadURL,
             localPath,
             tempFilePath,
             description])
        else:
            response = presignResponse
        if response['success']:
            result = self.__formatUploadNewFileResponse(response)
        else:
            result = response
        return result

    def deleteFilesAndDirectories(self, fileIds, directoryIds, unsyncFileIds, unsyncDirectoryIds, enableCheckUnsync = False, forceDelete = False):
        """
        Description: delete files and directories by id
        @return: True if success; False if failed
        """
        fileIdsToDelete = []
        fileIdsToUnsync = []
        for fileId in fileIds:
            fileIdsToDelete.append(-fileId)

        for fileId in unsyncFileIds:
            fileIdsToUnsync.append(-fileId)

        return self.autoRepeatQuery(self.getFangCloudHttpClient().deleteFilesAndDirectories, [fileIdsToDelete,
         directoryIds,
         fileIdsToUnsync,
         unsyncDirectoryIds,
         enableCheckUnsync,
         forceDelete])

    def moveFilesAndDirectories(self, targetFoldId, sequenceId, fileId = INVALID_RESOURCE_ID, directoryId = INVALID_RESOURCE_ID):
        """
        Description: move files and directories by id
        @return: True if success; False if failed
        """
        if fileId != INVALID_RESOURCE_ID:
            fileId = -fileId
        return self.autoRepeatQuery(self.getFangCloudHttpClient().moveFilesAndDirectories, [targetFoldId,
         sequenceId,
         fileId,
         directoryId])

    def downloadFile(self, fileId, tempPath, fileLocalPathToStore):
        """
        Description: download files by file id
        @fileId: int
        @fileLocalPathToStore: string
        @return: True if success, False if failed
        """
        return self.autoRepeatQuery(self.getFangCloudHttpClient().downloadFile, [-fileId, tempPath, fileLocalPathToStore])

    def getSyncedFolders(self):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getSyncedFolders, [])

    def getSyncedFiles(self):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getSyncedFiles, [])

    def getPagedSyncedFiles(self, pageId):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getPagedSyncedFiles, [pageId])

    def getSyncedFilesByPage(self):
        syncedFiles = []
        pageId = 1
        while True:
            result = self.getPagedSyncedFiles(pageId)
            syncedFiles += result['files']
            if not result.get('has_more', False):
                break
            pageId += 1

        return syncedFiles

    def getSynedFolderChildren(self, folderId, isSyncedFolder = True):
        isSecurityTokenExpired = True
        while isSecurityTokenExpired:
            isSecurityTokenExpired = False
            responseIds = self.autoRepeatQuery(self.getFangCloudHttpClient().getSynedFolderChildrenIds, [folderId, isSyncedFolder])
            filesRtn = []
            foldersRtn = []
            if responseIds.get('success', False) == True:
                pageSize = 5000
                foldersSplit = Utils.splitArrayByFixedSize(responseIds['folders'], pageSize)
                filesSplit = Utils.splitArrayByFixedSize(responseIds['files'], pageSize)
                totalLen = 0
                for curIndex1 in filesSplit:
                    totalLen += len(curIndex1)

                isSuccess = True
                if len(filesSplit) > len(foldersSplit):
                    lenMax = len(filesSplit)
                else:
                    lenMax = len(foldersSplit)
                for iCur in range(0, lenMax):
                    foldersRequest = []
                    filesRequest = []
                    if iCur < len(filesSplit):
                        filesRequest = filesSplit[iCur]
                    if iCur < len(foldersSplit):
                        foldersRequest = foldersSplit[iCur]
                    bulkTemp = self.autoRepeatQuery(self.getFangCloudHttpClient().getSyncedBulkInfo, [foldersRequest, filesRequest, responseIds['secure_token']])
                    if bulkTemp.get('success', False) == False:
                        isSuccess = False
                        if bulkTemp.get('error', '') == 'sync_bulk_get_invalid':
                            isSecurityTokenExpired = True
                        break
                    filesRtn = filesRtn + bulkTemp['files']
                    foldersRtn = foldersRtn + bulkTemp['folders']

            else:
                isSuccess = False
            if isSecurityTokenExpired:
                sleep(1)
                continue
            if isSuccess:
                return (foldersRtn, filesRtn)
            return ([], [])

    def markFolderAsSynced(self, folderId):
        response = self.autoRepeatQuery(self.getFangCloudHttpClient().markFolderAsSynced, [folderId])
        return response['success']

    def markFolderAsUnSynced(self, folderId):
        response = self.autoRepeatQuery(self.getFangCloudHttpClient().markFolderAsUnSynced, [folderId])
        return response['success']

    def uploadCrashLog(self, uploadPathList):
        aliyunInfo = self.autoRepeatQuery(self.getFangCloudHttpClient().getAliyunAccessLog, [uploadPathList.keys()])
        auth = oss2.Auth(aliyunInfo['access_key'], aliyunInfo['access_secret'])
        bucket = oss2.Bucket(auth, 'oss-cn-hangzhou.aliyuncs.com', aliyunInfo['bucket'])
        tempResourceController = TempResourceController()
        for fileName in uploadPathList.keys():
            filePath = uploadPathList[fileName]
            tempFilePath = tempResourceController.getRandomFileNameOnTempPath()
            shutil.copyfile(filePath, tempFilePath)
            objectKey = aliyunInfo['object_keys'][fileName]
            with open(tempFilePath, 'rb') as fileobj:
                repeatCount = 0
                while True:
                    try:
                        result = bucket.put_object(aliyunInfo['object_keys'][fileName], fileobj, headers={'x-oss-security-token': aliyunInfo['security_token']})
                        self.logger.debug('request_id: {0}'.format(result.request_id))
                        break
                    except Exception as exception:
                        if repeatCount > 0:
                            self.logger.error(exception, exc_info=1)
                            raise exception
                        else:
                            repeatCount += 1

            os.remove(tempFilePath)
            self.autoRepeatQuery(self.getFangCloudHttpClient().uploadCrashLogCallBack, [objectKey])

    def downloadUpdateFile(self, url, localPath):
        """
        Description: download sync app update file to local
        url: file url to be download
        localPath: file path to store
        """
        client = self.getFangCloudHttpClient()
        return client.downloadUpdateFile(url, localPath)

    def lockResource(self, serverId):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().lockResource, [-serverId])

    def unlockResource(self, serverId):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().unlockResource, [-serverId])

    def clearResourceOnServer(self):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().clearResourceOnServer, [])

    def getAllServerItems(self):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getAllServerItems, [])

    def clientVersionCheck(self):
        try:
            return self.autoRepeatQuery(self.getFangCloudHttpClient().clientVersionCheck, [])
        except AutoRepeatQueryException:
            return {'success': True}

    def getRealTimeUri(self):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().getRealTimeUri, [])

    def inviteUser(self, folderId, users):
        return self.autoRepeatQuery(self.getFangCloudHttpClient().invite, [folderId, users])
+++ okay decompyling FangCloudHttpAdapter.pyc 
# decompiled 1 files: 1 okay, 0 failed, 0 verify failed
# 2016.10.21 16:37:04 CST
