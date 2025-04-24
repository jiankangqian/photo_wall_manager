# 照片墙 Web 应用

这是一个基于 Flask 开发的简单照片墙 Web 应用程序。用户可以登录、上传照片，并在主页上浏览所有展示的照片。登录页面包含动态的烟花和星空背景效果。

## 主要功能

*   用户认证：
    *   登录 (用户名、密码、验证码)
    *   登出
    *   后台命令行创建用户
*   照片管理：
    *   上传照片 (需要登录)
    *   在首页以照片墙形式展示所有上传的照片
*   界面效果：
    *   登录页面包含 CSS 动态烟花动画
    *   登录页面包含 JavaScript 生成的动态星空背景

## 技术栈

*   **后端:** Python 3, Flask
*   **数据库:** MySQL (通过 PyMySQL 连接)
*   **ORM:** Flask-SQLAlchemy
*   **用户会话管理:** Flask-Login
*   **WSGI 服务器 (生产):** Gunicorn (推荐用于 Linux), Waitress (适用于 Windows)
*   **配置管理:** python-dotenv (`.env` 文件)
*   **图像处理:** Pillow (用于验证码)
*   **验证码:** captcha
*   **前端:** HTML, CSS, JavaScript
*   **部署:** Docker (提供了 Dockerfile)

## 本地设置与运行

**1. 克隆仓库:**

```bash
git clone <你的仓库地址>
cd <项目目录>
```

**2. 创建并激活虚拟环境:**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

**3. 安装依赖:**

```bash
pip install -r requirements.txt
```

**4. 配置环境变量:**

*   复制 `.env.example` (如果提供了) 或手动创建 `.env` 文件。
*   在 `.env` 文件中至少设置以下内容，用于开发环境：
    ```dotenv
    FLASK_ENV=development
    SECRET_KEY='a_random_secret_key_for_development' # 开发密钥，不需要非常强壮
    # 替换为你的本地或开发数据库连接信息
    DATABASE_URL='mysql+pymysql://dev_user:dev_password@localhost/photo_wall_dev'
    # 配置上传文件夹路径 (如果需要)
    # UPLOAD_FOLDER='uploads'
    ```
*   **重要:** 确保 `DATABASE_URL` 指向的数据库已经创建。

**5. 初始化数据库 (如果需要):**

*   您可能需要一个命令来创建数据库表结构。如果使用了 Flask-Migrate，通常是：
    ```bash
    flask db init  # 仅第一次
    flask db migrate -m "Initial migration."
    flask db upgrade
    ```
*   如果您的项目没有迁移脚本，请检查 `app.py` 或相关代码中是否有创建表的逻辑 (例如 `db.create_all()`)，并确保在首次运行时执行。

**6. 创建第一个用户:**

*   运行 Flask CLI 命令添加用户：
    ```bash
    flask create-user
    ```
*   按照提示输入用户名和密码。

**7. 运行开发服务器:**

```bash
flask run --host=0.0.0.0 --port=5394
```

*   应用将在 `http://localhost:5394` 或 `http://<你的本地IP>:5394` 上可用。

## 配置

应用通过根目录下的 `.env` 文件加载配置。

*   `.env`: 用于本地开发环境。**不要提交到 Git 仓库。**
*   `.env.production`: 用于生产环境。包含真实的数据库凭据和强 `SECRET_KEY`。**绝对不要提交到 Git 仓库！** 应在部署时手动创建或通过安全的方式注入。

关键环境变量：

*   `FLASK_ENV`: `development` 或 `production`
*   `SECRET_KEY`: 用于 Session 加密的密钥，生产环境必须是强随机值。
*   `DATABASE_URL`: 数据库连接字符串。
*   `UPLOAD_FOLDER`: (如果配置了) 照片上传的目标文件夹。

## 部署 (Docker)

项目包含 `Dockerfile` 和 `.dockerignore` 文件，用于构建 Docker 镜像。

1.  **在服务器上准备 `.env.production` 文件**，包含生产环境的真实配置。
2.  **构建镜像:**
    ```bash
    sudo docker build -t photo-wall-app .
    ```
3.  **运行容器:**
    ```bash
    sudo docker run -d -p 5394:5394 --name photo-wall-container --env-file .env.production photo-wall-app
    ```
    *   确保服务器的防火墙/安全组已开放 5394 端口。
    *   建议在生产中使用 Nginx 等反向代理处理 HTTPS 和静态文件。

## API 文档

详细的 API 接口说明请参见 `API_DOCUMENTATION.md` 文件。

## 项目结构 (示例)

```
.
├── .env                # 开发环境变量 (不提交)
├── .env.production     # 生产环境变量 (不提交)
├── .gitignore          # Git 忽略配置
├── .dockerignore       # Docker 忽略配置
├── Dockerfile          # Docker 构建文件
├── README.md           # 项目说明 (本文档)
├── API_DOCUMENTATION.md # API 接口文档
├── requirements.txt    # Python 依赖
├── app.py              # Flask 应用主文件
├── models.py           # (可能) SQLAlchemy 模型定义
├── commands.py         # (可能) Flask CLI 命令定义 (如 create-user)
├── static/             # 静态文件 (CSS, JS, Images)
│   ├── css/
│   └── js/
├── templates/          # HTML 模板
│   ├── index.html
│   ├── login.html
│   └── upload.html
└── uploads/            # (运行时创建) 上传文件存储目录 (需要配置)
``` 