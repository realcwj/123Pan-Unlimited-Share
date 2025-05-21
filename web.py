import os
import sys
import io
import time
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, get_flashed_messages
from werkzeug.utils import secure_filename
import werkzeug.security # For safe_join
from Pan123 import Pan123

DEBUG = False

app = Flask(__name__)
app.secret_key = '114514'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'123share'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 10

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mode', methods=['POST'])
def select_mode():
    mode = request.form.get('mode')
    if mode == 'export':
        return redirect(url_for('export_form'))
    elif mode == 'import':
        return redirect(url_for('import_form'))
    elif mode == 'link':
        return redirect(url_for('link_form'))
    else:
        flash('无效的模式选择!', 'error')
        return redirect(url_for('index'))

@app.route('/export', methods=['GET', 'POST'])
def export_form():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        home_file_id_str = request.form.get('homeFilePath', '0')
        user_specified_base_name = request.form.get('saveFilename', 'exported_data.123share').strip()

        if not username or not password:
            flash('手机号/邮箱和密码不能为空!', 'error')
            return render_template('export_form.html')
        if not user_specified_base_name:
            flash('导出文件名不能为空!', 'error')
            return render_template('export_form.html')

        # --- Add timestamp to filename ---
        timestamp = str(int(time.time()))
        # Ensure there's no leading/trailing whitespace from user input on the base name
        user_specified_base_name = user_specified_base_name.strip()
        # Prepend timestamp
        filename_with_timestamp = f"{timestamp}_{user_specified_base_name}"
        # --- End timestamp addition ---

        # Use secure_filename for the actual filename on the server's disk, based on the timestamped name
        server_disk_filename = secure_filename(filename_with_timestamp)
        # If secure_filename results in an empty string (e.g., input was just ".." or similar)
        if not server_disk_filename:
            # Fallback to a generic name, still with timestamp to ensure uniqueness
            server_disk_filename = f"{timestamp}_default_export.123share"
        
        save_path_on_server = os.path.join(app.config['UPLOAD_FOLDER'], server_disk_filename)

        console_log = "未能捕获控制台输出。"
        old_stdout = sys.stdout
        sys.stdout = captured_output_buffer = io.StringIO()
        export_success = False

        try:
            driver = Pan123(debug=DEBUG)
            if driver.doLogin(username=username, password=password):
                try:
                    parent_file_id_internal = int(home_file_id_str)
                except ValueError:
                    parent_file_id_internal = home_file_id_str
                
                export_success = driver.exportFiles(
                    parentFileId=parent_file_id_internal,
                    savePath=save_path_on_server
                )
                driver.doLogout()
            else:
                flash('登录失败，请检查用户名和密码。', 'error')
        except Exception as e:
            flash(f'导出过程中发生错误: {str(e)}', 'error')
            app.logger.error(f"Export error: {e}", exc_info=True)
        finally:
            sys.stdout = old_stdout
            console_log = captured_output_buffer.getvalue()
            captured_output_buffer.close()

        if export_success:
            flash(f'文件已成功导出为 {filename_with_timestamp}。请点击下方链接下载。', 'success')
            return render_template('result.html',
                                   message=f"导出成功: {filename_with_timestamp}",
                                   # Pass the timestamped name as the original_filename for download suggestion
                                   download_link=url_for('download_file', server_filename=server_disk_filename, original_filename=filename_with_timestamp),
                                   show_home_button=True,
                                   console_log=console_log)
        else:
            if not get_flashed_messages(category_filter=['error']):
                 flash('导出失败，请检查日志或输入。', 'error')
            return render_template('result.html',
                                   error_message="导出操作未成功完成。",
                                   console_log=console_log,
                                   show_home_button=True)

    return render_template('export_form.html')

@app.route('/import', methods=['GET', 'POST'])
def import_form():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        file = request.files.get('filePath')

        if not username or not password:
            flash('手机号/邮箱和密码不能为空!', 'error')
            return render_template('import_form.html')

        if not file or file.filename == '':
            flash('请选择要上传的 .123share 文件!', 'error')
            return render_template('import_form.html')

        original_filename = file.filename
        if allowed_file(original_filename):
            file_path_on_server = None
            import_success = False
            
            console_log = "未能捕获控制台输出。"
            old_stdout = sys.stdout
            sys.stdout = captured_output_buffer = io.StringIO()

            try:
                upload_dir = app.config['UPLOAD_FOLDER']
                # For import, the original filename (including Chinese chars) is critical for Pan123 lib.
                # We save it with its original name in a safe way.
                # Timestamping is generally for EXPORTED files to avoid server-side name clashes from multiple export operations.
                # If the user uploads "测试.123share", we save it as "测试.123share" on server for Pan123.importFiles
                potential_path = werkzeug.security.safe_join(upload_dir, original_filename)
                
                if potential_path is None:
                    raise ValueError(f'上传的文件名 "{original_filename}" 包含不安全字符或路径。')
                file_path_on_server = potential_path
                
                os.makedirs(os.path.dirname(file_path_on_server), exist_ok=True)
                file.save(file_path_on_server)
                app.logger.info(f"File saved to: {file_path_on_server}")

                driver = Pan123(debug=DEBUG)
                if driver.doLogin(username=username, password=password):
                    import_success = driver.importFiles(filePath=file_path_on_server) # Pan123 needs the actual path with original name
                    driver.doLogout()
                else:
                    flash('登录失败，请检查用户名和密码。', 'error')
            
            except ValueError as ve:
                flash(str(ve), 'error')
            except werkzeug.exceptions.BadRequestData:
                 flash(f'错误：上传的文件名 "{original_filename}" 格式无效或包含非法字符。', 'error')
            except Exception as e:
                flash(f'导入过程中发生错误: {str(e)}', 'error')
                app.logger.error(f"Import error with file {original_filename}: {e}", exc_info=True)
            finally:
                sys.stdout = old_stdout
                console_log = captured_output_buffer.getvalue()
                captured_output_buffer.close()
            
            if import_success:
                flash('文件导入成功!', 'success')
                # Optional: clean up the uploaded file from server
                # if file_path_on_server and os.path.exists(file_path_on_server):
                #     try: os.remove(file_path_on_server)
                #     except Exception as e_del: app.logger.error(f"Error deleting {file_path_on_server}: {e_del}")
                return render_template('result.html', message="文件导入成功！", show_home_button=True, console_log=console_log)
            else:
                if not get_flashed_messages(category_filter=['error']):
                    flash('导入失败，请检查文件或日志。', 'error')
                return render_template('result.html',
                                   error_message="导入操作未成功完成。",
                                   console_log=console_log,
                                   show_home_button=True)
        else:
            flash('只允许上传 .123share 文件!', 'error')
        return render_template('import_form.html')

    return render_template('import_form.html')

