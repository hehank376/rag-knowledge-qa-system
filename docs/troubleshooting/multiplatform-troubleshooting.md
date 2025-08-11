# 多平台模型故障排除指南

本指南帮助您诊断和解决使用多平台模型支持功能时遇到的常见问题。

## 快速诊断工具

### 系统健康检查

首先运行系统健康检查来快速识别问题：

```python
from rag_system.utils.health_checker import ModelHealthChecker
import asyncio

async def quick_diagnosis():
    checker = ModelHealthChecker()
    
    # 检查整体系统健康状态
    health_status = await checker.check_system_health()
    print(f"系统状态: {health_status['overall_status']}")
    
    # 检查各个组件
    for component, status in health_status['components'].items():
        print(f"{component}: {status['status']}")
        if status['status'] != 'healthy':
            print(f"  问题: {status.get('error', '未知错误')}")

# 运行诊断
asyncio.run(quick_diagnosis())
```

### 配置验证工具

```python
from rag_system.utils.compatibility import check_config_compatibility
from rag_system.config.loader import ConfigLoader

def validate_config():
    loader = ConfigLoader()
    config = loader.load_config()
    
    issues = check_config_compatibility(config)
    if issues:
        print("配置问题：")
        for issue in issues:
            print(f"- {issue}")
    else:
        print("配置验证通过")

validate_config()
```

## 常见问题分类

### 1. 连接和认证问题

#### 问题：API 密钥无效
**错误信息：**
```
AuthenticationError: Invalid API key provided
```

**解决步骤：**
1. 检查 API 密钥格式是否正确
2. 确认密钥没有过期
3. 验证密钥权限是否足够
4. 检查环境变量是否正确设置

```bash
# 检查环境变量
echo $OPENAI_API_KEY
echo $SILICONFLOW_API_KEY

# 测试 API 密钥
curl -H "Authorization: Bearer $OPENAI_API_KEY" \
     https://api.openai.com/v1/models
```

#### 问题：连接超时
**错误信息：**
```
TimeoutError: Request timed out after 30 seconds
```

**解决步骤：**
1. 检查网络连接
2. 增加超时设置
3. 检查防火墙配置
4. 验证 API 端点 URL

```yaml
# 增加超时设置
llm:
  provider: "openai"
  model: "gpt-4"
  timeout: 120  # 增加到120秒
  connect_timeout: 10  # 连接超时
  request_timeout: 100  # 请求超时
```

#### 问题：SSL 证书验证失败
**错误信息：**
```
SSLError: certificate verify failed
```

**解决步骤：**
1. 更新系统证书
2. 检查系统时间是否正确
3. 临时禁用 SSL 验证（仅开发环境）

```python
# 临时解决方案（仅开发环境）
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
```

### 2. 模型和提供商问题

#### 问题：模型不存在或不支持
**错误信息：**
```
ModelNotFoundError: Model 'gpt-5' not found
```

**解决步骤：**
1. 检查模型名称拼写
2. 确认提供商支持该模型
3. 查看提供商的模型列表
4. 检查模型是否需要特殊权限

```python
# 获取支持的模型列表
from rag_system.llm.factory import LLMFactory

factory = LLMFactory()
providers = factory.get_supported_providers()
for provider in providers:
    print(f"{provider}: {factory.get_supported_models(provider)}")
```

#### 问题：提供商服务不可用
**错误信息：**
```
ServiceUnavailableError: Provider 'siliconflow' is currently unavailable
```

**解决步骤：**
1. 检查提供商状态页面
2. 尝试切换到备用提供商
3. 检查 API 配额是否用完
4. 联系提供商技术支持

```yaml
# 配置备用提供商
global:
  enable_fallback: true
  fallback_provider: "openai"
  fallback_model: "gpt-3.5-turbo"
```

### 3. 配置问题

#### 问题：配置文件格式错误
**错误信息：**
```
ConfigurationError: Invalid YAML format in config file
```

**解决步骤：**
1. 检查 YAML 语法
2. 验证缩进是否正确
3. 检查特殊字符是否需要引号
4. 使用 YAML 验证工具

```bash
# 验证 YAML 格式
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

#### 问题：必需参数缺失
**错误信息：**
```
ConfigurationError: Missing required parameter 'api_key' for provider 'openai'
```

**解决步骤：**
1. 检查配置文件完整性
2. 确认所有必需参数都已设置
3. 检查环境变量是否正确

```python
# 检查配置完整性
from rag_system.config.validator import ConfigValidator

validator = ConfigValidator()
issues = validator.validate_config('config.yaml')
for issue in issues:
    print(f"配置问题: {issue}")
