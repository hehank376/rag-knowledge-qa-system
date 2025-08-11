#!/usr/bin/env python3
"""
统一重排序解决方案
支持API调用和本地模型两种模式，与嵌入模型架构保持一致
"""

# 1. 创建重排序基类
reranking_base_code = '''
"""
重排序模型基类
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RerankingConfig:
    """重排序配置"""
    provider: str = "local"  # local, siliconflow, openai
    model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_length: int = 512
    batch_size: int = 32
    timeout: float = 30.0
    retry_attempts: int = 3
    device: str = "cpu"


class BaseReranking(ABC):
    """重排序模型基类"""
    
    def __init__(self, config: RerankingConfig):
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化重排序模型"""
        pass
    
    @abstractmethod
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """重排序文档列表，返回分数"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": self.config.provider,
            "model": self.config.model,
            "max_length": self.config.max_length,
            "batch_size": self.config.batch_size,
            "initialized": self._initialized
        }
'''

# 2. 创建SiliconFlow重排序实现
siliconflow_reranking_code = '''
"""
SiliconFlow重排序模型实现
"""
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
import httpx

from .base import BaseReranking, RerankingConfig
from ..utils.exceptions import ProcessingError
from ..utils.model_exceptions import (
    ModelConnectionError, ModelResponseError, ModelAuthenticationError,
    ModelRateLimitError, ModelTimeoutError
)

logger = logging.getLogger(__name__)


class SiliconFlowReranking(BaseReranking):
    """SiliconFlow重排序模型实现"""
    
    def __init__(self, config: RerankingConfig):
        super().__init__(config)
        self.api_key = config.api_key or ""
        self.base_url = config.base_url or "https://api.siliconflow.cn/v1"
        self.model = config.model
        self.timeout = config.timeout
        self.retry_attempts = config.retry_attempts
        self._client: Optional[httpx.AsyncClient] = None
        
        if not self.api_key:
            raise ValueError("SiliconFlow API key is required")
    
    async def initialize(self) -> None:
        """初始化SiliconFlow客户端"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'RAG-System/1.0'
            }
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout
            )
            
            # 测试连接
            if not self.api_key.startswith("test-"):
                await self._test_connection()
            
            self._initialized = True
            logger.info(f"SiliconFlow重排序模型初始化成功: {self.model}")
            
        except Exception as e:
            logger.error(f"SiliconFlow重排序模型初始化失败: {str(e)}")
            if self._client:
                await self._client.aclose()
                self._client = None
            raise ProcessingError(f"SiliconFlow重排序模型初始化失败: {str(e)}")
    
    async def _test_connection(self) -> None:
        """测试API连接"""
        try:
            await self.rerank("test query", ["test document"])
            logger.debug("SiliconFlow重排序API连接测试成功")
        except Exception as e:
            raise ModelConnectionError(f"SiliconFlow重排序API连接测试失败: {str(e)}", "siliconflow", self.model)
    
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """重排序文档列表"""
        if not self._initialized:
            raise ProcessingError("SiliconFlow重排序服务未初始化")
        
        if not documents:
            return []
        
        try:
            return await self._call_rerank_api(query, documents)
        except Exception as e:
            logger.error(f"重排序失败: {str(e)}")
            raise ProcessingError(f"重排序失败: {str(e)}")
    
    async def _call_rerank_api(self, query: str, documents: List[str]) -> List[float]:
        """调用SiliconFlow重排序API"""
        if not self._client:
            raise ProcessingError("HTTP客户端未初始化")
        
        payload = {
            'model': self.model,
            'query': query,
            'documents': documents,
            'return_documents': False,
            'top_k': len(documents)
        }
        
        for attempt in range(self.retry_attempts):
            try:
                start_time = time.time()
                
                response = await self._client.post('/rerank', json=payload)
                processing_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 提取重排序分数
                    scores = []
                    for item in result.get("results", []):
                        scores.append(item.get("relevance_score", 0.0))
                    
                    logger.debug(f"重排序API调用成功: 处理时间 {processing_time:.2f}s")
                    return scores
                    
                elif response.status_code == 401:
                    raise ModelAuthenticationError(
                        f"API认证失败: {response.text}", 
                        "siliconflow", 
                        self.model
                    )
                elif response.status_code == 429:
                    raise ModelRateLimitError(
                        f"API限流: {response.text}", 
                        "siliconflow", 
                        self.model
                    )
                else:
                    raise ModelResponseError(
                        f"API请求失败: {response.status_code} - {response.text}",
                        "siliconflow",
                        self.model
                    )
                    
            except httpx.TimeoutException:
                if attempt == self.retry_attempts - 1:
                    raise ModelTimeoutError(
                        f"API请求超时: {self.timeout}s",
                        "siliconflow",
                        self.model
                    )
                
                wait_time = 2 ** attempt
                logger.warning(f"API请求超时，等待 {wait_time}s 后重试")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise
                
                wait_time = 2 ** attempt
                logger.warning(f"API调用失败，等待 {wait_time}s 后重试: {str(e)}")
                await asyncio.sleep(wait_time)
        
        raise ProcessingError("API调用重试次数已用完")
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            scores = asyncio.run(self.rerank("test", ["document"]))
            return len(scores) == 1
        except:
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        self._initialized = False
        logger.info("SiliconFlow重排序模型资源清理完成")
'''

