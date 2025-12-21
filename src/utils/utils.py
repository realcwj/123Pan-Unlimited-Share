import hashlib
import requests
import json
import base64

from getGlobalLogger import logger

# 构建AbsPath
def makeAbsPath(fullDict, parentFileId=0):
    _parentMapping = {} # {子文件ID: 父文件夹ID}
    # 遍历所有文件夹和文件列表，记录每个文件的父文件夹ID
    for key, value in fullDict.items():
        for item in value:
            _parentMapping[item.get("FileId")] = int(key) # item.get("ParentFileId")
    logger.debug(f"_parentMapping: {json.dumps(_parentMapping, ensure_ascii=False)}")
    # 遍历所有文件夹和文件列表，添加AbsPath
    for key, value in fullDict.items():
        for item in value:
            _absPath = str(item.get("FileId"))
            logger.debug(f"_absPath: {_absPath}")
            logger.debug(f"int(_absPath.split('/')[0]): {int(_absPath.split('/')[0])}")
            while _absPath.split("/")[0] != str(parentFileId):
                _absPath = f"{_parentMapping.get(int(_absPath.split('/')[0]))}/{_absPath}"
            item.update({"AbsPath": _absPath})
    return fullDict

# 对FileId和parentFileId匿名化, 同步修改AbsPath
def anonymizeId(itemsList):
    RESULT = []
    MAP_ID = {}
    count = 0
    # 第零遍: 对 itemsList 中的所有 item 进行排序
    # 这是为了确保具有相同目录和文件结构的项目最后产生的ID顺序一致(防止重复)
    itemsList.sort(key=lambda x: x.get("FileName"))
    # 第一遍: 遍历所有的item.get("FileId")(包含文件和文件夹), 构建映射表
    for item in itemsList:
        if item.get("FileId") not in MAP_ID:
            MAP_ID[item.get("FileId")] = count # 只映射不修改数据
            count += 1
        if item.get("parentFileId") not in MAP_ID: # 根目录只出现在parentFileId
            MAP_ID[item.get("parentFileId")] = count # 只映射不修改数据
            count += 1
    # 第二遍: 遍历所有的item.get("parentFileId")和item.get("AbsPath")(包含文件和文件夹), 替换为匿名化后的ID
    for item in itemsList:
        _absPath = item.get("AbsPath").split("/")
        _absPath = [str(MAP_ID[int(i)]) for i in _absPath if len(i)]
        _absPath = "/".join(_absPath)
        RESULT.append({
            "FileId": MAP_ID[item.get("FileId")],
            "FileName": item.get("FileName"),
            "Type": item.get("Type"),
            "Size": item.get("Size"),
            "Etag": item.get("Etag"),
            "parentFileId": MAP_ID[item.get("parentFileId")],
            "AbsPath": _absPath,
        })
    return RESULT

# 输入一段文本(这里是base64加密厚的字符串), 输出string的hash值
def getStringHash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest() # 返回的一定是长度为64的字符串

# 检查IP是否为中国大陆地区
# True: 支持 (境外IP)
# False: 不支持 (中国大陆IP)
def isAvailableRegion():
    check_ip_url = "https://ipv4.ping0.cc/geo"
    response = requests.get(check_ip_url).text.replace("\n", "")
    if "中国" in response and not any(keyword in response for keyword in ["香港", "澳门", "台湾"]):
            logger.warning(f"不支持当前IP地址使用: {response}")
            return False
    else:
        logger.info(f"当前IP地址支持使用: {response}")
        return True

# 内部函数：获取文件名对应的图标
def _get_icon(file_name: str) -> str:
    if not file_name or '.' not in file_name:
        return "📄"
 
    file_type = file_name.split('.')[-1].lower()
    if file_type in ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'svg', 'webp']:
        return "🖼️"
    elif file_type in ['mp3', 'wav', 'ogg', 'dsd', 'flac', 'aac', 'wma', 'm4a', 'mpc', 'ape', 'wv', 'wvx', 'dff', 'dsf', 'm4p']:
        return "🎵"
    elif file_type in ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', '3gp', 'm4v', 'ogv', 'asf', 'mts', 'm2ts', 'ts']:
        return "🎥"
    elif file_type in ['zip', 'rar', '7z', 'tar', 'gz', 'bz2']:
        return "📦"
    else:
        return "📄"
 
