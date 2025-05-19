from Pan123 import Pan123

if __name__ == "__main__":
    # 手机号/邮箱
    username = "13588886666"
    # 密码
    password = "123456"
    # 文件位置
    filePath = "./result.123share"
    # 模式："export" (分享) 或 "import" (导入)
    mode = "export"
    # 分享文件才需要的参数：文件夹ID (如果要分享整个网盘，填 0 )
    homeFilePath = 0
    
    
    
    #########################################################################
    #############################下边的代码不用动 #############################
    #########################################################################
    driver = Pan123(debug=False)
    # 登录
    driver.doLogin(username=username, password=password)
    # 导出
    if mode == "export":
        driver.exportFiles(parentFileId=homeFilePath, savePath=filePath)
        print("导出成功")
    # 导入
    elif mode == "import":
        driver.importFiles(filePath=filePath)
        print("导入成功")
    # 退出登录
    driver.doLogout()