# [123云盘](https://www.123pan.com) 无限制分享工具（API接口文档）

## 目录

- [123云盘 无限制分享工具（API接口文档）](#123云盘-无限制分享工具api接口文档)
  - [目录](#目录)
  - [1. 从私人网盘导出 (`/api/export`)](#1-从私人网盘导出-apiexport)
  - [2. 导入到私人网盘 (`/api/import`)](#2-导入到私人网盘-apiimport)
  - [3. 从分享链接导出 (`/api/link`)](#3-从分享链接导出-apilink)
  - [4. 列出公共分享 (`/api/list_public_shares`)](#4-列出公共分享-apilist_public_shares)
  - [5. 获取公共分享内容 (`/api/get_public_share_content`)](#5-获取公共分享内容-apiget_public_share_content)

## 1. 从私人网盘导出 (`/api/export`)

此接口用于从登录用户的 123 云盘中导出指定文件夹（或整个网盘）的元数据。导出的数据是一个 Base64 编码的字符串，可以直接用于后续的导入操作或保存为 `.123share` 文件。用户可以选择是否将导出的文件提交到本项目的资源共享计划中（如果启用）。

-   **URL:** `/api/export`
-   **方法:** `POST`
-   **请求头:**
    -   `Content-Type: application/json`
-   **请求体 (JSON):**

    | 参数名                  | 类型         | 是否必须 | 默认值    | 说明                                                                                                    |
    | ----------------------- | ------------ | -------- | --------- | ------------------------------------------------------------------------------------------------------- |
    | `username`              | `string`     | 是       |           | 123 云盘的登录账号（手机号或邮箱）。                                                                           |
    | `password`              | `string`     | 是       |           | 123 云盘的登录密码。                                                                                      |
    | `homeFilePath`          | `string`/`int` | 是       |           | 要导出的文件夹 ID。填 `0` 表示导出整个网盘根目录下的所有内容。其他文件夹 ID 可通过浏览器开发者工具获取。 |
    | `userSpecifiedBaseName` | `string`     | 否       | `""`      | 用户指定的分享名。如果提供，并且 `shareProject` 为 `true`，此名称将用于生成提交到共享计划的文件名的一部分。也可能被前端用作下载文件的建议名称。 |
    | `shareProject`          | `boolean`    | 否       | `false`   | 是否将导出的文件提交到资源共享计划。如果为 `true`，导出的内容副本将保存到服务器的待审核目录。                   |

-   **响应 (NDJSON - `application/x-ndjson`):**
    服务器会流式发送一系列 JSON 对象，每个对象结构如下：

    | 字段名     | 类型             | 说明                                                                                                                                                                                             |
    | ---------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | `isFinish` | `boolean` / `null` | - `true`: 表示操作最终成功完成，此时 `message` 字段包含 Base64 编码的分享数据。 <br> - `false`: 表示操作过程中发生错误，此时 `message` 字段包含错误描述。<br> - `null`: 表示这是一个中间状态的日志消息。 |
    | `message`  | `string`         | 操作状态信息、日志、错误描述，或最终的 Base64 分享数据 (当 `isFinish: true`)。                                                                                                                     |

-   **成功示例:**
    **请求:**
    ```json
    {
        "username": "user@example.com",
        "password": "yourpassword123",
        "homeFilePath": "0",
        "userSpecifiedBaseName": "我的重要备份",
        "shareProject": true
    }
    ```
    **响应 (片段，实际为多行 NDJSON):**
    ```json
    {"isFinish": null, "message": "登录成功，开始导出文件列表..."}
    {"isFinish": null, "message": "获取文件列表中：parentFileId: 0"}
    {"isFinish": null, "message": "读取文件夹中..."}
    ...
    {"isFinish": null, "message": "数据匿名化完成"}
    {"isFinish": true, "message": "LONG_BASE64_ENCODED_STRING_DATA_HERE"}
    {"isFinish": null, "message": "文件已提交至资源共享计划审核队列: 16xxxxxxxx_我的重要备份.123share"}
    {"isFinish": null, "message": "已注销账号。"}
    ```

-   **失败示例 (登录失败):**
    **请求:** (密码错误)
    ```json
    {
        "username": "user@example.com",
        "password": "wrongpassword",
        "homeFilePath": "0"
    }
    ```
    **响应 (NDJSON):**
    ```json
    {"isFinish": false, "message": "登录失败，请检查用户名和密码。"}
    ```

-   **注意事项:**
    -   客户端必须能够处理流式 NDJSON 响应。
    -   导出的 Base64 字符串可能非常长，请确保客户端能处理大字符串。
    -   `homeFilePath` 除了 `0` (根目录) 以外的值，需要用户自行从 123 云盘网页版获取。

---

## 2. 导入到私人网盘 (`/api/import`)

此接口用于将之前导出的 `.123share` 文件内容（Base64 编码的字符串）导入到登录用户的 123 云盘中。导入时会在用户网盘的根目录下创建一个新的文件夹来存放导入的内容。

-   **URL:** `/api/import`
-   **方法:** `POST`
-   **请求头:**
    -   `Content-Type: application/json`
-   **请求体 (JSON):**

    | 参数名           | 类型     | 是否必须 | 默认值 | 说明                                                                     |
    | ---------------- | -------- | -------- | ------ | ------------------------------------------------------------------------ |
    | `username`       | `string` | 是       |        | 123 云盘的登录账号（手机号或邮箱）。                                          |
    | `password`       | `string` | 是       |        | 123 云盘的登录密码。                                                        |
    | `base64Data`     | `string` | 是       |        | `.123share` 文件的内容，即 Base64 编码的元数据字符串。                         |
    | `rootFolderName` | `string` | 是       |        | 在用户 123 云盘根目录中创建的文件夹名称，导入的内容将存放在此文件夹下。 |

-   **响应 (NDJSON - `application/x-ndjson`):**
    服务器会流式发送一系列 JSON 对象，每个对象结构如下：

    | 字段名     | 类型             | 说明                                                                                                                                                            |
    | ---------- | ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
    | `isFinish` | `boolean` / `null` | - `true`: 表示操作最终成功完成。 <br> - `false`: 表示操作过程中发生错误。<br> - `null`: 表示这是一个中间状态的日志消息或进度更新。                                 |
    | `message`  | `string`         | 操作状态信息、日志、进度（如正在创建哪个文件夹/上传哪个文件）、错误描述，或最终的成功信息。 当 `isFinish: true` 时，通常会包含实际创建的根文件夹全名。 |

-   **成功示例:**
    **请求:**
    ```json
    {
        "username": "user@example.com",
        "password": "yourpassword123",
        "base64Data": "LONG_BASE64_ENCODED_STRING_DATA_HERE",
        "rootFolderName": "我导入的电影合集"
    }
    ```
    **响应 (片段，实际为多行 NDJSON):**
    ```json
    {"isFinish": null, "message": "登录成功，开始导入文件..."}
    {"isFinish": null, "message": "正在读取数据..."}
    {"isFinish": null, "message": "数据读取完成"}
    {"isFinish": null, "message": "正在清洗数据..."}
    {"isFinish": null, "message": "数据清洗完成"}
    {"isFinish": null, "message": "正在重建目录结构..."}
    {"isFinish": null, "message":"[1/10][速度: 1.50 个/秒][预估剩余时间: 6.00 秒] 正在创建文件夹: 电影系列1"}
    ...
    {"isFinish": null, "message": "目录结构重建完成"}
    {"isFinish": null, "message": "正在上传文件..."}
    {"isFinish": null, "message":"[1/50][速度: 0.80 个/秒][预估剩余时间: 61.25 秒] 正在上传文件: 电影1.mp4"}
    ...
    {"isFinish": null, "message": "文件上传完成"}
    {"isFinish": true, "message": "导入完成, 保存到123网盘根目录中的: >>> 我导入的电影合集_20231027103000_GitHub@realcwj <<< 文件夹"}
    {"isFinish": null, "message": "已注销账号。"}
    ```

-   **失败示例 (Base64 数据无效):**
    **请求:**
    ```json
    {
        "username": "user@example.com",
        "password": "yourpassword123",
        "base64Data": "INVALID_OR_CORRUPTED_BASE64_DATA",
        "rootFolderName": "无效导入"
    }
    ```
    **响应 (NDJSON):**
    ```json
    {"isFinish": null, "message": "登录成功，开始导入文件..."}
    {"isFinish": null, "message": "正在读取数据..."}
    {"isFinish": false, "message": "读取数据失败, 报错：Incorrect padding"}
    {"isFinish": null, "message": "已注销账号。"}
    ```
-   **注意事项:**
    -   客户端必须能够处理流式 NDJSON 响应。
    -   导入过程可能较长，特别是当文件和文件夹数量较多时。客户端应能处理长时间的连接和持续的日志输出。
    -   实际创建的根文件夹名会自动附加时间戳和项目标识，以避免重名。

---

## 3. 从分享链接导出 (`/api/link`)

此接口用于从 123 云盘的公开分享链接中导出元数据。导出的数据格式与 `/api/export` 相同，是一个 Base64 编码的字符串。用户可以选择是否将导出的文件提交到本项目的资源共享计划中。

-   **URL:** `/api/link`
-   **方法:** `POST`
-   **请求头:**
    -   `Content-Type: application/json`
-   **请求体 (JSON):**

    | 参数名                  | 类型         | 是否必须 | 默认值    | 说明                                                                                                                                       |
    | ----------------------- | ------------ | -------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
    | `parentFileId`          | `string`/`int` | 是       |           | 要从分享链接中导出的文件夹 ID。通常填 `0` 表示导出分享链接根目录下的所有内容。如果分享链接本身指向特定子文件夹，可能需要提供该子文件夹的ID（较少见）。 |
    | `shareKey`              | `string`     | 是       |           | 123 云盘分享链接中的 Key 部分（例如，链接 `https://www.123pan.com/s/xxxx-yyyy` 中的 `xxxx-yyyy`）。                                        |
    | `sharePwd`              | `string`     | 否       | `""`      | 分享链接的密码（提取码）。如果分享链接没有密码，则留空或不传此字段。                                                                            |
    | `userSpecifiedBaseName` | `string`     | 否       | `""`      | 用户指定的分享名。如果提供，并且 `shareProject` 为 `true`，此名称将用于生成提交到共享计划的文件名的一部分。                                         |
    | `shareProject`          | `boolean`    | 否       | `false`   | 是否将导出的文件提交到资源共享计划。如果为 `true`，导出的内容副本将保存到服务器的待审核目录。                                                    |

-   **响应 (NDJSON - `application/x-ndjson`):**
    同 `/api/export` 接口，服务器会流式发送一系列 JSON 对象。

-   **成功示例:**
    **请求:**
    ```json
    {
        "parentFileId": "0",
        "shareKey": "ABCd-EfGh",
        "sharePwd": "1234",
        "userSpecifiedBaseName": "某分享资源",
        "shareProject": false
    }
    ```
    **响应 (片段，实际为多行 NDJSON):**
    ```json
    {"isFinish": null, "message": "开始从分享链接导出文件列表..."}
    {"isFinish": null, "message": "获取文件列表中：parentFileId: 0"}
    ...
    {"isFinish": null, "message": "数据匿名化完成"}
    {"isFinish": true, "message": "ANOTHER_LONG_BASE64_ENCODED_STRING_DATA_HERE"}
    ```

-   **失败示例 (分享链接无效或密码错误):**
    **请求:**
    ```json
    {
        "parentFileId": "0",
        "shareKey": "INVALID-KEY",
        "sharePwd": "wrongpass"
    }
    ```
    **响应 (NDJSON):**
    ```json
    {"isFinish": null, "message": "开始从分享链接导出文件列表..."}
    {"isFinish": null, "message": "获取文件列表中：parentFileId: 0"}
    {"isFinish": false, "message": "获取文件列表失败：{...error_details_from_pan_api...}"}
    ```
-   **注意事项:**
    -   客户端必须能够处理流式 NDJSON 响应.
    -   此接口不需要用户登录凭证，因为它处理的是公开（或有密码）的分享链接。

---

## 4. 列出公共分享 (`/api/list_public_shares`)

此接口用于获取服务器上公共资源库中所有可用的 `.123share` 文件列表。这些文件通常是由其他用户通过本工具的“加入资源共享计划”功能提交并审核通过的。

-   **URL:** `/api/list_public_shares`
-   **方法:** `GET`
-   **请求参数:** 无
-   **响应 (JSON - `application/json`):**

    | 字段名    | 类型      | 说明                                                                                                 |
    | --------- | --------- | ---------------------------------------------------------------------------------------------------- |
    | `success` | `boolean` | 操作是否成功。`true` 表示成功获取列表，`false` 表示失败。                                                   |
    | `files`   | `array`   | 仅当 `success` 为 `true` 时出现。一个包含文件对象的数组，每个对象代表一个公共分享文件。文件按 `name` 字段排序。 |
    | `message` | `string`  | 仅当 `success` 为 `false` 时出现，包含错误描述。                                                          |

    每个 `files` 数组中的文件对象结构：
    | 字段名     | 类型     | 说明                                        |
    | ---------- | -------- | ------------------------------------------- |
    | `name`     | `string` | 文件名（不包含 `.123share` 后缀）。         |
    | `filename` | `string` | 完整的文件名（包含 `.123share` 后缀）。     |

-   **成功示例:**
    **响应:**
    ```json
    {
        "success": true,
        "files": [
            { "name": "经典电影合集", "filename": "经典电影合集.123share" },
            { "name": "学习资料包", "filename": "学习资料包.123share" }
        ]
    }
    ```

-   **失败示例 (服务器错误):**
    **响应:**
    ```json
    {
        "success": false,
        "message": "获取公共分享列表失败: Internal server error"
    }
    ```

---

## 5. 获取公共分享内容 (`/api/get_public_share_content`)

此接口用于获取公共资源库中指定的 `.123share` 文件的实际内容（Base64 编码的字符串）以及建议的根目录名，方便用户直接用于导入操作。

-   **URL:** `/api/get_public_share_content`
-   **方法:** `GET`
-   **请求参数 (Query String):**

    | 参数名     | 类型     | 是否必须 | 说明                                                            |
    | ---------- | -------- | -------- | --------------------------------------------------------------- |
    | `filename` | `string` | 是       | 要获取内容的完整文件名（例如 `经典电影合集.123share`）。需要进行 URL 编码。 |

-   **响应 (JSON - `application/json`):**

    | 字段名           | 类型     | 说明                                                                 |
    | ---------------- | -------- | -------------------------------------------------------------------- |
    | `success`        | `boolean`| 操作是否成功。`true` 表示成功获取文件内容，`false` 表示失败。              |
    | `base64Data`     | `string` | 仅当 `success` 为 `true` 时出现。文件的 Base64 编码内容。                 |
    | `rootFolderName` | `string` | 仅当 `success` 为 `true` 时出现。建议的根目录名（通常是文件名去除后缀）。 |
    | `message`        | `string` | 仅当 `success` 为 `false` 时出现，包含错误描述。                           |

-   **成功示例:**
    **请求:** `/api/get_public_share_content?filename=%E7%BB%8F%E5%85%B8%E7%94%B5%E5%BD%B1%E5%90%88%E9%9B%86.123share`
    (其中 `%E7...` 是 "经典电影合集.123share" 的 URL 编码)
    **响应:**
    ```json
    {
        "success": true,
        "base64Data": "CONTENT_OF_THE_SHARE_FILE_AS_BASE64_STRING",
        "rootFolderName": "经典电影合集"
    }
    ```

-   **失败示例 (文件未找到):**
    **请求:** `/api/get_public_share_content?filename=non_existent_file.123share`
    **响应:**
    ```json
    {
        "success": false,
        "message": "文件未找到。"
    }
    ```

-   **注意事项:**
    -   `filename` 参数必须正确进行 URL 编码，特别是当文件名包含空格或中文字符时。
    -   服务器对 `filename` 参数进行了基本的安全检查，以防止路径遍历攻击。