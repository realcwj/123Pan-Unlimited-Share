# [123云盘](https://www.123pan.com) 无限制分享助手

## 这能做什么？

- 根据 123 云盘的分享政策：
    
    > 我们不会非法或非经授权地访问、使用、改变或披露您在123云盘的文件数据。**除非您主动分享**，或涉及法定监管事项，我们有权按照法律法规和有关监管机构规范性文件的规定对您通过123云盘传输、分享的文件数据，进行主动或依举报地审查、监督。
    
    也就是：**任何您分享的文件将会遭到内容审查**。然而，对于你自己上传、未分享的文件，只要有权机关不主动查你，123云盘不会主动审查你的数据。

    本助手的目的就是在**不创建分享链接**的情况下，实现分享文件的功能。

## 如何使用？

### 准备

1. 下载本项目

2. 安装依赖

    ```shell
    pip install tqdm pickle requests 
    ```

### 分享文件

1. 修改 `run.py` 的内容

    ```python
    # 手机号/邮箱
    username = "13588886666"
    # 密码
    password = "123456"
    # 文件位置
    filePath = "./result.123share"
    # 模式："export" (分享) 或 "import" (导入)
    mode = "export"
    # 分享文件才需要的参数：文件夹ID (如果要分享整个网盘，填 0 )
    homeFilePath = 0 # 如果分享整个网盘, 速度会很慢
    ```

    - `homeFilePath` 可以通过 123 云盘的网页版获取 （见下方 [FAQ](#FAQ)）

2. 运行 `run.py`

    ```shell
    python run.py
    ```

3. 等待完成

4. 分享 `result.123share` 文件给他人

### 接收文件

1. 修改 `run.py` 的内容

    ```python
    # 手机号/邮箱
    username = "13588886666"
    # 密码
    password = "123456"
    # 文件位置
    filePath = "./result.123share"
    # 模式："export" (分享) 或 "import" (导入)
    mode = "import"
    ```

2. 运行 `run.py`

    ```shell
    python run.py
    ```

3. 等待完成

4. 进入 123云盘 根目录, 查看接收的文件

## FAQ

### 如何获取 `homeFilePath` ?

1. 打开 123 云盘网页版

2. 打开你想分享的整个文件夹

3. 复制浏览器链接中的最后一部分数字

    ![how_to_share.png](./images/how_to_share.png)

    - 如上图所示, 分享的文件夹ID为 `13685159`