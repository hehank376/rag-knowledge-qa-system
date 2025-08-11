"""
向量存储服务实现
"""
import logging
from typing import List, Dict, Any, Optional

from ..models.vector import Vector, SearchResult
from ..models.config import VectorStoreConfig
from ..vector_store.base import VectorStoreBase
from ..vector_store.chroma_store import ChromaVectorStore
from ..utils.exceptions import VectorStoreError, ConfigurationError
from .base import BaseService

logger = logging.getLogger(__name__)


class VectorStoreService(BaseService):
    """向量存储服务"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__()
        self.config = config
        self._store: Optional[VectorStoreBase] = None
    
    async def initialize(self) -> None:
        """初始化向量存储服务"""
        try:
            logger.info(f"初始化向量存储服务，类型: {self.config.type}")
            
            # 根据配置创建向量存储实例
            if self.config.type.lower() == "chroma":
                self._store = ChromaVectorStore(self.config)
            else:
                raise ConfigurationError(f"不支持的向量存储类型: {self.config.type}")
            
            # 初始化向量存储
            await self._store.initialize()
            
            logger.info("向量存储服务初始化成功")
            
        except Exception as e:
            logger.error(f"向量存储服务初始化失败: {str(e)}")
            raise VectorStoreError(f"向量存储服务初始化失败: {str(e)}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._store:
            await self._store.cleanup()
            self._store = None
        logger.info("向量存储服务资源清理完成")
    
    def _ensure_initialized(self) -> None:
        """确保服务已初始化"""
        if not self._store or not self._store.is_initialized():
            raise VectorStoreError("向量存储服务未初始化")
    
    async def add_vectors(self, vectors: List[Vector]) -> bool:
        """添加向量"""
        self._ensure_initialized()
        
        if not vectors:
            logger.warning("向量列表为空，跳过添加")
            return True
        
        try:
            logger.info(f"添加 {len(vectors)} 个向量")
            result = await self._store.add_vectors(vectors)
            
            if result:
                logger.info(f"成功添加 {len(vectors)} 个向量")
            else:
                logger.warning("向量添加失败")
            
            return result
            
        except Exception as e:
            logger.error(f"添加向量失败: {str(e)}")
            raise VectorStoreError(f"添加向量失败: {str(e)}")
    
    async def search_similar(self, query_vector: List[float], top_k: int = 5,
                           similarity_threshold: float = 0.0) -> List[SearchResult]:
        """搜索相似向量"""
        self._ensure_initialized()
        
        if not query_vector:
            raise VectorStoreError("查询向量不能为空")
        
        if top_k <= 0:
            raise VectorStoreError("top_k必须大于0")
        
        try:
            logger.debug(f"搜索相似向量，维度: {len(query_vector)}, top_k: {top_k}")
            
            results = await self._store.search_similar(
                query_vector=query_vector,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            logger.debug(f"找到 {len(results)} 个相似向量")
            return results
            
        except Exception as e:
            logger.error(f"搜索相似向量失败: {str(e)}")
            raise VectorStoreError(f"搜索相似向量失败: {str(e)}")
    
    async def delete_vectors(self, document_id: str) -> bool:
        """删除指定文档的所有向量"""
        self._ensure_initialized()
        
        if not document_id:
            raise VectorStoreError("文档ID不能为空")
        
        try:
            logger.info(f"删除文档 {document_id} 的向量")
            result = await self._store.delete_vectors(document_id)
            
            if result:
                logger.info(f"成功删除文档 {document_id} 的向量")
            else:
                logger.warning(f"删除文档 {document_id} 的向量失败")
            
            return result
            
        except Exception as e:
            logger.error(f"删除向量失败: {str(e)}")
            raise VectorStoreError(f"删除向量失败: {str(e)}")
    
    async def update_vectors(self, document_id: str, vectors: List[Vector]) -> bool:
        """更新指定文档的向量"""
        self._ensure_initialized()
        
        if not document_id:
            raise VectorStoreError("文档ID不能为空")
        
        if not vectors:
            logger.warning("向量列表为空，执行删除操作")
            return await self.delete_vectors(document_id)
        
        try:
            logger.info(f"更新文档 {document_id} 的 {len(vectors)} 个向量")
            result = await self._store.update_vectors(document_id, vectors)
            
            if result:
                logger.info(f"成功更新文档 {document_id} 的向量")
            else:
                logger.warning(f"更新文档 {document_id} 的向量失败")
            
            return result
            
        except Exception as e:
            logger.error(f"更新向量失败: {str(e)}")
            raise VectorStoreError(f"更新向量失败: {str(e)}")
    
    async def get_vector_count(self) -> int:
        """获取向量总数"""
        self._ensure_initialized()
        
        try:
            count = await self._store.get_vector_count()
            logger.debug(f"向量总数: {count}")
            return count
            
        except Exception as e:
            logger.error(f"获取向量数量失败: {str(e)}")
            raise VectorStoreError(f"获取向量数量失败: {str(e)}")
    
    async def clear_all_vectors(self) -> bool:
        """清空所有向量"""
        self._ensure_initialized()
        
        try:
            logger.warning("清空所有向量数据")
            result = await self._store.clear_all()
            
            if result:
                logger.info("成功清空所有向量数据")
            else:
                logger.warning("清空向量数据失败")
            
            return result
            
        except Exception as e:
            logger.error(f"清空向量数据失败: {str(e)}")
            raise VectorStoreError(f"清空向量数据失败: {str(e)}")
    
    async def get_store_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        self._ensure_initialized()
        
        try:
            if hasattr(self._store, 'get_collection_info'):
                info = await self._store.get_collection_info()
            else:
                count = await self.get_vector_count()
                info = {
                    "type": self.config.type,
                    "count": count
                }
            
            return info
            
        except Exception as e:
            logger.error(f"获取存储信息失败: {str(e)}")
            raise VectorStoreError(f"获取存储信息失败: {str(e)}")
    
    async def batch_search(self, query_vectors: List[List[float]], top_k: int = 5,
                          similarity_threshold: float = 0.0) -> List[List[SearchResult]]:
        """批量搜索相似向量"""
        self._ensure_initialized()
        
        if not query_vectors:
            return []
        
        try:
            logger.debug(f"批量搜索 {len(query_vectors)} 个查询向量")
            
            if hasattr(self._store, 'batch_search'):
                # 使用向量存储的批量搜索功能
                results = await self._store.batch_search(
                    query_vectors=query_vectors,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold
                )
            else:
                # 逐个搜索
                results = []
                for query_vector in query_vectors:
                    result = await self.search_similar(
                        query_vector=query_vector,
                        top_k=top_k,
                        similarity_threshold=similarity_threshold
                    )
                    results.append(result)
            
            logger.debug(f"批量搜索完成，返回 {len(results)} 组结果")
            return results
            
        except Exception as e:
            logger.error(f"批量搜索失败: {str(e)}")
            raise VectorStoreError(f"批量搜索失败: {str(e)}")


# 向量存储服务接口（保持向后兼容）
class VectorStoreInterface:
    """向量存储服务接口（已弃用，请使用VectorStoreService）"""
    
    def __init__(self):
        import warnings
        warnings.warn(
            "VectorStoreInterface已弃用，请使用VectorStoreService",
            DeprecationWarning,
            stacklevel=2
        )