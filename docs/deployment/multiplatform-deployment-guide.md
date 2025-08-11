# 多平台模型部署指南

本指南详细介绍如何在不同环境中部署和配置 RAG 系统的多平台模型支持功能。

## 部署架构概述

### 系统组件

RAG 系统的多平台模型支持包含以下核心组件：

```
┌─────────────────────────────────────────────────────────────┐
│                    RAG System                              │
├─────────────────────────────────────────────────────────────┤
│  API Layer                                                  │
│  ├── FastAPI Server                                         │
│  ├── Authentication & Authorization                         │
│  └── Request/Response Handling                              │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                              │
│  ├── QA Service                                             │
│  ├── Embedding Service                                      │
│  ├── Document Service                                       │
│  └── Health Check Service                                   │
├─────────────────────────────────────────────────────────────┤
│  Model Layer                                                │
│  ├── LLM Factory                                            │
│  ├── Embedding Factory                                      │
│  ├── Provider Implementations                               │
│  └── Model Health Checker                                   │
├─────────────────────────────────────────────────────────────┤
│  Storage Layer                                              │
│  ├── Vector Store (ChromaDB)                                │
│  ├── Document Database (SQLite/PostgreSQL)                  │
│  └── Configuration Storage                                  │
└─────────────────────────────────────────────────────────────┘
```

### 支持的部署模式

1. **单机部署** - 适合开发和小规模使用
2. **容器化部署** - 使用 Docker 进行标准化部署
3. **集群部署** - 高可用和高性能场景
4. **云原生部署** - 使用 Kubernetes 进行弹性扩展

## 环境准备

### 系统要求

**最低配置：**
- CPU: 2 核心
- 内存: 4GB RAM
- 存储: 20GB 可用空间
- 网络: 稳定的互联网连接

**推荐配置：**
- CPU: 4+ 核心
- 内存: 8GB+ RAM
- 存储: 50GB+ SSD
- 网络: 高速互联网连接

### 软件依赖

```bash
# Python 环境
Python 3.8+
pip 21.0+

# 系统依赖
curl
git
sqlite3 (或 PostgreSQL)

# 可选依赖
Docker 20.10+
Docker Compose 2.0+
Kubernetes 1.20+
```

## 单机部署

### 1. 环境设置

```bash
# 创建项目目录
mkdir rag-system-deployment
cd rag-system-deployment

# 克隆项目
git clone <repository-url> .

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```### 2. 配置文
件设置

```bash
# 复制配置模板
cp config/production.yaml.template config/production.yaml

# 编辑配置文件
nano config/production.yaml
```

**生产环境配置示例：**
```yaml
llm:
  provider: "siliconflow"
  model: "Qwen/Qwen2-72B-Instruct"
  api_key: "${SILICONFLOW_API_KEY}"
  base_url: "https://api.siliconflow.cn/v1"
  temperature: 0.3
  max_tokens: 2000
  timeout: 30
  retry_attempts: 3

embeddings:
  provider: "siliconflow"
  model: "BAAI/bge-large-zh-v1.5"
  api_key: "${SILICONFLOW_API_KEY}"
  base_url: "https://api.siliconflow.cn/v1"
  dimensions: 1024
  batch_size: 150
  timeout: 30

global:
  enable_fallback: true
  fallback_provider: "openai"
  enable_cache: true
  cache_ttl: 3600
  health_check_enabled: true
  monitoring_enabled: true
```

### 3. 环境变量配置

```bash
# 创建环境变量文件
cat > .env << EOF
# 主要 API 密钥
SILICONFLOW_API_KEY=your-siliconflow-api-key
OPENAI_API_KEY=your-openai-api-key

# 数据库配置
DATABASE_URL=sqlite:///./rag_system.db

# 服务配置
RAG_ENV=production
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8000

# 安全配置
SECRET_KEY=your-secret-key-here
API_KEY_HASH=your-api-key-hash

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090
EOF

# 设置环境变量权限
chmod 600 .env
```

### 4. 数据库初始化

```bash
# 初始化数据库
python -m rag_system.database.init_db

# 验证数据库连接
python -c "from rag_system.database.connection import get_db; print('数据库连接成功')"
```

### 5. 启动服务

```bash
# 启动 RAG 系统
python -m rag_system.api.main

# 或使用 uvicorn
uvicorn rag_system.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 6. 验证部署

```bash
# 健康检查
curl http://localhost:8000/api/health

