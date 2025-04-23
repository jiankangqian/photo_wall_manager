import os
from dotenv import load_dotenv # 导入 load_dotenv

# --- 加载环境变量 ---
# 根据 FLASK_ENV 决定加载哪个 .env 文件
# 如果 FLASK_ENV 未设置或为 'development'，加载 .env
# 如果 FLASK_ENV 设置为 'production'，加载 .env.production
env_file = '.env.production' if os.environ.get('FLASK_ENV') == 'production' else '.env'
load_dotenv(dotenv_path=env_file) # 加载指定的环境变量文件

import random
from io import BytesIO
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from captcha.image import ImageCaptcha
from PIL import Image # Pillow is used by captcha
from sqlalchemy import desc, asc # 导入排序

# --- 配置 ---
app = Flask(__name__)
# 从环境变量读取配置
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_fallback_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+mysqlconnector://root:20190901@localhost/photo_wall')
# 其他配置保持不变
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 128 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

# 确保上传目录存在
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' # 未登录用户访问受保护页面时重定向到登录页
login_manager.login_message = u"请先登录以访问此页面。"
login_manager.login_message_category = "info"

MAX_PHOTOS_PER_GROUP = 21

# --- 数据库模型 ---
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Photo(db.Model):
    __tablename__ = 'photos'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255))
    group_id = db.Column(db.Integer, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.TIMESTAMP, server_default=db.func.current_timestamp())

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- 验证码 ---
image_captcha = ImageCaptcha(width=280, height=90)

def generate_captcha_text(length=4):
    return ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=length)) # 排除易混淆字符

@app.route('/captcha')
def get_captcha():
    captcha_text = generate_captcha_text()
    session['captcha'] = captcha_text # 将验证码文本存入 session
    session.modified = True # 确保 session 被保存
    image_data = image_captcha.generate(captcha_text)
    return send_file(BytesIO(image_data.read()), mimetype='image/png')

# --- 视图函数 (基础) ---
@app.route('/')
def index():
    # 指向你的照片墙页面
    return render_template('photo_wall.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_photos'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        captcha_input = request.form.get('captcha', '').upper()
        captcha_session = session.get('captcha', '').upper()

        if not captcha_session or captcha_input != captcha_session:
            flash('验证码错误', 'danger')
            session.pop('captcha', None) # 清除旧验证码
            return render_template('login.html')

        session.pop('captcha', None) # 验证成功后清除

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True) # remember=True 会设置长期 cookie
            flash('登录成功!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_photos'))
        else:
            flash('用户名或密码错误', 'danger')

    # GET 请求 或 登录失败
    session.pop('captcha', None)
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出登录。', 'info')
    return redirect(url_for('login'))

# --- 辅助函数 ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# --- 管理后台路由 ---
@app.route('/admin/photos', methods=['GET', 'POST'])
@login_required
def admin_photos():
    if request.method == 'POST':
        uploaded_files = request.files.getlist('photo')
        group_id = request.form.get('group_id', type=int)
        processed_count = 0
        skipped_files_count = 0
        error_files = []
        group_limit = MAX_PHOTOS_PER_GROUP

        if not uploaded_files or all(f.filename == '' for f in uploaded_files):
            flash('没有选择任何文件', 'warning')
            return redirect(request.url)

        if len(uploaded_files) > group_limit:
            flash(f'您选择的文件超过了单次上传限制 ({group_limit} 张)！', 'danger')
            return redirect(request.url)

        if group_id not in [1, 2, 3]:
            flash('无效的照片组ID', 'danger')
            return redirect(request.url)

        try:
            current_photo_count = db.session.query(Photo).filter_by(group_id=group_id).count()
            available_slots = group_limit - current_photo_count

            if available_slots <= 0:
                flash(f'照片组 {group_id} 已达到 {group_limit} 张照片的上限，无法再添加。', 'warning')
                return redirect(url_for('admin_photos'))

            files_to_process = uploaded_files
            if len(uploaded_files) > available_slots:
                files_to_process = uploaded_files[:available_slots]
                skipped_files_count = len(uploaded_files) - available_slots
                flash(f'照片组 {group_id} 空间不足，只能添加 {available_slots} 张照片。{skipped_files_count} 张照片未被上传。', 'warning')

        except Exception as e:
             flash(f'检查照片组数量时出错: {e}', 'danger')
             return redirect(url_for('admin_photos'))

        subfolder = f'group{group_id}'
        group_folder_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(group_folder_path, exist_ok=True)
                
        for file in files_to_process:
            if file and file.filename != '' and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                filename = f"{os.urandom(8).hex()}_{original_filename}"
                filepath = os.path.join(group_folder_path, filename)
                try:
                    file.save(filepath)
                    new_photo = Photo(
                        filename=filename,
                        original_filename=original_filename,
                        group_id=group_id
                    )
                    db.session.add(new_photo)
                    processed_count += 1
                except Exception as e:
                    db.session.rollback()
                    flash(f'保存文件 {original_filename} 或添加到数据库失败: {e}', 'danger')
                    error_files.append(original_filename)
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except OSError as remove_error:
                             flash(f'无法删除失败上传的文件 {filename}: {remove_error}', 'warning')

            elif file and file.filename != '':
                flash(f'文件类型不允许: {secure_filename(file.filename)}', 'warning')
                error_files.append(secure_filename(file.filename))
        
        try:
            if processed_count > 0:
                 db.session.commit()
                 flash(f'{processed_count} 张照片成功添加到组 {group_id}!', 'success')
            summary_message = []
            if skipped_files_count > 0:
                 summary_message.append(f"{skipped_files_count} 张因超出组容量限制未上传")
            if error_files:
                summary_message.append(f"{len(error_files)} 张因类型错误或保存失败未处理")

            if summary_message:
                flash("上传总结：" + "； ".join(summary_message), 'info')
        except Exception as e:
             db.session.rollback()
             flash(f'提交数据库时发生错误: {e}', 'danger')

        return redirect(url_for('admin_photos'))

    photos_group1 = Photo.query.filter_by(group_id=1).order_by(Photo.sort_order.asc()).all()
    photos_group2 = Photo.query.filter_by(group_id=2).order_by(Photo.sort_order.asc()).all()
    photos_group3 = Photo.query.filter_by(group_id=3).order_by(Photo.sort_order.asc()).all()

    counts = {
        1: len(photos_group1),
        2: len(photos_group2),
        3: len(photos_group3)
    }

    return render_template('admin_photos.html',
                           photos_group1=photos_group1,
                           photos_group2=photos_group2,
                           photos_group3=photos_group3,
                           counts=counts, 
                           limit=MAX_PHOTOS_PER_GROUP)