# 生成目录树
# 本函数由 Gemini 2.5 Pro 生成
def generateContentTree(b64_data_str: str) -> dict:
    # 0. 解码 base64 数据
    try:
        all_items_list = json.loads(base64.urlsafe_b64decode(b64_data_str).decode("utf-8"))
    except Exception as e:
        logger.error(f"generateContentTree: 解码 base64 数据失败: {e}", exc_info=True)
        return {"isFinish": False, "message": f"错误: {e}"}
 
    # 1. 构建节点映射表 (FileId -> item_data) 并初始化子节点列表
    nodes = {}
    for item_dict in all_items_list:
        item = item_dict.copy()
        item['children'] = []
        nodes[item['FileId']] = item
 
    # 2. 构建树形结构
    root_items = []
    all_file_ids_in_data = set(nodes.keys())
 
    for item_id, item_data in nodes.items():
        parent_id = item_data.get('parentFileId')
        if parent_id is not None and parent_id in nodes:
            nodes[parent_id]['children'].append(item_data)
        elif parent_id not in all_file_ids_in_data or parent_id is None: # 处理根项目或父项不在当前列表中的情况
            root_items.append(item_data)
 
    # 3. 排序: 先按类型(文件夹优先)，再按文件名
    for node in nodes.values():
        if node['children']:
            # 确保 Type 存在，如果不存在则默认为文件类型 (0)
            node['children'].sort(key=lambda x: (x.get('Type', 0) != 1, x['FileName']))
    
    root_items.sort(key=lambda x: (x.get('Type', 0) != 1, x['FileName']))
 
    # 4. 递归生成树形字符串列表，每个条目是 [行文本, FileId]
    tree_lines_with_ids = [] 
 
    def generate_lines_for_list_recursive(item_list, base_prefix):
        num_items = len(item_list)
        for i, item_data in enumerate(item_list):
            is_last = (i == num_items - 1)
            # 确保 Type 存在
            icon = "📂" if item_data.get('Type') == 1 else _get_icon(item_data['FileName'])
            connector = "└── " if is_last else "├── "
            line_text = f"{base_prefix}{connector}{icon} {item_data['FileName']}"
            tree_lines_with_ids.append([line_text, item_data['FileId']]) # 存储行文本和FileId
            
            children_prefix = base_prefix + ("    " if is_last else "│   ")
            if item_data['children']:
                generate_lines_for_list_recursive(item_data['children'], children_prefix)
 
    # 5. 从根节点开始生成
    num_root_items = len(root_items)
    for i, root_item_data in enumerate(root_items):
        # 确保 Type 存在
        icon = "📂" if root_item_data.get('Type') == 1 else _get_icon(root_item_data['FileName'])
        root_line_text = f"{icon} {root_item_data['FileName']}"
        tree_lines_with_ids.append([root_line_text, root_item_data['FileId']])
        
        if root_item_data['children']:
            generate_lines_for_list_recursive(root_item_data['children'], "") 
                                                                    
    logger.debug(f"generateContentTree: 生成的目录树条目数: {len(tree_lines_with_ids)}")
    return {"isFinish": True, "message": tree_lines_with_ids}

# 将 etag 转换为 123FastLink 使用 Base62 加密后的字符串 
def encryptEtagTo123FastLinkEtag(etag: str) -> str:
    _BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    # 将十六进制字符串转换为整数
    big_int_value = int(etag, 16)

    # 将整数转换为 Base62 字符串
    if big_int_value == 0:
        return _BASE62_CHARS[0]
    base62_chars_list = []
    n = big_int_value
    while n > 0:
        remainder = n % 62
        base62_chars_list.append(_BASE62_CHARS[remainder])
        n = n // 62
    
    # 反转列表并连接成字符串
    return "".join(reversed(base62_chars_list))

# 将 123FastLink 使用 Base62 加密后的字符串转换为 etag
def decrypt123FastLinkEtagToEtag(encrypted_etag: str) -> str:
    _BASE62_CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    # 将 Base62 字符串转换为整数
    big_int_value = 0
    for char in encrypted_etag:
        big_int_value = big_int_value * 62 + _BASE62_CHARS.index(char)

    # 将整数转换为十六进制字符串
    hex_str = hex(big_int_value)[2:]

    # 确保十六进制字符串长度为 32
    if len(hex_str) < 32:
        hex_str = "0" * (32 - len(hex_str)) + hex_str

    return hex_str

