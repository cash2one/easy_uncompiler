# 2016.10.21 16:38:15 CST
#Embedded file name: com/fangcloud/httpconnection/FangCloudUrls.pyc
"""
Created on 2014-10-16

@author: renjun
"""
from com.fangcloud.utils import Utils
from com.fangcloud.utils.Utils import BuildType

class FangCloudUrl:
    URL = {}
    UPLOAD_HOST = None
    HOST = None
    REALTIME_FETCH_ADDRESS_URL = None

    @staticmethod
    def LoadHost():
        if Utils.SYNC_BUILD == BuildType.Test:
            FangCloudUrl.HOST = 'https://staging.fangcloud.net'
            FangCloudUrl.API_HOST = 'https://api.fangcloud.net' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://rlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.Production:
            FangCloudUrl.HOST = 'https://www.fangcloud.com'
            FangCloudUrl.API_HOST = 'https://api.fangcloud.com' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.com'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'http://rlb.fangcloud.com/server_info'
        elif Utils.SYNC_BUILD == BuildType.Dev:
            FangCloudUrl.HOST = 'https://syncdev.fangcloud.net'
            FangCloudUrl.API_HOST = 'https://syncdevapi.fangcloud.net' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://syncdevupload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://syncdevrlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.syj:
            FangCloudUrl.HOST = 'https://staging.fangcloud.net'
            FangCloudUrl.API_HOST = 'http://syj.fangcloud.net' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://rlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.master2:
            FangCloudUrl.HOST = 'https://master2.fangcloud.net'
            FangCloudUrl.API_HOST = 'https://api2.fangcloud.net' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://rlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.Zhangli:
            FangCloudUrl.HOST = 'http://zhangli.fangcloud.net'
            FangCloudUrl.API_HOST = 'https://api.fangcloud.net' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://rlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.DecathlonTest:
            FangCloudUrl.HOST = 'https://decathlontest.fangcloud.net'
            FangCloudUrl.API_HOST = 'https://api2.fangcloud.net' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://rlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.DecathlonProduction:
            FangCloudUrl.HOST = 'https://decathlon.fangcloud.com'
            FangCloudUrl.API_HOST = 'https://api.fangcloud.com' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.com'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'http://rlb.fangcloud.com/server_info'
        elif Utils.SYNC_BUILD == BuildType.master2:
            FangCloudUrl.HOST = 'https://master2.fangcloud.net'
            FangCloudUrl.API_HOST = 'https://api2.fangcloud.net' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://rlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.trTest:
            FangCloudUrl.HOST = 'http://jinko.fangcloud.net'
            FangCloudUrl.API_HOST = 'http://jinko.fangcloud.net' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://rlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.jkTest:
            FangCloudUrl.HOST = 'http://cloud.jinkosolar.com:81'
            FangCloudUrl.API_HOST = 'http://cloud.jinkosolar.com:81/sync' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://rlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.zsuTest:
            FangCloudUrl.HOST = 'https://cloud.zjnu.edu.cn'
            FangCloudUrl.API_HOST = 'https://cloud.zjnu.edu.cn' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.net'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'https://rlb.fangcloud.net/server_info'
        elif Utils.SYNC_BUILD == BuildType.zsuProduction:
            FangCloudUrl.HOST = 'https://cloud.zjnu.edu.cn'
            FangCloudUrl.API_HOST = 'https://cloud.zjnu.edu.cn' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.com'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'http://rlb.fangcloud.com/server_info'
        elif Utils.SYNC_BUILD == BuildType.trProduction:
            FangCloudUrl.HOST = 'https://trcloud.fangcloud.com'
            FangCloudUrl.API_HOST = 'https://api.fangcloud.com' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.com'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'http://rlb.fangcloud.com/server_info'
        elif Utils.SYNC_BUILD == BuildType.jkProduction:
            FangCloudUrl.HOST = 'http://cloud.jinkosolar.com:81'
            FangCloudUrl.API_HOST = 'http://cloud.jinkosolar.com:81/sync' if Utils.SYNC_ENABLE_API_HOST else FangCloudUrl.HOST
            FangCloudUrl.UPLOAD_HOST = 'https://upload.fangcloud.com'
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = 'http://rlb.fangcloud.com/server_info'

    @staticmethod
    def ReloadUrls(host = None, uploadHost = None, realtimeFetchUrl = None, apiHost = None):
        if host is not None:
            FangCloudUrl.HOST = host
        if uploadHost is not None:
            FangCloudUrl.UPLOAD_HOST = uploadHost
        if realtimeFetchUrl is not None:
            FangCloudUrl.REALTIME_FETCH_ADDRESS_URL = realtimeFetchUrl
        if apiHost is not None and Utils.SYNC_ENABLE_API_HOST:
            FangCloudUrl.API_HOST = apiHost
        elif host is not None:
            FangCloudUrl.API_HOST = host
        SERVER_API = FangCloudUrl.API_HOST + '/api/v1'
        UPLOAD_SERVER_API = FangCloudUrl.UPLOAD_HOST + '/api/v1'
        SSO_API = FangCloudUrl.HOST + '/sso/api'
        FangCloudUrl.URL = {'WEB_HOME_PAGE': FangCloudUrl.HOST + '/apps/files/home',
         'FOLDER_URL': FangCloudUrl.HOST + '/apps/files/home/d/%d',
         'FILE_URL': FangCloudUrl.HOST + '/apps/files/home/d/%d/f/%d',
         'HISTORY_URL': FangCloudUrl.HOST + '/apps/files/home/d/%d/f/%d/history',
         'SHARE': FangCloudUrl.HOST + '/share/%s',
         'USER_LOGIN': SERVER_API + '/user/auth',
         'USER_LOGOUT': SSO_API + '/user/log_out',
         'USER_ACCOUNT_INFO': SERVER_API + '/user/account_info',
         'RERRESH_AUTH_TOKEN': SERVER_API + '/user/refresh_auth_token',
         'FOLDER_CHILDREN': SERVER_API + '/folder/children/%d',
         'CREATE_FOLDER': SERVER_API + '/folder/create',
         'FILE_UPDATE_WITH_RESOURCE': SERVER_API + '/file/update/%d',
         'FOLDER_UPDATE_WITH_RESOURCE': SERVER_API + '/folder/update/%d',
         'FILE_DOWNLOAD_WITH_RESOURCE': SERVER_API + '/file/download/%d',
         'ITEM_DELETE': SERVER_API + '/item/delete_for_sync',
         'ITEM_MOVE': SERVER_API + '/item/move_for_sync',
         'GET_SYNCED_FOLDERS': SERVER_API + '/folder/get_synced_folders',
         'GET_SYNCED_FILES': SERVER_API + '/folder/get_synced_files',
         'GET_PAGED_SYNCED_FILES': SERVER_API + '/folder/get_paged_synced_files',
         'GET_SYNCED_FOLDERS_CHILDREN': SERVER_API + '/folder/get_synced_children/%d',
         'GET_SYNCED_FOLDERS_CHILDREN_IDS': SERVER_API + '/folder/get_synced_children_ids/%d',
         'GET_SYNCED_BULK_INFO': SERVER_API + '/folder/bulk_synced_info',
         'MARK_FOLDER_AS_SYNCED': SERVER_API + '/folder/mark_as_sync',
         'MARK_FOLDER_AS_UNSYNCED': SERVER_API + '/folder/mark_as_unsync',
         'FILE_SYNC_INFO': SERVER_API + '/file/synced_info/%d',
         'FOLDER_SYNC_INFO': SERVER_API + '/folder/synced_info/%d',
         'FOLDER_OWNER_INFO': SERVER_API + '/folder/owner_info/%d',
         'FILE_SHARE': SERVER_API + '/file/share/%d',
         'FOLDER_SHARE': SERVER_API + '/folder/share/%d',
         'CRASH_LOG': SERVER_API + '/user/crash_log',
         'ALIYUN_ACCESS_CRASH_LOG': SERVER_API + '/user/get_aliyun_access_for_crash_log',
         'CRASH_LOG_UPLOADED_CALL_BACK': SERVER_API + '/user/crash_log_uploaded_call_back',
         'LOCK_ITEM': SERVER_API + '/item/lock',
         'UNLOCK_ITEM': SERVER_API + '/item/unlock',
         'FILE_UPLOAD': UPLOAD_SERVER_API + '/file/upload',
         'FILE_PRESIGN_UPLOAD': SERVER_API + '/file/presign_upload',
         'FILE_UPLOAD_WITH_RESOURCE': UPLOAD_SERVER_API + '/file/upload/%d?sequence_id=%d',
         'FILE_UPLOAD_CHECK_FILE_EXISTS_IN_SAME_DIR_IN_SAME_NAME': SERVER_API + '/file/check_file_exist',
         'FILE_MULTI_UPLOAD': SERVER_API + '/file/start_multi_upload',
         'FILE_MULTI_UPLOAD_WITH_FILE_ID': SERVER_API + '/file/start_multi_upload/%d',
         'FILE_MULTI_UPLOAD_GET_CHECKSUM': SERVER_API + '/file/get_upload_token',
         'FILE_MULTI_UPLOAD_GET_CHECKSUM_WITH_FILE_ID': SERVER_API + '/file/get_upload_token/%d',
         'USER_TIMESTAMP': SERVER_API + '/user/timestamp',
         'CLIENT_VERSION_CHECK': SERVER_API + '/user/client_version_check',
         'GET_ALL_ITEMS': SERVER_API + '/item/get_all_items_for_test?test_security=%s',
         'DELETE_ALL_ITEMS': SERVER_API + '/item/delete_all_items_for_test?test_security=%s',
         'SYNC_INTERFACE_WEBVIEW_LOGIN_URL': FangCloudUrl.HOST + '/client/auth/sync_login',
         'SYNC_INTERFACE_WEBVIEW_SELECT_FOLDER_URL': FangCloudUrl.HOST + '/client/files',
         'SYNC_INTERFACE_SEMIR_WEBVIEW_SELECT_FOLDER_URL': FangCloudUrl.HOST + '/sync_image_browser/home',
         'SYNC_INTERFACE_WEBVIEW_FIRST_RUN_URL': FangCloudUrl.API_HOST + '/client/help',
         'SYNC_INTERFACE_WEBVIEW_FORGET_PASSWORD_URL': FangCloudUrl.HOST + '/auth/forgot_password',
         'INVITE': SERVER_API + '/collab/invite'}


FangCloudUrl().LoadHost()
FangCloudUrl().ReloadUrls()
+++ okay decompyling FangCloudUrls.pyc 
# decompiled 1 files: 1 okay, 0 failed, 0 verify failed
# 2016.10.21 16:38:16 CST
