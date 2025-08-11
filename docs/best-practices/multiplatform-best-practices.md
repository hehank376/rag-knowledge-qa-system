# 多平台模型最佳实践指南

本指南总结了使用 RAG 系统多平台模型支持的最佳实践，帮助您构建稳定、高效、安全的 AI 应用。

## 架构设计最佳实践

### 1. 提供商选择策略

#### 主备提供商配置

```yaml
# 推荐的主备配置
llm:
  provider: "siliconflow"  # 主提供商：性价比高，中文优化
  model: "Qwen/Qwen2-72B-Instruct"
  api_key: "${SILICONFLOW_API_KEY}"
  
global:
  enable_fallback: true
  fallback_provider: "openai"  # 备用提供商：稳定可靠
  fallback_model: "gpt-3.5-turbo"
  fallback_api_key: "${OPENAI_API_KEY}"
```

#### 多提供商负载均衡

```python
# 智能提供商选择策略
class ProviderSelector:
    def __init__(self):
        self.providers = {
            'siliconflow': {'weight': 0.6, 'cost': 0.001, 'latency': 1.2},
            'openai': {'weight': 0.3, 'cost': 0.02, 'latency': 0.8},
            'deepseek': {'weight': 0.1, 'cost': 0.0005, 'latency': 1.5}
        }
    
    def select_provider(self, criteria='balanced'):
        """根据不同标准选择提供商"""
        if criteria == 'cost':
            return min(self.providers.items(), key=lambda x: x[1]['cost'])[0]
        elif criteria == 'speed':
            return min(self.providers.items(), key=lambda x: x[1]['latency'])[0]
        else:  # balanced
            return self._weighted_selection()
```

### 2. 模型配置优化

#### 生产环境配置

```yaml
# 生产环境推荐配置
llm:
  provider: "siliconflow"
  model: "Qwen/Qwen2-72B-Instruct"
  temperature: 0.1  # 低温度确保输出稳定
  max_tokens: 2000
  timeout: 30  # 适中的超时时间
  retry_attempts: 3
  top_p: 0.8  # 保守的采样策略
  
embeddings:
  provider: "siliconflow"
  model: "BAAI/bge-large-zh-v1.5"
  batch_size: 100  # 平衡性能和资源使用
  max_concurrent_requests: 3
  timeout: 30
```

#### 开发环境配置

```yaml
# 开发环境推荐配置
llm:
  provider: "mock"  # 使用模拟提供商节省成本
  model: "mock-llm"
  temperature: 0.7  # 较高温度增加多样性
  max_tokens: 1000  # 限制长度节省成本
  debug: true
  
embeddings:
  provider: "mock"
  model: "mock-embedding"
  batch_size: 50
  debug: true
```

## 性能优化最佳实践

### 1. 批处理优化

#### 智能批处理策略

```python
class SmartBatcher:
    def __init__(self, base_batch_size=100):
        self.base_batch_size = base_batch_size
        self.performance_history = []
    
    def get_optimal_batch_size(self, text_lengths, system_load):
        """根据文本长度和系统负载动态调整批处理大小"""
        avg_length = sum(text_lengths) / len(text_lengths)
        
        # 根据文本长度调整
        if avg_length > 1000:
            batch_size = self.base_batch_size // 2
        elif avg_length < 200:
            batch_size = self.base_batch_size * 2
        else:
            batch_size = self.base_batch_size
        
        # 根据系统负载调整
        if system_load > 0.8:
            batch_size = max(10, batch_size // 2)
        elif system_load < 0.3:
            batch_size = min(200, batch_size * 1.5)
        
        return int(batch_size)
    
    def process_with_adaptive_batching(self, texts):
        """自适应批处理"""
        system_load = psutil.cpu_percent() / 100
        text_lengths = [len(text) for text in texts]
        
        optimal_batch_size = self.get_optimal_batch_size(text_lengths, system_load)
        
        results = []
        for i in range(0, len(texts), optimal_batch_size):
            batch = texts[i:i + optimal_batch_size]
            batch_result = self.process_batch(batch)
            results.extend(batch_result)
        
        return results
```

### 2. 缓存策略

#### 多层缓存架构

