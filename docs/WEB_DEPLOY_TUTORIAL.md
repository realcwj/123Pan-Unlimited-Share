# [123云盘](https://www.123pan.com) 无限制分享工具（Web界面本地部署教程）

## 目录

- [123云盘 无限制分享工具（Web界面本地部署教程）](#123云盘-无限制分享工具web界面本地部署教程)
  - [目录](#目录)
  - [一、准备](#一准备)
  - [二、启动](#二启动)

## 一、准备

1. 安装 `Python`

2. 下载本项目

3. 安装依赖

    ```shell
    pip install tqdm requests flask beautifulsoup4
    ```

4. 修改 `web.py` 的内容（可以跳过本步骤）

- 文件开头（约第14行的位置）
  
    ```python
    # 修改为你自己的密钥
    app.secret_key = '114514_new_secret_key_for_updates'
    ```

- 文件末尾
  
    ```python
    # Telegram 的那个频道名称，大家应该都知道是telegram的哪个群, 自己填入（@xxxx的xxxx部分）, GitHub不明说了
    channel_name = "" # 程序会从该频道爬取资源、自动导入到公共资源库中
    message_after_id = 8050 # 从 8050 开始爬, 因为该频道之前的分享内容【全】【都】【失】【效】【了】
    port = 33333 # 网页运行端口
    ```

## 二、启动

1. 运行 `web.py`

    ```shell
    python web.py
    ```

2. 控制台窗口长这样

    ```shell
    (py312) d:\123Pan-Unlimited-Share>python web.py
    * Serving Flask app 'web'
    * Debug mode: off
    WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
    * Running on all addresses (0.0.0.0)
    * Running on http://127.0.0.1:33333        <<< 访问连接在这里
    * Running on http://198.18.0.1:33333       <<< 访问连接在这里
    Press CTRL+C to quit
    ```

3. 打开浏览器，访问 `{host}:{port}`, 例如：`http://127.0.0.1:33333`

4. 网页内的操作同：[>>> 123云盘无限制分享工具（Web界面使用教程） <<<](WEB_TUTORIAL.md)







