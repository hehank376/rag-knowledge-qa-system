"""
重排序基类和配置

提供统一的重排序接口和配置管理，与嵌入模型架构保持一致。
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, ConfigDict

logger = logging.getLogger(__name__)


class RerankingConfig(BaseModel):
    """重排序配置类 - 统一配置格式"""
    
    provider: str = Field("local", description="重排序提供商", pattern="^[a-zA-Z][a-zA-Z0-9_-]*$")
    model: str = Field("cross-encoder/ms-marco-MiniLM-L-6-v2", description="重排序模型名称", min_length=1)
    model_name: Optional[str] = Field(None, description="模型名称（兼容字段）")
    
    # API相关配置
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API基础URL")
    
    # 模型参数
    max_length: int = Field(512, gt=0, le=2048, description="最大文本长度")
    batch_size: int = Field(32, gt=0, le=256, description="批处理大小")
    timeout: int = Field(30, gt=0, le=300, description="超时时间（秒）")
    
    # 本地模型配置
    device: str = Field("cpu", description="设备类型（cpu/cuda）")
    model_cache_dir: Optional[str] = Field(None, description="模型缓存目录")
    
    # 高级配置
    retry_attempts: int = Field(3, ge=0, le=10, description="重试次数")
    enable_fallback: bool = Field(True, description="启用备用模型")
    fallback_provider: str = Field("mock", description="备用提供商")
    
    # 性能配置
    max_concurrent_requests: int = Field(10, gt=0, le=100, description="最大并发请求数")
    request_interval: float = Field(0.1, ge=0, le=5.0, description="请求间隔（秒）")
    
    # 额外参数
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="额外参数")
    
    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "provider": "siliconflow",
                "model": "BAAI/bge-reranker-v2-m3",
                "api_key": "sk-...",
                "base_url": "https://api.siliconflow.cn/v1",
                "max_length": 512,
                "batch_size": 32,
                "timeout": 30
            }
        }
    )
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        """验证提供商名称"""
        supported_providers = {
            'local', 'siliconflow', 'openai', 'mock', 
            'sentence_transformers', 'huggingface'
        }
        if v.lower() not in supported_providers:
            raise ValueError(f"不支持的重排序提供商: {v}. 支持的提供商: {', '.join(supported_providers)}")
        return v.lower()
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v):
        """验证模型名称"""
        if not v or v.isspace():
            raise ValueError("重排序模型名称不能为空")
        return v.strip()
    
    @field_validator('device')
    @classmethod
    def validate_device(cls, v):
        """验证设备类型"""
        if v.lower() not in ['cpu', 'cuda', 'mps']:
            raise ValueError("设备类型必须是 'cpu', 'cuda' 或 'mps'")
        return v.lower()
    
    def get_model_name(self) -> str:
        """获取模型名称，优先使用model_name，然后是model"""
        return self.model_name or self.model
    
    def is_api_provider(self) -> bool:
        """判断是否为API提供商"""
        api_providers = {'siliconflow', 'openai'}
        return self.provider in api_providers and self.api_key and self.base_url
    
    def is_local_provider(self) -> bool:
        """判断是否为本地提供商"""
        local_providers = {'local', 'sentence_transformers', 'huggingface'}
        return self.provider in local_providers
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return self.model_dump()


class BaseReranking(ABC):
    """重排序基类 - 统一接口"""
    
    def __init__(self, config: RerankingConfig):
        """
        初始化重排序模型
        
        Args:
            config: 重排序配置
        """
        self.config = config
        self._initialized = False
        self._model = None
        
        logger.info(f"初始化重排序模型: {config.provider} - {config.get_model_name()}")
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        初始化重排序模型
        
        Raises:
            Exception: 初始化失败时抛出异常
        """
        pass
    
    @abstractmethod
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """
        对文档进行重排序
        
        Args:
            query: 查询文本
            documents: 文档列表
            
        Returns:
            重排序分数列表，分数越高排名越靠前
            
        Raises:
            Exception: 重排序失败时抛出异常
        """
        pass
    
    @abstractmethod
    async def rerank_batch(self, queries: List[str], documents_list: List[List[str]]) -> List[List[float]]:
        """
        批量重排序
        
        Args:
            queries: 查询列表
            documents_list: 文档列表的列表
            
        Returns:
            重排序分数列表的列表
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass
    
    @abstractmethod
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def get_config(self) -> RerankingConfig:
        """获取配置"""
        return self.config
    
    def _validate_inputs(self, query: str, documents: List[str]) -> None:
        """验证输入参数"""
        if not query or not query.strip():
            raise ValueError("查询文本不能为空")
        
        if not documents:
            raise ValueError("文档列表不能为空")
        
        if not all(doc and doc.strip() for doc in documents):
            raise ValueError("文档列表中不能包含空文档")
    
    def _truncate_text(self, text: str, max_length: Optional[int] = None) -> str:
        """截断文本到指定长度"""
        max_len = max_length or self.config.max_length
        if len(text) <= max_len:
            return text
        return text[:max_len]
    
    def _prepare_pairs(self, query: str, documents: List[str]) -> List[Tuple[str, str]]:
        """准备查询-文档对"""
        query = self._truncate_text(query)
        pairs = []
        
        for doc in documents:
            doc = self._truncate_text(doc)
            pairs.append((query, doc))
        
        return pairs
    
    async def _handle_error(self, error: Exception, operation: str) -> None:
        """统一错误处理"""
        error_msg = f"{operation}失败: {str(error)}"
        logger.error(error_msg)
        raise Exception(error_msg) from error


class RerankingMetrics:
    """重排序性能指标"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_processing_time = 0.0
        self.total_documents_processed = 0
        self.average_processing_time = 0.0
        self.average_documents_per_request = 0.0
    
    def update_request(self, processing_time: float, document_count: int, success: bool = True):
        """更新请求指标"""
        self.total_requests += 1
        self.total_processing_time += processing_time
        self.total_documents_processed += document_count
        
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # 更新平均值
        if self.total_requests > 0:
            self.average_processing_time = self.total_processing_time / self.total_requests
            self.average_documents_per_request = self.total_documents_processed / self.total_requests
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def failure_rate(self) -> float:
        """失败率"""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.success_rate,
            'failure_rate': self.failure_rate,
            'total_processing_time': self.total_processing_time,
            'average_processing_time': self.average_processing_time,
            'total_documents_processed': self.total_documents_processed,
            'average_documents_per_request': self.average_documents_per_request
        }
    
    def reset(self):
        """重置指标"""
        self.__init__()