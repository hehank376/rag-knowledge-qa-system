"""
OpenAI嵌入模型实现
"""
import logging
import asyncio
import time
from typing import List, Dict, Any, Optional
import httpx

from ..utils.exceptions import ProcessingError
from .base import BaseEmbedding, EmbeddingConfig, EmbeddingResult

logger = logging.getLogger(__name__)


class OpenAIEmbedding(BaseEmbedding):
    """OpenAI嵌入模型实现"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        self._model_dimensions = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072
        }
    
    async def initialize(self) -> None:
        """初始化OpenAI客户端"""
        try:
            if not self.config.api_key:
                raise ProcessingError("OpenAI API密钥未配置")
            
            # 创建HTTP客户端
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            }
            
            self._client = httpx.AsyncClient(
                base_url=self.config.api_base or "https://api.openai.com/v1",
                headers=headers,
                timeout=self.config.timeout
            )
            
            # 只在非测试环境下测试连接
            if not self.config.api_key.startswith("test-"):
                await self._test_connection()
            
            self._initialized = True
            logger.info(f"OpenAI嵌入模型初始化成功: {self.config.model}")
            
        except Exception as e:
            logger.error(f"OpenAI嵌入模型初始化失败: {str(e)}")
            raise ProcessingError(f"OpenAI嵌入模型初始化失败: {str(e)}")
    
    async def _test_connection(self) -> None:
        """测试API连接"""
        try:
            # 使用简单文本测试连接
            await self._create_embedding(["test"])
            logger.debug("OpenAI API连接测试成功")
        except Exception as e:
            raise ProcessingError(f"OpenAI API连接测试失败: {str(e)}")
    
    async def embed_text(self, text: str) -> List[float]:
        """对单个文本进行向量化"""
        if not self._initialized:
            raise ProcessingError("OpenAI嵌入服务未初始化")
        
        if not self._validate_text(text):
            raise ProcessingError("无效的文本输入")
        
        try:
            embeddings = await self._create_embedding([text])
            return embeddings[0]
        except Exception as e:
            logger.error(f"文本向量化失败: {str(e)}")
            raise ProcessingError(f"文本向量化失败: {str(e)}")
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """对多个文本进行批量向量化"""
        if not self._initialized:
            raise ProcessingError("OpenAI嵌入服务未初始化")
        
        if not self._validate_texts(texts):
            raise ProcessingError("无效的文本列表输入")
        
        try:
            logger.info(f"开始批量向量化: {len(texts)} 个文本")
            
            # 分块处理
            text_chunks = self._chunk_texts(texts)
            all_embeddings = []
            
            for i, chunk in enumerate(text_chunks):
                logger.debug(f"处理第 {i+1}/{len(text_chunks)} 批文本")
                
                chunk_embeddings = await self._create_embedding(chunk)
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
        # 对于OpenAI，查询和文档使用相同的嵌入方法
        return await self.embed_text(query)
    
    async def _create_embedding(self, texts: List[str]) -> List[List[float]]:
        """调用OpenAI API创建嵌入"""
        if not self._client:
            raise ProcessingError("HTTP客户端未初始化")
        
        payload = {
            "input": texts,
            "model": self.config.model
        }
        
        # 添加维度参数（如果支持）
        if self.config.dimensions and self.config.model.startswith("text-embedding-3"):
            payload["dimensions"] = self.config.dimensions
        
        for attempt in range(self.config.retry_attempts):
            try:
                start_time = time.time()
                
                response = await self._client.post("/embeddings", json=payload)
                response.raise_for_status()
                
                result = response.json()
                processing_time = time.time() - start_time
                
                # 提取嵌入向量
                embeddings = []
                for item in result["data"]:
                    embeddings.append(item["embedding"])
                
                logger.debug(f"API调用成功: 处理时间 {processing_time:.2f}s")
                return embeddings
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:  # 限流
                    wait_time = 2 ** attempt
                    logger.warning(f"API限流，等待 {wait_time}s 后重试")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise ProcessingError(f"API请求失败: {e.response.status_code} - {e.response.text}")
            
            except Exception as e:
                if attempt == self.config.retry_attempts - 1:
                    raise
                
                wait_time = 2 ** attempt
                logger.warning(f"API调用失败，等待 {wait_time}s 后重试: {str(e)}")
                await asyncio.sleep(wait_time)
        
        raise ProcessingError("API调用重试次数已用完")
    
    def get_embedding_dimension(self) -> int:
        """获取嵌入向量的维度"""
        if self.config.dimensions:
            return self.config.dimensions
        
        return self._model_dimensions.get(self.config.model, 1536)
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        self._initialized = False
        logger.info("OpenAI嵌入模型资源清理完成")
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计（如果API支持）"""
        return {
            "model": self.config.model,
            "provider": "openai",
            "dimensions": self.get_embedding_dimension(),
            "batch_size": self.config.batch_size
        }
    
    def embed(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量（同步版本，用于兼容）"""
        import asyncio
        try:
            return asyncio.run(self.embed_text(text))
        except Exception as e:
            logger.error(f"同步嵌入生成失败: {str(e)}")
            raise ProcessingError(f"同步嵌入生成失败: {str(e)}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量（同步版本，用于兼容）"""
        import asyncio
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
            import asyncio
            test_embedding = asyncio.run(self.embed_text("test"))
            return len(test_embedding) == self.get_embedding_dimension()
        except:
            return False