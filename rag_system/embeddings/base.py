"""
嵌入模型基类
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from dataclasses import dataclass
import json
import yaml

logger = logging.getLogger(__name__)


class EmbeddingConfig(BaseModel):
    """嵌入模型配置"""
    provider: str = Field("openai", description="嵌入模型提供商", pattern="^[a-zA-Z][a-zA-Z0-9_-]*$")
    model: str = Field("text-embedding-ada-002", description="嵌入模型名称", min_length=1)
    api_key: Optional[str] = Field(None, description="API密钥")
    api_base: Optional[str] = Field(None, description="API基础URL")
    base_url: Optional[str] = Field(None, description="基础URL（兼容字段）")
    max_tokens: int = Field(8192, gt=0, le=100000, description="最大令牌数")
    batch_size: int = Field(100, gt=0, le=1000, description="批处理大小")
    dimensions: Optional[int] = Field(None, gt=0, le=10000, description="向量维度")
    dimension: Optional[int] = Field(None, gt=0, le=10000, description="向量维度（兼容字段）")
    timeout: int = Field(60, gt=0, le=3600, description="超时时间（秒）")
    retry_attempts: int = Field(3, ge=0, le=10, description="重试次数")
    
    # 高级配置
    encoding_format: Optional[str] = Field(None, description="编码格式")
    truncate: Optional[str] = Field(None, description="截断策略")
    
    # 平台特定配置
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="额外参数")
    
    model_config = ConfigDict(
        extra="forbid",  # 禁止额外字段
        validate_assignment=True,  # 赋值时验证
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "provider": "openai",
                "model": "text-embedding-ada-002",
                "api_key": "sk-...",
                "max_tokens": 8192,
                "batch_size": 100,
                "timeout": 60,
                "retry_attempts": 3
            }
        }
    )
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        """验证提供商名称"""
        supported_providers = {
            'openai', 'siliconflow', 'modelscope', 'deepseek', 
            'ollama', 'mock', 'huggingface', 'sentence_transformers'
        }
        if v.lower() not in supported_providers:
            raise ValueError(f"不支持的嵌入提供商: {v}. 支持的提供商: {', '.join(supported_providers)}")
        return v.lower()
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v):
        """验证模型名称"""
        if not v or v.isspace():
            raise ValueError("嵌入模型名称不能为空")
        return v.strip()
    
    @field_validator('encoding_format')
    @classmethod
    def validate_encoding_format(cls, v):
        """验证编码格式"""
        if v and v not in ['float', 'base64']:
            raise ValueError("编码格式必须是 'float' 或 'base64'")
        return v
    
    @field_validator('truncate')
    @classmethod
    def validate_truncate(cls, v):
        """验证截断策略"""
        if v and v not in ['start', 'end']:
            raise ValueError("截断策略必须是 'start' 或 'end'")
        return v
    
    @model_validator(mode='after')
    def validate_api_key(self):
        """验证API密钥"""
        provider = self.provider.lower()
        if provider not in ['mock', 'ollama', 'sentence_transformers'] and not self.api_key:
            raise ValueError(f"提供商 {provider} 需要API密钥")
        return self
    
    @model_validator(mode='after')
    def validate_url_fields(self):
        """验证URL字段"""
        # 统一使用base_url字段
        if self.api_base and not self.base_url:
            self.base_url = self.api_base
        elif self.base_url and not self.api_base:
            self.api_base = self.base_url
        
        return self
    
    @model_validator(mode='after')
    def validate_dimension_fields(self):
        """验证维度字段"""
        # 统一使用dimensions字段
        if self.dimension and not self.dimensions:
            self.dimensions = self.dimension
        elif self.dimensions and not self.dimension:
            self.dimension = self.dimensions
        
        return self
    
    @model_validator(mode='after')
    def validate_provider_specific(self):
        """验证提供商特定配置"""
        provider = self.provider.lower()
        model = self.model
        
        # OpenAI特定验证
        if provider == 'openai':
            valid_models = {
                'text-embedding-ada-002', 'text-embedding-3-small', 
                'text-embedding-3-large'
            }
            if model not in valid_models and not model.startswith('text-embedding'):
                # 允许新模型，只发出警告
                pass
            
            # 设置默认维度
            if model == 'text-embedding-ada-002' and not self.dimensions:
                self.dimensions = 1536
            elif model == 'text-embedding-3-small' and not self.dimensions:
                self.dimensions = 1536
            elif model == 'text-embedding-3-large' and not self.dimensions:
                self.dimensions = 3072
        
        # SiliconFlow特定验证
        elif provider == 'siliconflow':
            if not self.base_url:
                self.base_url = 'https://api.siliconflow.cn/v1'
        
        # Mock特定配置
        elif provider == 'mock':
            if not self.dimensions:
                self.dimensions = 768  # 默认维度
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(exclude_none=True)
    
    def to_json(self, **kwargs) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json(exclude_none=True, **kwargs)
    
    def to_yaml(self) -> str:
        """转换为YAML字符串"""
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingConfig':
        """从字典创建配置"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EmbeddingConfig':
        """从JSON字符串创建配置"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'EmbeddingConfig':
        """从YAML字符串创建配置"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
    
    @classmethod
    def get_default_config(cls, provider: str, model: str) -> 'EmbeddingConfig':
        """获取默认配置"""
        defaults = {
            'openai': {
                'api_key': 'your-api-key-here',
                'max_tokens': 8192,
                'batch_size': 100,
                'timeout': 60,
                'retry_attempts': 3,
                'encoding_format': 'float'
            },
            'siliconflow': {
                'api_key': 'your-api-key-here',
                'base_url': 'https://api.siliconflow.cn/v1',
                'max_tokens': 8192,
                'batch_size': 100,
                'timeout': 60,
                'retry_attempts': 3
            },
            'mock': {
                'max_tokens': 8192,
                'batch_size': 100,
                'timeout': 10,
                'retry_attempts': 1,
                'dimensions': 768
            }
        }
        
        config_data = {
            'provider': provider,
            'model': model,
            **defaults.get(provider.lower(), defaults['openai'])
        }
        
        return cls(**config_data)
    
    def merge_with(self, other: 'EmbeddingConfig') -> 'EmbeddingConfig':
        """与另一个配置合并"""
        merged_data = self.to_dict()
        other_data = other.to_dict()
        
        # 合并extra_params
        if 'extra_params' in other_data:
            merged_data['extra_params'] = {
                **merged_data.get('extra_params', {}),
                **other_data['extra_params']
            }
            del other_data['extra_params']
        
        merged_data.update(other_data)
        return self.__class__(**merged_data)
    
    def validate_compatibility(self) -> List[str]:
        """验证配置兼容性，返回警告列表"""
        warnings = []
        
        # 检查批处理大小
        if self.batch_size > 500:
            warnings.append(f"批处理大小较大 ({self.batch_size})，可能导致内存不足")
        
        # 检查令牌数设置
        if self.max_tokens > 8192 and self.provider == 'openai':
            warnings.append("OpenAI嵌入模型的最大令牌数建议不超过8192")
        
        # 检查超时设置
        if self.timeout < 30:
            warnings.append(f"超时时间较短 ({self.timeout}秒)，可能导致请求失败")
        
        # 检查维度设置
        if self.dimensions and self.dimensions > 4096:
            warnings.append(f"向量维度较高 ({self.dimensions})，可能影响性能")
        
        return warnings


