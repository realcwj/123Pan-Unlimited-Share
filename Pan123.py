import time
import requests
from tqdm import tqdm
import base64
import json
import os

class Pan123:
    # Refer: https://github.com/AlistGo/alist/blob/main/drivers/123/util.go
    
    def __init__(self, sleepTime=0.1, debug=False):
        # 等待时间
        self.sleepTime = sleepTime
        # 调试模式
        self.debug = debug
        # 初始化accessToken和headers
        self.accessToken = None
        self.headers = {
            "origin":        "https://www.123pan.com",
            "referer":       "https://www.123pan.com/",
            "authorization": None, # Bearer {accessToken}
            "user-agent":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "platform":      "web",
            "app-version":   "3",
        }
        # 用于记录self.listFiles访问过的文件夹：{文件夹Id: 文件夹名称}
        self.listFilesVisited = {}
        # 用于记录self.listShare访问过的文件夹：{文件夹Id: 文件夹名称}
        self.listShareVisited = {}
    
    def getActionUrl(self, actionName):
        # 执行各类操作的Url
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
            "S3Complete":       f"{MainApi}/file/s3_complete_multipart_upload",
            "ShareList":        f"{MainApi}/share/get",
        }
        # 返回对应操作的API地址, 如果不存在则返回None
        return apis.get(actionName, None)

    def doLogin(self, username, password):
        # 登录操作
        # 如果包含'@'且'@'后面有'.'，则认为是邮箱格式
        if ("@" in username) and ("." in username.split("@")[-1]):
            # 邮箱登录
            payload = {
                "mail": username,
                "password": password,
                "type": 2,
            }
        else:
            # 用户名密码登录
            payload = {
                "passport": username,
                "password": password,
                "remember": True,
            }
        # 发送登录请求
        headers = {
			"origin": "https://www.123pan.com",
			"referer": "https://www.123pan.com/",
			"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
			"platform": "web",
			"app-version": "3",
		}
        try:
            response_data = requests.post(
                url = self.getActionUrl("SignIn"),
                headers = headers,
                json = payload
            ).json()
            # sendRequest方法会处理检查API响应中的'code'字段（登录成功时期望值为200）
            # 如果登录成功，'code'将是200
            token = response_data.get("data", {}).get("token") # 从响应数据中提取token
            if token:
                self.accessToken = token # 存储获取到的access_token
                self.headers["authorization"] = f"Bearer {self.accessToken}"
                if self.debug:
                    print(f"登录成功，access_token: {self.accessToken}")
                return True
            else:
                # 理论上，如果code不是200或者token缺失，sendRequest的code检查应该已经捕获了此情况
                # 此处作为一个额外保障
                print(f"登录失败：响应中未找到令牌，尽管API调用可能已成功。响应: {response_data}")
                return None
        except Exception as e:
            print(f"登录请求发生异常: {e}")
            self.accessToken = None
            return None
    
    def doLogout(self):
        # 注销操作
        # 发送注销请求
        try:
            response_data = requests.post(
                url = self.getActionUrl("Logout"),
                headers = self.headers
            ).json()
            # sendRequest方法会处理检查API响应中的'code'字段（注销成功时期望值为200）
            if response_data.get("code") == 200:
                self.accessToken = None
                self.headers["authorization"] = None
                if self.debug:
                    print("注销成功")
                return True
            else:
                print(f"注销失败：响应中未找到令牌，尽管API调用可能已成功。响应: {response_data}")
                return None
        except Exception as e:
            print(f"注销请求发生异常: {e}")
            self.accessToken = None
            return None
        
    def listFiles(self, parentFileId):
        
        # 如果已经访问过这个文件夹，就跳过
        if parentFileId in self.listFilesVisited:
            return None
        
        print(f"获取文件列表中：parentFileId: {parentFileId}")

        page = 0
        body = {
			"driveId":              "0",
			"limit":                "100",
			"next":                 "0",
			"orderBy":              "file_id",
			"orderDirection":       "desc",
			"parentFileId":         parentFileId,
			"trashed":              "false",
			"SearchData":           "",
			"Page":                 None,
			"OnlyLookAbnormalFile": "0",
			"event":                "homeListFile",
			"operateType":          "4",
			"inDirectSpace":        "false",
		}
        
        # 记录当前文件夹内的所有文件和文件夹
        ALL_ITEMS = []
        
        try:
            while True:
                # 更新Page参数
                page += 1
                body.update({"Page": f"{page}"})
                if self.debug:
                    print(f"获取文件列表中：正在获取第{page}页")
                # 发送请求
                response_data = requests.get(
                    url = self.getActionUrl("FileList"),
                    headers = self.headers,
                    params = body
                ).json()
                if response_data.get("code") == 0:
                    response_data = response_data.get("data")
                    # 把文件列表添加到ALL_FILES
                    ALL_ITEMS.extend(response_data.get("InfoList"))
                    # 如果没有下一页，就退出循环
                    if (response_data.get("Next") == "-1") or (len(response_data.get("InfoList")) == 0):
                        if self.debug:
                            print("已是最后一页")
                        break
                    # 否则进入下一页 (等待self.sleepTime秒, 防止被封)
                    else:
                        if self.debug:
                            print(f"等待{self.sleepTime}秒后进入下一页")
                        time.sleep(self.sleepTime)
                else:
                    print(f"获取文件列表失败：响应中未找到令牌，尽管API调用可能已成功。响应: {response_data}")
                    return None

            # 递归获取子文件夹下的文件
            for sub_file in ALL_ITEMS:
                if sub_file.get("Type") == 1:
                    self.listFiles(sub_file.get("FileId"))

            # 记录当前文件夹内的所有文件
            self.listFilesVisited[parentFileId] = ALL_ITEMS

        except Exception as e:
            print(f"获取文件列表请求发生异常: {e}")
            return None

    def exportFiles(self, parentFileId, savePath="./export.123"):
        # 读取文件夹
        self.listFiles(parentFileId=parentFileId)
        # 清洗数据
        ALL_ITEMS = []
        for key, value in self.listFilesVisited.items():
            # 遍历所有文件夹和文件列表
            for item in value:
                # 遍历所有文件和文件夹
                ALL_ITEMS.append({
                    "FileId": item.get("FileId"),
                    "FileName": item.get("FileName"),
                    "Type": item.get("Type"),
                    "Size": item.get("Size"),
                    "Etag": item.get("Etag"),
                    "parentFileId": item.get("ParentFileId"),
                    "AbsPath": item.get("AbsPath").split(f"{parentFileId}/")[-1], # 以输入的parentFileId作为根目录
                })
        # 保存数据
        # with open(savePath, "w", encoding="utf-8") as f:
        #     json.dump(ALL_ITEMS, f, indent=4, ensure_ascii=False)
        # 使用 base64 加密json数据防止被简单的内容审查程序读取内容
        with open(savePath, "wb") as f:
            f.write(base64.b64encode(json.dumps(ALL_ITEMS, ensure_ascii=False).encode("utf-8")))
        print(f"导出完成, 保存到: {savePath}")
    
    def createFolder(self, parentFileId, folderName):
        body = {
            "driveId":      0,
            "etag":         "",
            "fileName":     folderName,
            "parentFileId": parentFileId,
            "size":         0,
            "type":         1,
            # "duplicate": 1,
            # "NotReuse": True,
            # "event": "newCreateFolder",
            # "operateType": 1,
            # "RequestSource": None,
        }
        try:
            response_data = requests.post(
                url = self.getActionUrl("Mkdir"),
                headers = self.headers,
                json = body
            ).json()
            if response_data.get("code") == 0:
                fileId = response_data.get("data").get("Info").get("FileId")
                if self.debug:
                    print(f"创建文件夹成功：{folderName}, fileId: {fileId}")
                # 返回文件夹Id
                return fileId
            else:
                print(f"创建文件夹失败：响应中未找到令牌，尽管API调用可能已成功。响应: {response_data}")
                return None
        except Exception as e:
            print(f"创建文件夹请求发生异常: {e}")
            return None
    
    def uploadFile(self, etag, fileName, parentFileId, size):
        body = {
            "driveId": 0,
            "etag": etag,
            "fileName": fileName,
            "parentFileId": parentFileId,
            "size": size,
            "type": 0,
            # "RequestSource": None,
            "duplicate": 2, # 2->覆盖 1->重命名 0->默认
        }
        try:
            response_data = requests.post(
                url = self.getActionUrl("UploadRequest"),
                headers = self.headers,
                json = body
            ).json()
            if response_data.get("code") == 0:
                fileId = response_data.get("data").get("Info").get("FileId")
                if self.debug:
                    print(f"上传文件成功：{fileName}, fileId: {fileId}")
                # 返回文件夹Id
                return fileId
            else:
                print(f"上传文件失败：响应中未找到令牌，尽管API调用可能已成功。响应: {response_data}")
                return None
        except Exception as e:
            print(f"上传文件请求发生异常: {e}")
            return None
    
    def importFiles(self, filePath="./export.123"):
        # 读取数据
        with open(filePath, "rb") as f:
            files_list = json.loads(base64.b64decode(f.read()).decode("utf-8"))
        
        # 从filePath中获取文件名
        saveFileName = os.path.basename(filePath).split(".123share")[0]
        
        ID_MAP = {} # {原文件夹ID: 新文件夹ID}
        
        # 遍历数据，分类文件夹和文件
        ALL_FOLDERS = []
        ALL_FILES = []
        for item in files_list:
            if item.get("Type") == 1:
                ALL_FOLDERS.append({
                    **item,
                    "folderDepth": item.get("AbsPath").count("/"),
                })
            elif item.get("Type") == 0:
                ALL_FILES.append({
                    **item,
                    "fileDepth": item.get("AbsPath").count("/"),
                })
            else:
                raise ValueError(f"未知类型：{item}")

        ALL_FOLDERS.sort(key=lambda x: x.get("folderDepth")) # 按照深度从0(根目录)开始排序
        # 先在根目录创建文件夹
        current_time = time.strftime("%Y%m%d%H%M%S", time.localtime())
        rootFolderName = f"{saveFileName}_GitHub@realcwj" # 请尊重作者, 感谢配合!
        rootFolderId = self.createFolder(
            parentFileId = 0,
            folderName = rootFolderName
        )
        # 如果分享的内容包含目录 (root目录放在目录的检测中记录)
        for folder in tqdm(ALL_FOLDERS):
            # 如果是根目录, 获取原根目录的parentFileId, 映射到rootFolderId
            if folder.get("folderDepth") == 0:
                ID_MAP[folder.get("parentFileId")] = rootFolderId
            # 创建新文件夹
            newFolderId = self.createFolder(
                parentFileId = ID_MAP.get(folder.get("parentFileId")), # 基于新的目录结构创建文件夹
                folderName = folder.get("FileName") 
            )
            # 映射原文件夹ID到新文件夹ID
            ID_MAP[folder.get("FileId")] = newFolderId
        
        # 遍历数据, 上传文件
        for item in tqdm(ALL_FILES):
            if item.get("fileDepth") == 0:
                ID_MAP[item.get("parentFileId")] = rootFolderId
            self.uploadFile(
                etag = item.get("Etag"),
                fileName = item.get("FileName"),
                parentFileId = ID_MAP.get(item.get("parentFileId")), # 基于新的目录结构上传文件
                size = item.get("Size")
            )
        print(f"导入完成, 保存到123网盘根目录中的: >>> {rootFolderName} <<< 文件夹")
    
    def listShare(self, parentFileId, shareKey, sharePwd):
        
        # 如果已经访问过这个文件夹，就跳过
        if parentFileId in self.listShareVisited:
            return None
        
        print(f"获取文件列表中：parentFileId: {parentFileId}")

        page = 0
        body = {
			"limit":          "100",
			"next":           "0",
			"orderBy":        "file_id",
			"orderDirection": "desc",
			"parentFileId":   parentFileId,
			"Page":           None,
			"shareKey":       shareKey,
			"SharePwd":       sharePwd,
		}
        
        # 记录当前文件夹内的所有文件和文件夹
        ALL_ITEMS = []
        
        try:
            while True:
                # 更新Page参数
                page += 1
                body.update({"Page": f"{page}"})
                if self.debug:
                    print(f"获取文件列表中：正在获取第{page}页")
                # 发送请求
                response_data = requests.get(
                    url = self.getActionUrl("ShareList"),
                    headers = self.headers,
                    params = body
                ).json()
                if response_data.get("code") == 0:
                    response_data = response_data.get("data")
                    # 把文件列表添加到ALL_FILES
                    ALL_ITEMS.extend(response_data.get("InfoList"))
                    # 如果没有下一页，就退出循环
                    if (response_data.get("Next") == "-1") or (len(response_data.get("InfoList")) == 0):
                        if self.debug:
                            print("已是最后一页")
                        break
                    # 否则进入下一页 (等待self.sleepTime秒, 防止被封)
                    else:
                        if self.debug:
                            print(f"等待{self.sleepTime}秒后进入下一页")
                        time.sleep(self.sleepTime)
                else:
                    print(f"获取文件列表失败：响应中未找到令牌，尽管API调用可能已成功。响应: {response_data}")
                    return None

            # 递归获取子文件夹下的文件
            for sub_file in ALL_ITEMS:
                if sub_file.get("Type") == 1:
                    self.listShare(
                        parentFileId = sub_file.get("FileId"),
                        shareKey = shareKey,
                        sharePwd = sharePwd
                    )

            # 记录当前文件夹内的所有文件
            self.listShareVisited[parentFileId] = ALL_ITEMS

        except Exception as e:
            print(f"获取文件列表请求发生异常: {e}")
            return None
    
    def makeAbsPath(self, fullDict, parentFileId=0):
        _parentMapping = {} # {子文件ID: 父文件夹ID}
        # 遍历所有文件夹和文件列表，记录每个文件的父文件夹ID
        for key, value in tqdm(fullDict.items()):
            for item in value:
                _parentMapping[item.get("FileId")] = int(key) # item.get("ParentFileId")
        if self.debug:
            print(f"_parentMapping: {_parentMapping}")
        # 遍历所有文件夹和文件列表，添加AbsPath
        for key, value in tqdm(fullDict.items()):
            for item in value:
                _absPath = str(item.get("FileId"))
                if self.debug:
                    print(f"_absPath: {_absPath}")
                    print(f"int(_absPath.split('/')[0]): {int(_absPath.split('/')[0])}")
                while _absPath.split("/")[0] != str(parentFileId):
                    _absPath = f"{_parentMapping.get(int(_absPath.split('/')[0]))}/{_absPath}"
                item.update({"AbsPath": _absPath})
        return fullDict

    def exportShare(self, shareKey, sharePwd, parentFileId=0, savePath="./export.123"):
        # 读取文件夹
        self.listShare(
            parentFileId=parentFileId,
            shareKey=shareKey,
            sharePwd=sharePwd
            )
        
        # 生成路径
        self.listShareVisited = self.makeAbsPath(
            fullDict=self.listShareVisited,
            parentFileId=parentFileId
        )
        
        # 清洗数据
        ALL_ITEMS = []
        for key, value in self.listShareVisited.items():
            # 遍历所有文件夹和文件列表
            for item in value:
                # 遍历所有文件和文件夹
                ALL_ITEMS.append({
                    "FileId": item.get("FileId"),
                    "FileName": item.get("FileName"),
                    "Type": item.get("Type"),
                    "Size": item.get("Size"),
                    "Etag": item.get("Etag"),
                    "parentFileId": item.get("ParentFileId"),
                    "AbsPath": item.get("AbsPath").split(f"{parentFileId}/")[-1], # 以输入的parentFileId作为根目录
                })
        # 保存数据
        # with open(savePath, "w", encoding="utf-8") as f:
        #     json.dump(ALL_ITEMS, f, indent=4, ensure_ascii=False)
        # 使用 base64 加密json数据防止被简单的内容审查程序读取内容
        with open(savePath, "wb") as f:
            f.write(base64.b64encode(json.dumps(ALL_ITEMS, ensure_ascii=False).encode("utf-8")))
        print(f"导出完成, 保存到: {savePath}")