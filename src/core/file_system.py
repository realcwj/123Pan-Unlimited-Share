import json
import base64
from typing import Dict, Optional, List, Tuple

from .models import FileNode, TYPE_DIRECTORY
from ..database.Pan123Database import Pan123Database
from ..config.loadSettings import loadSettings

# 决定是否分桶
SPLIT_FOLDER = loadSettings('SPLIT_FOLDER')

# 初始化缓存结构
MEMORY_CACHE_BY_NAME: Dict[str, Tuple[str, str]] = {}
MEMORY_CACHE_BY_BUCKET: Dict[str, List[str]] = {}
MEMORY_CACHE_NAMES_LIST: List[str] = []  # 平铺模式下的全部 rootFolderName
HASH_BUCKET_NAMES: List[str] = [f"{i:02x}" for i in range(256)]

def load_data_into_memory(db: Pan123Database):
    """
    数据加载和分组（分桶/平铺）
    """
    print("开始从数据库加载所有公开分享数据到内存...")
    page = 1
    all_shares = []

    while True:
        print(f"正在读取分享数据 (批次 {page}) ...")
        shares_page, is_end_page = db.listData(visibleFlag=True, page=page, limit=10000)
        all_shares.extend(shares_page)
        if is_end_page:
            break
        page += 1
    
    print(f"共获取 {len(all_shares)} 条分享记录，构建缓存 ...")
    # 清空所有缓存结构
    MEMORY_CACHE_BY_NAME.clear()
    MEMORY_CACHE_BY_BUCKET.clear()
    MEMORY_CACHE_NAMES_LIST.clear()

    # 建桶
    for bucket_name in HASH_BUCKET_NAMES:
        MEMORY_CACHE_BY_BUCKET[bucket_name] = []
    
    temp_name_list = []
    for codeHash, rootFolderName, _ in all_shares:
        data = db.getDataByHash(codeHash)
        if data:
            _rootFolderName, shareCode, _visibleFlag = data[0]
            MEMORY_CACHE_BY_NAME[rootFolderName] = (shareCode, codeHash)
            # 平铺模式要用的全量name
            temp_name_list.append(rootFolderName)
            # 桶模式用的哈希前缀
            bucket = codeHash[:2]
            MEMORY_CACHE_BY_BUCKET[bucket].append(rootFolderName)
        else:
            print(f"警告：无法解析 codeHash 为 {codeHash} 的数据，已跳过")

    MEMORY_CACHE_NAMES_LIST.extend(sorted(temp_name_list))
    for bucket_key in MEMORY_CACHE_BY_BUCKET:
        MEMORY_CACHE_BY_BUCKET[bucket_key].sort()
    print(f"内存缓存构建完成，总条目 {len(MEMORY_CACHE_BY_NAME)}.")

