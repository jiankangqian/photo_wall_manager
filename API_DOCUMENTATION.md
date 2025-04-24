# 照片墙应用 API 文档 (草案)

**基准 URL:** 假设您的应用部署后可以通过 `http://<你的服务器IP>:5394` 访问。

**认证方式:** 基于 Session/Cookie。用户成功登录后，服务器会在响应中设置一个 Session Cookie，后续请求需要携带此 Cookie 以表明用户身份。

**数据格式:**
*   请求体 (Request Body): 主要使用 `application/x-www-form-urlencoded` (普通表单提交) 或 `multipart/form-data` (文件上传)，部分接口可能接受 `application/json`。
*   响应体 (Response Body): 成功时通常返回 HTML 页面（对于网页浏览）或 JSON 数据（如果设计为 API 接口）。错误时可能返回 HTML 错误页或 JSON 错误信息。

---

## 一、 认证接口 (Authentication)

### 1. 显示登录页面

*   **URL:** `/login`
*   **Method:** `GET`
*   **描述:** 返回包含登录表单的 HTML 页面。
*   **认证:** 无需
*   **请求参数:** 无
*   **成功响应:**
    *   **Code:** `200 OK`
    *   **Content-Type:** `text/html`
    *   **Body:** 登录页面的 HTML 内容。
*   **错误响应:**
    *   **Code:** `500 Internal Server Error` (服务器内部错误)

### 2. 用户登录

*   **URL:** `/login`
*   **Method:** `POST`
*   **描述:** 处理用户提交的登录表单，验证凭据。成功后设置 Session Cookie 并重定向到首页。
*   **认证:** 无需
*   **请求参数 (form-data):**
    *   `username` (string, required): 用户名
    *   `password` (string, required): 密码
    *   `captcha` (string, required): 验证码输入值
*   **成功响应:**
    *   **Code:** `302 Found`
    *   **Headers:** `Set-Cookie: session=...`, `Location: /` (重定向到首页)
*   **错误响应:**
    *   **Code:** `400 Bad Request` (缺少必要字段)
    *   **Code:** `401 Unauthorized` (用户名/密码错误 或 验证码错误)
    *   **Code:** `500 Internal Server Error`
    *   **Body:** 通常会重新渲染登录页面并显示错误信息。

### 3. 用户登出

*   **URL:** `/logout`
*   **Method:** `POST` (推荐使用 POST 防止 CSRF) 或 `GET`
*   **描述:** 清除当前用户的 Session，实现登出。
*   **认证:** **需要** (用户必须已登录)
*   **请求参数:** 无
*   **成功响应:**
    *   **Code:** `302 Found`
    *   **Headers:** `Set-Cookie: session=...; Expires=...` (清除 Cookie), `Location: /login` (重定向到登录页)
*   **错误响应:**
    *   **Code:** `401 Unauthorized` (用户未登录)
    *   **Code:** `500 Internal Server Error`

### 4. 获取验证码图片

*   **URL:** `/captcha.png` (或其他您定义的路径)
*   **Method:** `GET`
*   **描述:** 生成一个新的验证码图片并返回。同时在服务器端 Session 中存储对应的验证码文本以供后续验证。
*   **认证:** 无需
*   **请求参数:** 无
*   **成功响应:**
    *   **Code:** `200 OK`
    *   **Content-Type:** `image/png`
    *   **Headers:** `Set-Cookie: session=...` (更新包含验证码信息的 Session)
    *   **Body:** PNG 格式的验证码图片数据。
*   **错误响应:**
    *   **Code:** `500 Internal Server Error`

---

## 二、 照片接口 (Photos)

### 1. 显示照片墙 (首页)

*   **URL:** `/`
*   **Method:** `GET`
*   **描述:** 显示主照片墙页面，展示照片列表。
*   **认证:** 可能无需（取决于是否允许匿名查看）
*   **请求参数:** 可能包含分页参数，如 `?page=1`
*   **成功响应:**
    *   **Code:** `200 OK`
    *   **Content-Type:** `text/html`
    *   **Body:** 照片墙主页面的 HTML 内容，包含图片列表。
*   **错误响应:**
    *   **Code:** `500 Internal Server Error`

### 2. 显示上传照片页面

*   **URL:** `/upload` (或其他您定义的路径)
*   **Method:** `GET`
*   **描述:** 返回包含文件上传表单的 HTML 页面。
*   **认证:** **需要**
*   **请求参数:** 无
*   **成功响应:**
    *   **Code:** `200 OK`
    *   **Content-Type:** `text/html`
    *   **Body:** 上传页面的 HTML 内容。
*   **错误响应:**
    *   **Code:** `401 Unauthorized`
    *   **Code:** `500 Internal Server Error`

### 3. 上传照片

*   **URL:** `/upload` (或其他您定义的路径)
*   **Method:** `POST`
*   **描述:** 处理用户上传的照片文件，保存文件并可能在数据库中记录相关信息。
*   **认证:** **需要**
*   **请求参数 (multipart/form-data):**
    *   `photo` (file, required): 用户选择的照片文件。
    *   `caption` (string, optional): 照片描述/标题。
*   **成功响应:**
    *   **Code:** `302 Found`
    *   **Headers:** `Location: /` (重定向到首页或其他成功页面)
*   **错误响应:**
    *   **Code:** `400 Bad Request` (未上传文件、文件类型不支持、文件过大等)
    *   **Code:** `401 Unauthorized`
    *   **Code:** `500 Internal Server Error`

### 4. 获取照片文件

*   **URL:** `/uploads/<filename>` (或其他您配置的静态文件服务路径)
*   **Method:** `GET`
*   **描述:** 根据文件名获取并返回实际的图片文件。此路径通常由 Flask 的 `send_from_directory` 或 Nginx 等 Web 服务器直接处理。
*   **认证:** 可能无需（取决于照片是否公开）
*   **请求参数:**
    *   `filename` (string, required): URL 路径中的文件名。
*   **成功响应:**
    *   **Code:** `200 OK`
    *   **Content-Type:** 图片的 MIME 类型 (e.g., `image/jpeg`, `image/png`)
    *   **Body:** 图片的二进制数据。
*   **错误响应:**
    *   **Code:** `404 Not Found` (文件不存在)
    *   **Code:** `401 Unauthorized` (如果照片需要认证才能查看)
    *   **Code:** `500 Internal Server Error`

---

## 三、 用户接口 (Users) (可选/待确认)

*这部分接口的存在性需要您确认，`flask create-user` 命令是后台管理操作，不一定是公开的注册接口。*

### 1. 显示注册页面 (如果存在)

*   **URL:** `/register` (假设路径)
*   **Method:** `GET`
*   **描述:** 返回包含用户注册表单的 HTML 页面。
*   **认证:** 无需
*   **成功响应:**
    *   **Code:** `200 OK`, **Content-Type:** `text/html`

### 2. 用户注册 (如果存在)

*   **URL:** `/register` (假设路径)
*   **Method:** `POST`
*   **描述:** 处理用户提交的注册信息。
*   **认证:** 无需
*   **请求参数 (form-data):**
    *   `username` (string, required)
    *   `password` (string, required)
    *   `password_confirm` (string, required)
    *   `captcha` (string, required)
*   **成功响应:**
    *   **Code:** `302 Found`, **Headers:** `Location: /login` (重定向到登录页)
*   **错误响应:**
    *   **Code:** `400 Bad Request` (字段缺失、密码不匹配、用户名已存在、验证码错误等)
    *   **Code:** `500 Internal Server Error`

---

**请务必根据您的实际代码调整和确认以上接口信息。** 