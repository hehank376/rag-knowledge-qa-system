# 多平台模型 API 使用指南

本指南详细介绍如何通过 API 使用 RAG 系统的多平台模型支持功能。

## API 概述

RAG 系统提供了统一的 API 接口来管理和使用多个 AI 模型提供商。主要的 API 端点包括：

- `/api/config` - 配置管理
- `/api/models` - 模型管理
- `/api/health` - 健康检查
- `/api/qa` - 问答服务
- `/api/embeddings` - 嵌入服务

## 配置管理 API

### 获取当前配置

```http
GET /api/config
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "llm": {
      "provider": "siliconflow",
      "model": "Qwen/Qwen2-7B-Instruct",
      "temperature": 0.7,
      "max_tokens": 2000
    },
    "embeddings": {
      "provider": "siliconflow",
      "model": "BAAI/bge-large-zh-v1.5",
      "dimensions": 1024,
      "batch_size": 100
    }
  }
}
```

### 更新配置

```http
PUT /api/config
Content-Type: application/json

{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "api_key": "sk-your-api-key",
    "temperature": 0.7,
    "max_tokens": 2000
  },
  "embeddings": {
    "provider": "openai",
    "model": "text-embedding-ada-002",
    "api_key": "sk-your-api-key",
    "dimensions": 1536,
    "batch_size": 100
  }
}
```

**响应示例：**
```json
{
  "status": "success",
  "message": "配置更新成功",
  "data": {
    "config_updated": true,
    "restart_required": false
  }
}
```

### 验证配置

```http
POST /api/config/validate
Content-Type: application/json

{
  "llm": {
    "provider": "siliconflow",
    "model": "Qwen/Qwen2-7B-Instruct",
    "api_key": "your-api-key"
  }
}
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "valid": true,
    "issues": [],
    "recommendations": [
      "建议设置 timeout 参数以提高稳定性"
    ]
  }
}
```

## 模型管理 API

### 获取支持的提供商列表

```http
GET /api/models/providers
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "providers": [
      {
        "name": "openai",
        "display_name": "OpenAI",
        "supported_models": {
          "llm": ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"],
          "embeddings": ["text-embedding-ada-002", "text-embedding-3-small"]
        },
        "requires_api_key": true,
        "default_base_url": "https://api.openai.com/v1"
      },
      {
        "name": "siliconflow",
        "display_name": "SiliconFlow",
        "supported_models": {
          "llm": ["Qwen/Qwen2-7B-Instruct", "Qwen/Qwen2-72B-Instruct"],
          "embeddings": ["BAAI/bge-large-zh-v1.5", "BAAI/bge-base-zh-v1.5"]
        },
        "requires_api_key": true,
        "default_base_url": "https://api.siliconflow.cn/v1"
      }
    ]
  }
}
```

### 获取特定提供商的模型列表

```http
GET /api/models/providers/{provider_name}/models
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "provider": "siliconflow",
    "models": {
      "llm": [
        {
          "name": "Qwen/Qwen2-7B-Instruct",
          "display_name": "通义千问 2-7B",
          "description": "7B参数的中文优化对话模型",
          "max_tokens": 8192,
          "supports_streaming": true,
          "cost_per_1k_tokens": 0.001
        },
        {
          "name": "Qwen/Qwen2-72B-Instruct",
          "display_name": "通义千问 2-72B",
          "description": "72B参数的高质量对话模型",
          "max_tokens": 8192,
          "supports_streaming": true,
          "cost_per_1k_tokens": 0.01
        }
      ],
      "embeddings": [
        {
          "name": "BAAI/bge-large-zh-v1.5",
          "display_name": "BGE Large 中文 v1.5",
          "description": "1024维中文优化嵌入模型",
          "dimensions": 1024,
          "max_input_length": 512,
          "cost_per_1k_tokens": 0.0001
        }
      ]
    }
  }
}
```

### 测试模型连接

```http
POST /api/models/test
Content-Type: application/json

{
  "provider": "siliconflow",
  "model": "Qwen/Qwen2-7B-Instruct",
  "api_key": "your-api-key",
  "base_url": "https://api.siliconflow.cn/v1",
  "test_type": "llm"
}
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "connection_successful": true,
    "response_time": 1.23,
    "test_response": "测试响应内容",
    "model_info": {
      "model": "Qwen/Qwen2-7B-Instruct",
      "provider": "siliconflow",
      "version": "v1.0"
    }
  }
}
```

## 健康检查 API

### 系统健康状态

