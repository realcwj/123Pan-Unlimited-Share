import os
import sys
import io
import time
import json
import base64
from flask import Flask, render_template, request, redirect, url_for, flash, Response, stream_with_context, jsonify, make_response
from werkzeug.utils import secure_filename # 仅用于资源共享计划的文件名安全处理
from Pan123 import Pan123

# DEBUG = True # 开发时可以设为 True
DEBUG = True

app = Flask(__name__)
app.secret_key = '114514_new_secret_key_for_updates' # 建议更新密钥

# 资源共享计划的目录
PUBLIC_SHARE_CHECK_FOLDER = os.path.join(os.getcwd(), 'public', 'check')
PUBLIC_SHARE_OK_FOLDER = os.path.join(os.getcwd(), 'public', 'ok')

# 应用启动时创建所需目录
if not os.path.exists(PUBLIC_SHARE_CHECK_FOLDER):
    os.makedirs(PUBLIC_SHARE_CHECK_FOLDER)
if not os.path.exists(PUBLIC_SHARE_OK_FOLDER):
    os.makedirs(PUBLIC_SHARE_OK_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

# --- API Endpoints ---

@app.route('/api/export', methods=['POST'])
def api_export():
    data = request.get_json()
    if not data:
        return jsonify({"isFinish": False, "message": "错误的请求：没有提供JSON数据。"}), 400

    username = data.get('username')
    password = data.get('password')
    home_file_path_str = data.get('homeFilePath', '0')
    user_specified_base_name = data.get('userSpecifiedBaseName', '').strip()
    share_project = data.get('shareProject', False)

    if not username or not password:
        return jsonify({"isFinish": False, "message": "用户名和密码不能为空。"}), 400
    if not home_file_path_str: # homeFilePath 允许为 0
         return jsonify({"isFinish": False, "message": "文件夹ID不能为空。"}), 400

    try:
        parent_file_id_internal = int(home_file_path_str)
    except ValueError:
        parent_file_id_internal = home_file_path_str # 允许字符串形式的ID

    timestamp = str(int(time.time()))
    if user_specified_base_name:
        filename_base = f"{timestamp}_{user_specified_base_name}"
    else:
        filename_base = timestamp
    
    # 确保文件名后缀正确
    if not filename_base.endswith(".123share"):
        filename_for_sharing = f"{filename_base}.123share"
    else:
        filename_for_sharing = filename_base

    def generate_export():
        driver = Pan123(debug=DEBUG)
        login_success = driver.doLogin(username=username, password=password)
        
        if not login_success:
            yield f"{json.dumps({'isFinish': False, 'message': '登录失败，请检查用户名和密码。'})}\n"
            return

        yield f"{json.dumps({'isFinish': None, 'message': '登录成功，开始导出文件列表...'})}\n"
        
        final_b64_data = None
        try:
            for state in driver.exportFiles(parentFileId=parent_file_id_internal):
                if state.get("isFinish") is True:
                    final_b64_data = state["message"] # 这是 bytes 类型
                    # 将 bytes 转换为 base64 字符串发送给前端
                    yield f"{json.dumps({'isFinish': True, 'message': final_b64_data.decode('utf-8')})}\n"
                elif state.get("isFinish") is False:
                    yield f"{json.dumps(state)}\n"
                else: # isFinish is None
                    yield f"{json.dumps(state)}\n"
            
            if final_b64_data and share_project:
                try:
                    # 安全处理一下文件名，尽管它主要基于时间戳和用户输入（已处理strip）
                    safe_share_filename = secure_filename(filename_for_sharing)
                    if not safe_share_filename: # 如果 secure_filename 返回空
                        safe_share_filename = f"{timestamp}_unsafe_fallback.123share"

                    share_file_path = os.path.join(PUBLIC_SHARE_CHECK_FOLDER, safe_share_filename)
                    with open(share_file_path, "wb") as f:
                        f.write(final_b64_data)
                    yield f"{json.dumps({'isFinish': None, 'message': f'文件已提交至资源共享计划审核队列: {safe_share_filename}'})}\n"
                except Exception as e_share:
                    yield f"{json.dumps({'isFinish': None, 'message': f'加入资源共享计划失败: {str(e_share)}'})}\n"

        except Exception as e:
            yield f"{json.dumps({'isFinish': False, 'message': f'导出过程中发生错误: {str(e)}'})}\n"
            app.logger.error(f"Export API error: {e}", exc_info=True)
        finally:
            if login_success: # 只有登录成功了才尝试注销
                driver.doLogout()
                yield f"{json.dumps({'isFinish': None, 'message': '已注销账号。'})}\n"

    return Response(stream_with_context(generate_export()), content_type='application/x-ndjson')

@app.route('/api/import', methods=['POST'])
def api_import():
    data = request.get_json()
    if not data:
        return jsonify({"isFinish": False, "message": "错误的请求：没有提供JSON数据。"}), 400

    username = data.get('username')
    password = data.get('password')
    base64_data_str = data.get('base64Data') # 前端传来的应是base64字符串
    root_folder_name = data.get('rootFolderName')

    if not username or not password:
        return jsonify({"isFinish": False, "message": "用户名和密码不能为空。"}), 400
    if not base64_data_str:
        return jsonify({"isFinish": False, "message": "分享码 (base64Data) 不能为空。"}), 400
    if not root_folder_name:
        return jsonify({"isFinish": False, "message": "根目录名不能为空。"}), 400

    try:
        # Pan123.py的importFiles期望base64Data是bytes
        base64_data_bytes = base64.urlsafe_b64decode(base64_data_str.encode('utf-8'))
    except Exception as e:
        return jsonify({"isFinish": False, "message": f"分享码格式错误: {str(e)}"}), 400
        
    def generate_import():
        driver = Pan123(debug=DEBUG)
        login_success = driver.doLogin(username=username, password=password)

        if not login_success:
            yield f"{json.dumps({'isFinish': False, 'message': '登录失败，请检查用户名和密码。'})}\n"
            return
        
        yield f"{json.dumps({'isFinish': None, 'message': '登录成功，开始导入文件...'})}\n"
        
        try:
            for state in driver.importFiles(base64Data=base64_data_bytes, rootFolderName=root_folder_name):
                yield f"{json.dumps(state)}\n" # state 已经是 {"isFinish": ..., "message": ...} 格式
        except Exception as e:
            yield f"{json.dumps({'isFinish': False, 'message': f'导入过程中发生错误: {str(e)}'})}\n"
            app.logger.error(f"Import API error: {e}", exc_info=True)
        finally:
            if login_success:
                driver.doLogout()
                yield f"{json.dumps({'isFinish': None, 'message': '已注销账号。'})}\n"
                
    return Response(stream_with_context(generate_import()), content_type='application/x-ndjson')

@app.route('/api/link', methods=['POST'])
def api_link():
    data = request.get_json()
    if not data:
        return jsonify({"isFinish": False, "message": "错误的请求：没有提供JSON数据。"}), 400

    parent_file_id_str = data.get('parentFileId', '0')
    share_key = data.get('shareKey')
    share_pwd = data.get('sharePwd', '') # 密码可以为空
    user_specified_base_name = data.get('userSpecifiedBaseName', '').strip()
    share_project = data.get('shareProject', False)

    if not share_key:
        return jsonify({"isFinish": False, "message": "分享链接 Key 不能为空。"}), 400
    if not parent_file_id_str: # parentFileId 允许为 0
        return jsonify({"isFinish": False, "message": "文件夹ID不能为空。"}), 400
        
    try:
        parent_file_id_internal = int(parent_file_id_str)
    except ValueError:
        parent_file_id_internal = parent_file_id_str

    timestamp = str(int(time.time()))
    # 构建基础文件名
    if user_specified_base_name:
        filename_base_parts = [timestamp, user_specified_base_name]
    else:
        filename_base_parts = [timestamp]
    
    # 为资源共享计划的文件名添加key和pwd信息 (如果存在)
    share_info_parts = [share_key]
    if share_pwd:
        share_info_parts.append(share_pwd)
    
    filename_base_for_sharing = "_".join(filename_base_parts + share_info_parts)

    if not filename_base_for_sharing.endswith(".123share"):
        filename_for_sharing = f"{filename_base_for_sharing}.123share"
    else:
        filename_for_sharing = filename_base_for_sharing

    def generate_link_export():
        driver = Pan123(debug=DEBUG) # Link export不需要登录
        yield f"{json.dumps({'isFinish': None, 'message': '开始从分享链接导出文件列表...'})}\n"
        
        final_b64_data = None
        try:
            for state in driver.exportShare(
                parentFileId=parent_file_id_internal, 
                shareKey=share_key, 
                sharePwd=share_pwd
            ):
                if state.get("isFinish") is True:
                    final_b64_data = state["message"] # bytes
                    yield f"{json.dumps({'isFinish': True, 'message': final_b64_data.decode('utf-8')})}\n"
                elif state.get("isFinish") is False:
                    yield f"{json.dumps(state)}\n"
                else: # isFinish is None
                    yield f"{json.dumps(state)}\n"

            if final_b64_data and share_project:
                try:
                    safe_share_filename = secure_filename(filename_for_sharing)
                    if not safe_share_filename:
                        safe_share_filename = f"{timestamp}_{share_key}_unsafe_fallback.123share"
                    
                    share_file_path = os.path.join(PUBLIC_SHARE_CHECK_FOLDER, safe_share_filename)
                    with open(share_file_path, "wb") as f:
                        f.write(final_b64_data)
                    yield f"{json.dumps({'isFinish': None, 'message': f'文件已提交至资源共享计划审核队列: {safe_share_filename}'})}\n"
                except Exception as e_share:
                    yield f"{json.dumps({'isFinish': None, 'message': f'加入资源共享计划失败: {str(e_share)}'})}\n"

        except Exception as e:
            yield f"{json.dumps({'isFinish': False, 'message': f'从分享链接导出过程中发生错误: {str(e)}'})}\n"
            app.logger.error(f"Link export API error: {e}", exc_info=True)

    return Response(stream_with_context(generate_link_export()), content_type='application/x-ndjson')

@app.route('/api/list_public_shares', methods=['GET'])
def list_public_shares():
    try:
        share_files = []
        if os.path.exists(PUBLIC_SHARE_OK_FOLDER):
            for f_name in os.listdir(PUBLIC_SHARE_OK_FOLDER):
                if f_name.endswith(".123share"):
                    # 提取不带后缀的文件名作为 "name"，完整文件名作为 "value"
                    base_name = os.path.splitext(f_name)[0]
                    share_files.append({"name": base_name, "filename": f_name})
        return jsonify({"success": True, "files": sorted(share_files, key=lambda x: x['name'])}), 200
    except Exception as e:
        app.logger.error(f"Error listing public shares: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"获取公共分享列表失败: {str(e)}"}), 500

@app.route('/api/get_public_share_content', methods=['GET'])
def get_public_share_content():
    filename = request.args.get('filename')
    if not filename:
        return jsonify({"success": False, "message": "缺少文件名参数。"}), 400

    # 安全性：确保文件名不包含路径遍历字符
    safe_filename = secure_filename(filename)
    if safe_filename != filename or not filename.endswith(".123share"):
        return jsonify({"success": False, "message": "无效的文件名。"}), 400

    file_path = os.path.join(PUBLIC_SHARE_OK_FOLDER, safe_filename)

    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "文件未找到。"}), 404

    try:
        with open(file_path, "rb") as f:
            content_bytes = f.read()
        # 将字节串转换为 base64 字符串返回
        content_b64_str = base64.urlsafe_b64encode(content_bytes).decode('utf-8')
        root_folder_name = os.path.splitext(safe_filename)[0] # 使用不带后缀的文件名作为根目录名建议
        return jsonify({"success": True, "base64Data": content_b64_str, "rootFolderName": root_folder_name}), 200
    except Exception as e:
        app.logger.error(f"Error reading public share {safe_filename}: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"读取分享文件内容失败: {str(e)}"}), 500

# --- HTML Routes ---
@app.route('/export')
def export_page():
    resp = make_response(render_template('export_form.html'))
    return resp

@app.route('/import')
def import_page():
    resp = make_response(render_template('import_form.html'))
    return resp

@app.route('/link')
def link_page():
    resp = make_response(render_template('link_form.html'))
    return resp

if __name__ == '__main__':
    # 确保在生产环境中 DEBUG 为 False
    # app.run(debug=DEBUG, host='0.0.0.0', port=33333)
    # 根据用户原始的 web.py，debug 是全局变量
    app.run(debug=DEBUG, host='0.0.0.0', port=33333, threaded=True) # threaded=True有助处理并发请求