#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WebDAV 服务启动文件
将123Pan-Unlimited-Share的数据库挂载为WebDAV服务
"""

import uvicorn
from fastapi import FastAPI
from .webdav_router import router as webdav_router
from ..core.file_system import vfs
from ..config.loadSettings import loadSettings

app = FastAPI(
    title="123Pan Unlimited WebDAV",
    description="将 123Pan Unlimited Share 的数据库挂载为WebDAV服务",
    version="1.0.0",
    docs_url=None, 
    redoc_url=None,
)

app.include_router(webdav_router)

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host=loadSettings("WEBDAV_HOST"), 
        port=loadSettings("WEBDAV_PORT"), 
        # debug 参数
        # log_level="info",
        # access_log=True
        # 发布参数
        log_level="warning",
        access_log=False
    )