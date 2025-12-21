# 123云盘无限制分享工具

一个基于123云盘秒传机制的文件分享工具，通过记录文件Hash值来实现跨账号传输文件，突破常规分享的数量、大小和时效限制。

## 项目简介

本项目利用123云盘的秒传功能，通过记录待分享文件的Hash值并保存到 `.123share` 文件中，接收方使用相同的Hash值模拟上传，触发秒传机制，从而实现无限制的文件分享。

### 核心特性

- 📁 **跨账号传输**：通过秒传机制实现不同账号间文件传输
- 🚀 **无限制分享**：突破数量、文件大小、有效时间限制
- 🔄 **多种分享模式**：
  - `export`：从私人网盘导出文件
  - `import`：导入分享文件
  - `link`：从分享链接导出内容
- 🔗 **支持长短分享码**：生成短码（站内用）和长码/`.123share`文件（跨站用）
- 🌐 **Web界面**：基于Flask的可视化操作界面
- 🗄️ **公共数据库**：资源共享计划，可搜索导入共享资源
- 📊 **格式转换**：支持`.123share`与`123FastLink`格式互转
- 🛡️ **ID匿名化**：保护分享者身份
- ⚙️ **API接口**：提供程序化调用能力

## 安装与部署

### 环境要求

- Python 3.7+
- 依赖包：flask, fastapi, tqdm, requests, beautifulsoup4, pyyaml, uvicorn

### 快速开始

1. **克隆项目**
```bash
git clone https://github.com/your-repo/123Pan-Unlimited-Share.git
cd 123Pan-Unlimited-Share
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置参数**
修改 `settings.yaml` 文件中的必要配置项：
- 123云盘账号密码
- 管理员登录信息
- 端口号等

4. **启动服务**
```bash
# 启动Web界面
python web.py

# 或直接运行脚本模式
python run.py
```

## 使用方法

### Web界面使用

启动服务后访问 `http://localhost:33333`（端口可能根据配置变化）

- **导出模式**：从个人网盘导出文件为`.123share`文件
- **导入模式**：从`.123share`文件导入到个人网盘
- **链接模式**：从分享链接导出内容
- **转换模式**：不同格式间转换

### 脚本使用

编辑 `run.py` 文件配置相应参数：

```python
mode = "export"  # "export", "import", "link"
filePath = "path/to/your/file.123share"
username = "your_phone_or_email"
password = "your_password"
```

### 管理后台

访问 `http://localhost:33333/{ADMIN_ENTRY}/login` 进行后台管理
- 查看和管理分享内容
- 更新数据库
- 审核共享资源

## API接口

项目提供完整的API接口，支持程序化调用：

- `/api/export` - 导出文件
- `/api/import` - 导入文件  
- `/api/link` - 从链接导出
- `/api/search_database` - 搜索公共数据库
- `/api/transform*` - 格式转换接口

## 配置说明

主要配置位于 `settings.yaml`：

- `DATABASE_PATH`: 数据库路径
- `PORT`: Web服务端口
- `ADMIN_ENTRY`: 管理后台入口
- `BAN_IP`: IP区域限制开关
- `TASK_QUEUE_TIMEOUT_SECONDS`: 任务超时时间

## 项目结构

```
├── api/                 # API处理函数
├── assets/              # 静态资源和数据库
├── docs/                # 文档
├── src/                 # 核心源码
│   ├── config/          # 配置加载
│   ├── database/        # 数据库操作
│   └── utils/           # 工具函数
├── static/              # 静态文件(CSS, JS)
├── templates/           # HTML模板
├── Pan123.py            # 核心类定义
├── web.py               # Web服务入口
├── run.py               # 脚本模式入口
└── settings.yaml        # 配置文件
```

## 注意事项

⚠️ **重要提示**：
- 推荐本地部署，避免使用他人搭建的网页
- 遵守123云盘服务条款
- 不要滥用API，避免被封IP
- 建议在大陆IP服务器部署（根据配置需求）

## 法律声明

本项目仅供技术学习与研究，旨在探讨云存储服务中秒传功能的技术实现原理。使用者需严格遵守相关法律法规，不得用于任何非法用途。

## 许可证

本项目采用 GPLv3 许可证。