@app.route('/admin/photos/update_order', methods=['POST'])
@login_required
def update_photo_order():
    try:
        photo_orders = request.get_json()
        if not isinstance(photo_orders, list):
            return jsonify({"success": False, "message": "无效的数据格式"}), 400

        updated = 0
        for item in photo_orders:
            photo_id = item.get('id')
            sort_order = item.get('order')
            if photo_id is not None and sort_order is not None:
                photo = Photo.query.get(photo_id)
                if photo:
                    photo.sort_order = int(sort_order)
                    updated += 1
                else:
                    print(f"照片ID不存在: {photo_id}")
            else:
                print(f"跳过无效的项目: {item}") 

        if updated > 0:
            db.session.commit()
            return jsonify({"success": True, "message": f"已更新{updated}张照片的顺序", "updated_count": updated})
        else:
            return jsonify({"success": False, "message": "没有照片被更新"}), 404
            
    except Exception as e:
        db.session.rollback()
        print(f"更新排序时出错: {e}")
        return jsonify({"success": False, "message": f"更新失败: {e}"}), 500

@app.route('/admin/photos/delete/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    subfolder = f'group{photo.group_id}'
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, photo.filename)
    try:
        db.session.delete(photo)
        db.session.flush()

        if os.path.exists(filepath):
            os.remove(filepath)
        else:
            flash(f'数据库记录已删除，但未找到对应的文件: {filepath}', 'warning')

        db.session.commit()
        flash('照片已成功删除。', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'删除照片失败: {e}', 'danger')
    return redirect(url_for('admin_photos'))

@app.route('/admin/photos/delete_batch', methods=['POST'])
@login_required
def delete_batch():
    if not request.is_json:
        return jsonify(success=False, message="请求格式错误，需要JSON格式"), 400
    
    data = request.json
    photo_ids = data.get('ids', [])
    
    if not photo_ids:
        return jsonify(success=False, message="未提供要删除的照片ID"), 400
    
    deleted_count = 0
    errors = []
    
    for photo_id in photo_ids:
        photo = Photo.query.get(photo_id)
        if not photo:
            errors.append(f"照片ID {photo_id} 不存在")
            continue
        
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'group{photo.group_id}', photo.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            db.session.delete(photo)
            deleted_count += 1
        except Exception as e:
            errors.append(f"删除照片ID {photo_id} 时出错: {str(e)}")
            db.session.rollback() # 仅回滚当前照片的删除
    
    if deleted_count > 0:
        try:
            db.session.commit() # 提交所有成功的删除
        except Exception as commit_error:
            flash(f"提交批量删除时发生错误: {commit_error}", "danger")
            return jsonify(success=False, message="提交数据库时出错", deleted_count=0, errors=errors + [f"Commit error: {commit_error}"])
    
    return jsonify(
        success=True,
        deleted_count=deleted_count,
        errors=errors
    )