```http
GET /api/health
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "overall_status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "components": {
      "llm": {
        "status": "healthy",
        "provider": "siliconflow",
        "model": "Qwen/Qwen2-7B-Instruct",
        "response_time": 1.2,
        "last_check": "2024-01-15T10:29:45Z"
      },
      "embeddings": {
        "status": "healthy",
        "provider": "siliconflow",
        "model": "BAAI/bge-large-zh-v1.5",
        "response_time": 0.8,
        "last_check": "2024-01-15T10:29:50Z"
      },
      "vector_store": {
        "status": "healthy",
        "type": "chroma",
        "collections": 3,
        "total_documents": 1250
      },
      "database": {
        "status": "healthy",
        "type": "sqlite",
        "size": "45.2MB"
      }
    }
  }
}
```

### 详细健康检查

```http
GET /api/health/detailed
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "overall_status": "healthy",
    "checks": [
      {
        "name": "llm_connectivity",
        "status": "pass",
        "duration": 1.23,
        "details": "成功连接到 SiliconFlow API"
      },
      {
        "name": "embedding_connectivity",
        "status": "pass",
        "duration": 0.87,
        "details": "嵌入模型响应正常"
      },
      {
        "name": "vector_store_connectivity",
        "status": "pass",
        "duration": 0.15,
        "details": "向量数据库连接正常"
      },
      {
        "name": "api_rate_limits",
        "status": "pass",
        "duration": 0.05,
        "details": "API 调用频率正常"
      }
    ],
    "performance_metrics": {
      "avg_llm_response_time": 1.45,
      "avg_embedding_response_time": 0.92,
      "requests_per_minute": 25,
      "error_rate": 0.02
    }
  }
}
```

## 问答服务 API

### 发送问答请求

```http
POST /api/qa/ask
Content-Type: application/json

{
  "question": "什么是人工智能？",
  "session_id": "session_123",
  "context": {
    "max_results": 5,
    "similarity_threshold": 0.7
  },
  "model_config": {
    "temperature": 0.7,
    "max_tokens": 1000
  }
}
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "answer": "人工智能（AI）是计算机科学的一个分支...",
    "session_id": "session_123",
    "sources": [
      {
        "document_name": "AI基础知识.pdf",
        "chunk_id": "chunk_001",
        "similarity": 0.89,
        "content": "人工智能的定义和基本概念..."
      }
    ],
    "model_info": {
      "llm_provider": "siliconflow",
      "llm_model": "Qwen/Qwen2-7B-Instruct",
      "embedding_provider": "siliconflow",
      "embedding_model": "BAAI/bge-large-zh-v1.5"
    },
    "performance": {
      "total_time": 2.34,
      "retrieval_time": 0.45,
      "generation_time": 1.89
    }
  }
}
```

### 流式问答请求

```http
POST /api/qa/ask/stream
Content-Type: application/json

{
  "question": "解释机器学习的基本原理",
  "session_id": "session_123"
}
```

**响应（Server-Sent Events）：**
```
data: {"type": "start", "session_id": "session_123"}

data: {"type": "sources", "sources": [...]}

data: {"type": "token", "content": "机器"}

data: {"type": "token", "content": "学习"}

data: {"type": "token", "content": "是"}

data: {"type": "end", "performance": {...}}
```

## 嵌入服务 API

### 生成文本嵌入

```http
POST /api/embeddings/generate
Content-Type: application/json

{
  "texts": [
    "这是第一段文本",
    "这是第二段文本"
  ],
  "model_config": {
    "batch_size": 10
  }
}
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "embeddings": [
      {
        "text": "这是第一段文本",
        "embedding": [0.1, 0.2, 0.3, ...],
        "dimensions": 1024
      },
      {
        "text": "这是第二段文本",
        "embedding": [0.4, 0.5, 0.6, ...],
        "dimensions": 1024
      }
    ],
    "model_info": {
      "provider": "siliconflow",
      "model": "BAAI/bge-large-zh-v1.5",
      "dimensions": 1024
    },
    "performance": {
      "total_time": 0.89,
      "texts_processed": 2,
      "avg_time_per_text": 0.445
    }
  }
}
```

### 批量嵌入处理

```http
POST /api/embeddings/batch
Content-Type: application/json

{
  "texts": ["文本1", "文本2", ...],  // 最多1000个文本
  "batch_size": 50,
  "parallel_processing": true
}
```

## 错误处理

