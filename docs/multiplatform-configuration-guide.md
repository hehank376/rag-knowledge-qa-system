# 多平台模型配置指南

## 概述

本指南详细介绍了如何配置和使用多平台模型支持系统。该系统支持多个AI模型提供商，包括OpenAI、SiliconFlow、ModelScope、DeepSeek和本地Ollama等。

## 支持的平台

### 1. OpenAI
- **模型类型**: GPT系列模型
- **支持功能**: 文本生成、嵌入
- **API类型**: REST API

### 2. SiliconFlow (硅基流动)
- **模型类型**: Qwen、ChatGLM、BGE等
- **支持功能**: 文本生成、嵌入
- **API类型**: OpenAI兼容API

### 3. ModelScope (魔塔)
- **模型类型**: 通义千问、ChatGLM等
- **支持功能**: 文本生成、嵌入
- **API类型**: ModelScope API

### 4. DeepSeek
- **模型类型**: DeepSeek系列模型
- **支持功能**: 文本生成、嵌入
- **API类型**: OpenAI兼容API

### 5. Ollama (本地部署)
- **模型类型**: Llama、Mistral等开源模型
- **支持功能**: 文本生成、嵌入
- **API类型**: Ollama API

## 配置文件结构

### 基本配置格式

```yaml
# config.yaml
app:
  name: "RAG知识问答系统"
  version: "2.0.0"
  debug: false

llm:
  provider: "siliconflow"
  model: "Qwen/Qwen2-7B-Instruct"
  api_key: "${SILICONFLOW_API_KEY}"
  base_url: "https://api.siliconflow.cn/v1"
  temperature: 0.7
  max_tokens: 2000
  timeout: 60
  retry_attempts: 3

embeddings:
  provider: "siliconflow"
  model: "BAAI/bge-large-zh-v1.5"
  api_key: "${SILICONFLOW_API_KEY}"
  base_url: "https://api.siliconflow.cn/v1"
  dimensions: 1024
  batch_size: 100
  timeout: 60

vector_store:
  type: "chroma"
  persist_directory: "./chroma_db"
  collection_name: "documents"

database:
  url: "sqlite:///./database/documents.db"
  echo: false
```

### 环境变量配置

```bash
# .env
SILICONFLOW_API_KEY=your_siliconflow_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
MODELSCOPE_API_KEY=your_modelscope_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
```

## 各平台配置示例

### OpenAI 配置

```yaml
llm:
  provider: "openai"
  model: "gpt-3.5-turbo"
  api_key: "${OPENAI_API_KEY}"
  temperature: 0.7
  max_tokens: 1000
  timeout: 60
  retry_attempts: 3

embeddings:
  provider: "openai"
  model: "text-embedding-ada-002"
  api_key: "${OPENAI_API_KEY}"
  dimensions: 1536
  batch_size: 100
```

**最佳实践**:
- 使用环境变量存储API密钥
- 设置合理的超时时间（60秒）
- 启用重试机制（3次）
- 根据需求调整temperature参数

### SiliconFlow 配置

```yaml
llm:
  provider: "siliconflow"
  model: "Qwen/Qwen2-7B-Instruct"
  api_key: "${SILICONFLOW_API_KEY}"
  base_url: "https://api.siliconflow.cn/v1"
  temperature: 0.7
  max_tokens: 2000
  timeout: 60
  retry_attempts: 3

embeddings:
  provider: "siliconflow"
  model: "BAAI/bge-large-zh-v1.5"
  api_key: "${SILICONFLOW_API_KEY}"
  base_url: "https://api.siliconflow.cn/v1"
  dimensions: 1024
  batch_size: 100
```

**支持的模型**:
- **LLM模型**: Qwen/Qwen2-7B-Instruct, Qwen/Qwen2-72B-Instruct, THUDM/chatglm3-6b
- **嵌入模型**: BAAI/bge-large-zh-v1.5, BAAI/bge-base-zh-v1.5, BAAI/bge-small-zh-v1.5

**最佳实践**:
- 使用中文优化的模型（如BGE系列）
- 根据性能需求选择模型大小
- 设置合适的批处理大小

### ModelScope 配置