@app.route('/admin/photo_upload', methods=['GET', 'POST'])
@login_required
def photo_upload():
    if request.method == 'POST':
        uploaded_files = request.files.getlist('photo')
        group_id = request.form.get('group_id', type=int)
        processed_count = 0
        skipped_files_count = 0
        error_files = []
        group_limit = MAX_PHOTOS_PER_GROUP

        if not uploaded_files or all(f.filename == '' for f in uploaded_files):
            flash('没有选择任何文件', 'warning')
            return redirect(request.url)

        if len(uploaded_files) > group_limit:
            flash(f'您选择的文件超过了单次上传限制 ({group_limit} 张)！', 'danger')
            return redirect(request.url)

        if group_id not in [1, 2, 3]:
            flash('无效的照片组ID', 'danger')
            return redirect(request.url)

        try:
            current_photo_count = db.session.query(Photo).filter_by(group_id=group_id).count()
            available_slots = group_limit - current_photo_count

            if available_slots <= 0:
                flash(f'照片组 {group_id} 已达到 {group_limit} 张照片的上限，无法再添加。', 'warning')
                return redirect(url_for('admin_photos'))

            files_to_process = uploaded_files
            if len(uploaded_files) > available_slots:
                files_to_process = uploaded_files[:available_slots]
                skipped_files_count = len(uploaded_files) - available_slots
                flash(f'照片组 {group_id} 空间不足，只能添加 {available_slots} 张照片。{skipped_files_count} 张照片未被上传。', 'warning')

        except Exception as e:
             flash(f'检查照片组数量时出错: {e}', 'danger')
             return redirect(url_for('admin_photos'))

        subfolder = f'group{group_id}'
        group_folder_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(group_folder_path, exist_ok=True)
                
        for file in files_to_process:
            if file and file.filename != '' and allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                filename = f"{os.urandom(8).hex()}_{original_filename}"
                filepath = os.path.join(group_folder_path, filename)
                try:
                    file.save(filepath)
                    new_photo = Photo(
                        filename=filename,
                        original_filename=original_filename,
                        group_id=group_id
                    )
                    db.session.add(new_photo)
                    processed_count += 1
                except Exception as e:
                    db.session.rollback()
                    flash(f'保存文件 {original_filename} 或添加到数据库失败: {e}', 'danger')
                    error_files.append(original_filename)
                    if os.path.exists(filepath):
                        os.remove(filepath)
            else:
                if file and file.filename != '':
                    error_files.append(file.filename)

        if processed_count > 0:
            try:
                db.session.commit()
                flash(f'成功上传了 {processed_count} 张照片到组 {group_id}。', 'success')
            except Exception as commit_error:
                flash(f'提交数据库时发生错误: {commit_error}', 'danger')
                db.session.rollback()

        if error_files:
            flash(f'以下文件未能正确处理或类型不允许: {", ".join(error_files)}', 'warning')

        if skipped_files_count > 0:
            flash(f'由于组 {group_id} 空间限制，{skipped_files_count} 张照片未被上传。', 'warning')

        return redirect(url_for('admin_photos'))
    
    return render_template('photo_upload.html')

@app.route('/api/photos')
def api_photos():
    try:
        photos_group1 = Photo.query.filter_by(group_id=1).order_by(Photo.sort_order.asc()).all()
        photos_group2 = Photo.query.filter_by(group_id=2).order_by(Photo.sort_order.asc()).all()
        photos_group3 = Photo.query.filter_by(group_id=3).order_by(Photo.sort_order.asc()).all()

        def photos_to_dict(photos):
            return [url_for('static', filename=f'uploads/group{p.group_id}/{p.filename}') for p in photos]

        result = {
            'group1': photos_to_dict(photos_group1),
            'group2': photos_to_dict(photos_group2),
            'group3': photos_to_dict(photos_group3)
        }
        return jsonify(result)
    except Exception as e:
        print(f"Error fetching API photos: {e}")
        return jsonify({"error": "无法获取照片数据"}), 500

# --- 初始化命令 ---
@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("Database tables created.")

@app.cli.command("create-user")
def create_user():
    username = input("Enter username: ")
    password = input("Enter password: ")
    confirm_password = input("Confirm password: ")

    if password != confirm_password:
        print("Passwords do not match.")
        return

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        print(f"User '{username}' already exists.")
        return

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    print(f"User '{username}' created successfully.")


if __name__ == '__main__':
    # 获取端口，默认为 5394
    port = int(os.environ.get('PORT', 5394))
    # 决定是否开启 Debug 模式
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    app.run(debug=debug_mode, host='0.0.0.0', port=port) 