```

### 4. 性能问题

#### 问题：响应速度慢
**症状：**
- API 调用耗时过长
- 系统响应缓慢

**解决步骤：**
1. 检查网络延迟
2. 优化批处理大小
3. 增加并发请求数
4. 选择更快的模型

```yaml
# 性能优化配置
embeddings:
  batch_size: 200  # 增加批处理大小
  max_concurrent_requests: 10  # 增加并发数
  timeout: 30  # 减少超时时间

llm:
  model: "gpt-3.5-turbo"  # 使用更快的模型
  max_tokens: 1000  # 减少生成长度
```

#### 问题：内存使用过高
**症状：**
- 系统内存不足
- 进程被杀死

**解决步骤：**
1. 减少批处理大小
2. 限制并发请求数
3. 清理缓存
4. 增加系统内存

```python
# 内存优化
import gc

# 定期清理内存
def cleanup_memory():
    gc.collect()
    
# 减少批处理大小
embeddings_config = {
    'batch_size': 50,  # 从100减少到50
    'max_concurrent_requests': 2  # 减少并发
}
```

### 5. 数据和向量问题

#### 问题：嵌入维度不匹配
**错误信息：**
```
DimensionMismatchError: Expected 1536 dimensions, got 1024
```

**解决步骤：**
1. 检查嵌入模型配置
2. 重建向量数据库
3. 使用维度转换工具
4. 确保配置一致性

```python
# 检查向量维度
from rag_system.vector_store.chroma_store import ChromaVectorStore

store = ChromaVectorStore()
collections = store.list_collections()
for collection in collections:
    info = store.get_collection_info(collection)
    print(f"集合 {collection}: 维度 {info['dimensions']}")

# 重建向量数据库
from rag_system.utils.vector_migration import rebuild_vectors

rebuild_vectors(
    old_dimensions=1536,
    new_dimensions=1024,
    new_embedding_model="BAAI/bge-large-zh-v1.5"
)
```

#### 问题：向量检索结果不准确
**症状：**
- 检索到不相关的文档
- 相似度分数异常

**解决步骤：**
1. 检查嵌入模型是否适合数据
2. 调整相似度阈值
3. 重新处理文档
4. 检查文本预处理流程

```python
# 调整检索参数
retrieval_config = {
    'similarity_threshold': 0.8,  # 提高阈值
    'max_results': 3,  # 减少结果数量
    'rerank': True  # 启用重排序
}

# 测试检索质量
from rag_system.services.retrieval_service import RetrievalService

service = RetrievalService()
results = service.retrieve("测试查询", **retrieval_config)
for result in results:
    print(f"相似度: {result['similarity']:.3f}, 内容: {result['content'][:100]}")
```

### 6. API 限制和配额问题

#### 问题：超出 API 调用限制
**错误信息：**
```
RateLimitError: Rate limit exceeded. Please try again later.
```

**解决步骤：**
1. 实施请求限流
2. 增加重试延迟
3. 升级 API 计划
4. 使用多个 API 密钥

```python
# 实施指数退避重试
import time
import random

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            if attempt == max_retries - 1:
                raise
            delay = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(delay)
```

#### 问题：API 配额不足
**错误信息：**
```
QuotaExceededError: Insufficient quota
```

**解决步骤：**
1. 检查 API 使用量
2. 充值或升级账户
3. 优化 API 调用
4. 使用缓存减少调用

```python
# 监控 API 使用量
from rag_system.utils.usage_monitor import APIUsageMonitor

monitor = APIUsageMonitor()
usage = monitor.get_daily_usage()
print(f"今日使用量: {usage['requests']}/{usage['limit']}")
print(f"剩余配额: {usage['remaining']}")
```

## 调试工具和技巧

### 1. 日志分析

启用详细日志记录：

```python
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)

# 启用特定模块的调试日志
logger = logging.getLogger('rag_system')
logger.setLevel(logging.DEBUG)