# 将本项目的分享码转换为 123FastLink 格式的 json
def transformShareCodeTo123FastLinkJson(rootFolderName, shareCode):
    # 解析 base64 数据
    data = base64.urlsafe_b64decode(shareCode).decode("utf-8")
    data = json.loads(data)
    
    # 存储最终输出
    OUTPUT = {
        "scriptVersion": "114514",
        "exportVersion": "114514",
        "usesBase62EtagsInExport": True,
        "commonPath": f"{rootFolderName}/",
        "files": [] # [{"path": ..., "size": ..., "etag", ...}, ...]
    }

    NAME_MAP = {} # {FileId: FileName}
    # 第一轮:
    # 遍历每条数据, 记载每个 FileId 对应的 FileName
    for item in data:
        NAME_MAP[str(item["FileId"])] = item["FileName"] # 这里吧FileId统一为string格式防止报错

    # 第二轮:
    # 遍历每条数据, 构建完整目录
    for item in data:
        # 跳过文件夹
        if item["Type"] == 1:
            continue

        path = "/".join([NAME_MAP[id] for id in item['AbsPath'].split('/')])
        OUTPUT['files'].append({
            "path": path,
            "size": item["Size"],
            "etag": encryptEtagTo123FastLinkEtag(item["Etag"]),
        })
        
    return OUTPUT

