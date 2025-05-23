# [123云盘](https://www.123pan.com) 无限制分享工具（Python脚本运行教程）

## 目录

- [123云盘 无限制分享工具（Python脚本运行教程）](#123云盘-无限制分享工具python脚本运行教程)
  - [目录](#目录)
  - [一、准备](#一准备)
  - [二、从个人网盘分享文件](#二从个人网盘分享文件)
  - [三、从分享链接导出文件](#三从分享链接导出文件)
  - [四、接收文件](#四接收文件)

## 一、准备

1. 安装 `Python`

2. 下载本项目

3. 安装依赖

    ```shell
    pip install tqdm requests
    ```

## 二、从个人网盘分享文件

1. **请确保所有文件都已上传到123云盘**

2. 修改 `run.py` 的内容

    ```python
    # 模式："export" (从私人网盘分享)
    mode = "export"

    # 文件位置
    #   建议填写完整路径：
    #   Windows系统（示例）:
    #       filePath = r"D:\123Pan-Unlimited-Share\share\result.123share"
    #                  ^ 注意引号前面有个r
    #   Linux系统（示例）:
    #       filePath = "/home/xxx/123Pan-Unlimited-Share/share/result.123share" 
    filePath = r"D:\123Pan-Unlimited-Share\share\result.123share"

    # 手机号/邮箱
    username = "13566668888"
    # 密码
    password = "ABCDabcd1234"

    # 要分享的文件夹ID (如果要分享整个网盘，填 0 , 但是速度会很慢)
    homeFilePath = 0
    ```

    - `homeFilePath` 可以通过 123 云盘的网页版获取 （见下方 [FAQ](#FAQ)）

3. 运行 `run.py`

    ```shell
    python run.py
    ```

4. 等待完成

5. 控制台窗口长这样

    ```shell
    (py312) d:\123Pan-Unlimited-Share>python run.py
    获取文件列表中：parentFileId: xxxxxxxx
    获取文件列表中：parentFileId: xxxxxxxx
    获取文件列表中：parentFileId: xxxxxxxx
    获取文件列表中：parentFileId: xxxxxxxx
    获取文件列表中：parentFileId: xxxxxxxx
    获取文件列表中：parentFileId: xxxxxxxx
    获取文件列表中：parentFileId: xxxxxxxx
    获取文件列表中：parentFileId: xxxxxxxx
    获取文件列表中：parentFileId: xxxxxxxx
    导出完成, 保存到: D:\123Pan-Unlimited-Share\share\result.123share
    导出成功
    ```

6. 分享 `result.123share` 文件给他人

## 三、从分享链接导出文件

1. 修改 `run.py` 的内容

    ```python
    # 模式："link" (从分享链接导出)
    mode = "link"

    # 文件位置
    #   建议填写完整路径：
    #   Windows系统（示例）:
    #       filePath = r"D:\123Pan-Unlimited-Share\share\result.123share"
    #                  ^ 注意这里有个r
    #   Linux系统（示例）:
    #       filePath = "/home/xxx/123Pan-Unlimited-Share/share/result.123share" 
    filePath = r"D:\123Pan-Unlimited-Share\share\result.123share"

    # 示例分享链接：
    # https://www.******.com/s/abcd-efg
    # 提取码：ABCD
    # parentFileId = "0"        # 根目录填 0 , 如需分享指定目录需要从浏览器F12获取
    # shareKey = "abcd-efg"
    # sharePwd = "ABCD"

    # 分享文件夹ID (如果要导出整个分享链接的内容，填 0)
    parentFileId = "0"
    # 分享链接
    shareKey = "abcd-efg"
    # 分享密码
    sharePwd = "ABCD"
    ```

2. 运行 `run.py`

    ```shell
    python run.py
    ```

3. 等待完成

4. 控制台窗口长这样

    ```shell
    (py312) d:\123Pan-Unlimited-Share>python run.py
    获取文件列表中：parentFileId: xxxxxxxx
    100%|█████████████████████| 1/1 [00:00<?, ?it/s]
    100%|█████████████████████| 1/1 [00:00<?, ?it/s]
    导出完成, 保存到: D:\123Pan-Unlimited-Share\share\result.123share
    ```

5. 分享 `result.123share` 文件给他人

## 四、接收文件

1. 修改 `run.py` 的内容

    ```python
    # 模式："import" (导入)
    mode = "import"

    # 文件位置
    #   建议填写完整路径：
    #   Windows系统（示例）:
    #       filePath = r"D:\123Pan-Unlimited-Share\share\result.123share"
    #                  ^ 注意这里有个r
    #   Linux系统（示例）:
    #       filePath = "/home/xxx/123Pan-Unlimited-Share/share/result.123share" 
    filePath = r"D:\123Pan-Unlimited-Share\share\result.123share"

    # 手机号/邮箱
    username = "13566668888"
    # 密码
    password = "ABCDabcd1234"
    ```

2. 运行 `run.py`

    ```shell
    python run.py
    ```

3. 等待完成

4. 进入 123云盘 根目录, 查看接收的文件

5. 控制台窗口长这样

    ```shell
    (py312) d:\123Pan-Unlimited-Share>python run.py
    100%|█████████████████████| 22/22 [00:09<00:00,  2.43it/s]
    100%|█████████████████████| 427/427 [03:05<00:00,  2.30it/s]
    导入完成, 保存到123网盘根目录中的: >>> result_GitHub@realcwj <<< 文件夹
    导入成功
    ```

- **注意：** 导入的文件夹名称为 `xxxxx.123share` 中的 `xxxxx` 部分。