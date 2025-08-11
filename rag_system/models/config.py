"""
配置相关数据模型
"""
import json
import yaml
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any, Union
from pathlib import Path


@dataclass
class DatabaseConfig:
    """数据库配置"""
    url: str = "sqlite:///./database/rag_system.db"
    echo: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DatabaseConfig':
        """从字典创建实例"""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if not self.url:
            errors.append("数据库URL不能为空")
        
        # 验证SQLite路径
        if self.url and self.url.startswith("sqlite:///"):
            db_path = self.url.replace("sqlite:///", "")
            if db_path != ":memory:":
                db_dir = Path(db_path).parent
                if not db_dir.exists():
                    try:
                        db_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        errors.append(f"无法创建数据库目录: {str(e)}")
        
        return errors


@dataclass
class VectorStoreConfig:
    """向量存储配置"""
    type: str = "chroma"
    persist_directory: str = "./chroma_db"
    collection_name: str = "knowledge_base"
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorStoreConfig':
        """从字典创建实例"""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        supported_types = ["chroma", "pinecone", "faiss"]
        if self.type not in supported_types:
            errors.append(f"不支持的向量存储类型: {self.type}. 支持的类型: {', '.join(supported_types)}")
        
        # 验证Pinecone配置
        if self.type == "pinecone":
            if not self.pinecone_api_key:
                errors.append("Pinecone向量存储需要API密钥")
            if not self.pinecone_environment:
                errors.append("Pinecone向量存储需要环境配置")
            if not self.pinecone_index_name:
                errors.append("Pinecone向量存储需要索引名称")
        
        # 验证Chroma配置
        if self.type == "chroma":
            if self.persist_directory:
                persist_path = Path(self.persist_directory)
                if persist_path.exists() and not persist_path.is_dir():
                    errors.append(f"Chroma持久化路径不是目录: {self.persist_directory}")
        
        return errors


@dataclass
class EmbeddingsConfig:
    """嵌入模型配置"""
    provider: str = "openai"
    model: str = "text-embedding-ada-002"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    batch_size: int = 100
    dimensions: Optional[int] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60
    retry_attempts: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingsConfig':
        """从字典创建实例"""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证提供商
        supported_providers = ["openai", "siliconflow", "modelscope", "deepseek", "ollama", "mock"]
        if self.provider not in supported_providers:
            errors.append(f"不支持的嵌入模型提供商: {self.provider}. 支持的提供商: {', '.join(supported_providers)}")
        
        # 验证分块大小
        if self.chunk_size <= 0:
            errors.append("文档分块大小必须大于0")
        
        # 验证分块重叠
        if self.chunk_overlap < 0:
            errors.append("文档分块重叠不能为负数")
        
        # 验证分块重叠不能大于分块大小
        if self.chunk_overlap >= self.chunk_size:
            errors.append("文档分块重叠不能大于或等于分块大小")
        
        # 验证批处理大小
        if self.batch_size <= 0:
            errors.append("批处理大小必须大于0")
        
        # 验证超时时间
        if self.timeout <= 0:
            errors.append("超时时间必须大于0")
        
        # 验证重试次数
        if self.retry_attempts < 0:
            errors.append("重试次数不能为负数")
        
        # 验证维度
        if self.dimensions is not None and self.dimensions <= 0:
            errors.append("嵌入向量维度必须大于0")
        
        return errors


@dataclass
class LLMConfig:
    """大语言模型配置"""
    provider: str = "openai"
    model: str = "gpt-4"
    temperature: float = 0.1
    max_tokens: int = 1000
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 60
    retry_attempts: int = 3
    stream: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """从字典创建实例"""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证提供商
        supported_providers = ["openai", "siliconflow", "modelscope", "deepseek", "ollama", "mock"]
        if self.provider not in supported_providers:
            errors.append(f"不支持的LLM提供商: {self.provider}. 支持的提供商: {', '.join(supported_providers)}")
        
        # 验证模型名称
        if not self.model and self.provider != "mock":
            errors.append("LLM模型名称不能为空")
        
        # 验证温度参数
        if self.temperature < 0 or self.temperature > 2:
            errors.append("LLM温度参数必须在0-2之间")
        
        # 验证最大令牌数
        if self.max_tokens <= 0:
            errors.append("LLM最大令牌数必须大于0")
        
        # 验证超时时间
        if self.timeout <= 0:
            errors.append("超时时间必须大于0")
        
        # 验证重试次数
        if self.retry_attempts < 0:
            errors.append("重试次数不能为负数")
        
        return errors


@dataclass
class RetrievalConfig:
    """检索配置"""
    top_k: int = 5
    similarity_threshold: float = 0.7
    search_mode: str = "semantic"
    enable_rerank: bool = False
    enable_cache: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetrievalConfig':
        """从字典创建实例"""
        # 过滤掉不支持的字段，保持向后兼容
        supported_fields = {'top_k', 'similarity_threshold', 'search_mode', 'enable_rerank', 'enable_cache'}
        filtered_data = {k: v for k, v in data.items() if k in supported_fields}
        return cls(**filtered_data)
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.top_k <= 0:
            errors.append("检索数量必须大于0")
        
        if self.similarity_threshold < 0 or self.similarity_threshold > 1:
            errors.append("相似度阈值必须在0-1之间")
        
        # 验证搜索模式
        valid_search_modes = ["semantic", "keyword", "hybrid"]
        if self.search_mode not in valid_search_modes:
            errors.append(f"无效的搜索模式: {self.search_mode}. 支持的模式: {', '.join(valid_search_modes)}")
        
        return errors


