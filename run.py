from Pan123 import Pan123

if __name__ == "__main__":

    # 模式："export" (从私人网盘分享) 或 "import" (导入) 或 "link" (从分享链接导出)
    mode = "import"

    # 【所有模式需要填写】文件位置
    filePath = "./share/result.123share"

    # 【仅export/import模式需要填写】手机号/邮箱
    username = "13566668888"
    # 【仅export/import模式需要填写】密码
    password = "ABCDabcd1234"

    # 【仅export模式需要填写】要分享的文件夹ID (如果要分享整个网盘，填 0 , 但是速度会很慢)
    homeFilePath = 0

    # 示例分享链接：
    # https://www.******.com/s/abcd-efg
    # 提取码：ABCD
    # parentFileId = "0"        # 根目录填 0 , 如需分享指定目录需要从浏览器F12获取
    # shareKey = "abcd-efg"
    # sharePwd = "ABCD"

    # 【仅link模式需要填写】分享文件夹ID (如果要导出整个分享链接的内容，填 0)
    parentFileId = "0"
    # 【仅link模式需要填写】分享链接
    shareKey = "abcd-efg"
    # 【仅link模式需要填写】分享密码
    sharePwd = "ABCD"






    #########################################################################
    #############################下边的代码不用动 #############################
    #########################################################################
    # 初始化
    driver = Pan123(debug=False)
    # 登录
    if mode in ["export", "import"]:
        driver.doLogin(
            username=username,
            password=password
        )
    # 从个人网盘导出
    if mode == "export":
        driver.exportFiles(
            parentFileId=homeFilePath,
            savePath=filePath
            )
        print("导出成功")
    # 从分享链接导出
    elif mode == "link":
        driver.exportShare(
            parentFileId=parentFileId,
            shareKey=shareKey,
            sharePwd=sharePwd,
            savePath=filePath
        )
    # 导入
    elif mode == "import":
        driver.importFiles(
            filePath=filePath
        )
        print("导入成功")
    else:
        raise Exception("未知模式")
    # 退出登录
    if mode in ["export", "import"]:
        driver.doLogout()