```python
class MultiLevelCache:
    def __init__(self):
        self.memory_cache = {}  # L1: 内存缓存
        self.redis_cache = redis.Redis()  # L2: Redis缓存
        self.disk_cache = {}  # L3: 磁盘缓存
    
    def get(self, key):
        """多层缓存查找"""
        # L1: 内存缓存
        if key in self.memory_cache:
            return self.memory_cache[key]
        
        # L2: Redis缓存
        redis_value = self.redis_cache.get(key)
        if redis_value:
            value = json.loads(redis_value)
            self.memory_cache[key] = value  # 回填L1
            return value
        
        # L3: 磁盘缓存
        if key in self.disk_cache:
            value = self.disk_cache[key]
            self.redis_cache.setex(key, 3600, json.dumps(value))  # 回填L2
            self.memory_cache[key] = value  # 回填L1
            return value
        
        return None
    
    def set(self, key, value, ttl=3600):
        """多层缓存设置"""
        self.memory_cache[key] = value
        self.redis_cache.setex(key, ttl, json.dumps(value))
        self.disk_cache[key] = value
```

### 3. 连接池管理

```python
class ConnectionPoolManager:
    def __init__(self):
        self.pools = {}
    
    def get_pool(self, provider, pool_size=10):
        """获取连接池"""
        if provider not in self.pools:
            self.pools[provider] = self.create_pool(provider, pool_size)
        return self.pools[provider]
    
    def create_pool(self, provider, pool_size):
        """创建连接池"""
        return {
            'connections': [],
            'max_size': pool_size,
            'current_size': 0,
            'lock': threading.Lock()
        }
    
    def get_connection(self, provider):
        """获取连接"""
        pool = self.get_pool(provider)
        with pool['lock']:
            if pool['connections']:
                return pool['connections'].pop()
            elif pool['current_size'] < pool['max_size']:
                conn = self.create_connection(provider)
                pool['current_size'] += 1
                return conn
            else:
                # 等待可用连接
                return self.wait_for_connection(pool)
```

## 安全最佳实践

### 1. API 密钥管理

#### 密钥轮换策略

```python
class APIKeyRotator:
    def __init__(self):
        self.key_store = {}
        self.rotation_schedule = {}
    
    def add_key(self, provider, key, expiry_date):
        """添加API密钥"""
        if provider not in self.key_store:
            self.key_store[provider] = []
        
        self.key_store[provider].append({
            'key': key,
            'expiry': expiry_date,
            'usage_count': 0,
            'last_used': None
        })
    
    def get_active_key(self, provider):
        """获取活跃的API密钥"""
        if provider not in self.key_store:
            raise ValueError(f"No keys available for provider: {provider}")
        
        # 选择未过期且使用次数最少的密钥
        valid_keys = [
            key for key in self.key_store[provider]
            if key['expiry'] > datetime.now()
        ]
        
        if not valid_keys:
            raise ValueError(f"All keys expired for provider: {provider}")
        
        # 返回使用次数最少的密钥
        return min(valid_keys, key=lambda x: x['usage_count'])
    
    def rotate_keys(self):
        """定期轮换密钥"""
        for provider in self.key_store:
            # 检查即将过期的密钥
            for key_info in self.key_store[provider]:
                days_until_expiry = (key_info['expiry'] - datetime.now()).days
                if days_until_expiry <= 7:  # 7天内过期
                    self.request_new_key(provider)
```

#### 环境变量安全管理

```bash
# .env.template
# 主要提供商API密钥
SILICONFLOW_API_KEY=your-siliconflow-api-key
OPENAI_API_KEY=your-openai-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key

# 备用API密钥（用于轮换）
SILICONFLOW_API_KEY_BACKUP=your-backup-key
OPENAI_API_KEY_BACKUP=your-backup-key

# 数据库加密密钥
DATABASE_ENCRYPTION_KEY=your-32-char-encryption-key

# JWT密钥
JWT_SECRET_KEY=your-jwt-secret-key

# 系统安全配置
ALLOWED_HOSTS=localhost,yourdomain.com
CORS_ORIGINS=https://yourdomain.com
```

### 2. 输入验证和过滤