@dataclass
class RerankingConfig:
    """重排序模型配置"""
    provider: str = "sentence_transformers"
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    model_name: Optional[str] = None
    batch_size: int = 32
    max_length: int = 512
    timeout: float = 30.0
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RerankingConfig':
        """从字典创建实例"""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        # 验证提供商
        supported_providers = ["sentence_transformers", "siliconflow", "openai", "mock"]
        if self.provider not in supported_providers:
            errors.append(f"不支持的重排序提供商: {self.provider}. 支持的提供商: {', '.join(supported_providers)}")
        
        # 验证模型名称
        if not self.model and self.provider != "mock":
            errors.append("重排序模型名称不能为空")
        
        # 验证批处理大小
        if self.batch_size <= 0:
            errors.append("批处理大小必须大于0")
        
        # 验证最大长度
        if self.max_length <= 0:
            errors.append("最大文本长度必须大于0")
        
        # 验证超时时间
        if self.timeout <= 0:
            errors.append("超时时间必须大于0")
        
        return errors


@dataclass
class APIConfig:
    """API配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: List[str] = field(default_factory=lambda: ["http://localhost:3000"])
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIConfig':
        """从字典创建实例"""
        return cls(**data)
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.port <= 0 or self.port > 65535:
            errors.append("端口号必须在1-65535之间")
        
        if not self.host:
            errors.append("主机地址不能为空")
        
        return errors


@dataclass
class AppConfig:
    """应用配置"""
    name: str = "RAG Knowledge QA System"
    version: str = "1.0.0"
    debug: bool = False
    database: DatabaseConfig = None
    vector_store: VectorStoreConfig = None
    embeddings: EmbeddingsConfig = None
    llm: LLMConfig = None
    retrieval: RetrievalConfig = None
    reranking: RerankingConfig = None
    api: APIConfig = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfig':
        """从字典创建实例"""
        # 处理嵌套配置对象
        config_data = data.copy()
        
        if 'database' in config_data and config_data['database']:
            config_data['database'] = DatabaseConfig.from_dict(config_data['database'])
        
        if 'vector_store' in config_data and config_data['vector_store']:
            config_data['vector_store'] = VectorStoreConfig.from_dict(config_data['vector_store'])
        
        if 'embeddings' in config_data and config_data['embeddings']:
            config_data['embeddings'] = EmbeddingsConfig.from_dict(config_data['embeddings'])
        
        if 'llm' in config_data and config_data['llm']:
            config_data['llm'] = LLMConfig.from_dict(config_data['llm'])
        
        if 'retrieval' in config_data and config_data['retrieval']:
            config_data['retrieval'] = RetrievalConfig.from_dict(config_data['retrieval'])
        
        if 'reranking' in config_data and config_data['reranking']:
            config_data['reranking'] = RerankingConfig.from_dict(config_data['reranking'])
        
        if 'api' in config_data and config_data['api']:
            config_data['api'] = APIConfig.from_dict(config_data['api'])
        
        return cls(**config_data)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AppConfig':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def to_yaml(self) -> str:
        """转换为YAML字符串"""
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'AppConfig':
        """从YAML字符串创建实例"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
    
    def save_to_file(self, file_path: str, format: str = 'yaml') -> None:
        """保存配置到文件"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'json':
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.to_json())
        elif format.lower() == 'yaml':
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.to_yaml())
        else:
            raise ValueError(f"不支持的格式: {format}. 支持的格式: json, yaml")
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'AppConfig':
        """从文件加载配置"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 根据文件扩展名确定格式
        if path.suffix.lower() in ['.yaml', '.yml']:
            return cls.from_yaml(content)
        elif path.suffix.lower() == '.json':
            return cls.from_json(content)
        else:
            # 尝试YAML格式
            try:
                return cls.from_yaml(content)
            except yaml.YAMLError:
                # 如果YAML失败，尝试JSON
                return cls.from_json(content)
    
    def validate(self) -> List[str]:
        """验证整个配置"""
        errors = []
        
        # 验证应用基本信息
        if not self.name:
            errors.append("应用名称不能为空")
        
        if not self.version:
            errors.append("应用版本不能为空")
        
        # 验证各个子配置
        if self.database:
            errors.extend([f"数据库配置: {error}" for error in self.database.validate()])
        
        if self.vector_store:
            errors.extend([f"向量存储配置: {error}" for error in self.vector_store.validate()])
        
        if self.embeddings:
            errors.extend([f"嵌入模型配置: {error}" for error in self.embeddings.validate()])
        
        if self.llm:
            errors.extend([f"LLM配置: {error}" for error in self.llm.validate()])
        
        if self.retrieval:
            errors.extend([f"检索配置: {error}" for error in self.retrieval.validate()])
        
        if self.reranking:
            errors.extend([f"重排序配置: {error}" for error in self.reranking.validate()])
        
        if self.api:
            errors.extend([f"API配置: {error}" for error in self.api.validate()])
        
        return errors
    
    def get_default_config(self) -> 'AppConfig':
        """获取默认配置"""
        return AppConfig(
            name="RAG Knowledge QA System",
            version="1.0.0",
            debug=False,
            database=DatabaseConfig(),
            vector_store=VectorStoreConfig(),
            embeddings=EmbeddingsConfig(),
            llm=LLMConfig(),
            retrieval=RetrievalConfig(),
            reranking=RerankingConfig(),
            api=APIConfig()
        )