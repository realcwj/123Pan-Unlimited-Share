from functools import wraps
from flask import session, flash, redirect, url_for
from src.config.loadSettings import loadSettings

ADMIN_ENTRY = loadSettings("ADMIN_ENTRY") 

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('请先登录以访问此页面。', 'warning')
            # admin_login_page 是在web.py中定义的路由别名
            return redirect(url_for('admin_login_page')) 
        return f(*args, **kwargs)
    return decorated_function