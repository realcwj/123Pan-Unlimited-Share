import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..config.loadSettings import loadSettings
from ...Pan123 import Pan123
import base64
import requests
import yaml
import json
import time

if not os.path.exists("cache.json"):
    with open("cache.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "accessToken": "",
                "tokenCreateTime": "",
                "lastDeleteTime": "",
            },
            f,
            indent=4,
            ensure_ascii=False)

def get_file_url(name, etag, size) -> str:
    # 读取配置文件
    settings_data = {
        "123PAN_USERNAME": loadSettings("123PAN_USERNAME"),
        "123PAN_PASSWORD": loadSettings("123PAN_PASSWORD")
    }
    # 实例化
    driver = Pan123()
    # 登录账号并保存Token（假设有效期24h）
    if os.path.exists("cache.json"):
        with open("cache.json", "r", encoding="utf-8") as f:
            cache_data = json.load(f)
    else:
        cache_data = {
            "accessToken": "",
            "tokenCreateTime": "",
            "lastDeleteTime": "",
        }
    if cache_data.get("tokenCreateTime") \
        and time.time() - cache_data.get("tokenCreateTime") < 25 * 24 * 60 * 60 \
        and cache_data.get("accessToken"): # accessToken 30天有效, 这里设置为25天, 省事
        driver.setAccessToken(cache_data.get("accessToken"))
    else:
        driver.doLogin(
            username=settings_data.get("123PAN_USERNAME"),
            password=settings_data.get("123PAN_PASSWORD")
        )
        if driver.getAccessToken() is None:
            print("登录失败, 请检查用户名或密码能否正常登录")
            return "http://222.186.21.40:33333/NGGYU.mp4"
        cache_data["accessToken"] = driver.getAccessToken()
        cache_data["tokenCreateTime"] = int(time.time())
        with open("cache.json", "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=4, ensure_ascii=False)
    # 创建缓存文件夹
    action_result = driver.createFolder(0, "__缓存目录_无视即可_24h自动清理__123Pan-Unlimited-WebDAV", True)
    if action_result.get("isFinish"):
        cacheFolderInfo = action_result.get("message").get("Info")
        cacheFolderId = cacheFolderInfo.get("FileId")
    else:
        print(action_result.get("message"))
        return "http://222.186.21.40:33333/NGGYU.mp4"
    # 上传文件
    action_result = driver.uploadFile(
                            etag=etag,
                            fileName=name,
                            parentFileId=cacheFolderId,
                            size=size,
                            raw_data=True
                        )
    if action_result.get("isFinish"):
        file_data = action_result.get("message").get("Info")
        # print(action_result.get("message").get("Info"))
    else:
        print(action_result.get("message"))
        return "http://222.186.21.40:33333/NGGYU.mp4"
    # 获取下载地址
    action_result = driver.downloadFile(
        etag=file_data.get("Etag"),
        fileId=file_data.get("FileId"),
        S3KeyFlag=file_data.get("S3KeyFlag"),
        type=file_data.get("Type"),
        fileName=file_data.get("FileName"),
        size=file_data.get("Size")
    )
    if action_result.get("isFinish"):
        download_link = action_result.get("message")
        # print(download_link)
    else:
        print(action_result.get("message"))
        return "http://222.186.21.40:33333/NGGYU.mp4"
    # 删除文件夹
    # 如果缓存里没有上次删除时间, 则把当前时间设置为上次删除时间
    if not cache_data.get("lastDeleteTime"):
        cache_data["lastDeleteTime"] = int(time.time())
        with open("cache.json", "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=4, ensure_ascii=False)
    # 现在缓存里一定有时间，判断间隔是否24小时，如果大于24小时则删除
    if time.time() - cache_data.get("lastDeleteTime") > 24 * 60 * 60:
        # 删除文件夹
        action_result = driver.deleteFile([cacheFolderInfo], True)
        if action_result.get("isFinish"):
            print(f"彻底删除文件夹 {cacheFolderInfo.get('FileName')} 成功")
            # print(action_result)
        else:
            print(action_result.get("message"))
            return "http://222.186.21.40:33333/NGGYU.mp4"
        # 缓存里的时间更新为当前时间
        cache_data["lastDeleteTime"] = int(time.time())
        with open("cache.json", "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=4, ensure_ascii=False) 
    # 退出登录
    # driver.doLogout()
    # 获取跳转后的链接
    real_url = download_link.split("params=")[-1].split("&")[0]
    real_url = base64.b64decode(real_url).decode("utf-8")
    # 判断该链接是不是最终链接
    headers = {"Referer": "https://www.123pan.com/"}
    response = requests.get(real_url, headers=headers, allow_redirects=False)
    if response.status_code == 302:
        # 如果是 302 重定向，从 'Location' 头获取最终 URL
        final_url = response.headers.get("location")
    elif response.status_code < 300:
        # 如果是成功状态码 (如 200 OK)，解析 JSON
        try:
            data = response.json()
            final_url = data.get("data").get("redirect_url")
        except requests.exceptions.JSONDecodeError:
            print("Status was 2xx, but failed to decode JSON response.")
            return None
    else:
        # 其他非成功状态码
        print(f"Request failed with status code: {response.status_code}")
        return None
    
    print(f"获取到 {name} 的真实 URL: {final_url}")

    return final_url



if __name__ == "__main__":
    name = "提灯映桃花 晚安时间到·楚河（CV：袁铭喆）微博@种草小呆萌.mp4"
    etag = "df5f8f335a1043be16e3e6e8f83c3072"
    size = 552721
    get_file_url(name=name, etag=etag, size=size)