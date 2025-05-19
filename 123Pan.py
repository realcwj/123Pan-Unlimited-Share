import time
import requests

class Pan123:
    def __init__(self, sleepTime):
        # 等待时间
        self.sleepTime = sleepTime
        self.accessToken = None
    
    def getApi(self, actionName):
        # 执行各类操作的API地址
        # Refer: https://github.com/AlistGo/alist/blob/main/drivers/123/util.go
        LoginApi = "https://login.123pan.com/api"
        MainApi = "https://www.123pan.com/b/api"
        apis = {
            "SignIn":           f"{LoginApi}/user/sign_in",
            "Logout":           f"{MainApi}/user/logout",
            "UserInfo":         f"{MainApi}/user/info",
            "FileList":         f"{MainApi}/file/list/new",
            "DownloadInfo":     f"{MainApi}/file/download_info",
            "Mkdir":            f"{MainApi}/file/upload_request",
            "Move":             f"{MainApi}/file/mod_pid",
            "Rename":           f"{MainApi}/file/rename",
            "Trash":            f"{MainApi}/file/trash",
            "UploadRequest":    f"{MainApi}/file/upload_request",
            "UploadComplete":   f"{MainApi}/file/upload_complete",
            "S3PreSignedUrls":  f"{MainApi}/file/s3_repare_upload_parts_batch",
            "S3Auth":           f"{MainApi}/file/s3_upload_object/auth",
            "UploadCompleteV2": f"{MainApi}/file/upload_complete/v2",
            "S3Complete":       f"{MainApi}/file/s3_complete_multipart_upload"
        }
        # 返回对应操作的API地址, 如果不存在则返回None
        return apis.get(actionName, None)
    
    
    
    def doLogin(username, password):
        