# 添加文件处理器
handler = logging.FileHandler('debug.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
```

### 2. 网络诊断

```bash
# 测试网络连接
ping api.openai.com
ping api.siliconflow.cn

# 测试 HTTPS 连接
curl -I https://api.openai.com/v1/models

# 检查 DNS 解析
nslookup api.openai.com

# 测试端口连通性
telnet api.openai.com 443
```

### 3. 性能分析

```python
import time
import psutil
from functools import wraps

def performance_monitor(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024
        
        print(f"函数 {func.__name__}:")
        print(f"  执行时间: {end_time - start_time:.2f}秒")
        print(f"  内存使用: {end_memory - start_memory:.2f}MB")
        
        return result
    return wrapper

# 使用装饰器监控性能
@performance_monitor
def test_embedding():
    # 测试嵌入生成
    pass
```

### 4. 配置测试工具

```python
def test_all_configurations():
    """测试所有配置的有效性"""
    from rag_system.config.loader import ConfigLoader
    from rag_system.utils.health_checker import ModelHealthChecker
    
    loader = ConfigLoader()
    checker = ModelHealthChecker()
    
    # 测试不同的配置文件
    config_files = [
        'config/production.yaml',
        'config/development.yaml',
        'examples/configs/openai-config.yaml',
        'examples/configs/siliconflow-config.yaml'
    ]
    
    for config_file in config_files:
        try:
            print(f"测试配置文件: {config_file}")
            config = loader.load_config(config_file)
            
            # 验证配置
            issues = check_config_compatibility(config)
            if issues:
                print(f"  配置问题: {issues}")
                continue
            
            # 测试连接
            health = asyncio.run(checker.check_config_health(config))
            print(f"  健康状态: {health['status']}")
            
        except Exception as e:
            print(f"  错误: {e}")
        print()

test_all_configurations()
```

## 常见错误代码参考

| 错误代码 | 描述 | 可能原因 | 解决方案 |
|---------|------|----------|----------|
| `AUTH_001` | API 密钥无效 | 密钥错误或过期 | 检查并更新 API 密钥 |
| `AUTH_002` | 权限不足 | 密钥权限不够 | 升级 API 权限或使用其他密钥 |
| `CONN_001` | 连接超时 | 网络问题 | 检查网络连接，增加超时设置 |
| `CONN_002` | SSL 错误 | 证书问题 | 更新证书或检查系统时间 |
| `MODEL_001` | 模型不存在 | 模型名称错误 | 检查模型名称拼写 |
| `MODEL_002` | 模型不可用 | 服务维护 | 等待或切换其他模型 |
| `CONFIG_001` | 配置格式错误 | YAML 语法错误 | 检查配置文件格式 |
| `CONFIG_002` | 参数缺失 | 必需参数未设置 | 补充缺失的配置参数 |
| `QUOTA_001` | 超出限制 | API 调用过频 | 实施限流或等待 |
| `QUOTA_002` | 配额不足 | 账户余额不足 | 充值或升级账户 |
| `DATA_001` | 维度不匹配 | 嵌入模型不一致 | 重建向量数据库 |
| `DATA_002` | 数据格式错误 | 输入数据格式问题 | 检查数据预处理 |

## 预防性维护

### 1. 定期健康检查

设置定期健康检查任务：

```python
import schedule
import time

def daily_health_check():
    """每日健康检查"""
    checker = ModelHealthChecker()
    health = asyncio.run(checker.check_system_health())
    
    if health['overall_status'] != 'healthy':
        # 发送告警通知
        send_alert(f"系统健康检查失败: {health}")

# 每天上午9点执行健康检查
schedule.every().day.at("09:00").do(daily_health_check)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 2. 配置备份和版本控制

```bash
# 备份配置文件
cp config.yaml config.yaml.backup.$(date +%Y%m%d)

# 使用 Git 进行版本控制
git add config.yaml
git commit -m "更新配置: 切换到新的嵌入模型"
```

### 3. 监控和告警

```python
def setup_monitoring():
    """设置监控和告警"""
    from rag_system.utils.monitoring import MetricsCollector
    
    collector = MetricsCollector()
    
    # 设置告警阈值
    collector.set_alert_threshold('response_time', 5.0)  # 5秒
    collector.set_alert_threshold('error_rate', 0.1)     # 10%
    collector.set_alert_threshold('memory_usage', 0.8)   # 80%
    
    # 启动监控
    collector.start_monitoring()
```

### 4. 自动故障恢复

```python
class AutoRecovery:
    def __init__(self):
        self.recovery_strategies = {
            'connection_timeout': self.handle_timeout,
            'rate_limit': self.handle_rate_limit,
            'model_unavailable': self.handle_model_unavailable
        }
    
    def handle_timeout(self, error):
        """处理超时错误"""
        # 增加超时时间
        # 重试请求
        pass
    
    def handle_rate_limit(self, error):
        """处理限流错误"""
        # 实施退避策略
        # 切换到备用 API 密钥
        pass
    
    def handle_model_unavailable(self, error):
        """处理模型不可用"""
        # 切换到备用模型
        # 通知管理员
        pass
```

通过遵循这个故障排除指南，您应该能够快速诊断和解决大多数多平台模型支持相关的问题。如果问题仍然存在，请收集详细的错误日志和系统信息，联系技术支持团队。