```python
class InputValidator:
    def __init__(self):
        self.max_input_length = 10000
        self.forbidden_patterns = [
            r'<script.*?>.*?</script>',  # XSS防护
            r'javascript:',
            r'data:text/html',
            r'eval\s*\(',
        ]
        self.pii_patterns = [
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # 信用卡号
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # 邮箱
        ]
    
    def validate_input(self, text):
        """验证输入文本"""
        if len(text) > self.max_input_length:
            raise ValueError(f"输入长度超过限制: {len(text)} > {self.max_input_length}")
        
        # 检查恶意模式
        for pattern in self.forbidden_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                raise ValueError(f"输入包含禁止的模式: {pattern}")
        
        return True
    
    def sanitize_input(self, text):
        """清理输入文本"""
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 转义特殊字符
        text = html.escape(text)
        
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def detect_pii(self, text):
        """检测个人身份信息"""
        detected_pii = []
        for pattern in self.pii_patterns:
            matches = re.findall(pattern, text)
            if matches:
                detected_pii.extend(matches)
        
        return detected_pii
```

## 监控和可观测性最佳实践

### 1. 结构化日志

```python
import structlog

# 配置结构化日志
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class LoggingMiddleware:
    def __init__(self):
        self.logger = structlog.get_logger()
    
    def log_request(self, request_id, method, endpoint, user_id=None):
        """记录请求日志"""
        self.logger.info(
            "request_started",
            request_id=request_id,
            method=method,
            endpoint=endpoint,
            user_id=user_id,
            timestamp=datetime.now().isoformat()
        )
    
    def log_model_call(self, request_id, provider, model, input_tokens, output_tokens, duration):
        """记录模型调用日志"""
        self.logger.info(
            "model_call_completed",
            request_id=request_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            duration=duration,
            cost=self.calculate_cost(provider, input_tokens, output_tokens)
        )
    
    def log_error(self, request_id, error_type, error_message, provider=None):
        """记录错误日志"""
        self.logger.error(
            "error_occurred",
            request_id=request_id,
            error_type=error_type,
            error_message=error_message,
            provider=provider,
            timestamp=datetime.now().isoformat()
        )
```

### 2. 分布式追踪

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

class DistributedTracing:
    def __init__(self):
        # 配置追踪
        trace.set_tracer_provider(TracerProvider())
        tracer = trace.get_tracer(__name__)
        
        # 配置Jaeger导出器
        jaeger_exporter = JaegerExporter(
            agent_host_name="localhost",
            agent_port=6831,
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        self.tracer = tracer
    
    def trace_model_call(self, provider, model, operation):
        """追踪模型调用"""
        with self.tracer.start_as_current_span(f"{provider}_{model}_{operation}") as span:
            span.set_attribute("provider", provider)
            span.set_attribute("model", model)
            span.set_attribute("operation", operation)
            
            try:
                result = self.execute_operation(operation)
                span.set_attribute("success", True)
                return result
            except Exception as e:
                span.set_attribute("success", False)
                span.set_attribute("error", str(e))
                raise
```

## 成本优化最佳实践

### 1. 智能成本控制

```python
class CostController:
    def __init__(self):
        self.daily_budget = 100.0  # 每日预算
        self.current_spend = 0.0
        self.cost_per_provider = {
            'openai': {'input': 0.03, 'output': 0.06},  # 每1K tokens
            'siliconflow': {'input': 0.001, 'output': 0.002},
            'deepseek': {'input': 0.0005, 'output': 0.001}
        }
    
    def calculate_cost(self, provider, input_tokens, output_tokens):
        """计算调用成本"""
        if provider not in self.cost_per_provider:
            return 0.0
        
        rates = self.cost_per_provider[provider]
        cost = (input_tokens / 1000 * rates['input'] + 
                output_tokens / 1000 * rates['output'])
        return cost
    
    def check_budget(self, estimated_cost):
        """检查预算限制"""
        if self.current_spend + estimated_cost > self.daily_budget:
            raise BudgetExceededException(
                f"预算不足: 当前支出 {self.current_spend}, "
                f"预估成本 {estimated_cost}, "
                f"日预算 {self.daily_budget}"
            )
    
    def select_cost_effective_provider(self, input_tokens, output_tokens):
        """选择成本最低的提供商"""
        costs = {}
        for provider, rates in self.cost_per_provider.items():
            cost = self.calculate_cost(provider, input_tokens, output_tokens)
            costs[provider] = cost
        
        return min(costs.items(), key=lambda x: x[1])[0]
```

### 2. 使用量监控

```python
class UsageMonitor:
    def __init__(self):
        self.usage_stats = defaultdict(lambda: {
            'requests': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'cost': 0.0,
            'errors': 0
        })
    
    def record_usage(self, provider, input_tokens, output_tokens, cost, success=True):
        """记录使用量"""
        stats = self.usage_stats[provider]
        stats['requests'] += 1
        stats['input_tokens'] += input_tokens
        stats['output_tokens'] += output_tokens
        stats['cost'] += cost
        
        if not success:
            stats['errors'] += 1
    
    def get_daily_report(self):
        """生成日报"""
        total_cost = sum(stats['cost'] for stats in self.usage_stats.values())
        total_requests = sum(stats['requests'] for stats in self.usage_stats.values())
        
        report = {
            'date': datetime.now().date().isoformat(),
            'total_cost': total_cost,
            'total_requests': total_requests,
            'providers': dict(self.usage_stats),
            'cost_per_request': total_cost / max(total_requests, 1)
        }
        
        return report
```

## 错误处理和恢复最佳实践

### 1. 优雅降级策略

```python
class GracefulDegradation:
    def __init__(self):
        self.fallback_chain = [
            'siliconflow',
            'deepseek', 
            'openai',
            'mock'  # 最后的兜底
        ]
    
    def execute_with_fallback(self, operation, *args, **kwargs):
        """带降级的执行"""
        last_error = None
        
        for provider in self.fallback_chain:
            try:
                return self.execute_with_provider(provider, operation, *args, **kwargs)
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider} failed: {e}")
                continue
        
        # 所有提供商都失败，返回缓存结果或默认响应
        cached_result = self.get_cached_result(*args, **kwargs)
        if cached_result:
            return cached_result
        
        # 返回默认响应
        return self.get_default_response(*args, **kwargs)
