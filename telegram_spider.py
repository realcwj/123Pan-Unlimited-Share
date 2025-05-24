import requests
import json
import os
from bs4 import BeautifulSoup
import urllib.parse
from tqdm import tqdm
from Pan123 import Pan123

def getContent(channel_name, after_id, debug=False):

    base_url = f"https://t.me/s/{channel_name}"
    
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Cookie': 'stel_ssid=114514', # 待研究
        'DNT': '1',
        'Origin': 'https://t.me',
        'Priority': 'u=1, i',
        'Sec-CH-UA': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        'Sec-CH-UA-Mobile': '?0',
        'Sec-CH-UA-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }

    request_url = f"{base_url}?after={after_id}"

    # 设置动态 Referer
    # headers['Referer'] = f"{base_url}?after={after_id - 22}" # 待研究, 似乎差值是固定22
    # 这个似乎不重要？？？

    response = requests.post(request_url, headers=headers, data="", timeout=10)
    response.raise_for_status()  # 对 4XX 或 5XX 响应会抛出 HTTPError
    
    xml_data = json.loads(response.text)
    
    # return xml_data
    
    if debug:
        print(f"请求：{request_url}")
        # print(f"响应：{response.text}")
    
    # 返回的内容有以下几种情况：
    ## 第一种：后面还有东西，存在"tgme_widget_message_centered js-messages_more_wrap"字段，指向下一页
    ## 第二种：后面还有东西，但是不足20条，不存在"tgme_widget_message_centered js-messages_more_wrap"字段
    ## 第三种：啥都没有，xml_data=""
    
    # 处理第三种情况
    if xml_data == "":
        return {}, None

    # 存储消息内容：{int(id): "<div>...</div>", int(id): "<div>...</div>", ...}
    message_dict = {}
    
    xml_data = xml_data.split("\n")
    pos = 0
    while pos < len(xml_data):
        line = xml_data[pos]
        
        if "tgme_widget_message_text js-message_text" in line:
            # 向后几行寻找 f"https://t.me/{channel_name}/" (message底部, 显示xx人已观看的位置)
            id_keyword = f"https://t.me/{channel_name}/"
            pos += 1 # 从下一行开始搜索
            current_message_id = None
            while pos < len(xml_data):
                search_line = xml_data[pos]
                if id_keyword in search_line:
                    current_message_id = search_line.split(id_keyword)[1].split("\"")[0]
                    current_message_id = int(current_message_id) # 转换为 int, 此处还可以确保分割正确
                    break
                pos += 1
            if current_message_id is None:
                raise ValueError("找不到消息id")
            else:
                message_dict[current_message_id] = line
            if debug:
                print(f"存储消息：{current_message_id}")
            continue
        # 处理第一种情况
        elif "tgme_widget_message_centered js-messages_more_wrap" in line:
            # 截取 data-after="xxxx" 中的 xxxx
            line = line.split("data-after=\"")[1].split("\"")[0]
            line = int(line) # 转换为 int, 此处还可以确保分割正确
            if debug:
                print(f"下一页：{line}")
            return message_dict, line
        else:
            pos+=1
            continue

    # 处理第二种情况
    return message_dict, None

def beautifyXML(xml_text):
    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(xml_text, 'html.parser')
    # 获取每行的文本
    text_content = soup.get_text(separator='\n', strip=True)
    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
    # 获取所有的链接
    links = []
    for a_tag in soup.find_all('a', href=True):
        raw_link = a_tag['href']
        decoded_link = urllib.parse.unquote(raw_link) # Decode the URL
        links.append(decoded_link)

    return lines + links

def getNameLinkPwd(content_list, debug=False):
    # 乱七八糟的, 有没有大佬帮忙优化一下
    name = content_list[0]
    if any([i in name for i in ["automatically deleted", "com/s/", "无法进入群聊"]]):
        name = ""
    link = ""
    pwd = ""
    for line in content_list:
        # 替换中文符号
        line = line.replace("？", "?").replace("！", "!").replace("：", ":").replace("，", ",").replace("。", ".").replace("（", "(").replace("）", ")")
        if "名称" in line[:20]:
            name = line.split(":")[-1]
            if debug:
                print("这里替换了name变量")
                print(f"原文>>>{line}")
                print(f"名称>>>{name}")
        elif "/s/" in line:
            line = line.replace("提取码", "?提取码")
            if debug:
                print(f"原文>>>{line}")
            line = line.split(".com/s/")[1]
            if debug:
                print(f"链接>>>{line}")
            if "提取码" in line:
                link = line.split("?")[0]
                pwd = line.split(":")[1]
            else:
                link = line.strip()
    # 有的文件名有多个空格, 替换为一个空格
    name = name.replace("  ", " ").replace("  ", " ").replace("  ", " ")
    return {"name": name, "link": link, "pwd": pwd}

