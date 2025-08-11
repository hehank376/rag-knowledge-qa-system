# 健康监控系统

## 概述

本文档描述了RAG系统中实现的多平台模型健康监控系统。该系统提供了全面的模型健康检查、监控、告警和报告功能。

## 系统架构

### 核心组件

1. **ModelHealthChecker** - 模型健康检查器
2. **HealthMonitoringService** - 健康监控服务
3. **Health API** - 健康检查REST API
4. **Alert System** - 告警系统

### 数据模型

- `ModelHealthStatus` - 模型健康状态
- `ModelHealthCheckConfig` - 健康检查配置
- `Alert` - 告警信息
- `HealthStatus` - 健康状态枚举

## 功能特性

### 1. 模型健康检查

- **LLM健康检查**: 通过发送测试提示验证LLM响应
- **嵌入模型健康检查**: 通过嵌入测试文本验证向量生成
- **响应时间监控**: 记录模型响应时间
- **成功率统计**: 计算模型成功率和连续失败次数

### 2. 定期监控

- **自动检查**: 可配置的定期健康检查
- **启动时检查**: 系统启动时的健康验证
- **超时处理**: 健康检查超时保护
- **错误恢复**: 自动重试和错误恢复机制

### 3. 告警系统

- **多级告警**: INFO、WARNING、ERROR、CRITICAL
- **告警生命周期**: 创建、活跃、解决、历史记录
- **冷却机制**: 防止告警风暴
- **自定义处理器**: 支持多种告警处理方式

### 4. 监控报告

- **实时状态**: 获取当前健康状态
- **历史统计**: 成功率、失败次数等统计信息
- **详细报告**: JSON格式的完整健康报告
- **提供商视图**: 按提供商分组的健康状态

### 5. REST API

- `GET /health/` - 获取系统整体健康状态
- `GET /health/models` - 获取所有模型健康状态
- `GET /health/models/{provider}/{model}/{type}` - 获取特定模型状态
- `GET /health/providers/{provider}` - 获取提供商状态
- `GET /health/alerts` - 获取健康告警
- `GET /health/status` - 获取简化健康状态
- `POST /health/check` - 手动触发健康检查

## 配置选项

### ModelHealthCheckConfig

```python
@dataclass
class ModelHealthCheckConfig:
    check_interval: int = 300          # 检查间隔（秒）
    timeout: int = 30                  # 超时时间（秒）
    max_consecutive_failures: int = 3  # 最大连续失败次数
    test_prompt: str = "Hello, this is a health check test."
    test_text: str = "This is a test document for embedding health check."
    enable_startup_check: bool = True  # 启用启动时检查
    enable_periodic_check: bool = True # 启用定期检查
    failure_threshold: float = 0.8     # 成功率阈值
```

## 使用示例

### 1. 基本使用

```python
from rag_system.utils.health_checker import ModelHealthChecker, ModelHealthCheckConfig
from rag_system.llm.base import LLMConfig
from rag_system.embeddings.base import EmbeddingConfig

# 创建配置
config = ModelHealthCheckConfig(
    check_interval=60,
    timeout=10
)

# 创建健康检查器
checker = ModelHealthChecker(config)

# 配置模型
llm_configs = [
    LLMConfig(provider="openai", model="gpt-4", api_key="your-key")
]
embedding_configs = [
    EmbeddingConfig(provider="openai", model="text-embedding-ada-002", api_key="your-key")
]

# 执行健康检查
results = await checker.check_all_models(llm_configs, embedding_configs)

# 生成报告
report = checker.generate_health_report()
```

### 2. 监控服务

```python
from rag_system.services.health_monitoring_service import HealthMonitoringService

# 创建监控服务
monitoring_service = HealthMonitoringService(
    health_checker=checker,
    llm_configs=llm_configs,
    embedding_configs=embedding_configs
)

# 启动监控
await monitoring_service.start_monitoring()

# 获取活跃告警
alerts = monitoring_service.get_active_alerts()
```

### 3. 自定义告警处理器

```python
def custom_alert_handler(alert):
    print(f"Alert: {alert.title} - {alert.message}")
    # 发送邮件、Webhook等

monitoring_service.add_alert_handler(custom_alert_handler)
```

## 告警类型

### 系统级告警

- **系统整体健康状态异常** (CRITICAL): 多个模型不健康
- **系统健康状态降级** (WARNING): 部分模型不健康

### 模型级告警

- **模型不健康** (ERROR/CRITICAL): 模型连续失败
- **模型成功率较低** (WARNING): 成功率低于阈值

### 提供商级告警

- **提供商大量模型不健康** (ERROR): 50%以上模型不健康
- **提供商部分模型不健康** (WARNING): 部分模型不健康

## 性能考虑

### 1. 检查频率

- 默认5分钟检查一次，可根据需要调整
- 避免过于频繁的检查影响模型性能

### 2. 超时设置

- 默认30秒超时，防止长时间等待
- 可根据模型响应特性调整

### 3. 内存管理

- 限制告警历史记录数量
- 定期清理已解决的告警

### 4. 并发控制

- 使用异步操作避免阻塞
- 合理控制并发检查数量

## 扩展性

### 1. 自定义健康检查

可以扩展健康检查逻辑：

```python
class CustomHealthChecker(ModelHealthChecker):
    async def check_llm_health(self, llm_config):
        # 自定义检查逻辑
        pass
```

### 2. 自定义告警处理器

支持多种告警处理方式：

- 控制台输出
- 文件日志
- 邮件通知
- Webhook调用
- 消息队列

### 3. 监控指标扩展

可以添加更多监控指标：

- 模型延迟分布
- 错误类型统计
- 资源使用情况

## 最佳实践

### 1. 配置建议

- 根据模型特性调整超时时间
- 设置合适的检查间隔
- 配置告警阈值

### 2. 告警管理

- 设置告警冷却时间
- 分级处理不同级别告警
- 建立告警响应流程

### 3. 监控策略

- 启用启动时健康检查
- 监控关键模型的健康状态
- 定期审查健康报告

## 故障排除

### 常见问题

1. **模型检查失败**
   - 检查API密钥是否正确
   - 验证网络连接
   - 确认模型配置

2. **告警过多**
   - 调整告警阈值
   - 增加冷却时间
   - 检查模型稳定性

3. **性能影响**
   - 减少检查频率
   - 优化超时设置
   - 使用异步操作

## 测试

系统包含完整的测试套件：

- 单元测试: 测试各个组件功能
- 集成测试: 测试组件间协作
- API测试: 测试REST API接口

运行测试：

```bash
# 运行所有健康监控相关测试
python -m pytest tests/utils/test_model_health_checker.py -v
python -m pytest tests/services/test_health_monitoring_service.py -v
python -m pytest tests/api/test_health_api.py -v
python -m pytest tests/integration/test_health_monitoring_integration.py -v
```

## 演示

提供了完整的演示脚本：

```bash
# 运行健康检查器演示
python examples/model_health_checker_demo.py

# 运行健康监控系统演示
python examples/health_monitoring_demo.py
```

## 总结

健康监控系统为RAG系统提供了全面的模型健康管理能力，包括：

- ✅ 自动化健康检查
- ✅ 实时监控和告警
- ✅ 详细的健康报告
- ✅ REST API接口
- ✅ 可扩展的架构
- ✅ 完整的测试覆盖

该系统确保了多平台模型的可靠性和可用性，为生产环境提供了重要的监控保障。