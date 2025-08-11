"""
配置加载器
"""
import os
import re
import yaml
import logging
from typing import Dict, Any, Optional, Union, List
from pathlib import Path

from ..models.config import (
    AppConfig, DatabaseConfig, VectorStoreConfig, 
    EmbeddingsConfig, LLMConfig, RetrievalConfig, RerankingConfig, APIConfig
)
from ..utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器"""
    
    # 环境变量替换模式
    ENV_VAR_PATTERN = re.compile(r'\$\{([^}]+)\}')
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_config_path()
        print(f'获取的配置文件：{config_path}')
        print(f'获取的配置文件：{self.config_path}')
        self._validation_errors: List[str] = []
    
    def _get_config_path(self) -> str:
        """获取配置文件路径"""
        environment = os.getenv("ENVIRONMENT", "development")
        config_dir = Path("config")
        config_file = config_dir / f"{environment}.yaml"
        
        if config_file.exists():
            return str(config_file)
        
        # 回退到开发配置
        dev_config = config_dir / "development.yaml"
        if dev_config.exists():
            return str(dev_config)
        
        # 回退到默认配置文件
        return "config.yaml"
    
    def load_config(self) -> AppConfig:
        """加载配置"""
        try:
            # 加载YAML配置文件
            config_data = self._load_yaml_config()
            
            # 加载环境变量
            env_data = self._load_env_config()
            
            # 合并配置
            merged_config = self._merge_configs(config_data, env_data)
            
            # 创建配置对象
            return self._create_app_config(merged_config)
            
        except Exception as e:
            raise ConfigurationError(f"配置加载失败: {str(e)}")
    
    def _load_yaml_config(self) -> Dict[str, Any]:
        """加载YAML配置文件"""
        config_file = Path(self.config_path)
        
        if not config_file.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            return {}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 替换环境变量
                content = self._replace_env_variables(content)
                return yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML配置文件解析错误: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"配置文件读取错误: {str(e)}")
    
    def _replace_env_variables(self, content: str) -> str:
        """替换配置文件中的环境变量"""
        def replace_var(match):
            var_expr = match.group(1)
            # 支持默认值语法: ${VAR_NAME:default_value}
            if ':' in var_expr:
                var_name, default_value = var_expr.split(':', 1)
                return os.getenv(var_name.strip(), default_value.strip())
            else:
                var_name = var_expr.strip()
                value = os.getenv(var_name)
                if value is None:
                    logger.warning(f"环境变量 {var_name} 未设置")
                    return f"${{{var_name}}}"  # 保持原样
                return value
        
        return self.ENV_VAR_PATTERN.sub(replace_var, content)
    
    def _load_env_config(self) -> Dict[str, Any]:
        """加载环境变量配置"""
        return {
            # 数据库配置
            "database_url": os.getenv("DATABASE_URL"),
            
            # API密钥配置
            "openai_api_key": os.getenv("OPENAI_API_KEY"),
            "siliconflow_api_key": os.getenv("SILICONFLOW_API_KEY"),
            "modelscope_api_key": os.getenv("MODELSCOPE_API_KEY"),
            "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY"),
            
            # 向量存储配置
            "pinecone_api_key": os.getenv("PINECONE_API_KEY"),
            "pinecone_environment": os.getenv("PINECONE_ENVIRONMENT"),
            
            # Ollama配置
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            
            # 应用配置
            "app_debug": os.getenv("APP_DEBUG", "false").lower() == "true",
            "app_environment": os.getenv("ENVIRONMENT", "development"),
        }
    
    def _merge_configs(self, yaml_config: Dict[str, Any], env_config: Dict[str, Any]) -> Dict[str, Any]:
        """合并配置"""
        # 环境变量优先级更高
        merged = yaml_config.copy()
        
        # 合并应用配置（只有环境变量明确设置时才覆盖）
        if "app" not in merged:
            merged["app"] = {}
        # 只有环境变量明确设置了APP_DEBUG时才覆盖
        if os.getenv("APP_DEBUG") is not None:
            merged["app"]["debug"] = env_config["app_debug"]
        if env_config.get("app_environment"):
            merged["app"]["environment"] = env_config["app_environment"]
        
        # 合并数据库配置
        if env_config.get("database_url"):
            if "database" not in merged:
                merged["database"] = {}
            merged["database"]["url"] = env_config["database_url"]
        
        # 合并向量存储配置
        if env_config.get("pinecone_api_key") or env_config.get("pinecone_environment"):
            if "vector_store" not in merged:
                merged["vector_store"] = {}
            if env_config.get("pinecone_api_key"):
                merged["vector_store"]["pinecone_api_key"] = env_config["pinecone_api_key"]
            if env_config.get("pinecone_environment"):
                merged["vector_store"]["pinecone_environment"] = env_config["pinecone_environment"]
        
        # 合并Ollama配置
        if env_config.get("ollama_base_url"):
            if "ollama" not in merged:
                merged["ollama"] = {}
            merged["ollama"]["base_url"] = env_config["ollama_base_url"]
        
        # 添加API密钥
        merged["api_keys"] = {
            "openai": env_config.get("openai_api_key"),
            "siliconflow": env_config.get("siliconflow_api_key"),
            "modelscope": env_config.get("modelscope_api_key"),
            "deepseek": env_config.get("deepseek_api_key"),
            "pinecone": env_config.get("pinecone_api_key"),
        }
        
        return merged
    
    def _create_app_config(self, config_data: Dict[str, Any]) -> AppConfig:
        """创建应用配置对象"""
        # 重置验证错误
        self._validation_errors = []
        
        app_data = config_data.get("app", {})
        
        # 验证配置
        self._validate_config(config_data)
        
        # 如果有验证错误，抛出异常
        if self._validation_errors:
            error_msg = "配置验证失败:\n" + "\n".join(f"- {error}" for error in self._validation_errors)
            raise ConfigurationError(error_msg)
        
        return AppConfig(
            name=app_data.get("name", "RAG Knowledge QA System"),
            version=app_data.get("version", "1.0.0"),
            debug=app_data.get("debug", False),
            database=self._create_database_config(config_data.get("database", {})),
            vector_store=self._create_vector_store_config(config_data.get("vector_store", config_data.get("vector_db", {}))),
            embeddings=self._create_embeddings_config(config_data.get("embeddings", config_data.get("embedding", {}))),
            llm=self._create_llm_config(config_data.get("llm", {})),
            retrieval=self._create_retrieval_config(config_data.get("retrieval", {})),
            reranking=self._create_reranking_config(config_data.get("reranking", {})),
            api=self._create_api_config(config_data.get("api", {}))
        )
    
    def _validate_config(self, config_data: Dict[str, Any]) -> None:
        """验证配置"""
        # 验证LLM配置
        llm_config = config_data.get("llm", {})
        self._validate_llm_config(llm_config, config_data.get("api_keys", {}))
        
        # 验证嵌入模型配置（支持embedding和embeddings两种配置节名称）
        embeddings_config = config_data.get("embeddings", config_data.get("embedding", {}))
        self._validate_embeddings_config(embeddings_config, config_data.get("api_keys", {}))
        
        # 验证向量存储配置（支持vector_store和vector_db两种配置节名称）
        vector_store_config = config_data.get("vector_store", config_data.get("vector_db", {}))
        self._validate_vector_store_config(vector_store_config, config_data.get("api_keys", {}))
        
        # 验证数据库配置
        database_config = config_data.get("database", {})
        self._validate_database_config(database_config)
    
    def _validate_llm_config(self, llm_config: Dict[str, Any], api_keys: Dict[str, Any]) -> None:
        """验证LLM配置"""
        provider = llm_config.get("provider", "openai")
        
        # 验证提供商
        supported_providers = ["openai", "siliconflow", "modelscope", "deepseek", "ollama", "mock"]
        if provider not in supported_providers:
            self._validation_errors.append(
                f"不支持的LLM提供商: {provider}. 支持的提供商: {', '.join(supported_providers)}"
            )
        
        # 验证API密钥
        if provider in ["openai", "siliconflow", "modelscope", "deepseek"]:
            api_key = api_keys.get(provider)
            if not api_key:
                self._validation_errors.append(f"LLM提供商 {provider} 需要API密钥")
        
        # 验证模型名称（使用默认值进行验证）
        model = llm_config.get("model", "gpt-4")  # 使用默认值
        if not model and provider != "mock":
            self._validation_errors.append("LLM模型名称不能为空")
        
        # 验证温度参数
        temperature = llm_config.get("temperature")
        if temperature is not None and (temperature < 0 or temperature > 2):
            self._validation_errors.append("LLM温度参数必须在0-2之间")
        
        # 验证最大令牌数
        max_tokens = llm_config.get("max_tokens")
        if max_tokens is not None and max_tokens <= 0:
            self._validation_errors.append("LLM最大令牌数必须大于0")
    
    def _validate_embeddings_config(self, embeddings_config: Dict[str, Any], api_keys: Dict[str, Any]) -> None:
        """验证嵌入模型配置"""
        provider = embeddings_config.get("provider", "openai")
        
        # 验证提供商
        supported_providers = ["openai", "siliconflow", "modelscope", "deepseek", "ollama", "mock"]
        if provider not in supported_providers:
            self._validation_errors.append(
                f"不支持的嵌入模型提供商: {provider}. 支持的提供商: {', '.join(supported_providers)}"
            )
        
        # 验证API密钥
        if provider in ["openai", "siliconflow", "modelscope", "deepseek"]:
            api_key = api_keys.get(provider)
            if not api_key:
                self._validation_errors.append(f"嵌入模型提供商 {provider} 需要API密钥")
        
        # 验证分块大小
        chunk_size = embeddings_config.get("chunk_size")
        if chunk_size is not None and chunk_size <= 0:
            self._validation_errors.append("文档分块大小必须大于0")
        
        # 验证分块重叠
        chunk_overlap = embeddings_config.get("chunk_overlap")
        if chunk_overlap is not None and chunk_overlap < 0:
            self._validation_errors.append("文档分块重叠不能为负数")
        
        # 验证分块重叠不能大于分块大小
        if chunk_size and chunk_overlap and chunk_overlap >= chunk_size:
            self._validation_errors.append("文档分块重叠不能大于或等于分块大小")
    
    def _validate_vector_store_config(self, vector_store_config: Dict[str, Any], api_keys: Dict[str, Any]) -> None:
        """验证向量存储配置"""
        store_type = vector_store_config.get("type", "chroma")
        
        # 验证存储类型
        supported_types = ["chroma", "pinecone", "faiss"]
        if store_type not in supported_types:
            self._validation_errors.append(
                f"不支持的向量存储类型: {store_type}. 支持的类型: {', '.join(supported_types)}"
            )
        
        # 验证Pinecone配置
        if store_type == "pinecone":
            if not api_keys.get("pinecone"):
                self._validation_errors.append("Pinecone向量存储需要API密钥")
            
            environment = vector_store_config.get("pinecone_environment")
            if not environment:
                self._validation_errors.append("Pinecone向量存储需要环境配置")
        
        # 验证Chroma配置
        if store_type == "chroma":
            persist_dir = vector_store_config.get("persist_directory")
            if persist_dir:
                persist_path = Path(persist_dir)
                if persist_path.exists() and not persist_path.is_dir():
                    self._validation_errors.append(f"Chroma持久化路径不是目录: {persist_dir}")
    
    def _validate_database_config(self, database_config: Dict[str, Any]) -> None:
        """验证数据库配置"""
        url = database_config.get("url")
        # 如果没有提供URL，使用默认的SQLite数据库
        if not url:
            # 不报错，使用默认值
            return
        
        # 验证SQLite路径
        if url and url.startswith("sqlite:///"):
            db_path = url.replace("sqlite:///", "")
            if db_path != ":memory:":
                db_dir = Path(db_path).parent
                if not db_dir.exists():
                    try:
                        db_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        self._validation_errors.append(f"无法创建数据库目录: {str(e)}")
    
    def get_validation_errors(self) -> List[str]:
        """获取验证错误列表"""
        return self._validation_errors.copy()
    
    def validate_config_file(self, config_path: Optional[str] = None) -> List[str]:
        """验证配置文件并返回错误列表"""
        old_path = self.config_path
        if config_path:
            self.config_path = config_path
        
        try:
            self.load_config()
            return []
        except ConfigurationError as e:
            return [str(e)]
        except Exception as e:
            return [f"配置验证失败: {str(e)}"]
        finally:
            self.config_path = old_path
    
    def _create_database_config(self, data: Dict[str, Any]) -> DatabaseConfig:
        """创建数据库配置"""
        return DatabaseConfig(
            url=data.get("url", "sqlite:///./database/rag_system.db"),
            echo=data.get("echo", False)
        )
    
    def _create_vector_store_config(self, data: Dict[str, Any]) -> VectorStoreConfig:
        """创建向量存储配置"""
        # 支持不同的字段名映射
        store_type = data.get("type", "chroma")
        persist_dir = data.get("persist_directory", data.get("host", "./chroma_db"))
        collection_name = data.get("collection_name", "knowledge_base")
        
        # 如果persist_dir看起来像主机名，则使用默认目录
        if persist_dir and persist_dir.startswith("localhost"):
            persist_dir = "./chroma_db"
        
        return VectorStoreConfig(
            type=store_type,
            persist_directory=persist_dir,
            collection_name=collection_name
        )
    
    def _create_embeddings_config(self, data: Dict[str, Any]) -> EmbeddingsConfig:
        """创建嵌入配置"""
        return EmbeddingsConfig(
            provider=data.get("provider", "openai"),
            model=data.get("model", "text-embedding-ada-002"),
            chunk_size=data.get("chunk_size", 1000),
            chunk_overlap=data.get("chunk_overlap", 200),
            batch_size=data.get("batch_size", 100),
            dimensions=data.get("dimensions"),
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            timeout=data.get("timeout", 60),
            retry_attempts=data.get("retry_attempts", 3)
        )
    
    def _create_llm_config(self, data: Dict[str, Any]) -> LLMConfig:
        """创建LLM配置"""
        return LLMConfig(
            provider=data.get("provider", "openai"),
            model=data.get("model", "gpt-4"),
            temperature=data.get("temperature", 0.1),
            max_tokens=data.get("max_tokens", 1000),
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            timeout=data.get("timeout", 60),
            retry_attempts=data.get("retry_attempts", 3),
            stream=data.get("stream", False)
        )
    
    def _create_retrieval_config(self, data: Dict[str, Any]) -> RetrievalConfig:
        """创建检索配置"""
        return RetrievalConfig(
            top_k=data.get("top_k", 5),
            similarity_threshold=data.get("similarity_threshold", 0.7),
            search_mode=data.get("search_mode", "semantic"),
            enable_rerank=data.get("enable_rerank", False),
            enable_cache=data.get("enable_cache", False)
        )
    
    def _create_reranking_config(self, data: Dict[str, Any]) -> RerankingConfig:
        """创建重排序配置"""
        # 获取API密钥，优先使用配置文件，然后使用环境变量
        api_key = data.get("api_key")
        if not api_key:
            provider = data.get("provider", "sentence_transformers")
            if provider == "siliconflow":
                api_key = os.getenv("SILICONFLOW_API_KEY")
            elif provider == "openai":
                api_key = os.getenv("OPENAI_API_KEY")
        
        return RerankingConfig(
            provider=data.get("provider", "sentence_transformers"),
            model=data.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            model_name=data.get("model_name", data.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2")),
            batch_size=data.get("batch_size", 32),
            max_length=data.get("max_length", 512),
            timeout=data.get("timeout", 30.0),
            api_key=api_key,
            base_url=data.get("base_url")
        )
    
    def _create_api_config(self, data: Dict[str, Any]) -> APIConfig:
        """创建API配置"""
        return APIConfig(
            host=data.get("host", "0.0.0.0"),
            port=data.get("port", 8000),
            cors_origins=data.get("cors_origins", ["http://localhost:3000"])
        )