def startSpider(channel_name, message_after_id=None, save_interval=10, debug=False):

    # 如果没有填写channel_name, 直接跳过
    if not channel_name:
        print("[Telegram爬虫] 没有填写channel_name, 直接跳过")
        return
    
    # 请注意: 公共资源库不支持来自中国大陆IP地址的用户!
    # 请注意: 公共资源库不支持来自中国大陆IP地址的用户!
    # 请注意: 公共资源库不支持来自中国大陆IP地址的用户!
    
    # 检查IP, 如果是中国的, 退出程序
    # 当你看到这里, 请不要尝试删除本段代码, 强行运行, 不支持的IP地址是没法运行后续程序的!
    check_ip_url = "https://ipv4.ping0.cc/geo"
    response = requests.get(check_ip_url).text
    if "中国" in response and not any(keyword in response for keyword in ["香港", "澳门", "台湾"]):
            print(f"不支持当前IP地址使用：\n\n{response}")
            exit(0)
    else:
        print(f"当前IP地址支持使用：\n\n{response}")

    file_path = f"{channel_name}_message_raw.json"
    total_json_raw_data = {}
    next_page = message_after_id

    if os.path.exists(file_path):
        if message_after_id is not None:
            print("已存在Json文件, 强制message_after_id=None, 从Json文件中读取最大的一个数字开始爬")
            message_after_id = None
        with open(file_path, "r", encoding="utf-8") as f:
            total_json_raw_data = json.load(f)
        # 从Json的最大的一个数字开始爬
        next_page = max(total_json_raw_data.keys())

    count = 0
    while True:
        print(f"爬取第{int(next_page)+1}条message")
        message_dict, next_page = getContent(
            channel_name=channel_name,
            after_id=next_page,
            debug=debug
        )
        total_json_raw_data.update(message_dict)
        count += 1
        if count % save_interval == 0:
            # 保存到Json文件
            print(f"触发间隔{save_interval}, 保存到Json文件")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(total_json_raw_data, f, ensure_ascii=False, indent=4)
        # 退出条件: next_page is None（没有下一页了）
        if next_page is None:
            break
    # 保存到Json文件
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(total_json_raw_data, f, ensure_ascii=False, indent=4)

    # 用于保存处理后的数据
    total_json_processed_data = {}

    # 数据清洗，批量得到name, link, pwd
    for key, value in tqdm(total_json_raw_data.items(), desc="获取资源名称/链接/密码中..."):
        result = getNameLinkPwd(beautifyXML(value), debug=debug)
        if len(result.get("name")) and len(result.get("link")):
            total_json_processed_data[key] = result
    
    # 删除total_json_raw_data(后面也用不到了), 防止内容太多爆内存
    del total_json_raw_data
    
    # 保存到Json文件
    with open(f"{channel_name}_message_processed.json", "w", encoding="utf-8") as f:
        json.dump(total_json_processed_data, f, ensure_ascii=False, indent=4)
    
    # 调用 Pan123 导出 *.123share 到公共资源库
    driver = Pan123(debug=debug)
    for key, value in total_json_processed_data.items():
        # 如果name已经存在, 则跳过
        if os.path.exists(f"./public/ok/{value.get('name')}.123share"):
            if debug:
                print(f"[{key}] 跳过：{value.get('name')}, 原因：文件已存在")
            continue
        print(f"[{key}] 导出新增内容：{value.get('name')}")
        iter_driver = driver.exportShare(shareKey=value.get("link"), sharePwd=value.get("pwd"), parentFileId=0)
        for current_state in iter_driver:
            if current_state.get("isFinish"):
                with open(f"./public/ok/{value.get('name')}.123share", "w") as f:
                    f.write(current_state.get("message"))
                print(f"[{key}] 导出成功：{value.get('name')}")
            elif current_state.get("isFinish") is None:
                continue
            else:
                print(f"[{key}] 导出失败：{value.get('name')}, 原因：{current_state.get('message')}")
                break

if __name__ == "__main__":

    channel_name = "" # 大家应该都知道是telegram的哪个群, 自己填入（@xxxx的xxxx部分）, GitHub不明说了
    message_after_id = 8050 # 从 8050 开始爬, 因为之前的内容【全】【都】【失】【效】【了】

    startSpider(channel_name=channel_name, message_after_id=message_after_id, debug=False)

    # text = "<div class=\"tgme_widget_message_text js-message_text\" dir=\"auto\">名称：《浴血黑帮（2013）》全6季1080p蓝光原盘REMUX 内封特效字幕<br/><br/>描述：《浴血黑帮》讲述了战后伯明翰地区传奇黑帮家族Peaky Blinders的故事。时间要追溯到1919年，家族成员有一大嗜好，就是将剃刀刀片缝进他们帽子的帽檐之间，这也是“剃刀党”的名称由来。斯里安·墨菲将饰演一名残酷的黑帮份子Tommy Shelby ，是家族兄弟的领袖，嗜血无情。在那个时代，退伍军人、革命者和罪犯，都在社会底层挣扎生存。而当贝尔法斯特的警方负责人开始介入时，Tommy和他的黑帮势力制造出的恐怖统治开始了倾斜<br/><br/>链接：&nbsp;<a href=\"https://www.123912.com/s/IpPUVv-GXOj?%E6%8F%90%E5%8F%96%E7%A0%81:JZMM\" target=\"_blank\" rel=\"noopener\">https://www.123912.com/s/IpPUVv-GXOj?提取码:JZMM</a><br/><br/><i class=\"emoji\" style=\"background-image:url('//telegram.org/img/emoji/40/F09F8FB7.png')\"><b>🏷</b></i> 标签：<a href=\"?q=%23%E5%8E%9F%E7%9B%98REMUX\">#原盘REMUX</a> <a href=\"?q=%23%E8%8B%B1%E5%89%A7\">#英剧</a> <a href=\"?q=%23%E5%89%A7%E6%83%85\">#剧情</a><br/><i class=\"emoji\" style=\"background-image:url('//telegram.org/img/emoji/40/F09F9381.png')\"><b>📁</b></i> 大小：451.18GB<br/><i class=\"emoji\" style=\"background-image:url('//telegram.org/img/emoji/40/F09F8E89.png')\"><b>🎉</b></i> 来自：<a href=\"https://t.me/juziminmao\" target=\"_blank\">@juziminmao</a></div>"
    # text = beautifyXML(text)
    # text = getNameLinkPwd(text, debug=True)
    # print(text)