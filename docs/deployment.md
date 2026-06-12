# 部署说明

本文档介绍三种部署方案：本地运行、Streamlit Community Cloud、云服务器部署。

---

## 方案一：本地运行

**适用场景：** 个人使用、离线分析、数据安全要求高

### 安装

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

### 启动

```bash
streamlit run app.py
```

或使用项目提供的启动脚本：

```bash
run_app.bat                    # Windows
```

### 访问

浏览器打开 http://localhost:8501

### 关闭

在终端按 `Ctrl+C`。

---

## 方案二：Streamlit Community Cloud

**适用场景：** 快速公开演示、团队共享、无需管理服务器

### 前提

1. GitHub 账号，项目代码推送至 GitHub 仓库（公开或私有）
2. [Streamlit Community Cloud](https://streamlit.io/cloud) 账号（免费）

### 部署步骤

1. **推送代码到 GitHub**

   ```bash
   git add .
   git commit -m "Ready for Streamlit Cloud deployment"
   git push origin main
   ```

2. **在 Streamlit Community Cloud 中部署**

   - 访问 https://share.streamlit.io
   - 点击 "New app"
   - 选择 GitHub 仓库、分支（main）和主文件路径（`app.py`）
   - 点击 "Deploy"

3. **配置 Secrets（如需 AI 功能）**

   在 App Settings → Secrets 中添加：

   ```toml
   OPENAI_API_KEY = "sk-xxx"
   # 或其他厂商的 API Key
   ```

4. **注意事项**

   - **不要上传含敏感数据的文件到仓库**
   - `examples/` 目录中的示例数据是安全的模拟数据
   - Streamlit Cloud 有内存和 CPU 限制，大规模数据建议本地运行
   - 免费版应用在无访问时会自动休眠

---

## 方案三：云服务器部署

**适用场景：** 生产环境、团队长期使用、自定义域名

### 3.1 服务器要求

- 操作系统：Ubuntu 20.04+ / CentOS 7+ / Windows Server 2019+
- Python：3.11 或 3.12
- 内存：≥ 2 GB（推荐 4 GB）
- 磁盘：≥ 10 GB 可用空间

### 3.2 安装步骤（Ubuntu 为例）

```bash
# 1. 安装 Python
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip -y

# 2. 创建项目目录
mkdir -p /opt/gov-satisfaction-ai-report
cd /opt/gov-satisfaction-ai-report

# 3. 克隆项目（或上传代码）
git clone <your-repo-url> .

# 4. 创建虚拟环境
python3.12 -m venv .venv
source .venv/bin/activate

# 5. 安装依赖
pip install -r requirements.txt
```

### 3.3 启动服务

```bash
# 前台运行（测试用）
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# 后台运行
nohup streamlit run app.py --server.port 8501 --server.address 0.0.0.0 > streamlit.log 2>&1 &
```

### 3.4 防火墙配置

| 云服务商 | 操作 |
|----------|------|
| 阿里云 | 安全组 → 入方向 → 允许 TCP 8501 |
| 腾讯云 | 安全组 → 入站规则 → 允许 TCP 8501 |
| 华为云 | 安全组 → 入方向规则 → 允许 TCP 8501 |
| AWS | Security Group → Inbound → TCP 8501 / 0.0.0.0/0 |

### 3.5 访问

浏览器打开 `http://<服务器IP>:8501`

### 3.6 可选：Nginx 反向代理

安装 Nginx：

```bash
sudo apt install nginx -y
```

配置 `/etc/nginx/sites-available/streamlit`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/streamlit /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3.7 可选：systemd 服务

创建 `/etc/systemd/system/streamlit.service`：

```ini
[Unit]
Description=Streamlit Gov Satisfaction App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/gov-satisfaction-ai-report
Environment="PATH=/opt/gov-satisfaction-ai-report/.venv/bin"
ExecStart=/opt/gov-satisfaction-ai-report/.venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

启动并设置开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now streamlit
```

---

## 方案四：Docker 部署（未来方案）

> 本轮未包含 Dockerfile，以下为规划说明。

### 规划内容

- 基于 `python:3.12-slim` 镜像
- 使用 `requirements.txt` 安装依赖
- 通过 `EXPOSE 8501` 开放端口
- `CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]`

### 预期启动命令

```bash
docker build -t gov-satisfaction-ai-report .
docker run -p 8501:8501 gov-satisfaction-ai-report
```

容器化部署将在后续版本中正式支持。

---

## 安全提醒

1. **不要在代码仓库中提交 API Key** — 使用环境变量或 Streamlit Secrets
2. **不要上传包含真实个人隐私数据的文件** — 示例数据全部为模拟数据
3. **生产环境建议启用 HTTPS** — 使用 Nginx + Let's Encrypt 或云厂商 SSL 证书
4. **AI 功能依赖外部 API** — 确保服务器可以访问对应厂商的 API 域名
5. **Streamlit 自带防护有限** — 如需公网访问，建议加一层认证（如 Nginx basic auth）