# 3. 创建本地重排序实现
local_reranking_code = '''
"""
本地重排序模型实现
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from .base import BaseReranking, RerankingConfig
from ..utils.exceptions import ProcessingError

logger = logging.getLogger(__name__)


class LocalReranking(BaseReranking):
    """本地重排序模型实现"""
    
    def __init__(self, config: RerankingConfig):
        super().__init__(config)
        self.model_name = config.model
        self.max_length = config.max_length
        self.batch_size = config.batch_size
        self.device = config.device
        self.reranker_model = None
    
    async def initialize(self) -> None:
        """初始化本地重排序模型"""
        try:
            # 在线程池中加载模型以避免阻塞
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._load_model)
            
            self._initialized = True
            logger.info(f"本地重排序模型加载成功: {self.model_name}")
            
        except ImportError as e:
            logger.warning(f"sentence-transformers库未安装，本地重排序功能将被禁用: {e}")
            self._initialized = False
            raise ProcessingError(f"sentence-transformers库未安装: {e}")
        except Exception as e:
            logger.error(f"本地重排序模型加载失败: {e}")
            self._initialized = False
            raise ProcessingError(f"本地重排序模型加载失败: {e}")
    
    def _load_model(self) -> None:
        """加载重排序模型（在线程池中执行）"""
        try:
            from sentence_transformers import CrossEncoder
            
            # 加载交叉编码器模型
            self.reranker_model = CrossEncoder(
                self.model_name,
                max_length=self.max_length,
                device=self.device
            )
            
            logger.info(f"成功加载本地重排序模型: {self.model_name}")
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise
    
    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """重排序文档列表"""
        if not self._initialized or not self.reranker_model:
            raise ProcessingError("本地重排序模型未初始化")
        
        if not documents:
            return []
        
        try:
            # 准备查询-文档对
            pairs = [(query, doc) for doc in documents]
            
            # 在线程池中执行重排序计算
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, self._compute_scores, pairs)
            
            return scores.tolist() if hasattr(scores, 'tolist') else list(scores)
            
        except Exception as e:
            logger.error(f"本地重排序失败: {e}")
            raise ProcessingError(f"本地重排序失败: {e}")
    
    def _compute_scores(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """计算重排序分数（在线程池中执行）"""
        try:
            # 批处理计算分数
            if len(pairs) <= self.batch_size:
                scores = self.reranker_model.predict(pairs)
            else:
                scores = []
                for i in range(0, len(pairs), self.batch_size):
                    batch = pairs[i:i + self.batch_size]
                    batch_scores = self.reranker_model.predict(batch)
                    scores.extend(batch_scores)
            
            return scores
            
        except Exception as e:
            logger.error(f"重排序分数计算失败: {e}")
            raise
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self._initialized or not self.reranker_model:
                return False
            
            scores = asyncio.run(self.rerank("test", ["document"]))
            return len(scores) == 1
        except:
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self.reranker_model is not None:
            if hasattr(self.reranker_model, 'close'):
                self.reranker_model.close()
            self.reranker_model = None
        
        self._initialized = False
        logger.info("本地重排序模型资源清理完成")
'''