# 测试问答功能
curl -X POST http://localhost:8000/api/qa/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "测试问题"}'
```

## 容器化部署

### 1. Dockerfile

```dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN useradd -m -u 1000 raguser && chown -R raguser:raguser /app
USER raguser

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# 启动命令
CMD ["uvicorn", "rag_system.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Docker Compose

```yaml
version: '3.8'

services:
  rag-system:
    build: .
    ports:
      - "8000:8000"
    environment:
      - RAG_ENV=production
      - DATABASE_URL=postgresql://raguser:password@postgres:5432/ragdb
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=ragdb
      - POSTGRES_USER=raguser
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - rag-system
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 3. 构建和启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f rag-system

# 停止服务
docker-compose down
```

## Kubernetes 部署

### 1. 命名空间

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: rag-system
```

### 2. 配置映射

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rag-config
  namespace: rag-system
data:
  config.yaml: |
    llm:
      provider: "siliconflow"
      model: "Qwen/Qwen2-72B-Instruct"
      temperature: 0.3
      max_tokens: 2000
    embeddings:
      provider: "siliconflow"
      model: "BAAI/bge-large-zh-v1.5"
      dimensions: 1024
    global:
      enable_fallback: true
      health_check_enabled: true
```

### 3. 密钥管理

```yaml
# secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: rag-secrets
  namespace: rag-system
type: Opaque
data:
  siliconflow-api-key: <base64-encoded-key>
  openai-api-key: <base64-encoded-key>
  database-url: <base64-encoded-url>
```

### 4. 部署配置

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: rag-system
  namespace: rag-system
spec:
  replicas: 3
  selector:
    matchLabels:
      app: rag-system
  template:
    metadata:
      labels:
        app: rag-system
    spec:
      containers:
      - name: rag-system
        image: rag-system:latest
        ports:
        - containerPort: 8000
        env:
        - name: SILICONFLOW_API_KEY
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: siliconflow-api-key
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: rag-secrets
              key: database-url
        volumeMounts:
        - name: config
          mountPath: /app/config
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
      volumes:
      - name: config
        configMap:
          name: rag-config
```

### 5. 服务配置

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: rag-system-service
  namespace: rag-system
spec:
  selector:
    app: rag-system
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

### 6. Ingress 配置

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: rag-system-ingress
  namespace: rag-system
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - rag.yourdomain.com
    secretName: rag-tls
  rules:
  - host: rag.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: rag-system-service
            port:
              number: 80
```

### 7. 部署到 Kubernetes

```bash
# 应用配置
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# 检查部署状态
kubectl get pods -n rag-system
kubectl get services -n rag-system
kubectl logs -f deployment/rag-system -n rag-system
```

## 负载均衡和高可用

### 1. Nginx 配置

```nginx
# nginx.conf
upstream rag_backend {
    least_conn;
    server rag-system-1:8000 max_fails=3 fail_timeout=30s;
    server rag-system-2:8000 max_fails=3 fail_timeout=30s;
    server rag-system-3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name rag.yourdomain.com;
    
    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name rag.yourdomain.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # 限流
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    location / {
        limit_req zone=api burst=20 nodelay;
        
        proxy_pass http://rag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # 健康检查
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
    }
    
    # 健康检查端点
    location /health {
        access_log off;
        proxy_pass http://rag_backend/api/health;
    }
}
```

### 2. HAProxy 配置

```
# haproxy.cfg
global
    daemon
    maxconn 4096
    
defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms
    
frontend rag_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/rag.pem
    redirect scheme https if !{ ssl_fc }
    default_backend rag_backend
    
backend rag_backend
    balance roundrobin
    option httpchk GET /api/health
    server rag1 rag-system-1:8000 check
    server rag2 rag-system-2:8000 check
    server rag3 rag-system-3:8000 check
```

## 监控和日志

### 1. Prometheus 配置

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'rag-system'
    static_configs:
      - targets: ['rag-system:9090']
    metrics_path: /metrics
    scrape_interval: 30s
```

### 2. Grafana 仪表板

```json
{
  "dashboard": {
    "title": "RAG System Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
          }
        ]
      }
    ]
  }
}
```

### 3. 日志配置

```yaml
# logging.yaml
version: 1
formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  json:
    format: '{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: default
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /app/logs/rag-system.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  rag_system:
    level: INFO
    handlers: [console, file]
    propagate: no

root:
  level: WARNING
  handlers: [console]
```

## 安全配置

### 1. API 认证

```python
# security.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

### 2. 防火墙规则

```bash
# UFW 配置
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 3. SSL/TLS 配置

```bash
# 使用 Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d rag.yourdomain.com
```

这个部署指南涵盖了从单机部署到 Kubernetes 集群的各种部署场景，为不同规模的应用提供了完整的部署方案。