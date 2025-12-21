# -*- coding: utf-8 -*-

import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import yaml


# 读取配置文件
with open("settings.yaml", "r", encoding="utf-8") as f:
    settings_data = yaml.safe_load(f.read())

# 创建一个 HTTPBasic 安全实例
security = HTTPBasic()

# 定义正确的用户名和密码
CORRECT_USERNAME = settings_data.get("WEBDAV_USERNAME")
CORRECT_PASSWORD = settings_data.get("WEBDAV_PASSWORD")

def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    """
    一个 FastAPI 依赖项，用于校验 HTTP Basic 认证提供的用户名和密码。

    Args:
        credentials (HTTPBasicCredentials): FastAPI 从请求头中解析出的认证信息。

    Raises:
        HTTPException: 如果认证失败，则抛出 401 Unauthorized 异常。
    """
    # 使用 secrets.compare_digest 来安全地比较字符串，可以防止时序攻击
    is_correct_username = secrets.compare_digest(credentials.username, CORRECT_USERNAME)
    is_correct_password = secrets.compare_digest(credentials.password, CORRECT_PASSWORD)

    if not (is_correct_username and is_correct_password):
        # 如果认证失败，构造并抛出异常
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码不正确",
            # 必须包含 WWW-Authenticate 头，以便浏览器或客户端弹出认证对话框
            headers={"WWW-Authenticate": "Basic"},
        )
    
    # 认证成功，函数正常返回，请求将继续处理
    print(f"用户 '{credentials.username}' 认证成功。")