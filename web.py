import os
from getGlobalLogger import logger

from flask import Flask, render_template, request, make_response, \
                    session, redirect, url_for, flash

from src.config.loadSettings import loadSettings
from src.database.Pan123Database import Pan123Database

# --- 从 api 包导入处理函数 ---
from api.action_export import handle_export_request
from api.action_import import handle_import_request
from api.action_link import handle_link_request
from api.list_public_shares import handle_list_public_shares
from api.get_content_tree import handle_get_content_tree
from api.get_sharecode import handle_get_sharecode
from api.submit_database import handle_submit_database
from api.search_database import handle_search_database
from api.action_transform import handle_transform_to_123fastlink_json_request, handle_transform_from_123fastlink_json_request

# --- 从 api.admin 包导入Admin API处理函数 ---
from api.admin.admin_utils import admin_required
from api.admin.get_shares import handle_admin_get_shares
from api.admin.update_share_status import handle_admin_update_share_status
from api.admin.update_share_name import handle_admin_update_share_name
from api.admin.delete_share import handle_admin_delete_share
from api.admin.update_database import handle_admin_update_database # 新增导入

# --- 加载配置 ---
ADMIN_ENTRY = loadSettings("ADMIN_ENTRY")
ADMIN_USERNAME = loadSettings("ADMIN_USERNAME")
ADMIN_PASSWORD = loadSettings("ADMIN_PASSWORD")
PORT = loadSettings("PORT")
DATABASE_PATH = loadSettings("DATABASE_PATH") 
SECRET_KEY = loadSettings("SECRET_KEY")
BAN_IP_ENABLED = loadSettings("BAN_IP")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Flask 应用初始化 ---
app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, 'static'),
    template_folder=os.path.join(BASE_DIR,'templates')
    )
app.secret_key = SECRET_KEY

# --- 将全局 logger 配置应用到 Flask ---
if app.logger: # Flask app logger
    app.logger.handlers.clear() # 清除 Flask 默认的 basicConfig 处理器
    for handler in logger.handlers: # 将我们全局 logger 的处理器赋给它
        app.logger.addHandler(handler)
    app.logger.setLevel(logger.level) # 确保 Flask logger 的级别与全局 logger 一致

logger.info(f"Flask 应用已加载全局日志配置。Flask logger level: {app.logger.level}")

# --- HTML 路由 ---
@app.route('/')
def index():
    return render_template('index.html', BAN_IP_ENABLED=BAN_IP_ENABLED)

@app.route('/banip')
def banip_page():
    return render_template('banip.html')

@app.route('/export')
def export_page():
    return render_template('export_form.html', BAN_IP_ENABLED=BAN_IP_ENABLED)

@app.route('/import')
def import_page():
    return render_template('import_form.html', BAN_IP_ENABLED=BAN_IP_ENABLED)

@app.route('/link')
def link_page():
    return render_template('link_form.html', BAN_IP_ENABLED=BAN_IP_ENABLED)

@app.route('/transform')
def transform_page():
    return render_template('transform.html', BAN_IP_ENABLED=BAN_IP_ENABLED)

# --- Admin HTML 路由 ---
@app.route(f'/{ADMIN_ENTRY}/login', methods=['GET', 'POST'])
def admin_login_page(): # 此路由不需要 admin_required
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session['admin_username'] = username 
            flash('登录成功！', 'success')
            
            resp = make_response(redirect(url_for('admin_dashboard_page'))) # 指向下面的 dashboard 路由
            resp.set_cookie('admin_username', username, max_age=30*24*60*60) # 30天有效
            return resp
        else:
            flash('用户名或密码错误。', 'danger')
    return render_template('admin_login.html', admin_entry=ADMIN_ENTRY)

@app.route(f'/{ADMIN_ENTRY}/dashboard')
@admin_required # 保护 Admin Dashboard HTML 页面
def admin_dashboard_page():
    return render_template('admin_dashboard.html', admin_entry=ADMIN_ENTRY, admin_username=session.get('admin_username'))

