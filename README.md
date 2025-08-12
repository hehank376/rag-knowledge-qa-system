# RAG Knowledge QA System

基于RAG的检索增强生成知识库问答系统

## 项目结构

```
rag_system/
├── api/                    # API接口层
├── config/                 # 配置管理
│   ├── __init__.py
│   └── loader.py          # 配置加载器
├── models/                 # 数据模型
│   ├── __init__.py
│   ├── config.py          # 配置模型
│   ├── document.py        # 文档模型
│   ├── qa.py             # 问答模型
│   └── vector.py         # 向量模型
├── services/              # 业务服务层
│   ├── __init__.py
│   ├── base.py           # 基础服务接口
│   ├── document_processor.py  # 文档处理服务
│   ├── document_service.py    # 文档管理服务
│   ├── qa_service.py          # 问答服务
│   ├── session_service.py     # 会话管理服务
│   └── vector_service.py      # 向量存储服务
├── utils/                 # 工具模块
│   ├── __init__.py
│   ├── exceptions.py     # 自定义异常
│   └── helpers.py        # 工具函数
└── __init__.py
```
## 系统截图
<img width="3056" height="1668" alt="image" src="https://github.com/user-attachments/assets/81684f41-ba69-42cc-b7a3-d9e73b1fbccc" />
<img width="3056" height="1668" alt="image" src="https://github.com/user-attachments/assets/75b9bd51-8d45-403f-8cf0-e7916385a5ff" />
<img width="3056" height="1668" alt="image" src="https://github.com/user-attachments/assets/8ef7c66c-884d-4a41-9aed-c25fea0910b1" />
<img width="3056" height="1668" alt="image" src="https://github.com/user-attachments/assets/ef115597-465b-4833-be97-56c387ba3dd7" />


## 安装

1. 克隆项目
```bash
git clone <repository-url>
cd rag-knowledge-qa-system
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入实际的API密钥
```

4. 配置系统
```bash
# 编辑 config.yaml 文件，根据需要调整配置
```

## 核心功能

- 📄 文档上传和处理（支持PDF、Word、Markdown等格式）
- 🔍 智能文档检索和向量化存储
- 💬 基于上下文的问答对话
- 📊 会话管理和历史记录
- ⚙️ 灵活的配置管理系统

## 技术栈

- **Web框架**: FastAPI
- **向量数据库**: ChromaDB
- **AI框架**: LangChain
- **数据库**: SQLAlchemy + SQLite
- **文档处理**: PyPDF2, python-docx
- **配置管理**: YAML + 环境变量

## 开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
pytest

# 代码格式化
black rag_system/

# 类型检查
mypy rag_system/
```

## 许可证

MIT License
