from dataclasses import dataclass, field
from typing import List, Optional

# 0 代表文件
TYPE_FILE = 0
# 1 代表目录
TYPE_DIRECTORY = 1

@dataclass
class FileNode:
    """
    数据类，用于表示文件系统中的一个节点（文件或目录）。
    使用 dataclass 可以自动生成 __init__, __repr__ 等方法，代码更简洁。
    """
    # 节点的唯一ID
    id: int
    # 节点的父节点ID
    parent_id: int
    # 文件或目录名
    name: str
    # 节点类型: 0 for file, 1 for directory
    type: int
    # 文件大小（字节）
    size: int
    # 文件的 ETag，可用于校验和获取真实链接
    etag: str
    # 节点的完整路径（此模型中暂不使用，但在构建树时可用于参考）
    abs_path_str: str
    # 节点的子节点列表，默认为空列表
    children: List['FileNode'] = field(default_factory=list)
    # 节点的父节点对象引用，默认为 None，在构建树时填充
    parent: Optional['FileNode'] = None