"""
向量存储基类
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import logging

from ..models.vector import Vector, SearchResult
from ..models.config import VectorStoreConfig

logger = logging.getLogger(__name__)


class VectorStoreBase(ABC):
    """向量存储基类"""
    
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化向量存储"""
        pass
    
    @abstractmethod
    async def add_vectors(self, vectors: List[Vector]) -> bool:
        """添加向量到存储"""
        pass
    
    @abstractmethod
    async def search_similar(self, query_vector: List[float], top_k: int = 5, 
                           similarity_threshold: float = 0.0) -> List[SearchResult]:
        """搜索相似向量"""
        pass
    
    @abstractmethod
    async def delete_vectors(self, document_id: str) -> bool:
        """删除指定文档的所有向量"""
        pass
    
    @abstractmethod
    async def update_vectors(self, document_id: str, vectors: List[Vector]) -> bool:
        """更新指定文档的向量"""
        pass
    
    @abstractmethod
    async def get_vector_count(self) -> int:
        """获取向量总数"""
        pass
    
    @abstractmethod
    async def clear_all(self) -> bool:
        """清空所有向量"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def _validate_vector(self, vector: Vector) -> bool:
        """验证向量格式"""
        if not vector.id or not vector.document_id or not vector.chunk_id:
            logger.error("向量缺少必要的ID信息")
            return False
        
        if not vector.embedding or not isinstance(vector.embedding, list):
            logger.error("向量嵌入数据无效")
            return False
        
        if len(vector.embedding) == 0:
            logger.error("向量嵌入数据为空")
            return False
        
        return True
    
    def _validate_vectors(self, vectors: List[Vector]) -> bool:
        """验证向量列表"""
        if not vectors:
            logger.error("向量列表为空")
            return False
        
        for vector in vectors:
            if not self._validate_vector(vector):
                return False
        
        return True