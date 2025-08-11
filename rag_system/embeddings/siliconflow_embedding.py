"""
SiliconFlow Embedding Implementation
硅基流动嵌入模型实现
"""
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
import httpx

from .base import BaseEmbedding, EmbeddingConfig, EmbeddingResult
from ..utils.exceptions import ProcessingError
from ..utils.model_exceptions import (
    ModelConnectionError, ModelResponseError, ModelAuthenticationError,
    ModelRateLimitError, ModelTimeoutError
)

logger = logging.getLogger(__name__)


class SiliconFlowEmbedding(BaseEmbedding):
    """硅基流动嵌入模型实现"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self.api_key = config.api_key or ""
        self.base_url = config.base_url or config.api_base or "https://api.siliconflow.cn/v1"
        self.model = config.model if config.model != "text-embedding-ada-002" else "BAAI/bge-large-zh-v1.5"
        self.dimension = config.dimension or config.dimensions or 1024
        self.batch_size = config.batch_size
        self.timeout = config.timeout
        self.retry_attempts = config.retry_attempts
        self._client: Optional[httpx.AsyncClient] = None
        
        # 模型维度映射
        self._model_dimensions = {
            "BAAI/bge-large-zh-v1.5": 1024,
            "BAAI/bge-base-zh-v1.5": 768,
            "BAAI/bge-small-zh-v1.5": 512,
            "BAAI/bge-large-en-v1.5": 1024,
            "BAAI/bge-base-en-v1.5": 768,
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "text-embedding-ada-002": 1536
        }
        
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
            logger.info(f"SiliconFlow嵌入模型初始化成功: {self.model}")
            
        except Exception as e:
            logger.error(f"SiliconFlow嵌入模型初始化失败: {str(e)}")
            if self._client:
                await self._client.aclose()
                self._client = None
            raise ProcessingError(f"SiliconFlow嵌入模型初始化失败: {str(e)}")
    
    async def _test_connection(self) -> None:
        """测试API连接"""
        try:
            await self._create_embeddings(["test"])
            logger.debug("SiliconFlow嵌入API连接测试成功")
        except Exception as e:
            raise ModelConnectionError(f"SiliconFlow嵌入API连接测试失败: {str(e)}", "siliconflow", self.model)
    
    async def embed_text(self, text: str) -> List[float]:
        """对单个文本进行向量化"""
        if not self._initialized:
            raise ProcessingError("SiliconFlow嵌入服务未初始化")
        
        if not self._validate_text(text):
            raise ProcessingError("无效的文本输入")
        
        try:
            embeddings = await self._create_embeddings([text])
            return embeddings[0]
        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            raise ProcessingError(f"文本向量化失败: {str(e)}")
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """对多个文本进行批量向量化"""
        if not self._initialized:
            raise ProcessingError("SiliconFlow嵌入服务未初始化")
        
        if not self._validate_texts(texts):
            raise ProcessingError("无效的文本列表输入")
        
        try:
            logger.info(f"开始批量向量化: {len(texts)} 个文本")
            
            # 分块处理
            text_chunks = self._chunk_texts(texts)
            all_embeddings = []
            
            for i, chunk in enumerate(text_chunks):
                logger.debug(f"处理第 {i+1}/{len(text_chunks)} 批文本")
                
                chunk_embeddings = await self._create_embeddings(chunk)
                all_embeddings.extend(chunk_embeddings)
                
                # 避免API限流
                if i < len(text_chunks) - 1:
                    await asyncio.sleep(0.1)
            
            logger.info(f"批量向量化完成: 生成 {len(all_embeddings)} 个向量")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"批量文本向量化失败: {str(e)}")
            raise ProcessingError(f"批量文本向量化失败: {str(e)}")
    
    async def embed_query(self, query: str) -> List[float]:
        """对查询文本进行向量化"""
        # 对于SiliconFlow，查询和文档使用相同的嵌入方法
        return await self.embed_text(query)
    
    async def _create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """调用SiliconFlow API创建嵌入"""
        if not self._client:
            raise ProcessingError("HTTP客户端未初始化")
        
        payload = {
            'model': self.model,
            'input': texts,
            'encoding_format': 'float'
        }
        
        for attempt in range(self.retry_attempts):
            try:
                start_time = time.time()
                
                response = await self._client.post('/embeddings', json=payload)
                processing_time = time.time() - start_time
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # 提取嵌入向量
                    embeddings = []
                    for item in result["data"]:
                        embeddings.append(item["embedding"])
                    
                    logger.debug(f"API调用成功: 处理时间 {processing_time:.2f}s")
                    return embeddings
                    
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
                
            except ModelRateLimitError:
                if attempt == self.retry_attempts - 1:
                    raise
                
                wait_time = 2 ** attempt
                logger.warning(f"API限流，等待 {wait_time}s 后重试")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise
                
                wait_time = 2 ** attempt
                logger.warning(f"API调用失败，等待 {wait_time}s 后重试: {str(e)}")
                await asyncio.sleep(wait_time)
        
        raise ProcessingError("API调用重试次数已用完")
    
    def get_embedding_dimension(self) -> int:
        """获取嵌入向量的维度"""
        if self.dimension:
            return self.dimension
        
        return self._model_dimensions.get(self.model, 1024)
    
    def embed(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量（同步版本，用于兼容）"""
        try:
            return asyncio.run(self.embed_text(text))
        except Exception as e:
            logger.error(f"同步嵌入生成失败: {str(e)}")
            raise ProcessingError(f"同步嵌入生成失败: {str(e)}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量（同步版本，用于兼容）"""
        try:
            return asyncio.run(self.embed_texts(texts))
        except Exception as e:
            logger.error(f"同步批量嵌入生成失败: {str(e)}")
            raise ProcessingError(f"同步批量嵌入生成失败: {str(e)}")
    
    def get_dimension(self) -> int:
        """获取嵌入向量维度（兼容方法）"""
        return self.get_embedding_dimension()
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            test_embedding = asyncio.run(self.embed_text("test"))
            return len(test_embedding) == self.get_embedding_dimension()
        except:
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        self._initialized = False
        logger.info("SiliconFlow嵌入模型资源清理完成")
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": "siliconflow",
            "model": self.model,
            "dimensions": self.get_embedding_dimension(),
            "max_tokens": self.config.max_tokens,
            "batch_size": self.batch_size,
            "base_url": self.base_url
        }
    
    def get_available_models(self) -> List[str]:
        """获取可用的嵌入模型列表"""
        return [
            'BAAI/bge-large-zh-v1.5',
            'BAAI/bge-base-zh-v1.5',
            'BAAI/bge-small-zh-v1.5',
            'BAAI/bge-large-en-v1.5',
            'BAAI/bge-base-en-v1.5',
            'sentence-transformers/all-MiniLM-L6-v2',
            'text-embedding-ada-002'
        ]