"""
模拟嵌入模型实现（用于测试和开发）
"""
import logging
import asyncio
import random
from typing import List, Dict, Any
import hashlib

from .base import BaseEmbedding, EmbeddingConfig
from ..utils.exceptions import ProcessingError

logger = logging.getLogger(__name__)


class MockEmbedding(BaseEmbedding):
    """模拟嵌入模型实现"""
    
    def __init__(self, config: EmbeddingConfig):
        super().__init__(config)
        self._dimensions = config.dimensions or 384
    
    async def initialize(self) -> None:
        """初始化模拟嵌入模型"""
        # 模拟初始化延迟
        await asyncio.sleep(0.1)
        self._initialized = True
        logger.info(f"模拟嵌入模型初始化成功: 维度={self._dimensions}")
    
    async def embed_text(self, text: str) -> List[float]:
        """对单个文本进行向量化"""
        if not self._initialized:
            raise ProcessingError("嵌入模型未初始化")
        
        if not self._validate_text(text):
            raise ValueError("无效的文本输入")
        
        # 模拟处理延迟
        await asyncio.sleep(0.01)
        
        # 基于文本内容生成确定性的向量
        return self._generate_embedding(text)
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """对多个文本进行批量向量化"""
        if not self._initialized:
            raise ProcessingError("嵌入模型未初始化")
        
        if not texts:
            return []
        
        if not self._validate_texts(texts):
            raise ProcessingError("无效的文本列表输入")
        
        logger.info(f"开始批量向量化: {len(texts)} 个文本")
        
        # 模拟批处理延迟
        await asyncio.sleep(0.01 * len(texts))
        
        embeddings = []
        for text in texts:
            embedding = self._generate_embedding(text)
            embeddings.append(embedding)
        
        logger.info(f"批量向量化完成: 生成 {len(embeddings)} 个向量")
        return embeddings
    
    async def embed_query(self, query: str) -> List[float]:
        """对查询文本进行向量化"""
        return await self.embed_text(query)
    
    def _generate_embedding(self, text: str) -> List[float]:
        """生成确定性的嵌入向量"""
        # 使用文本的哈希值作为随机种子，确保相同文本生成相同向量
        hash_value = hashlib.md5(text.encode()).hexdigest()
        seed = int(hash_value[:8], 16)
        
        # 设置随机种子
        random.seed(seed)
        
        # 生成向量
        embedding = []
        for _ in range(self._dimensions):
            # 生成[-1, 1]范围内的随机数
            value = random.uniform(-1, 1)
            embedding.append(value)
        
        # 归一化向量（可选）
        norm = sum(x * x for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        
        return embedding
    
    def get_embedding_dimension(self) -> int:
        """获取嵌入向量的维度"""
        return self._dimensions
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._initialized = False
        logger.info("模拟嵌入模型资源清理完成")
    
    async def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        base_info = await super().get_model_info()
        base_info.update({
            "type": "mock",
            "deterministic": True,
            "description": "模拟嵌入模型，用于测试和开发"
        })
        return base_info
    
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
            # 测试生成一个简单的嵌入向量
            test_embedding = self.embed("test")
            return len(test_embedding) == self._dimensions
        except:
            return False