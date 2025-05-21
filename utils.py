from tqdm import tqdm

# 构建AbsPath
def makeAbsPath(fullDict, parentFileId=0, debug=False):
    _parentMapping = {} # {子文件ID: 父文件夹ID}
    # 遍历所有文件夹和文件列表，记录每个文件的父文件夹ID
    for key, value in tqdm(fullDict.items()):
        for item in value:
            _parentMapping[item.get("FileId")] = int(key) # item.get("ParentFileId")
    if debug:
        print(f"_parentMapping: {_parentMapping}")
    # 遍历所有文件夹和文件列表，添加AbsPath
    for key, value in tqdm(fullDict.items()):
        for item in value:
            _absPath = str(item.get("FileId"))
            if debug:
                print(f"_absPath: {_absPath}")
                print(f"int(_absPath.split('/')[0]): {int(_absPath.split('/')[0])}")
            while _absPath.split("/")[0] != str(parentFileId):
                _absPath = f"{_parentMapping.get(int(_absPath.split('/')[0]))}/{_absPath}"
            item.update({"AbsPath": _absPath})
    return fullDict

# 对FileId和parentFileId匿名化, 同步修改AbsPath
def anonymizeId(itemsList):
    RESULT = []
    MAP_ID = {}
    count = 0
    # 第一遍: 遍历所有的item.get("FileId")(包含文件和文件夹), 构建映射表
    for item in tqdm(itemsList, desc="匿名化ID, 构建映射表"):
        if item.get("FileId") not in MAP_ID:
            MAP_ID[item.get("FileId")] = count # 只映射不修改数据
            count += 1
        if item.get("parentFileId") not in MAP_ID: # 根目录只出现在parentFileId
            MAP_ID[item.get("parentFileId")] = count # 只映射不修改数据
            count += 1
    # 第二遍: 遍历所有的item.get("parentFileId")和item.get("AbsPath")(包含文件和文件夹), 替换为匿名化后的ID
    for item in tqdm(itemsList, desc="匿名化ID, 替换为匿名化后的ID"):
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