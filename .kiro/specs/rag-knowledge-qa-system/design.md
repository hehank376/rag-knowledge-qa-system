# 设计文档

## 概述

本文档描述了基于LangChain的RAG知识库问答系统的技术设计。系统采用模块化架构，包含文档处理、向量存储、检索生成和用户界面等核心模块。系统支持多种文档格式，使用向量数据库进行语义检索，并结合大语言模型生成准确的答案。

## 架构

### 系统架构图

```mermaid
graph TB
    A[用户界面] --> B[API网关]
    B --> C[文档管理服务]
    B --> D[问答服务]
    B --> E[会话管理服务]
    
    C --> F[文档处理器]
    F --> G[文本提取器]
    F --> H[文本分割器]
    F --> I[向量化器]
    
    I --> J[向量数据库]
    D --> J
    D --> K[大语言模型]
    
    C --> L[文档存储]
    E --> M[会话存储]
    
    N[配置管理] --> D
    N --> I
```

### 技术栈

- **后端框架**: FastAPI (Python)
- **向量数据库**: Chroma
- **嵌入模型**: Siliconflow Qwen3-Embedding
- **大语言模型**: Siliconflow DeepSeek-V3 或本地ollama模型
- **文档处理**: LangChain Document Loaders
- **前端**: React + TypeScript
- **数据库**: SQLite (开发) / PostgreSQL (生产)

## 组件和接口

### 1. 文档管理服务 (DocumentService)

**职责**: 处理文档上传、存储和管理

**核心接口**:
```python
class DocumentService:
    async def upload_document(self, file: UploadFile) -> DocumentInfo
    async def delete_document(self, doc_id: str) -> bool
    async def list_documents(self) -> List[DocumentInfo]
    async def get_document(self, doc_id: str) -> DocumentInfo
```

**依赖组件**:
- DocumentProcessor: 文档处理
- DocumentStorage: 文档存储

### 2. 文档处理器 (DocumentProcessor)

**职责**: 文档内容提取、分割和向量化

**核心接口**:
```python
class DocumentProcessor:
    async def process_document(self, file_path: str) -> ProcessResult
    def extract_text(self, file_path: str) -> str
    def split_text(self, text: str) -> List[TextChunk]
    async def vectorize_chunks(self, chunks: List[TextChunk]) -> List[Vector]
```

**支持的文档格式**:
- PDF: PyPDF2 / pdfplumber
- DOCX: python-docx
- TXT: 直接读取
- MD: markdown解析

### 3. 向量存储服务 (VectorStore)

**职责**: 向量的存储、检索和管理

**核心接口**:
```python
class VectorStore:
    async def add_vectors(self, vectors: List[Vector], metadata: List[dict]) -> bool
    async def search_similar(self, query_vector: Vector, top_k: int) -> List[SearchResult]
    async def delete_vectors(self, doc_id: str) -> bool
    async def update_vectors(self, doc_id: str, vectors: List[Vector]) -> bool
```

### 4. 问答服务 (QAService)

**职责**: 处理用户问题，执行检索和生成答案

**核心接口**:
```python
class QAService:
    async def answer_question(self, question: str, session_id: str) -> QAResponse
    async def vectorize_question(self, question: str) -> Vector
    async def retrieve_context(self, query_vector: Vector) -> List[Context]
    async def generate_answer(self, question: str, context: List[Context]) -> str
```

### 5. 会话管理服务 (SessionService)

**职责**: 管理用户会话和历史记录

**核心接口**:
```python
class SessionService:
    async def create_session(self) -> str
    async def save_qa_pair(self, session_id: str, question: str, answer: str) -> bool
    async def get_session_history(self, session_id: str) -> List[QAPair]
    async def delete_session(self, session_id: str) -> bool
```

## 数据模型

### 文档模型
```python
@dataclass
class DocumentInfo:
    id: str
    filename: str
    file_type: str
    file_size: int
    upload_time: datetime
    status: DocumentStatus  # PROCESSING, READY, ERROR
    chunk_count: int
    
@dataclass
class TextChunk:
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: dict
```

### 向量模型
```python
@dataclass
class Vector:
    id: str
    document_id: str
    chunk_id: str
    embedding: List[float]
    metadata: dict

@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    content: str
    similarity_score: float
    metadata: dict
```

### 问答模型
```python
@dataclass
class QAResponse:
    answer: str
    sources: List[SourceInfo]
    confidence_score: float
    processing_time: float

@dataclass
class SourceInfo:
    document_name: str
    chunk_content: str
    similarity_score: float
```

### 会话模型
```python
@dataclass
class QAPair:
    id: str
    session_id: str
    question: str
    answer: str
    sources: List[SourceInfo]
    timestamp: datetime

@dataclass
class Session:
    id: str
    created_at: datetime
    last_activity: datetime
    qa_count: int
```

## 错误处理

### 错误类型定义
```python
class DocumentError(Exception):
    """文档处理相关错误"""
    pass

class VectorStoreError(Exception):
    """向量存储相关错误"""
    pass

class QAError(Exception):
    """问答处理相关错误"""
    pass

class ConfigurationError(Exception):
    """配置相关错误"""
    pass
```

### 错误处理策略

1. **文档处理错误**:
   - 文件格式不支持: 返回明确错误信息
   - 文件损坏: 记录错误日志，通知用户
   - 处理超时: 异步处理，状态更新

2. **向量存储错误**:
   - 连接失败: 重试机制，降级处理
   - 存储空间不足: 清理策略，用户通知
   - 查询超时: 缓存机制，默认结果

3. **问答错误**:
   - 模型调用失败: 重试机制，备用模型
   - 无相关内容: 友好提示，建议操作
   - 生成超时: 流式响应，部分结果

## 测试策略

### 单元测试
- 各服务类的核心方法测试
- 数据模型验证测试
- 错误处理逻辑测试
- 覆盖率目标: 80%+

### 集成测试
- 文档上传到向量化的完整流程
- 问答的端到端流程
- 数据库操作集成测试
- API接口集成测试

### 性能测试
- 文档处理性能测试
- 向量检索性能测试
- 并发用户问答测试
- 内存和CPU使用监控

### 测试数据
- 准备多种格式的测试文档
- 构建标准问答对数据集
- 性能测试基准数据
- 边界条件测试用例

## 配置管理

### 配置文件结构
```yaml
# config.yaml
app:
  name: "RAG Knowledge QA System"
  version: "1.0.0"
  debug: false

database:
  url: "sqlite:///./database/rag_system.db"
  echo: false

vector_store:
  type: "chroma"  # chroma, pinecone
  persist_directory: "./chroma_db"
  collection_name: "knowledge_base"

embeddings:
  provider: "openai"  # openai, huggingface
  model: "text-embedding-ada-002"
  chunk_size: 1000
  chunk_overlap: 200

llm:
  provider: "openai"  # openai, huggingface
  model: "gpt-4"
  temperature: 0.1
  max_tokens: 1000

retrieval:
  top_k: 5
  similarity_threshold: 0.7

api:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["http://localhost:3000"]
```

### 环境变量
```bash
# .env
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_pinecone_env
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

## 部署架构

### 开发环境
- Docker Compose 本地部署
- SQLite 数据库
- Chroma 向量数据库
- 本地文件存储

### 生产环境
- Kubernetes 集群部署
- PostgreSQL 数据库
- Pinecone 向量数据库
- 云存储服务 (AWS S3/阿里云OSS)
- Redis 缓存
- Nginx 负载均衡

### 监控和日志
- Prometheus + Grafana 监控
- ELK Stack 日志收集
- 健康检查端点
- 性能指标收集