@app.route('/link', methods=['GET', 'POST'])
def link_form():
    if request.method == 'POST':
        share_key = request.form.get('shareKey')
        share_pwd = request.form.get('sharePwd')
        parent_file_id_str = request.form.get('parentFileId', '0')
        user_specified_base_name = request.form.get('saveFilename', 'shared_link_data.123share').strip()

        if not share_key:
            flash('分享链接的 Key 不能为空!', 'error')
            return render_template('link_form.html')
        if not user_specified_base_name:
            flash('导出文件名不能为空!', 'error')
            return render_template('link_form.html')

        # --- Add timestamp to filename ---
        timestamp = str(int(time.time()))
        user_specified_base_name = user_specified_base_name.strip()
        filename_with_timestamp = f"{timestamp}_{user_specified_base_name}"
        # --- End timestamp addition ---

        server_disk_filename = secure_filename(filename_with_timestamp)
        if not server_disk_filename:
            server_disk_filename = f"{timestamp}_default_shared_export.123share"
        
        save_path_on_server = os.path.join(app.config['UPLOAD_FOLDER'], server_disk_filename)

        console_log = "未能捕获控制台输出。"
        old_stdout = sys.stdout
        sys.stdout = captured_output_buffer = io.StringIO()
        link_export_success = False

        try:
            driver = Pan123(debug=DEBUG)
            try:
                parent_file_id_internal = int(parent_file_id_str)
            except ValueError:
                parent_file_id_internal = parent_file_id_str
            
            link_export_success = driver.exportShare(
                parentFileId=parent_file_id_internal,
                shareKey=share_key,
                sharePwd=share_pwd,
                savePath=save_path_on_server
            )
        except Exception as e:
            flash(f'从分享链接导出过程中发生错误: {str(e)}', 'error')
            app.logger.error(f"Link export error: {e}", exc_info=True)
        finally:
            sys.stdout = old_stdout
            console_log = captured_output_buffer.getvalue()
            captured_output_buffer.close()

        if link_export_success:
            flash(f'分享链接内容已成功导出为 {filename_with_timestamp}。请点击下方链接下载。', 'success')
            return render_template('result.html',
                                   message=f"从分享链接导出成功: {filename_with_timestamp}",
                                   download_link=url_for('download_file', server_filename=server_disk_filename, original_filename=filename_with_timestamp),
                                   show_home_button=True,
                                   console_log=console_log)
        else:
            if not get_flashed_messages(category_filter=['error']):
                 flash('从分享链接导出失败，请检查链接信息或日志。', 'error')
            return render_template('result.html',
                                   error_message="从分享链接导出操作未成功完成。",
                                   console_log=console_log,
                                   show_home_button=True)

    return render_template('link_form.html')

# 文件下载路由
@app.route('/uploads/<server_filename>')
def download_file(server_filename):
    original_filename_to_suggest = request.args.get('original_filename', server_filename)
    
    file_path_on_server_dir = app.config['UPLOAD_FOLDER']
    full_path_to_check = werkzeug.security.safe_join(file_path_on_server_dir, server_filename)

    if full_path_to_check is None or not os.path.isfile(full_path_to_check):
        app.logger.warning(f"Download attempt for non-existent or unsafe file: server_filename={server_filename}, original_filename={original_filename_to_suggest}, checked_path={full_path_to_check}")
        flash('错误：请求下载的文件未找到或路径不安全。','error')
        return redirect(url_for('index'))

    return send_from_directory(
        directory=file_path_on_server_dir,
        path=server_filename, # This is the actual filename on disk (e.g., timestamp_secured_name.123share)
        download_name=original_filename_to_suggest, # This is what the user sees (e.g., timestamp_测试.123share)
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=DEBUG, host='0.0.0.0', port=33333)