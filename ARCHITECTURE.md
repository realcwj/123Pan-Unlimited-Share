# 123Pan-Unlimited-Share 项目架构文档

## 项目概述

本项目是一个用于访问123云盘公开分享资源的系统，支持通过Web界面和WebDAV协议访问数据库中的分享资源。

## 项目结构

```
/workspace/
├── src/                           # 源代码主目录
│   ├── core/                      # 核心功能模块
│   │   ├── __init__.py
│   │   ├── models.py              # 数据模型定义
│   │   └── file_system.py         # 虚拟文件系统实现
│   ├── database/                  # 数据库相关模块
│   │   ├── __init__.py
│   │   └── Pan123Database.py      # 数据库操作类
│   ├── web/                       # Web界面模块
│   │   ├── __init__.py
│   │   └── (Flask相关文件)
│   ├── webdav/                    # WebDAV服务模块
│   │   ├── __init__.py
│   │   ├── webdav_main.py         # WebDAV服务主入口
│   │   ├── webdav_router.py       # WebDAV路由处理器
│   │   └── auth.py                # WebDAV认证模块
│   ├── utils/                     # 工具函数模块
│   │   ├── __init__.py
│   │   ├── get_file_url.py        # 获取文件下载链接
│   │   └── utils.py               # 通用工具函数
│   └── config/                    # 配置管理模块
│       ├── __init__.py
│       └── loadSettings.py        # 配置加载器
├── api/                           # API接口模块
├── assets/                        # 静态资源
├── docs/                          # 文档
├── templates/                     # Web模板
├── start.py                       # 项目启动脚本
├── settings.yaml                  # 配置文件
├── requirements.txt               # 依赖包列表
└── ARCHITECTURE.md                # 本架构文档
```

## 模块说明

### 1. Core 模块 (`src/core/`)

- `models.py`: 定义了 `FileNode` 等核心数据模型
- `file_system.py`: 实现虚拟文件系统，管理目录结构和文件访问

### 2. Database 模块 (`src/database/`)

- `Pan123Database.py`: 封装数据库操作，提供数据访问接口

### 3. WebDAV 模块 (`src/webdav/`)

- `webdav_main.py`: WebDAV服务的FastAPI应用入口
- `webdav_router.py`: WebDAV协议路由处理（PROPFIND, GET, OPTIONS）
- `auth.py`: WebDAV认证逻辑

### 4. Utils 模块 (`src/utils/`)

- `get_file_url.py`: 通过123云盘API获取文件真实下载链接
- `utils.py`: 通用工具函数

### 5. Config 模块 (`src/config/`)

- `loadSettings.py`: 从配置文件加载系统配置

## 主要功能

### 1. 数据库构建

- 从123云盘公开分享资源构建本地数据库
- 支持批量导入分享链接
- 提供数据库查询和管理功能

### 2. Web界面

- 提供友好的Web界面用于浏览和管理分享资源
- 支持搜索、筛选等功能
- 管理员后台面板

### 3. WebDAV服务

- 将数据库中的分享资源映射为WebDAV目录结构
- 支持文件浏览和下载
- 兼容各种WebDAV客户端

## 启动方式

```bash
# 启动Web界面服务（默认）
python start.py web

# 启动WebDAV服务
python start.py webdav

# 同时启动Web界面和WebDAV服务
python start.py both
```

## 配置说明

主要配置项在 `settings.yaml` 文件中定义：

- `DATABASE_PATH`: 数据库文件路径
- `PORT`: Web界面端口
- `WEBDAV_PORT`: WebDAV服务端口
- `WEBDAV_USERNAME/PASSWORD`: WebDAV认证凭据
- `SPLIT_FOLDER`: 是否启用目录分桶（大数据量时避免客户端崩溃）

## 重构改进

1. **模块化结构**: 代码按功能模块组织，便于维护和扩展
2. **清晰的导入路径**: 使用相对导入，避免路径冲突
3. **错误修复**: 修复了原代码中的变量引用错误
4. **可维护性**: 每个模块职责明确，便于单独测试和修改