```yaml
llm:
  provider: "modelscope"
  model: "qwen-turbo"
  api_key: "${MODELSCOPE_API_KEY}"
  temperature: 0.7
  max_tokens: 1500
  timeout: 60
  retry_attempts: 3

embeddings:
  provider: "modelscope"
  model: "text-embedding-v1"
  api_key: "${MODELSCOPE_API_KEY}"
  dimensions: 1536
  batch_size: 50
```

**最佳实践**:
- 使用魔塔平台的优化模型
- 注意API调用限制
- 设置较小的批处理大小

### DeepSeek 配置

```yaml
llm:
  provider: "deepseek"
  model: "deepseek-chat"
  api_key: "${DEEPSEEK_API_KEY}"
  base_url: "https://api.deepseek.com/v1"
  temperature: 0.7
  max_tokens: 2000
  timeout: 60
  retry_attempts: 3

embeddings:
  provider: "deepseek"
  model: "deepseek-embedding"
  api_key: "${DEEPSEEK_API_KEY}"
  base_url: "https://api.deepseek.com/v1"
  dimensions: 1536
  batch_size: 100
```

**最佳实践**:
- 利用DeepSeek的代码理解能力
- 适合技术文档问答场景
- 注意成本控制

### Ollama 本地配置

```yaml
llm:
  provider: "ollama"
  model: "llama2:7b"
  base_url: "http://localhost:11434"
  temperature: 0.7
  max_tokens: 2000
  timeout: 120
  retry_attempts: 2

embeddings:
  provider: "ollama"
  model: "nomic-embed-text"
  base_url: "http://localhost:11434"
  dimensions: 768
  batch_size: 50
```

**最佳实践**:
- 确保Ollama服务正在运行
- 预先下载所需模型
- 设置较长的超时时间
- 根据硬件性能调整批处理大小

## 高级配置选项

### 多模型配置

```yaml
llm:
  provider: "siliconflow"
  model: "Qwen/Qwen2-7B-Instruct"
  api_key: "${SILICONFLOW_API_KEY}"
  base_url: "https://api.siliconflow.cn/v1"
  
  # 备用模型配置
  fallback:
    provider: "openai"
    model: "gpt-3.5-turbo"
    api_key: "${OPENAI_API_KEY}"
  
  # 高级参数
  temperature: 0.7
  max_tokens: 2000
  top_p: 0.9
  frequency_penalty: 0.0
  presence_penalty: 0.0
  
  # 性能配置
  timeout: 60
  retry_attempts: 3
  retry_delay: 1.0
  
  # 额外参数
  extra_params:
    stream: false
    logprobs: false
```

### 健康检查配置

```yaml
health_check:
  enabled: true
  interval: 300  # 5分钟
  timeout: 30
  retry_attempts: 2
  
  # 检查项目
  checks:
    - llm_connectivity
    - embedding_connectivity
    - vector_store_status
    - database_status
```

### 性能优化配置

```yaml
performance:
  # 连接池配置
  connection_pool:
    max_connections: 10
    max_keepalive_connections: 5
    keepalive_expiry: 300
  
  # 缓存配置
  cache:
    enabled: true
    ttl: 3600  # 1小时
    max_size: 1000
  
  # 批处理配置
  batch_processing:
    max_batch_size: 100
    batch_timeout: 5.0
    parallel_batches: 3
```

## 配置验证

### 使用配置验证工具

```python
from rag_system.config.loader import ConfigLoader
from rag_system.utils.compatibility import check_config_compatibility

# 加载配置
loader = ConfigLoader()
config = loader.load_config()

# 验证配置
issues = check_config_compatibility(config)
if issues:
    print("配置问题:")
    for issue in issues:
        print(f"- {issue}")
else:
    print("配置验证通过")
```

### 配置测试脚本