```

### 2. 断路器模式

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func, *args, **kwargs):
        """通过断路器调用函数"""
        if self.state == 'OPEN':
            if self._should_attempt_reset():
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerOpenException("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """成功时重置计数器"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """失败时增加计数器"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'
    
    def _should_attempt_reset(self):
        """检查是否应该尝试重置"""
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
```

## 部署和运维最佳实践

### 1. 蓝绿部署

```bash
#!/bin/bash
# blue_green_deploy.sh

BLUE_ENV="rag-system-blue"
GREEN_ENV="rag-system-green"
CURRENT_ENV=$(kubectl get service rag-system-service -o jsonpath='{.spec.selector.version}')

if [ "$CURRENT_ENV" = "blue" ]; then
    NEW_ENV="green"
    OLD_ENV="blue"
else
    NEW_ENV="blue"
    OLD_ENV="green"
fi

echo "当前环境: $OLD_ENV, 部署到: $NEW_ENV"

# 部署新版本
kubectl set image deployment/rag-system-$NEW_ENV rag-system=rag-system:$NEW_VERSION

# 等待部署完成
kubectl rollout status deployment/rag-system-$NEW_ENV

# 健康检查
kubectl exec deployment/rag-system-$NEW_ENV -- curl -f http://localhost:8000/api/health

# 切换流量
kubectl patch service rag-system-service -p '{"spec":{"selector":{"version":"'$NEW_ENV'"}}}'

echo "部署完成，流量已切换到 $NEW_ENV"
```

### 2. 配置管理

```python
class ConfigManager:
    def __init__(self):
        self.config_versions = {}
        self.rollback_stack = []
    
    def update_config(self, new_config):
        """更新配置"""
        # 备份当前配置
        current_config = self.get_current_config()
        self.rollback_stack.append(current_config)
        
        # 验证新配置
        if not self.validate_config(new_config):
            raise ValueError("配置验证失败")
        
        # 应用新配置
        self.apply_config(new_config)
        
        # 健康检查
        if not self.health_check():
            self.rollback()
            raise RuntimeError("配置更新后健康检查失败，已回滚")
    
    def rollback(self):
        """回滚配置"""
        if not self.rollback_stack:
            raise ValueError("没有可回滚的配置")
        
        previous_config = self.rollback_stack.pop()
        self.apply_config(previous_config)
```

这个最佳实践指南涵盖了架构设计、性能优化、安全、监控、成本控制、错误处理和运维等各个方面，为构建生产级的多平台模型系统提供了全面的指导。