#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目启动脚本
支持启动Web界面服务或WebDAV服务
"""

import sys
import os
import argparse

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def start_web_service():
    """启动Web界面服务（Flask）"""
    print("启动Web界面服务...")
    from web import app
    from src.config.loadSettings import loadSettings
    
    PORT = loadSettings("PORT")
    print(f"Web服务启动在端口: {PORT}")
    
    app.run(
        debug=False,
        host='0.0.0.0',
        port=PORT,
        threaded=True
    )

def start_webdav_service():
    """启动WebDAV服务（FastAPI）"""
    print("启动WebDAV服务...")
    import uvicorn
    from src.webdav.webdav_main import app
    from src.config.loadSettings import loadSettings
    
    WEBDAV_HOST = loadSettings("WEBDAV_HOST")
    WEBDAV_PORT = loadSettings("WEBDAV_PORT")
    print(f"WebDAV服务启动在: http://{WEBDAV_HOST}:{WEBDAV_PORT}/")
    
    uvicorn.run(
        app,
        host=WEBDAV_HOST,
        port=WEBDAV_PORT,
        log_level="warning",
        access_log=False
    )

def main():
    parser = argparse.ArgumentParser(description='123Pan-Unlimited-Share 启动脚本')
    parser.add_argument('service', nargs='?', default='web', 
                        choices=['web', 'webdav', 'both'],
                        help='选择启动的服务: web (Web界面), webdav (WebDAV服务), both (同时启动)')
    
    args = parser.parse_args()
    
    if args.service == 'web':
        start_web_service()
    elif args.service == 'webdav':
        start_webdav_service()
    elif args.service == 'both':
        print("同时启动Web界面和WebDAV服务...")
        import threading
        
        # 启动Web界面服务
        web_thread = threading.Thread(target=start_web_service)
        web_thread.daemon = True
        web_thread.start()
        
        # 启动WebDAV服务
        start_webdav_service()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()