class VirtualFileSystem:
    """
    虚拟文件系统类，动态支持分桶和平铺两种根目录视图
    """
    def __init__(self, db_path: str):
        self.db = Pan123Database(dbpath=db_path)
        load_data_into_memory(self.db)
        self.root = FileNode(id=-1, parent_id=-2, name="ROOT", type=TYPE_DIRECTORY, size=0, etag="", abs_path_str="/")
        print(f"虚拟文件系统已初始化，数据从内存读取。")
        print(f"请通过WebDAV客户端挂载：\n\n")
        print(f"链接（本机访问）: http://127.0.0.1:{loadSettings('WEBDAV_PORT')}/")
        print(f"链接（局域网访问）: http://本机的局域网IP地址:{loadSettings('WEBDAV_PORT')}/")
        print(f"链接（公网访问）: http://本机的公网IP地址:{loadSettings('WEBDAV_PORT')}/")
        print(f"WebDAV 用户名: {loadSettings('WEBDAV_USERNAME')}")
        print(f"WebDAV 密码: {loadSettings('WEBDAV_PASSWORD')}")
        

    def _build_tree_from_share_code(self, share_code: str) -> List[FileNode]:
        """
        解析shareCode（base64）为本地虚拟树形结构
        """
        try:
            json_data = json.loads(base64.urlsafe_b64decode(share_code))
        except Exception as e:
            print(f"解析 shareCode 失败: {e}")
            return []
        nodes: Dict[int, FileNode] = {}
        for item in json_data:
            node = FileNode(
                id=item['FileId'],
                parent_id=item['parentFileId'],
                name=item['FileName'],
                type=item['Type'],
                size=item['Size'],
                etag=item['Etag'],
                abs_path_str=item.get('AbsPath', '')
            )
            nodes[item['FileId']] = node
        top_level_nodes = []
        for node in nodes.values():
            if node.parent_id in nodes:
                nodes[node.parent_id].children.append(node)
                node.parent = nodes[node.parent_id]
            else:
                top_level_nodes.append(node)
        return top_level_nodes

    def get_node_by_path(self, path: str) -> Optional[FileNode]:
        """
        路径匹配
        """
        path = path.strip('/')
        parts = path.split('/') if path else []

        # == 根目录 ==
        if not parts:
            self.root.children = []
            if SPLIT_FOLDER:
                # 256分桶
                for i, bucket_name in enumerate(HASH_BUCKET_NAMES):
                    bucket_node = FileNode(
                        id=200000 + i,
                        parent_id=self.root.id,
                        name=bucket_name,
                        type=TYPE_DIRECTORY,
                        size=0,
                        etag=f"bucket_{bucket_name}",
                        abs_path_str=bucket_name,
                        parent=self.root
                    )
                    self.root.children.append(bucket_node)
            else:
                # 平铺
                for i, name in enumerate(MEMORY_CACHE_NAMES_LIST):
                    _, codeHash = MEMORY_CACHE_BY_NAME.get(name, (None, None))
                    share_node = FileNode(
                        id=int(codeHash[:8], 16),
                        parent_id=self.root.id,
                        name=name,
                        type=TYPE_DIRECTORY,
                        size=0,
                        etag=codeHash,
                        abs_path_str=name,
                        parent=self.root
                    )
                    self.root.children.append(share_node)
            return self.root

        # == 分桶下一级 ==
        if SPLIT_FOLDER and len(parts) == 1 and parts[0] in HASH_BUCKET_NAMES:
            bucket_name = parts[0]
            bucket_node = FileNode(
                id=200000 + HASH_BUCKET_NAMES.index(bucket_name),
                parent_id=self.root.id,
                name=bucket_name,
                type=TYPE_DIRECTORY,
                size=0,
                etag=f"bucket_{bucket_name}",
                abs_path_str=bucket_name,
                parent=self.root
            )
            share_names = MEMORY_CACHE_BY_BUCKET.get(bucket_name, [])
            bucket_node.children = []
            for name in share_names:
                _, codeHash = MEMORY_CACHE_BY_NAME.get(name, (None, None))
                if codeHash:
                    share_folder_node = FileNode(
                        id=int(codeHash[:8], 16),
                        parent_id=bucket_node.id,
                        name=name,
                        type=TYPE_DIRECTORY,
                        size=0,
                        etag=codeHash,
                        abs_path_str=name,
                        parent=bucket_node
                    )
                    bucket_node.children.append(share_folder_node)
            return bucket_node

        # == 进入具体分享 ==
        # - 拆桶时路径是 /xx/分享名/...，平铺时路径是 /分享名/...
        root_folder_name = None
        parent_id = self.root.id
        bucket_name = None
        if SPLIT_FOLDER and len(parts) >= 2 and parts[0] in HASH_BUCKET_NAMES:
            bucket_name = parts[0]
            root_folder_name = parts[1]
            parent_id = 200000 + HASH_BUCKET_NAMES.index(bucket_name)
        elif not SPLIT_FOLDER and len(parts) >= 1:
            root_folder_name = parts[0]
        else:
            return None

        # 获取分享code
        share_data = MEMORY_CACHE_BY_NAME.get(root_folder_name)
        if not share_data:
            print(f"未找到分享: {root_folder_name}")
            return None
        shareCode, codeHash = share_data

        # 拆桶校验（安全健壮性）
        if SPLIT_FOLDER and bucket_name:
            if codeHash[:2] != bucket_name:
                print(f"分桶模式校验失败：分享 {root_folder_name} codeHash {codeHash} 不属于 {bucket_name} 桶")
                return None

        # 构建分享虚拟目录
        top_level_nodes = self._build_tree_from_share_code(shareCode)
        share_root_node = FileNode(
            id=int(codeHash[:8], 16),
            parent_id=parent_id,
            name=root_folder_name,
            type=TYPE_DIRECTORY,
            size=0,
            etag=codeHash,
            abs_path_str=root_folder_name,
            children=top_level_nodes
        )
        for node in top_level_nodes:
            node.parent = share_root_node
        # 仅分享目录
        if (SPLIT_FOLDER and len(parts) == 2) or (not SPLIT_FOLDER and len(parts) == 1):
            return share_root_node
        
        # 分享内部深层
        current_node = share_root_node
        idx_next = 2 if SPLIT_FOLDER else 1
        for part in parts[idx_next:]:
            found_child = None
            for child in current_node.children:
                if child.name == part:
                    found_child = child
                    break
            if found_child:
                current_node = found_child
            else:
                return None
        return current_node

# 实例化
vfs = VirtualFileSystem(db_path=loadSettings("DATABASE_PATH"))