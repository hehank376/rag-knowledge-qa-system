"""文档检索和相似度搜索服务"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..models.vector import SearchResult
from ..models.document import DocumentInfo
from ..models.config import VectorStoreConfig
from .vector_service import VectorStoreService
from .embedding_service import EmbeddingService
from .document_service import DocumentService
from ..utils.exceptions import ProcessingError, VectorStoreError
from .base import BaseService

logger = logging.getLogger(__name__)


class RetrievalService(BaseService):
    """文档检索和相似度搜索服务"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        
        # 初始化向量存储服务
        vector_config = VectorStoreConfig(
            type=self.config.get('vector_store_type', 'chroma'),
            persist_directory=self.config.get('vector_store_path', './chroma_db'),
            collection_name=self.config.get('collection_name', 'documents')
        )
        self.vector_service = VectorStoreService(vector_config)
        
        # 初始化嵌入服务
        embedding_config = {
            'provider': self.config.get('embedding_provider', 'mock'),
            'model': self.config.get('embedding_model', 'text-embedding-ada-002'),
            'api_key': self.config.get('embedding_api_key'),
            'api_base': self.config.get('embedding_api_base'),
            'batch_size': self.config.get('embedding_batch_size', 100),
            'dimensions': self.config.get('embedding_dimensions'),
            'timeout': self.config.get('embedding_timeout', 30)
        }
        self.embedding_service = EmbeddingService(embedding_config)
        
        # 初始化文档服务（用于获取文档元数据）
        document_config = {
            'storage_dir': self.config.get('storage_dir', './documents'),
            'vector_store_type': self.config.get('vector_store_type', 'chroma'),
            'vector_store_path': self.config.get('vector_store_path', './chroma_db'),
            'embedding_provider': self.config.get('embedding_provider', 'mock'),
            'embedding_model': self.config.get('embedding_model', 'text-embedding-ada-002'),
            'embedding_api_key': self.config.get('embedding_api_key'),
            'database_url': self.config.get('database_url', 'sqlite:///./database/documents.db')
        }
        self.document_service = DocumentService(document_config)
        
        # 检索配置
        self.default_top_k = self.config.get('default_top_k', 5)
        self.similarity_threshold = self.config.get('similarity_threshold', 0.7)
        self.max_results = self.config.get('max_results', 20)
    
    async def initialize(self) -> None:
        """初始化检索服务"""
        try:
            logger.info("初始化文档检索服务")
            
            # 初始化各个服务
            await self.vector_service.initialize()
            await self.embedding_service.initialize()
            await self.document_service.initialize()
            
            logger.info("文档检索服务初始化成功")
            
        except Exception as e:
            logger.error(f"文档检索服务初始化失败: {str(e)}")
            raise ProcessingError(f"文档检索服务初始化失败: {str(e)}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self.document_service:
                await self.document_service.cleanup()
            
            if self.embedding_service:
                await self.embedding_service.cleanup()
            
            if self.vector_service:
                await self.vector_service.cleanup()
            
            logger.info("文档检索服务资源清理完成")
            
        except Exception as e:
            logger.error(f"文档检索服务清理失败: {str(e)}")
    
    async def search_similar_documents(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
        document_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """搜索相似文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量，默认使用配置值
            similarity_threshold: 相似度阈值，默认使用配置值
            document_ids: 限制搜索的文档ID列表，None表示搜索所有文档
            
        Returns:
            搜索结果列表
        """
        try:
            logger.info(f"开始相似度搜索: query='{query[:50]}...', top_k={top_k}")
            print(f"开始相似度搜索: query='{query[:50]}...', top_k={top_k}")
            
            if not query or not query.strip():
                raise ProcessingError("查询内容不能为空")
            
            # 使用默认值
            top_k = top_k or self.default_top_k
            similarity_threshold = similarity_threshold or self.similarity_threshold
            
            # 限制最大结果数
            top_k = min(top_k, self.max_results)
            
            # 将查询文本向量化
            query_vector = await self.embedding_service.vectorize_query(query)
            #print(f"向量化完成: 问题生成向量内容={(query_vector)}")
            print(f"向量化完成: 问题生成向量数={len(query_vector)}")
            logger.info(f"向量化完成: 问题生成向量数={len(query_vector)}")
            # 执行向量搜索
            search_results = await self.vector_service.search_similar(
                query_vector=query_vector,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            # 如果指定了文档ID过滤，则过滤结果
            if document_ids:
                search_results = [
                    result for result in search_results 
                    if result.document_id in document_ids
                ]
            
            # 过滤低相似度结果
            filtered_results = [
                result for result in search_results 
                if result.similarity_score >= similarity_threshold
            ]
            
            logger.info(
                f"相似度搜索完成: 找到 {len(search_results)} 个结果, "
                f"过滤后 {len(filtered_results)} 个结果"
            )
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"相似度搜索失败: {str(e)}")
            raise ProcessingError(f"相似度搜索失败: {str(e)}")
    
    async def search_by_keywords(
        self, 
        keywords: List[str], 
        top_k: Optional[int] = None,
        document_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """基于关键词搜索文档
        
        Args:
            keywords: 关键词列表
            top_k: 返回结果数量
            document_ids: 限制搜索的文档ID列表
            
        Returns:
            搜索结果列表
        """
        try:
            logger.info(f"开始关键词搜索: keywords={keywords}, top_k={top_k}")
            
            if not keywords:
                raise ProcessingError("关键词列表不能为空")
            
            # 将关键词组合成查询文本
            query = " ".join(keywords)
            
            # 使用相似度搜索
            results = await self.search_similar_documents(
                query=query,
                top_k=top_k,
                document_ids=document_ids
            )
            
            logger.info(f"关键词搜索完成: 找到 {len(results)} 个结果")
            return results
            
        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            raise ProcessingError(f"关键词搜索失败: {str(e)}")
    
    async def search_by_document(
        self, 
        document_id: str, 
        top_k: Optional[int] = None,
        exclude_self: bool = True
    ) -> List[SearchResult]:
        """基于文档内容搜索相似文档
        
        Args:
            document_id: 参考文档ID
            top_k: 返回结果数量
            exclude_self: 是否排除自身文档
            
        Returns:
            搜索结果列表
        """
        try:
            logger.info(f"开始文档相似度搜索: document_id={document_id}, top_k={top_k}")
            
            # 获取文档信息
            document = await self.document_service.get_document(document_id)
            
            # 获取文档的向量表示（使用第一个文本块的向量作为代表）
            document_vectors = await self.vector_service.get_vectors_by_document(document_id)
            
            if not document_vectors:
                raise ProcessingError(f"文档 {document_id} 没有向量数据")
            
            # 使用第一个向量作为查询向量
            query_vector = document_vectors[0].embedding
            
            # 执行向量搜索
            search_results = await self.vector_service.search_similar(
                query_vector=query_vector,
                top_k=(top_k or self.default_top_k) + (1 if exclude_self else 0)
            )
            
            # 排除自身文档（如果需要）
            if exclude_self:
                search_results = [
                    result for result in search_results 
                    if result.document_id != document_id
                ]
            
            # 限制结果数量
            if top_k:
                search_results = search_results[:top_k]
            
            logger.info(f"文档相似度搜索完成: 找到 {len(search_results)} 个结果")
            return search_results
            
        except Exception as e:
            logger.error(f"文档相似度搜索失败: {str(e)}")
            raise ProcessingError(f"文档相似度搜索失败: {str(e)}")
    
    async def get_relevant_chunks(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        document_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """获取与查询相关的文本块
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            document_ids: 限制搜索的文档ID列表
            
        Returns:
            相关文本块列表
        """
        try:
            logger.info(f"开始获取相关文本块: query='{query[:50]}...', top_k={top_k}")
            
            # 执行相似度搜索
            results = await self.search_similar_documents(
                query=query,
                top_k=top_k,
                document_ids=document_ids
            )
            
            logger.info(f"获取相关文本块完成: 找到 {len(results)} 个块")
            return results
            
        except Exception as e:
            logger.error(f"获取相关文本块失败: {str(e)}")
            raise ProcessingError(f"获取相关文本块失败: {str(e)}")
    
    async def hybrid_search(
        self, 
        query: str, 
        top_k: Optional[int] = None,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        document_ids: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """混合搜索（语义搜索 + 关键词搜索）
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            semantic_weight: 语义搜索权重
            keyword_weight: 关键词搜索权重
            document_ids: 限制搜索的文档ID列表
            
        Returns:
            混合搜索结果列表
        """
        try:
            logger.info(f"开始混合搜索: query='{query[:50]}...', top_k={top_k}")
            
            if abs(semantic_weight + keyword_weight - 1.0) > 0.01:
                raise ProcessingError("语义搜索权重和关键词搜索权重之和必须等于1.0")
            
            top_k = top_k or self.default_top_k
            
            # 执行语义搜索
            semantic_results = await self.search_similar_documents(
                query=query,
                top_k=top_k * 2,  # 获取更多结果用于混合
                document_ids=document_ids
            )
            
            # 提取关键词进行关键词搜索
            keywords = self._extract_keywords(query)
            keyword_results = await self.search_by_keywords(
                keywords=keywords,
                top_k=top_k * 2,
                document_ids=document_ids
            )
            
            # 合并和重新排序结果
            hybrid_results = self._merge_search_results(
                semantic_results, keyword_results,
                semantic_weight, keyword_weight
            )
            
            # 限制结果数量
            hybrid_results = hybrid_results[:top_k]
            
            logger.info(f"混合搜索完成: 找到 {len(hybrid_results)} 个结果")
            return hybrid_results
            
        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            raise ProcessingError(f"混合搜索失败: {str(e)}")
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """从文本中提取关键词（简单实现）"""
        # 简单的关键词提取：分词并过滤停用词
        import re
        
        # 移除标点符号并分词
        words = re.findall(r'\b\w+\b', text.lower())
        
        # 简单的停用词列表
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        
        # 过滤停用词和短词
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        # 去重并限制数量
        keywords = list(dict.fromkeys(keywords))[:max_keywords]
        
        return keywords
    
    def _merge_search_results(
        self, 
        semantic_results: List[SearchResult], 
        keyword_results: List[SearchResult],
        semantic_weight: float, 
        keyword_weight: float
    ) -> List[SearchResult]:
        """合并语义搜索和关键词搜索结果"""
        # 创建结果字典，以chunk_id为键
        merged_results = {}
        
        # 处理语义搜索结果
        for result in semantic_results:
            chunk_id = result.chunk_id
            merged_results[chunk_id] = SearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                content=result.content,
                similarity_score=result.similarity_score * semantic_weight,
                metadata=result.metadata
            )
        
        # 处理关键词搜索结果
        for result in keyword_results:
            chunk_id = result.chunk_id
            if chunk_id in merged_results:
                # 合并分数
                merged_results[chunk_id].similarity_score += result.similarity_score * keyword_weight
            else:
                # 新结果
                merged_results[chunk_id] = SearchResult(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    content=result.content,
                    similarity_score=result.similarity_score * keyword_weight,
                    metadata=result.metadata
                )
        
        # 按相似度排序
        sorted_results = sorted(
            merged_results.values(), 
            key=lambda x: x.similarity_score, 
            reverse=True
        )
        
        return sorted_results
    
    async def get_document_statistics(self, document_id: str) -> Dict[str, Any]:
        """获取文档的检索统计信息"""
        try:
            logger.debug(f"获取文档检索统计: {document_id}")
            
            # 获取文档信息
            document = await self.document_service.get_document(document_id)
            
            # 获取文档的向量数据
            vectors = await self.vector_service.get_vectors_by_document(document_id)
            
            stats = {
                "document_id": document_id,
                "filename": document.filename,
                "chunk_count": len(vectors),
                "total_content_length": sum(len(v.metadata.get('content', '')) for v in vectors),
                "average_chunk_length": sum(len(v.metadata.get('content', '')) for v in vectors) / len(vectors) if vectors else 0,
                "embedding_dimensions": len(vectors[0].embedding) if vectors else 0,
                "created_at": document.upload_time.isoformat() if document.upload_time else None
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取文档统计失败: {document_id}, 错误: {str(e)}")
            raise ProcessingError(f"获取文档统计失败: {str(e)}")
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """获取检索服务统计信息"""
        try:
            # 获取向量存储统计
            vector_count = await self.vector_service.get_vector_count()
            
            # 获取文档统计
            document_stats = await self.document_service.get_service_stats()
            
            stats = {
                "service_name": "RetrievalService",
                "vector_count": vector_count,
                "document_count": document_stats.get('total_documents', 0),
                "ready_documents": document_stats.get('ready_documents', 0),
                "default_top_k": self.default_top_k,
                "similarity_threshold": self.similarity_threshold,
                "max_results": self.max_results,
                "embedding_provider": self.embedding_service._embedding_config.provider,
                "embedding_model": self.embedding_service._embedding_config.model,
                "vector_store_type": self.vector_service.config.type
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取检索服务统计失败: {str(e)}")
            return {"error": str(e)}
    
    async def test_search(self, test_query: str = "测试查询") -> Dict[str, Any]:
        """测试搜索功能"""
        try:
            start_time = datetime.now()
            
            # 测试相似度搜索
            results = await self.search_similar_documents(
                query=test_query,
                top_k=3
            )
            
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "test_query": test_query,
                "result_count": len(results),
                "processing_time": processing_time,
                "top_similarity": results[0].similarity_score if results else 0.0,
                "service_stats": await self.get_service_stats()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "test_query": test_query
            }