@dataclass
class EmbeddingResult:
    """嵌入结果"""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, Any]
    processing_time: float


class BaseEmbedding(ABC):
    """嵌入模型基类"""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化嵌入模型"""
        pass
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """对单个文本进行向量化"""
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """对多个文本进行批量向量化"""
        pass
    
    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """对查询文本进行向量化（可能与文档向量化有不同的处理）"""
        pass
    
    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """获取嵌入向量的维度"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量（同步版本，用于兼容）"""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量（同步版本，用于兼容）"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """获取嵌入向量维度（兼容方法）"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def _validate_text(self, text: str) -> bool:
        """验证文本输入"""
        if not text or not isinstance(text, str):
            return False
        
        if not text.strip():
            return False
        
        # 检查文本长度
        if len(text) > self.config.max_tokens * 4:  # 粗略估算token数
            logger.warning(f"文本长度可能超过模型限制: {len(text)} 字符")
        
        return True
    
    def _validate_texts(self, texts: List[str]) -> bool:
        """验证文本列表"""
        if not texts or not isinstance(texts, list):
            return False
        
        if len(texts) == 0:
            return False
        
        for text in texts:
            if not self._validate_text(text):
                return False
        
        return True
    
    def _chunk_texts(self, texts: List[str]) -> List[List[str]]:
        """将文本列表分块以适应批处理限制"""
        chunks = []
        for i in range(0, len(texts), self.config.batch_size):
            chunk = texts[i:i + self.config.batch_size]
            chunks.append(chunk)
        return chunks
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "dimensions": self.get_embedding_dimension(),
            "max_tokens": self.config.max_tokens,
            "batch_size": self.config.batch_size
        }