# 使用官方 Python 运行时作为父镜像
# 选择一个适合你项目的 Python 版本，slim 版本更小
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 将依赖文件复制到工作目录
# 先复制 requirements.txt 并安装依赖，可以利用 Docker 的构建缓存
COPY requirements.txt .

# 安装依赖
# --no-cache-dir 减少镜像大小
RUN pip install --no-cache-dir -r requirements.txt

# 将项目代码复制到工作目录
COPY . .

# 应用程序监听的端口 (需要和 Gunicorn 配置的端口一致)
EXPOSE 5394

# 定义容器启动时执行的命令
# 使用 Gunicorn 运行应用
# -b 0.0.0.0:5394 监听所有接口的 5394 端口
# -w 4 使用 4 个 worker 进程 (根据你的服务器 CPU 核心数调整)
# app:app 指向 app.py 文件中的 app Flask 实例
CMD ["gunicorn", "--bind", "0.0.0.0:5394", "--workers", "2", "app:app"]