def transform123FastLinkJsonToShareCode(json_dict):
    if not json_dict["usesBase62EtagsInExport"]: # usesBase62EtagsInExport必须为true
        raise Exception("未知格式")
    multiple_root_folder_flag = not len(json_dict["commonPath"]) # 如果commonPath为空, 则multiple_root_folder_flag为true
    
    # 最终输出: [{"rootFolderName": ..., "shareCode": ...}, ...]
    OUTPUT = [] # 如果multiple_root_folder_flag为true, 则会针对多个文件夹生成多个分享码
    # 用于存储ID映射表
    ALL_MAP = {} # 存储 {depth(int): {FileName(string): FileId(int)}}
    # 用于存储添加过的文件夹path
    ADDED_PATH = set()

    # 先不考虑多文件夹, 这里存储所有的文件/文件夹
    # 格式如下
    # {
    #     "FileId": int,
    #     "FileName": string,
    #     "Type": int, # 0: 文件, 1: 文件夹
    #     "Size": int,
    #     "Etag": string,
    #     "parentFileId": int,
    #     "AbsPath": string
    # }
    ALL_ITEMS = []

    # 注: 由于写到这里脑子太晕了, 所以这里直接暴力算法无脑解决
    
    root_folder_id = 0 # 这里让根文件夹的FileId为0
    id_count = 1 # 其他文件/文件夹排序从1开始

    # 第一轮: 
    # 首先考虑单文件情况: 如果路径没有斜杠, 则为单文件, 获取文件名后单独存储
    if multiple_root_folder_flag:
        _temp = []
        for item in json_dict["files"]:
            path = item["path"]
            if "/" not in path:
                # 对单个文件直接添加
                _item_json = [{
                    "FileId": 1,
                    "FileName": path,
                    "Type": 0,
                    "Size": item["size"],
                    "Etag": decrypt123FastLinkEtagToEtag(item["etag"]),
                    "parentFileId": root_folder_id, 
                    "AbsPath": "1"
                }]
                # 匿名化
                _item_json = anonymizeId(_item_json)
                OUTPUT.append({
                    "rootFolderName": path,
                    "shareCode": base64.urlsafe_b64encode(json.dumps(_item_json).encode("utf-8")).decode("utf-8") 
                })
            else:
                _temp.append(item)
        json_dict["files"] = _temp
            
    # 第二轮:
    # 遍历所有文件, 构建映射表
    for item in json_dict["files"]:
        path = item["path"].split("/")
        # path 的最后一项一定是文件名
        _folderNames = path[:-1]
        _fileName = path[-1]
        _current_depth = len(_folderNames)
        # 检查当前ALL_MAP是否有当前深度的dict
        for i in range(_current_depth+1):
            if i not in ALL_MAP:
                ALL_MAP[i] = {}
        # 添加文件
        if _fileName not in ALL_MAP[_current_depth]:
            ALL_MAP[_current_depth][_fileName] = id_count
            id_count += 1
        # 添加文件夹
        for _depth, _folderName in enumerate(_folderNames):
            if _folderName not in ALL_MAP[_depth]:
                ALL_MAP[_depth][_folderName] = id_count
                id_count += 1
    # 第三轮:
    # 遍历所有文件, 把所有项添加到ALL_ITEMS中
    for item in json_dict["files"]:
        path = item["path"].split("/")
        # path 的最后一项一定是文件名
        _folderNames = path[:-1]
        _fileName = path[-1]
        _current_depth = len(_folderNames)
        _parentFileId = root_folder_id if _current_depth == 0 else ALL_MAP[_current_depth - 1][_folderNames[-1]]
        _AbsPath = "/".join([str(ALL_MAP[i][j]) for i, j in enumerate(_folderNames)]) + "/" + str(ALL_MAP[_current_depth][_fileName])
        # 添加文件
        ALL_ITEMS.append({
            "FileId": ALL_MAP[_current_depth][_fileName],
            "FileName": _fileName,
            "Type": 0,
            "Size": item["size"],
            "Etag": decrypt123FastLinkEtagToEtag(item["etag"]),
            "parentFileId": _parentFileId,
            "AbsPath": _AbsPath
        })
        # 添加文件夹
        for _current_depth in range(len(_folderNames)):
            _folderName = _folderNames[_current_depth]
            _AbsPath = "/".join([str(ALL_MAP[i][j]) for i, j in enumerate(_folderNames[:_current_depth + 1])])
            if _AbsPath not in ADDED_PATH:
                ADDED_PATH.add(_AbsPath)
                ALL_ITEMS.append({
                    "FileId": ALL_MAP[_current_depth][_folderName],
                    "FileName": _folderName,
                    "Type": 1,
                    "Size": 0,
                    "Etag": "",
                    "parentFileId": root_folder_id if _current_depth == 0 else ALL_MAP[_current_depth - 1][_folderNames[_current_depth - 1]],
                    "AbsPath": _AbsPath   
                })

    # 第四轮:
    # 判断是否为多文件夹
    if multiple_root_folder_flag:
        # 对于多文件夹情况: 如果 str(item.get("FileId")) == item.get("AbsPath"), 则为根文件夹
        all_root_folders_files = {} # 存储 {rootFolderId(int): files(list)}
        all_root_folders_names = {} # 存储 {rootFolderId(int): rootFolderName(string)}
        # 第五轮:
        # 遍历所有文件, 寻找根文件夹
        for item in ALL_ITEMS:
            if str(item.get("FileId")) == item.get("AbsPath"):
                all_root_folders_files[int(item.get("FileId"))] = []
                all_root_folders_names[int(item.get("FileId"))] = item.get("FileName")
        # 第六轮:
        # 遍历所有文件, 把所有项添加到根文件夹中
        for item in ALL_ITEMS:
            # 如果是根目录, 蒋parentFileId改为-1
            if item.get("FileId") in all_root_folders_files.keys():
                # print(item.get("FileId"), item.get("FileName"))
                item["parentFileId"] = -1
            root_folder_id = int(item.get("AbsPath").split("/")[0])
            all_root_folders_files[root_folder_id].append(item)
        # 匿名化
        for root_folder_id, root_folder_files in all_root_folders_files.items():
            item = anonymizeId(root_folder_files)
            OUTPUT.append({
                "rootFolderName": all_root_folders_names[root_folder_id],
                "shareCode": base64.urlsafe_b64encode(json.dumps(item, ensure_ascii=False).encode("utf-8")).decode("utf-8")
            })
    else:
        # 对于单文件夹情况: 添加一个ID=0的文件夹(commonPath.replace("\")), 并给所有AbsPath添加0
        for item in ALL_ITEMS:
            item["AbsPath"] = "0" + item["AbsPath"]
        ALL_ITEMS.append({
            "FileId": 0,
            "FileName": json_dict["commonPath"].replace("/", "").replace("\\", ""),
            "Type": 1,
            "Size": 0,
            "Etag": "",
            "parentFileId": -1,
            "AbsPath": "0"
        })
        # 匿名化
        ALL_ITEMS = anonymizeId(ALL_ITEMS)
        # base64加密
        OUTPUT.append({
            "rootFolderName": json_dict["commonPath"].replace("/", "").replace("\\", ""),
            "shareCode": base64.urlsafe_b64encode(json.dumps(ALL_ITEMS, ensure_ascii=False).encode("utf-8")).decode("utf-8") 
        })

    return OUTPUT

def getSearchText(b64data, rootFolderName):
    result = rootFolderName + " "
    data = base64.urlsafe_b64decode(b64data).decode("utf-8")
    data = json.loads(data)
    for item in data:
        result += item["FileName"]
        result += " "
    return result