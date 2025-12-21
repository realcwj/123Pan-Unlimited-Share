import sqlite3
import os
import requests

from tqdm import tqdm
from utils import getStringHash, getSearchText
from getGlobalLogger import logger

class Pan123Database:
    def __init__(self, dbpath):
        # 确保数据库目录存在
        db_dir = os.path.dirname(dbpath)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # 验证数据库文件
        self.conn = sqlite3.connect(dbpath, check_same_thread=False)
        self.database = self.conn.cursor()
        
        # 如果是空的, 就创建表:
        # PAN123DATABASE (
        #   codeHash TEXT PRIMARY KEY, -- 分享内容（长码base64）的SHA256哈希值，作为短分享码
        #   rootFolderName TEXT,      -- 用户指定的分享根目录名
        #   visibleFlag BOOLEAN,      -- True: 公开可见（通过公共列表），False: 私有短码（不公开），None: 待审核（加入共享计划）
        #   shareCode TEXT,           -- 完整的分享码（即长码base64）
        #   timeStamp DATETIME DEFAULT (datetime('now', '+8 hours')) -- 数据插入时间 (GMT+8: 北京时间)
        # )

        # 创建主表
        self.database.execute("""
            CREATE TABLE IF NOT EXISTS PAN123DATABASE (
                codeHash TEXT PRIMARY KEY,
                rootFolderName TEXT NOT NULL,
                visibleFlag BOOLEAN,
                shareCode TEXT NOT NULL,
                timeStamp DATETIME DEFAULT (datetime('now', '+8 hours'))
            )
        """)
        
        # 创建 FTS 搜索表 PAN123DATABASE_SEARCH
        # codeHash 用于关联回主表，UNINDEXED 表示它不参与 FTS 的词汇索引，只是一个普通列
        # searchText 列将存储 rootFolderName 和所有 filename 的拼接文本，用于全文搜索
        # tokenize = 'unicode61' 是一个支持多种语言（包括中文单字分割）的较好分词器
        self.database.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS PAN123DATABASE_SEARCH USING fts5(
                codeHash UNINDEXED,
                searchText,
                tokenize = 'unicode61'
            )
        """)
        
        self.conn.commit()

    def importShareFiles(self, folder_path="./share"):
        # 检查 ./share 文件夹内是否存在 *.123share 文件, 如果存在, 则挨个读取, 并将其加入数据库, 随后删除该文件
        # 这个函数是为了兼容旧版本
        if not os.path.exists(folder_path): # 如果 share 不存在了，就直接返回
            logger.info(f"兼容模式：未找到 {folder_path} 文件夹，跳过旧文件导入。")
            return
            
        logger.info(f"兼容模式：开始导入 {folder_path} 文件夹内的所有 *.123share 文件。")
        filenames = os.listdir(folder_path)
        # 过滤确保是文件夹中的文件，而不是子目录
        filenames_to_process = []
        for filename in filenames:
            if filename.endswith(".123share") and os.path.isfile(os.path.join(folder_path, filename)):
                filenames_to_process.append(filename[:-9])

        for filename_base in tqdm(filenames_to_process):
            file_path_to_read = os.path.join(folder_path, f"{filename_base}.123share")
            try:
                with open(file_path_to_read, "r", encoding='utf-8') as f:
                    filedata = f.read().strip("\n").strip() # 去除换行和空格 (文件只有一行, 这个是确定的)
                codeHash = getStringHash(filedata)
                shareCode = filedata
                rootFolderName = filename_base # 使用去除.123share后缀的文件名
                
                # 尝试插入，如果已存在（基于主键codeHash），则跳过
                # 这里的visibleFlag默认为True因为它们来自旧的public/ok目录
                # 为避免重复插入导致错误，先查询
                self.database.execute("SELECT 1 FROM PAN123DATABASE WHERE codeHash=?", (codeHash,))
                if self.database.fetchone():
                    log_msg = f"兼容模式：{filename_base}.123share (codeHash: {codeHash}) 已存在于数据库，跳过导入。"
                    tqdm.write(log_msg)
                    logger.info(log_msg)
                else:
                    self.insertData(codeHash, rootFolderName, True, shareCode) # 默认旧的公开资源为 True
                    logger.info(f"兼容模式：成功导入 {filename_base}.123share 文件, rootFolderName: {rootFolderName}, codeHash: {codeHash}")
                #可以选择删除文件，但为了安全起见，先注释掉，可以手动清理
                # os.remove(file_path_to_read)
            except Exception as e:
                logger.error(f"兼容模式：处理 {filename_base}.123share 时发生错误: {e}", exc_info=True)

    def downloadLatestDatabase(self, file_path="./latest.db"):
        url = 'https://ghfast.top/https://github.com/realcwj/123Pan-Unlimited-Share/releases/download/database/PAN123DATABASE.latest.db' 
        r = requests.get(url)
        with open(file_path, "wb") as f:
            f.write(r.content)
        return file_path

    def importDatabase(self, database_path:str):
        # 导入一个数据库文件, 并将其数据合并到当前数据库
        # 导入的数据库文件格式与当前数据库相同
        # 只导入当前数据库没有的 codeHash 的条目的数据
        
        # 打开要导入的数据库文件
        conn_to_import = sqlite3.connect(database_path)
        database_to_import = conn_to_import.cursor()

        # 从要导入的数据库中获取所有 codeHash
        database_to_import.execute("SELECT codeHash FROM PAN123DATABASE")
        codeHashes_to_import = [row[0] for row in database_to_import.fetchall()]
        
        # 遍历要导入的数据库中的每一条记录
        logger.info(f"开始导入数据库: {database_path}")
        for codeHash in tqdm(codeHashes_to_import, desc=f"导入数据库: {database_path}"):
            # 检查当前数据库中是否已存在相同的 codeHash
            self.database.execute("SELECT 1 FROM PAN123DATABASE WHERE codeHash=?", (codeHash,))
            if self.database.fetchone():
                logger.debug(f"跳过导入 {codeHash}，因为它已存在于当前数据库。")
                continue  # 跳过已存在的记录

            # 从要导入的数据库中获取该记录的其他字段
            database_to_import.execute("SELECT rootFolderName, visibleFlag, shareCode FROM PAN123DATABASE WHERE codeHash=?", (codeHash,))
            rootFolderName, visibleFlag, shareCode = database_to_import.fetchone()

            # 插入到当前数据库
            self.insertData(codeHash, rootFolderName, visibleFlag, shareCode)
            logger.info(f"从外部数据库导入新增资源: {rootFolderName} (Hash: {codeHash}), visibleFlag: {visibleFlag}")

        # 关闭导入的数据库连接
        conn_to_import.close()
        logger.info(f"数据库 {database_path} 导入完成，尝试导入 {len(codeHashes_to_import)} 条记录。")
        
        # 删除导入的数据库文件
        os.remove(database_path)

    def insertData(self, codeHash:str, rootFolderName:str, visibleFlag:bool, shareCode:str):
        # visibleFlag: True: 公开, None: 公开(但是待审核), False: 私密 (仅生成短分享码，不加入公共列表)
        try:
            # 使用事务确保 PAN123DATABASE 和 PAN123DATABASE_SEARCH 的原子性操作
            self.conn.execute('BEGIN')

            # 插入主表数据
            self.database.execute(
                "INSERT INTO PAN123DATABASE (codeHash, rootFolderName, visibleFlag, shareCode) VALUES (?, ?, ?, ?)",
                (codeHash, rootFolderName, visibleFlag, shareCode)
            )
            
            # 准备 searchText 并插入到 PAN123DATABASE_SEARCH 表
            try:
                searchText = getSearchText(shareCode, rootFolderName)
                self.database.execute(
                    "INSERT INTO PAN123DATABASE_SEARCH (codeHash, searchText) VALUES (?, ?)",
                    (codeHash, searchText)
                )
            except Exception as e_fts:
                logger.error(f"为 codeHash={codeHash} 生成或插入 searchText 到 FTS表失败: {e_fts}", exc_info=True)
                self.conn.rollback()
                return False

            self.conn.commit()
            logger.debug(f"成功插入数据: codeHash={codeHash}, rootFolderName={rootFolderName}, visibleFlag={visibleFlag}, 并同步到FTS表。")
            return True
        except sqlite3.IntegrityError: # 捕获唯一约束冲突 (通常是 codeHash 已存在于 PAN123DATABASE)
            self.conn.rollback()
            logger.warning(f"插入数据失败: 短分享码 (codeHash): {codeHash} 已存在 (IntegrityError)。")
            return False
        except Exception as e:
            self.conn.rollback()
            logger.error(f"插入数据失败 (codeHash={codeHash}): {e}", exc_info=True)
            return False

    def getDataByHash(self, codeHash: str):
        self.database.execute(
            "SELECT rootFolderName, shareCode, visibleFlag FROM PAN123DATABASE WHERE codeHash=?",
            (codeHash,)
            )
        result = []
        for rootFolderName, shareCode, visibleFlag in self.database.fetchall():
            result.append((
                rootFolderName,
                shareCode,
                bool(visibleFlag) if visibleFlag is not None else None # 不知道为什么，从数据库里读出来的不是bool? 还要额外转一下 
            ))
        
        if len(result):
            logger.debug(f"通过 codeHash '{codeHash}' 查询到数据: rootFolderName='{result[0][0]}', visibleFlag={result[0][2]}") # result[0] 是元组
            return result # 返回 [(rootFolderName, shareCode, visibleFlag)]
        else:
            logger.debug(f"通过 codeHash '{codeHash}' 未查询到数据")
            return None

    def listData(self, visibleFlag: bool = True, page: int = 1, limit: int = 100):
        # 只展示visibleFlag为True (公开且审核通过) 的数据
        # 返回 [(codeHash, rootFolderName, timeStamp), ...], is_end_page
        if page < 1:
            page = 1
        offset = (page - 1) * limit

        # 获取总记录数
        self.database.execute("SELECT COUNT(*) FROM PAN123DATABASE WHERE visibleFlag=?", (visibleFlag,))
        total_records = self.database.fetchone()[0]
        
        self.database.execute(
            "SELECT codeHash, rootFolderName, timeStamp FROM PAN123DATABASE WHERE visibleFlag=? ORDER BY timeStamp DESC LIMIT ? OFFSET ?",
            (visibleFlag, limit, offset)
        )
        results = self.database.fetchall()
        
        is_end_page = (page * limit) >= total_records
        
        return results, is_end_page

    # 另一种方法: 同时进行 MATCH 搜索和 LIKE 搜索，但是这样速度很慢，暂时注释掉
    def searchDataByName(self, search_keyword: str, page: int = 1, visible_flag: bool = True):
        # 返回 [(codeHash, rootFolderName, timeStamp), ...], is_end_page
        if page < 1:
            page = 1
        limit = 100
        offset = (page - 1) * limit
        
        # 为 rootFolderName 的 LIKE 查询准备搜索模式，例如: %keyword%
        search_keyword_for_like = f"%{search_keyword}%"
        
        try:
            # 构造计算总记录数的 SQL (使用 CTE 和 UNION)
            # CTE (Common Table Expression) "MatchedHashes" 用于获取所有唯一匹配的 codeHash
            # UNION 操作会合并来自 FTS 搜索和 rootFolderName LIKE 搜索的 codeHash，并自动去重
            count_sql = """
                WITH MatchedHashes AS (
                    SELECT s.codeHash
                    FROM PAN123DATABASE_SEARCH s
                    JOIN PAN123DATABASE m_s ON s.codeHash = m_s.codeHash
                    WHERE s.searchText MATCH ? AND m_s.visibleFlag = ?  /* FTS 搜索并检查可见性 */
                    UNION
                    SELECT m_r.codeHash
                    FROM PAN123DATABASE m_r
                    WHERE m_r.rootFolderName LIKE ? AND m_r.visibleFlag = ? /* rootFolderName LIKE 搜索并检查可见性 */
                )
                SELECT COUNT(*) FROM MatchedHashes;
            """
            # 参数顺序对应SQL中的占位符:
            # 1. search_keyword (for FTS s.searchText MATCH ?)
            # 2. visible_flag (for FTS m_s.visibleFlag = ?)
            # 3. search_keyword_for_like (for LIKE m_r.rootFolderName LIKE ?)
            # 4. visible_flag (for LIKE m_r.visibleFlag = ?)
            self.database.execute(count_sql, (search_keyword, visible_flag, search_keyword_for_like, visible_flag))
            total_records_tuple = self.database.fetchone()
            total_records = total_records_tuple[0] if total_records_tuple else 0

            if total_records == 0: # 如果没有匹配的记录，提前返回，避免不必要的查询
                return [], True

            # 构造查询分页数据的 SQL
            # 从主表 PAN123DATABASE 中选取数据，其 codeHash 必须存在于 MatchedHashes CTE 中
            # 结果按照时间戳（timeStamp）降序排列
            data_sql = """
                WITH MatchedHashes AS (
                    SELECT s.codeHash
                    FROM PAN123DATABASE_SEARCH s
                    JOIN PAN123DATABASE m_s ON s.codeHash = m_s.codeHash
                    WHERE s.searchText MATCH ? AND m_s.visibleFlag = ? /* FTS 条件 */
                    UNION
                    SELECT m_r.codeHash
                    FROM PAN123DATABASE m_r
                    WHERE m_r.rootFolderName LIKE ? AND m_r.visibleFlag = ? /* LIKE 条件 */
                )
                SELECT m.codeHash, m.rootFolderName, m.timeStamp
                FROM PAN123DATABASE m
                JOIN MatchedHashes mh ON m.codeHash = mh.codeHash /* 确保只获取匹配到的哈希 */
                ORDER BY m.timeStamp DESC
                LIMIT ? OFFSET ?;
            """
            # 参数顺序对应SQL中的占位符:
            # 1. search_keyword (for FTS s.searchText MATCH ?)
            # 2. visible_flag (for FTS m_s.visibleFlag = ?)
            # 3. search_keyword_for_like (for LIKE m_r.rootFolderName LIKE ?)
            # 4. visible_flag (for LIKE m_r.visibleFlag = ?)
            # 5. limit (for LIMIT)
            # 6. offset (for OFFSET)
            self.database.execute(data_sql, (search_keyword, visible_flag, search_keyword_for_like, visible_flag, limit, offset))
            results = self.database.fetchall()

            is_end_page = (page * limit) >= total_records
            
            return results, is_end_page
        except sqlite3.OperationalError as e_op:
            # 特别处理FTS查询可能引起的OperationalError (比如MATCH语法问题)
            # 或者其他SQL操作层面的错误
            logger.error(f"搜索操作失败 (关键词: '{search_keyword}', visible: {visible_flag}): {e_op}", exc_info=True)
            return [], True # 返回空结果，并标记为最后一页
        except Exception as e: # 捕获其他所有通用异常
            logger.error(f"执行 searchDataByName (关键词: '{search_keyword}', visible: {visible_flag}) 时发生未知错误: {e}", exc_info=True)
            return [], True # 发生其他错误也返回空

    # def searchDataByName(self, search_keyword: str, page: int = 1, visible_flag: bool=True):
    #     # 返回 [(codeHash, rootFolderName, timeStamp), ...], is_end_page
    #     if page < 1:
    #         page = 1
    #     limit = 100
    #     offset = (page - 1) * limit
        
    #     # FTS5 的 MATCH 查询。search_keyword 可以是单个词或多个词。
    #     # FTS5 会自动处理空格，将其视为 AND 操作（默认情况下）。
    #     # 注意：FTS搜索词的语法可能需要处理特殊字符，但通常直接传递用户输入即可。
    #     # 确保只搜索 visibleFlag = 1 (True) 的项。
        
    #     try:
    #         # 构造计算总数的SQL
    #         count_sql = """
    #             SELECT COUNT(s.codeHash)
    #             FROM PAN123DATABASE_SEARCH s
    #             JOIN PAN123DATABASE m ON s.codeHash = m.codeHash
    #             WHERE s.searchText MATCH ? AND m.visibleFlag = ?
    #         """
    #         self.database.execute(count_sql, (search_keyword, visible_flag))
    #         total_records = self.database.fetchone()[0]

    #         # 构造查询数据的SQL
    #         # 从FTS表(s)搜索，然后JOIN主表(m)以获取 rootFolderName, timeStamp，并按时间戳排序
    #         query_sql = """
    #             SELECT s.codeHash, m.rootFolderName, m.timeStamp
    #             FROM PAN123DATABASE_SEARCH s
    #             JOIN PAN123DATABASE m ON s.codeHash = m.codeHash
    #             WHERE s.searchText MATCH ? AND m.visibleFlag = ?
    #             ORDER BY m.timeStamp DESC 
    #             LIMIT ? OFFSET ?
    #         """
    #         self.database.execute(query_sql, (search_keyword, visible_flag, limit, offset))
    #         results = self.database.fetchall()

    #         is_end_page = (page * limit) >= total_records
            
    #         return results, is_end_page
    #     except Exception as e:
    #         logger.error(f"执行 searchDataByName (关键词: '{search_keyword}') 时发生错误: {e}", exc_info=True)
    #         return [], True # 发生其他错误也返回空

    def deleteData(self, codeHash:str):
        self.database.execute("SELECT codeHash FROM PAN123DATABASE WHERE codeHash=?", (codeHash,))
        if self.database.fetchone() is None:
            logger.debug(f"尝试删除 codeHash: {codeHash}, 但主表记录不存在。")
            return False
        try:
            # 使用事务确保原子性
            self.conn.execute('BEGIN')

            # 从主表 PAN123DATABASE 删除
            self.database.execute("DELETE FROM PAN123DATABASE WHERE codeHash=?", (codeHash,))
            
            # 同时从 FTS 表 PAN123DATABASE_SEARCH 删除
            self.database.execute("DELETE FROM PAN123DATABASE_SEARCH WHERE codeHash=?", (codeHash,))
            
            self.conn.commit() # 提交事务
            logger.warning(f"已从主表和FTS表删除 codeHash: {codeHash}")
            return True
        except Exception as e:
            self.conn.rollback() # 回滚事务
            logger.error(f"删除 codeHash={codeHash} 时发生错误: {e}", exc_info=True)
            return False

    def getSharesByStatusPaged(self, status_filter: str, page: int = 1):
        # status_filter: "approved", "pending", "private"
        # 返回 [(codeHash, rootFolderName, shareCode, timeStamp, visibleFlag)...], is_end_page
        if page < 1:
            page = 1
        limit = 100
        offset = (page - 1) * limit

        sql_where_clause = ""

        if status_filter == "approved":
            sql_where_clause = "WHERE visibleFlag = 1" # True
        elif status_filter == "pending":
            sql_where_clause = "WHERE visibleFlag IS NULL"
        elif status_filter == "private":
            sql_where_clause = "WHERE visibleFlag = 0" # False
        else: # 如果状态无效，返回空
            return [], True

        # 获取总记录数
        count_sql = f"SELECT COUNT(*) FROM PAN123DATABASE {sql_where_clause}"
        self.database.execute(count_sql)
        total_records = self.database.fetchone()[0]

        query_sql = f"SELECT codeHash, rootFolderName, shareCode, timeStamp, visibleFlag FROM PAN123DATABASE {sql_where_clause} ORDER BY timeStamp DESC LIMIT ? OFFSET ?"
        
        self.database.execute(query_sql, (limit, offset)) # LIMIT 和 OFFSET 作为参数
        
        raw_results = self.database.fetchall()
        processed_results = []
        for codeHash, rootFolderName, shareCode, timeStamp, visibleFlag_db in raw_results:
            # 确保 visibleFlag 是 Python bool 或 None
            visible_flag_py = None
            if visibleFlag_db == 1:
                visible_flag_py = True
            elif visibleFlag_db == 0:
                visible_flag_py = False
            
            processed_results.append((
                codeHash,
                rootFolderName,
                shareCode,
                timeStamp,
                visible_flag_py
            ))
            
        is_end_page = (page * limit) >= total_records
        
        return processed_results, is_end_page

    def updateVisibleFlag(self, codeHash: str, newVisibleFlag: bool):
        try:
            self.database.execute("UPDATE PAN123DATABASE SET visibleFlag=? WHERE codeHash=?", (newVisibleFlag, codeHash))
            self.conn.commit()
            if self.database.rowcount > 0:
                logger.info(f"已更新 codeHash: {codeHash} 的 visibleFlag 为 {newVisibleFlag}")
                return True
            else:
                logger.warning(f"未找到 codeHash: {codeHash}，无法更新 visibleFlag。")
                return False
        except Exception as e:
            logger.error(f"更新 visibleFlag 失败 (codeHash: {codeHash}): {e}", exc_info=True)
            return False
 
    def updateRootFolderName(self, codeHash: str, newRootFolderName: str):
        # 更新 rootFolderName 时，需要同步更新 FTS 表中的 searchText
        # 获取 shareCode 以重新生成 searchText
        self.database.execute("SELECT shareCode FROM PAN123DATABASE WHERE codeHash=?", (codeHash,))
        row = self.database.fetchone()
        if not row:
            logger.warning(f"无法更新 rootFolderName：未在主表中找到 codeHash: {codeHash}。")
            return False
        shareCode = row[0] # 获取旧的 shareCode

        try:
            self.conn.execute('BEGIN') # 开始事务

            # 1. 更新主表 PAN123DATABASE
            self.database.execute("UPDATE PAN123DATABASE SET rootFolderName=? WHERE codeHash=?", (newRootFolderName, codeHash))
            
            # 检查主表是否真的更新了 (即 codeHash 存在)
            if self.database.rowcount > 0:
                # 2. 主表更新成功，现在更新 FTS 表 PAN123DATABASE_SEARCH
                # 重新生成 searchText
                new_searchText = getSearchText(shareCode, newRootFolderName)
                
                # 更新 FTS 表 (先删除再插入)
                self.database.execute("DELETE FROM PAN123DATABASE_SEARCH WHERE codeHash=?", (codeHash,))
                self.database.execute(
                    "INSERT INTO PAN123DATABASE_SEARCH (codeHash, searchText) VALUES (?, ?)",
                    (codeHash, new_searchText)
                )
                
                self.conn.commit() # 提交事务
                logger.debug(f"已更新 codeHash: {codeHash} 的 rootFolderName 为 {newRootFolderName}，并同步更新了FTS表。")
                return True
            else:
                # 如果主表更新的 rowcount 为 0，说明 codeHash 不存在，回滚。
                self.conn.rollback()
                logger.warning(f"无法更新 rootFolderName：主表中 codeHash: {codeHash} 更新影响行数为0（可能不存在）。")
                return False
        except Exception as e:
            self.conn.rollback() # 回滚事务
            logger.error(f"更新 rootFolderName (codeHash: {codeHash}) 或其FTS索引失败: {e}", exc_info=True)
            return False

    def close(self):
        if self.conn:
            self.conn.close()



if __name__ == "__main__":

    db = Pan123Database(dbpath="./assets/PAN123DATABASE.db")

    # 从 ./export 导入文件 (兼容旧版)
    # db.importShareFiles(folder_path="./export")
    
    # 从 ./assets/PAN123DATABASE_OLD.db 导入数据
    # db.importDatabase("./assets/PAN123DATABASE_OLD.db")

    # logger.info("\n\n--- 测试 listData (公开资源) ---\n")

    # public_shares, end_page = db.listData(page=1)
    
    # if public_shares:
    #     for item in public_shares:
    #         logger.info(str(item))
    # else:
    #     logger.info("无公开资源")
    
    # print(end_page)

    logger.info("\n\n--- 测试 searchDataByName ---\n")
    
    search_results, end_page = db.searchDataByName("柏林", page=1, visible_flag=True)

    if search_results:
        for item in search_results:
            logger.info(str(item))
    else:
        logger.info("未找到匹配的资源")

    print(end_page)

    db.close()