所有 API 端点都使用统一的错误响应格式：

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_API_KEY",
    "message": "提供的 API 密钥无效",
    "details": {
      "provider": "openai",
      "suggestion": "请检查 API 密钥是否正确设置"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 常见错误代码

| 错误代码 | 描述 | 解决方案 |
|---------|------|----------|
| `INVALID_API_KEY` | API 密钥无效 | 检查并更新 API 密钥 |
| `MODEL_NOT_FOUND` | 模型不存在 | 检查模型名称是否正确 |
| `PROVIDER_UNAVAILABLE` | 提供商服务不可用 | 检查网络连接或切换提供商 |
| `RATE_LIMIT_EXCEEDED` | 超出 API 调用限制 | 降低请求频率或升级 API 计划 |
| `INVALID_CONFIG` | 配置格式错误 | 检查配置文件格式 |
| `DIMENSION_MISMATCH` | 嵌入维度不匹配 | 确保嵌入模型维度与向量数据库一致 |
| `TIMEOUT_ERROR` | 请求超时 | 增加超时设置或检查网络 |
| `INSUFFICIENT_QUOTA` | API 配额不足 | 检查 API 使用量或充值 |

## 认证和安全

### API 密钥认证

大多数端点需要在请求头中包含认证信息：

```http
Authorization: Bearer your-rag-system-api-key
```

### 请求限制

- 每分钟最多 100 个请求
- 每小时最多 5000 个请求
- 单次请求最大 10MB
- 批量嵌入最多 1000 个文本

## SDK 和客户端库

### Python 客户端示例

```python
import requests
import json

class RAGClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def ask_question(self, question, session_id=None):
        """发送问答请求"""
        data = {
            'question': question,
            'session_id': session_id
        }
        response = requests.post(
            f'{self.base_url}/api/qa/ask',
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def update_config(self, config):
        """更新系统配置"""
        response = requests.put(
            f'{self.base_url}/api/config',
            headers=self.headers,
            json=config
        )
        return response.json()
    
    def check_health(self):
        """检查系统健康状态"""
        response = requests.get(
            f'{self.base_url}/api/health',
            headers=self.headers
        )
        return response.json()

# 使用示例
client = RAGClient('http://localhost:8000', 'your-api-key')

# 发送问答请求
result = client.ask_question('什么是机器学习？')
print(result['data']['answer'])

# 更新配置
new_config = {
    'llm': {
        'provider': 'openai',
        'model': 'gpt-4',
        'api_key': 'sk-your-key'
    }
}
client.update_config(new_config)

# 检查健康状态
health = client.check_health()
print(f"系统状态: {health['data']['overall_status']}")
```

### JavaScript 客户端示例

```javascript
class RAGClient {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async askQuestion(question, sessionId = null) {
        const response = await fetch(`${this.baseUrl}/api/qa/ask`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                question: question,
                session_id: sessionId
            })
        });
        return await response.json();
    }
    
    async updateConfig(config) {
        const response = await fetch(`${this.baseUrl}/api/config`, {
            method: 'PUT',
            headers: this.headers,
            body: JSON.stringify(config)
        });
        return await response.json();
    }
    
    async checkHealth() {
        const response = await fetch(`${this.baseUrl}/api/health`, {
            headers: this.headers
        });
        return await response.json();
    }
}

// 使用示例
const client = new RAGClient('http://localhost:8000', 'your-api-key');

// 发送问答请求
client.askQuestion('什么是深度学习？')
    .then(result => {
        console.log('回答:', result.data.answer);
    })
    .catch(error => {
        console.error('错误:', error);
    });
```

## 最佳实践

### 1. 配置管理
- 使用环境变量存储敏感信息
- 定期验证配置的有效性
- 实施配置版本控制

### 2. 错误处理
- 实现重试机制
- 记录详细的错误日志
- 提供用户友好的错误消息

### 3. 性能优化
- 使用批量处理减少 API 调用
- 实施请求缓存
- 监控 API 响应时间

### 4. 安全性
- 定期轮换 API 密钥
- 实施请求限制
- 验证输入数据

### 5. 监控和日志
- 监控 API 使用量和成本
- 记录关键操作日志
- 设置告警机制

## 故障排除

### 常见问题

1. **连接超时**
   - 检查网络连接
   - 增加超时设置
   - 验证 API 端点 URL

2. **认证失败**
   - 检查 API 密钥是否正确
   - 确认密钥权限
   - 检查密钥是否过期

3. **模型不可用**
   - 检查模型名称拼写
   - 确认提供商支持该模型
   - 检查 API 配额

4. **响应格式错误**
   - 检查 API 版本兼容性
   - 验证请求参数格式
   - 查看详细错误信息

### 调试技巧

1. 启用详细日志记录
2. 使用健康检查 API 诊断问题
3. 测试单个组件的连接性
4. 检查系统资源使用情况
5. 查看 API 提供商的状态页面

这个 API 指南提供了完整的接口文档和使用示例，帮助开发者快速集成和使用多平台模型支持功能。