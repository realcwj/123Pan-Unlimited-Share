import os
import time
import json
from flask import Flask, render_template, request, Response, stream_with_context, jsonify, make_response
import re
import unicodedata

from Pan123 import Pan123

DEBUG = False

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

def custom_secure_filename_part(name_str):
    """
    清理用户输入的文件名部分，移除路径相关和常见非法字符，但保留中文、字母、数字等。
    """
    if not name_str:
        return ""
    
    name_str = unicodedata.normalize('NFC', name_str)
    name_str = "".join(c for c in name_str if unicodedata.category(c)[0] != "C")
    name_str = re.sub(r'[\\/:*?"<>|]', '_', name_str)
    name_str = name_str.strip(' .')
    if re.fullmatch(r'\.+', name_str):
        return "_"
    if not name_str:
        return "untitled"
    return name_str

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
    user_specified_base_name_raw = data.get('userSpecifiedBaseName', '').strip()
    share_project = data.get('shareProject', False)

    if not username or not password:
        return jsonify({"isFinish": False, "message": "用户名和密码不能为空。"}), 400
    if not home_file_path_str:
         return jsonify({"isFinish": False, "message": "文件夹ID不能为空。"}), 400

    try:
        parent_file_id_internal = int(home_file_path_str)
    except ValueError:
        parent_file_id_internal = home_file_path_str 

    timestamp = str(int(time.time()))
    cleaned_user_name_part = custom_secure_filename_part(user_specified_base_name_raw)

    if cleaned_user_name_part:
        filename_base = f"{timestamp}_{cleaned_user_name_part}"
    else:
        filename_base = timestamp
    
    server_filename_for_sharing = f"{filename_base}.123share"
    if not server_filename_for_sharing.strip(' ._') or len(server_filename_for_sharing) <= len(".123share"):
        server_filename_for_sharing = f"{timestamp}_export_fallback.123share"

    def generate_export():
        driver = Pan123(debug=DEBUG)
        login_success = driver.doLogin(username=username, password=password)
        
        if not login_success:
            yield f"{json.dumps({'isFinish': False, 'message': '登录失败，请检查用户名和密码。'})}\n"
            return

        yield f"{json.dumps({'isFinish': None, 'message': '登录成功，开始导出文件列表...'})}\n"
        
        final_b64_string_data = None # 明确这是字符串
        try:
            for state in driver.exportFiles(parentFileId=parent_file_id_internal):
                if state.get("isFinish") is True:
                    final_b64_string_data = state["message"] # Pan123.py 现在返回字符串
                    yield f"{json.dumps({'isFinish': True, 'message': final_b64_string_data})}\n"
                elif state.get("isFinish") is False:
                    yield f"{json.dumps(state)}\n"
                else: 
                    yield f"{json.dumps(state)}\n"
            
            if final_b64_string_data and share_project:
                try:
                    share_file_path = os.path.join(PUBLIC_SHARE_CHECK_FOLDER, server_filename_for_sharing)
                    # 修改为文本写入模式 "w"
                    with open(share_file_path, "w", encoding="utf-8") as f:
                        f.write(final_b64_string_data) # 直接写入字符串
                    yield f"{json.dumps({'isFinish': None, 'message': f'文件已提交至资源共享计划审核队列: {server_filename_for_sharing}'})}\n"
                except Exception as e_share:
                    app.logger.error(f"Error saving to public share (export): {e_share}", exc_info=True)
                    yield f"{json.dumps({'isFinish': None, 'message': f'加入资源共享计划失败: {str(e_share)}'})}\n"

        except Exception as e:
            yield f"{json.dumps({'isFinish': False, 'message': f'导出过程中发生错误: {str(e)}'})}\n"
            app.logger.error(f"Export API error: {e}", exc_info=True)
        finally:
            if login_success: 
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
    base64_data_str = data.get('base64Data') # 这是从前端传来的 Base64 字符串
    root_folder_name = data.get('rootFolderName')

    if not username or not password:
        return jsonify({"isFinish": False, "message": "用户名和密码不能为空。"}), 400
    if not base64_data_str:
        return jsonify({"isFinish": False, "message": "分享码 (base64Data) 不能为空。"}), 400
    if not root_folder_name:
        return jsonify({"isFinish": False, "message": "根目录名不能为空。"}), 400

    def generate_import():
        driver = Pan123(debug=DEBUG)
        login_success = driver.doLogin(username=username, password=password)

        if not login_success:
            yield f"{json.dumps({'isFinish': False, 'message': '登录失败，请检查用户名和密码。'})}\n"
            return
        
        yield f"{json.dumps({'isFinish': None, 'message': '登录成功，开始导入文件...'})}\n"
        
        try:
            # 直接将字符串 base64_data_str 传递给 importFiles
            for state in driver.importFiles(base64Data=base64_data_str, rootFolderName=root_folder_name):
                yield f"{json.dumps(state)}\n" 
        except Exception as e:
            # 此处的异常更多是 stream_with_context 或 Flask 相关，核心逻辑在 Pan123.py
            yield f"{json.dumps({'isFinish': False, 'message': f'导入流处理过程中发生错误: {str(e)}'})}\n"
            app.logger.error(f"Import API stream error: {e}", exc_info=True)
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
    share_pwd = data.get('sharePwd', '') 
    user_specified_base_name_raw = data.get('userSpecifiedBaseName', '').strip()
    share_project = data.get('shareProject', False)

    if not share_key:
        return jsonify({"isFinish": False, "message": "分享链接 Key 不能为空。"}), 400
    if not parent_file_id_str: 
        return jsonify({"isFinish": False, "message": "文件夹ID不能为空。"}), 400
        
    try:
        parent_file_id_internal = int(parent_file_id_str)
    except ValueError:
        parent_file_id_internal = parent_file_id_str

    timestamp = str(int(time.time()))
    cleaned_user_name_part = custom_secure_filename_part(user_specified_base_name_raw)
    
    filename_parts = [timestamp]
    if cleaned_user_name_part:
        filename_parts.append(cleaned_user_name_part)
    
    safe_share_key = re.sub(r'[\\/:*?"<>|]', '_', share_key)
    filename_parts.append(safe_share_key)
    if share_pwd:
        safe_share_pwd = re.sub(r'[\\/:*?"<>|]', '_', share_pwd)
        filename_parts.append(safe_share_pwd)
    
    filename_base_for_sharing = "_".join(filename_parts)
    server_filename_for_sharing = f"{filename_base_for_sharing}.123share"
    if not server_filename_for_sharing.strip(' ._') or len(server_filename_for_sharing) <= len(".123share"):
        server_filename_for_sharing = f"{timestamp}_{safe_share_key}_link_fallback.123share"

    def generate_link_export():
        driver = Pan123(debug=DEBUG) 
        yield f"{json.dumps({'isFinish': None, 'message': '开始从分享链接导出文件列表...'})}\n"

        final_b64_string_data = None # 明确这是字符串
        try:
            for state in driver.exportShare(
                parentFileId=parent_file_id_internal, 
                shareKey=share_key, 
                sharePwd=share_pwd
            ):
                if state.get("isFinish") is True:
                    final_b64_string_data = state["message"] # Pan123.py 现在返回字符串
                    yield f"{json.dumps({'isFinish': True, 'message': final_b64_string_data})}\n"
                elif state.get("isFinish") is False:
                    yield f"{json.dumps(state)}\n"
                else: 
                    yield f"{json.dumps(state)}\n"

            if final_b64_string_data and share_project:
                try:
                    share_file_path = os.path.join(PUBLIC_SHARE_CHECK_FOLDER, server_filename_for_sharing)
                    # 修改为文本写入模式 "w"
                    with open(share_file_path, "w", encoding="utf-8") as f:
                        f.write(final_b64_string_data) # 直接写入字符串
                    yield f"{json.dumps({'isFinish': None, 'message': f'文件已提交至资源共享计划审核队列: {server_filename_for_sharing}'})}\n"
                except Exception as e_share:
                    app.logger.error(f"Error saving to public share (link): {e_share}", exc_info=True)
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

    if ".." in filename or os.path.isabs(filename) or \
       "/" in filename or "\\" in filename:
        app.logger.warning(f"Potentially unsafe filename detected in get_public_share_content: {filename}")
        return jsonify({"success": False, "message": "文件名包含非法字符或路径。"}), 400

    if not filename.endswith(".123share"):
        return jsonify({"success": False, "message": "无效的文件扩展名。"}), 400
    
    file_path = os.path.join(PUBLIC_SHARE_OK_FOLDER, filename)
    file_path = os.path.normpath(file_path)

    if not file_path.startswith(os.path.normpath(PUBLIC_SHARE_OK_FOLDER) + os.sep):
        app.logger.warning(f"Path traversal attempt detected or invalid path structure: {file_path}")
        return jsonify({"success": False, "message": "文件路径无效。"}), 400

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        app.logger.warning(f"Public share file not found or is not a file. Requested filename: '{request.args.get('filename')}', Looked for: '{file_path}'")
        return jsonify({"success": False, "message": "文件未找到。"}), 404

    try:
        # 修改为文本读取模式 "r"
        # 假设 .123share 文件中存储的就是 Base64 字符串
        with open(file_path, "r", encoding="utf-8") as f:
            content_b64_str = f.read().strip() # 直接读取文件内容作为 base64 字符串

        root_folder_name = os.path.splitext(filename)[0] 
        return jsonify({"success": True, "base64Data": content_b64_str, "rootFolderName": root_folder_name}), 200
    except Exception as e:
        app.logger.error(f"Error reading public share '{filename}': {e}", exc_info=True)
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
    app.run(debug=DEBUG, host='0.0.0.0', port=33333, threaded=True)