@app.route(f'/{ADMIN_ENTRY}/logout')
@admin_required # 保护 Admin Logout HTML 动作（虽然它是个重定向）
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    flash('您已成功注销。', 'info')
    resp = make_response(redirect(url_for('admin_login_page')))
    return resp

# --- API 路由 ---
@app.route('/api/export', methods=['POST'])
def api_export_route():
    return handle_export_request(request.get_json())

@app.route('/api/import', methods=['POST'])
def api_import_route():
    return handle_import_request(request.get_json())

@app.route('/api/link', methods=['POST'])
def api_link_route():
    return handle_link_request(request.get_json())

@app.route('/api/list_public_shares', methods=['GET'])
def api_list_public_shares_route():
    return handle_list_public_shares()

@app.route('/api/get_content_tree', methods=['POST'])
def api_get_content_tree_route():
    return handle_get_content_tree()

@app.route('/api/get_sharecode', methods=['POST'])
def api_get_sharecode_route():
    return handle_get_sharecode()

@app.route('/api/submit_database', methods=['POST'])
def api_submit_database_route():
    return handle_submit_database()

@app.route('/api/search_database', methods=['POST'])
def api_search_database_route():
    return handle_search_database()

@app.route('/api/transformShareCodeTo123FastLinkJson', methods=['POST'])
def api_transform_to_123fastlink_json_route():
    return handle_transform_to_123fastlink_json_request()

@app.route('/api/transform123FastLinkJsonToShareCode', methods=['POST'])
def api_transform_from_123fastlink_json_route():
    return handle_transform_from_123fastlink_json_request()

# --- Admin API 路由 ---
@app.route(f'/api/{ADMIN_ENTRY}/get_shares', methods=['GET'])
@admin_required
def api_admin_get_shares_route():
    return handle_admin_get_shares()

@app.route(f'/api/{ADMIN_ENTRY}/update_share_status', methods=['POST'])
@admin_required
def api_admin_update_share_status_route():
    return handle_admin_update_share_status()

@app.route(f'/api/{ADMIN_ENTRY}/update_share_name', methods=['POST'])
@admin_required
def api_admin_update_share_name_route():
    return handle_admin_update_share_name()

@app.route(f'/api/{ADMIN_ENTRY}/delete_share', methods=['POST'])
@admin_required
def api_admin_delete_share_route():
    return handle_admin_delete_share()

@app.route(f'/api/{ADMIN_ENTRY}/update_database', methods=['POST'])
@admin_required
def api_admin_update_database_route():
    return handle_admin_update_database()

# --- 应用启动入口 ---
if __name__ == '__main__':

    # 下载最新数据库
    # 注意：现在更新数据库功能已迁移到 后台管理面板 中
    # try:
    #     db = Pan123Database(dbpath=DATABASE_PATH)
    #     logger.info("正在下载最新数据库...")
    #     latest_db_path = db.downloadLatestDatabase()
    #     logger.info("正在导入最新数据库...")
    #     db.importDatabase(latest_db_path)
    #     db.close()
    # except Exception as e:
    #     logger.critical(f"数据库更新发生严重错误: {e}", exc_info=True)
    #     logger.info("按任意键结束...")
    #     input("按任意键结束")
    #     exit(0)

    # 启动Flask应用
    flask_debug_mode = True if loadSettings("LOGGER_LEVEL") == "DEBUG" else False
    logger.info(f"启动 Flask Web 服务... 访问地址: http://127.0.0.1:{PORT}/ 或 http://公网地址:IP/  或 https://公网域名/")
    logger.info(f"Flask 调试模式: {'开启' if flask_debug_mode else '关闭'}")
    app.run(
        debug=flask_debug_mode, # 如果 settings.yaml 设置 LOGGING_LEVEL="DEBUG", 这里为 True, 否则为 False
        host='0.0.0.0',
        port=PORT,
        threaded=True
        )