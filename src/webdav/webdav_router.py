from fastapi import APIRouter, Request, Response, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from urllib.parse import quote
import datetime
from xml.sax.saxutils import escape

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.file_system import vfs
from src.core.models import FileNode, TYPE_FILE, TYPE_DIRECTORY
from src.utils.get_file_url import get_file_url
from src.webdav.auth import verify_credentials

router = APIRouter()

# WebDAV 响应需要的XML命名空间
XML_NS = 'xmlns:D="DAV:"'

def _build_propfind_response_xml(node: FileNode, href: str) -> str:
    """
    为单个节点生成 PROPFIND 响应中的 <D:response> XML 片段。
    
    Args:
        node (FileNode): 要为其生成 XML 的文件/目录节点。
        href (str): 此节点在 WebDAV 服务器上的绝对路径 (如 / 或 /some_dir/file.mkv)。
    """
    # 确保目录的 href 总是以斜杠结尾
    final_href = href
    if node.type == TYPE_DIRECTORY and not final_href.endswith('/'):
        final_href += '/'
    
    # 根据节点类型设置 resourcetype
    if node.type == TYPE_DIRECTORY:
        resourcetype = "<D:resourcetype><D:collection/></D:resourcetype>"
    else:
        resourcetype = "<D:resourcetype/>"

    # 文件的 ETag (对于目录可以为空)
    etag_xml = f'<D:getetag>"{node.etag}"</D:getetag>' if node.etag else '<D:getetag/>'
    
    # 统一使用一个固定的时间戳，因为我们的文件系统是虚拟的且只读
    now_iso = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # 使用 escape() 对文件名进行 XML 转义，防止非法字符破坏XML结构
    display_name = escape(node.name)
    
    # 拼接单个节点的 propfind 响应 XML
    return f"""
    <D:response>
        <D:href>{final_href}</D:href>
        <D:propstat>
            <D:prop>
                <D:displayname>{display_name}</D:displayname>
                {resourcetype}
                <D:getcontentlength>{node.size}</D:getcontentlength>
                <D:getlastmodified>{now_iso}</D:getlastmodified>
                {etag_xml}
            </D:prop>
            <D:status>HTTP/1.1 200 OK</D:status>
        </D:propstat>
    </D:response>
    """

@router.api_route(
    "/{path:path}",
    methods=["PROPFIND", "GET", "OPTIONS"],
    dependencies=[Depends(verify_credentials)], # 对所有方法应用认证
    summary="WebDAV 主处理程序",
    tags=["WebDAV"]
)
async def handle_webdav_request(request: Request, path: str):
    """
    处理 WebDAV 请求的统一入口点。
    - OPTIONS: 返回服务器支持的方法。
    - PROPFIND: 返回目录列表或文件属性。
    - GET: 对文件请求进行重定向。
    """
    client_ip = request.client.host
    method = request.method
    print(f"接收到来自 {client_ip} 的请求: 方法={method}, 路径='/{path}'")

    # --- 处理 OPTIONS 请求 ---
    if method == "OPTIONS":
        headers = {
            "Allow": "OPTIONS, GET, PROPFIND",
            "DAV": "1"
        }
        return Response(status_code=status.HTTP_200_OK, headers=headers)

    # --- 获取请求的节点 ---
    node = vfs.get_node_by_path(path)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="资源未找到")

    # --- 处理 GET 请求 ---
    if method == "GET":
        if node.type == TYPE_FILE:
            print(f"GET文件: {node.name} {node.etag}")
            real_url = get_file_url(node.name, node.etag, node.size)
            return RedirectResponse(url=real_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
        elif node.type == TYPE_DIRECTORY:
            raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED, detail="不支持GET目录")
        
    # --- 处理 PROPFIND 请求 ---
    if method == "PROPFIND":
        depth = request.headers.get("Depth", "1")
        
        responses_xml = ""
        
        # 使用 request.url.path 来获取请求的原始路径，确保根目录的 href 正确
        # request.url.path 会保留原始的路径，例如 / 或 /Specials/
        request_href = request.url.path

        # 为请求的节点本身生成 XML
        responses_xml += _build_propfind_response_xml(node, request_href)

        # 如果是目录且查询深度为 "1"，则为其子节点也生成 XML
        if depth == "1" and node.type == TYPE_DIRECTORY:
            # 确保父路径以 '/' 结尾
            parent_href = request_href if request_href.endswith('/') else request_href + '/'
            for child in node.children:
                # 构造子节点的 href
                child_href = f"{parent_href}{quote(child.name)}"
                responses_xml += _build_propfind_response_xml(child, child_href)

        # 完整的 Multi-Status XML 响应
        full_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<D:multistatus {XML_NS}>
{responses_xml}
</D:multistatus>
"""
        return Response(content=full_xml, media_type="application/xml; charset=utf-8", status_code=207)

    # 如果是其他未实现的方法
    raise HTTPException(status_code=status.HTTP_405_METHOD_NOT_ALLOWED)