```python
#!/usr/bin/env python3
"""
配置测试脚本
"""
import asyncio
from rag_system.llm.factory import LLMFactory
from rag_system.embeddings.factory import EmbeddingFactory
from rag_system.config.loader import ConfigLoader

async def test_configuration():
    """测试配置"""
    try:
        # 加载配置
        loader = ConfigLoader()
        config = loader.load_config()
        
        # 测试LLM
        llm_factory = LLMFactory()
        llm = llm_factory.create_llm(config.llm)
        print(f"✓ LLM配置正常: {llm.config.provider}/{llm.config.model}")
        
        # 测试嵌入模型
        embedding_factory = EmbeddingFactory()
        embedding = embedding_factory.create_embedding(config.embeddings)
        print(f"✓ 嵌入模型配置正常: {embedding.config.provider}/{embedding.config.model}")
        
        print("✓ 所有配置测试通过")
        
    except Exception as e:
        print(f"✗ 配置测试失败: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_configuration())
```

## 常见问题和故障排除

### Q1: API密钥配置问题

**问题**: `API密钥无效或缺失`

**解决方案**:
1. 检查环境变量是否正确设置
2. 确认API密钥格式正确
3. 验证API密钥权限

```bash
# 检查环境变量
echo $SILICONFLOW_API_KEY
echo $OPENAI_API_KEY

# 测试API连接
curl -H "Authorization: Bearer $SILICONFLOW_API_KEY" \
     https://api.siliconflow.cn/v1/models
```

### Q2: 模型不可用

**问题**: `指定的模型不存在或不可用`

**解决方案**:
1. 检查模型名称拼写
2. 确认提供商支持该模型
3. 查看模型可用性状态

```python
# 查看可用模型
from rag_system.llm.factory import LLMFactory
factory = LLMFactory()
available_providers = factory.get_available_providers()
print("可用提供商:", available_providers)
```

### Q3: 连接超时

**问题**: `请求超时或连接失败`

**解决方案**:
1. 增加超时时间
2. 检查网络连接
3. 验证API端点URL

```yaml
llm:
  timeout: 120  # 增加到120秒
  retry_attempts: 5  # 增加重试次数
```

### Q4: 向量维度不匹配

**问题**: `嵌入向量维度与向量存储不匹配`

**解决方案**:
1. 检查嵌入模型的输出维度
2. 更新向量存储配置
3. 使用迁移工具转换现有数据

```python
# 检查向量维度
from rag_system.utils.migration_tools import check_vector_compatibility

report = check_vector_compatibility(source_dim=1536, target_dim=1024)
print(f"兼容性: {report.compatible}")
print(f"需要转换: {report.conversion_needed}")
```

### Q5: 性能问题

**问题**: `响应速度慢或资源使用过高`

**解决方案**:
1. 调整批处理大小
2. 启用缓存
3. 优化模型选择

```yaml
embeddings:
  batch_size: 50  # 减少批处理大小
  
performance:
  cache:
    enabled: true
    ttl: 3600
```

## 迁移指南

### 从单平台迁移到多平台

1. **备份现有配置**
```bash
cp config.yaml config.yaml.backup
```

2. **使用迁移工具**
```python
from rag_system.utils.migration_tools import migrate_config_file

success = migrate_config_file("config.yaml.backup", "config.yaml")
if success:
    print("迁移成功")
else:
    print("迁移失败，请检查日志")
```

3. **验证新配置**
```bash
python test_configuration.py
```

### 向量数据迁移

```python
from rag_system.utils.migration_tools import VectorDataMigrationTool

tool = VectorDataMigrationTool()

# 检查兼容性
report = tool.check_vector_compatibility(1536, 1024)
print(f"兼容性报告: {report}")

# 转换向量数据（如果需要）
if report.conversion_needed:
    converted_vectors = tool.convert_vector_dimensions(vectors, 1024)
```

## 最佳实践总结

### 安全性
- 使用环境变量存储敏感信息
- 定期轮换API密钥
- 限制API访问权限
- 启用日志审计

### 性能
- 根据使用场景选择合适的模型
- 合理设置批处理大小
- 启用缓存机制
- 监控资源使用情况

### 可靠性
- 配置备用模型
- 启用重试机制
- 设置健康检查
- 实施错误恢复策略

### 维护性
- 使用版本控制管理配置
- 编写配置文档
- 定期测试配置
- 监控系统状态

## 参考资料

- [API文档](./api-documentation.md)
- [部署指南](./deployment-guide.md)
- [故障排除](./troubleshooting.md)
- [性能优化](./performance-optimization.md)