# 4. 创建重排序工厂
reranking_factory_code = '''
"""
重排序模型工厂
"""
import logging
from typing import Dict, Type, Optional

from ..utils.exceptions import ConfigurationError, ProcessingError
from ..utils.model_exceptions import UnsupportedProviderError
from .base import BaseReranking, RerankingConfig
from .local_reranking import LocalReranking

logger = logging.getLogger(__name__)


class RerankingFactory:
    """重排序模型工厂类"""
    
    _providers: Dict[str, Type[BaseReranking]] = {
        "local": LocalReranking,
    }
    
    # 延迟加载的提供商映射
    _lazy_providers: Dict[str, str] = {
        "siliconflow": "rag_system.reranking.siliconflow_reranking.SiliconFlowReranking",
        "openai": "rag_system.reranking.openai_reranking.OpenAIReranking",
    }
    
    @classmethod
    def create_reranking(cls, config: RerankingConfig) -> BaseReranking:
        """创建重排序模型实例"""
        provider = config.provider.lower()
        reranking_class = cls._get_reranking_class(provider)
        
        try:
            reranking = reranking_class(config)
            logger.info(f"创建重排序模型实例成功: {provider} - {config.model}")
            return reranking
        except Exception as e:
            logger.error(f"创建重排序模型实例失败: {provider} - {str(e)}")
            raise ProcessingError(f"创建重排序模型实例失败: {str(e)}")
    
    @classmethod
    def _get_reranking_class(cls, provider: str) -> Type[BaseReranking]:
        """获取重排序模型类，支持延迟加载"""
        # 首先检查已加载的提供商
        if provider in cls._providers:
            return cls._providers[provider]
        
        # 检查延迟加载的提供商
        if provider in cls._lazy_providers:
            module_path = cls._lazy_providers[provider]
            try:
                # 动态导入模块
                module_name, class_name = module_path.rsplit('.', 1)
                module = __import__(module_name, fromlist=[class_name])
                reranking_class = getattr(module, class_name)
                
                # 缓存已加载的类
                cls._providers[provider] = reranking_class
                logger.debug(f"延迟加载重排序模型提供商: {provider}")
                return reranking_class
                
            except ImportError as e:
                logger.error(f"无法导入重排序模型提供商 {provider}: {str(e)}")
                raise UnsupportedProviderError(
                    f"重排序模型提供商 {provider} 不可用，可能缺少相关依赖",
                    provider
                )
            except AttributeError as e:
                logger.error(f"重排序模型提供商 {provider} 类不存在: {str(e)}")
                raise UnsupportedProviderError(
                    f"重排序模型提供商 {provider} 实现不正确",
                    provider
                )
        
        # 提供商不存在
        available_providers = cls.get_available_providers()
        raise UnsupportedProviderError(
            f"不支持的重排序模型提供商: {provider}. "
            f"支持的提供商: {', '.join(available_providers)}",
            provider
        )
    
    @classmethod
    def get_available_providers(cls) -> list:
        """获取可用的重排序提供商列表"""
        all_providers = set(cls._providers.keys())
        all_providers.update(cls._lazy_providers.keys())
        return sorted(list(all_providers))
    
    @classmethod
    def is_provider_available(cls, provider: str) -> bool:
        """检查提供商是否可用"""
        provider = provider.lower()
        
        if provider in cls._providers:
            return True
        
        if provider in cls._lazy_providers:
            try:
                cls._get_reranking_class(provider)
                return True
            except UnsupportedProviderError:
                return False
        
        return False


def create_reranking(config: RerankingConfig) -> BaseReranking:
    """便捷函数：创建重排序模型实例"""
    return RerankingFactory.create_reranking(config)
'''

print("🚀 统一重排序解决方案设计完成")
print("=" * 60)

print("📋 解决方案特点:")
print("✅ 统一架构：与嵌入模型保持一致的工厂模式")
print("✅ 双模式支持：API调用 + 本地模型")
print("✅ 配置驱动：根据provider自动选择实现")
print("✅ 延迟加载：按需加载提供商实现")
print("✅ 错误处理：完整的异常处理机制")
print("✅ 资源管理：自动清理和健康检查")

print("\n🎯 为什么这是最优方案:")
print("1. 架构一致性：与现有嵌入模型架构完全一致")
print("2. 灵活性：支持API和本地两种模式，满足不同需求")
print("3. 可扩展性：工厂模式易于添加新的提供商")
print("4. 配置驱动：通过配置文件控制使用哪种模式")
print("5. 向后兼容：保持现有接口不变")
print("6. 性能优化：延迟加载减少启动时间")
print("7. 错误恢复：完整的重试和降级机制")

print("\n📁 需要创建的文件:")
print("- rag_system/reranking/__init__.py")
print("- rag_system/reranking/base.py")
print("- rag_system/reranking/factory.py") 
print("- rag_system/reranking/local_reranking.py")
print("- rag_system/reranking/siliconflow_reranking.py")
print("- rag_system/reranking/mock_reranking.py")

print("\n🔧 配置示例:")
print("""
# API模式配置
reranking:
  provider: siliconflow
  model: BAAI/bge-reranker-v2-m3
  api_key: sk-xxx
  base_url: https://api.siliconflow.cn/v1

# 本地模式配置  
reranking:
  provider: local
  model: cross-encoder/ms-marco-MiniLM-L-6-v2
  device: cpu
""")

print("\n⚡ 实施步骤:")
print("1. 创建重排序模块目录结构")
print("2. 实现基类和工厂")
print("3. 实现各个提供商")
print("4. 修改重排序服务使用新架构")
print("5. 更新配置和测试")