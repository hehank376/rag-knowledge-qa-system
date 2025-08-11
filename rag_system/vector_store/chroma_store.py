"""
Chroma向量数据库实现
"""
import logging
from typing import List, Dict, Any, Optional
import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
except ImportError:
    chromadb = None

from ..models.vector import Vector, SearchResult
from ..models.config import VectorStoreConfig
from ..utils.exceptions import VectorStoreError
from .base import VectorStoreBase

logger = logging.getLogger(__name__)



class ChromaClientManager:
    """Chroma客户端管理器，解决单例冲突问题"""
    _clients = {}
    
    @classmethod
    def get_client(cls, persist_directory: str):
        """获取或创建Chroma客户端"""
        if persist_directory not in cls._clients:
            try:
                settings = Settings(
                    persist_directory=persist_directory,
                    anonymized_telemetry=False
                )
                cls._clients[persist_directory] = chromadb.PersistentClient(
                    path=persist_directory,
                    settings=settings
                )
            except ValueError as e:
                if "already exists" in str(e):
                    # 如果实例已存在，尝试获取现有实例
                    cls._clients[persist_directory] = chromadb.PersistentClient(
                        path=persist_directory
                    )
                else:
                    raise e
        return cls._clients[persist_directory]
    
    @classmethod
    def cleanup(cls):
        """清理所有客户端"""
        cls._clients.clear()

class ChromaVectorStore(VectorStoreBase):
    """Chroma向量数据库实现"""
    
    def __init__(self, config: VectorStoreConfig):
        super().__init__(config)
        
        if chromadb is None:
            raise VectorStoreError("ChromaDB未安装，请运行: pip install chromadb")
        
        self._client = None
        self._collection = None
        self._executor = ThreadPoolExecutor(max_workers=4)
    
    async def initialize(self) -> None:
        """初始化Chroma客户端和集合"""
        try:
            logger.info(f"初始化Chroma向量数据库: {self.config.persist_directory}")
            
            # 在线程池中执行同步操作
            await asyncio.get_event_loop().run_in_executor(
                self._executor, self._init_sync
            )
            
            self._initialized = True
            logger.info("Chroma向量数据库初始化成功")
            
        except Exception as e:
            logger.error(f"Chroma向量数据库初始化失败: {str(e)}")
            raise VectorStoreError(f"Chroma初始化失败: {str(e)}")
    
    def _init_sync(self) -> None:
        """同步初始化方法"""
        # 使用单例管理器获取客户端
        self._client = ChromaClientManager.get_client(self.config.persist_directory)
        
        # 获取或创建集合
        try:
            self._collection = self._client.get_collection(
                name=self.config.collection_name
            )
            logger.info(f"使用现有集合: {self.config.collection_name}")
        except Exception:
            # 集合不存在，创建新集合
            self._collection = self._client.create_collection(
                name=self.config.collection_name,
                metadata={"description": "RAG知识库向量存储", "hnsw:space": "cosine"}
            )
            logger.info(f"创建新集合: {self.config.collection_name}")
    
    async def add_vectors(self, vectors: List[Vector]) -> bool:
        """添加向量到Chroma"""
        if not self._initialized:
            raise VectorStoreError("向量存储未初始化")
        
        if not self._validate_vectors(vectors):
            return False
        
        try:
            logger.info(f"添加 {len(vectors)} 个向量到Chroma")
            
            # 准备数据
            ids = []
            embeddings = []
            metadatas = []
            documents = []
            
            for vector in vectors:
                ids.append(vector.id)
                embeddings.append(vector.embedding)
                
                # 准备元数据
                metadata = {
                    "document_id": vector.document_id,
                    "chunk_id": vector.chunk_id,
                    **vector.metadata
                }
                metadatas.append(metadata)
                
                # 使用实际的文档内容
                content = vector.metadata.get("content", vector.chunk_id)
                documents.append(content)
            
            # 在线程池中执行添加操作
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
            )
            
            logger.info(f"成功添加 {len(vectors)} 个向量")
            return True
            
        except Exception as e:
            logger.error(f"添加向量失败: {str(e)}")
            raise VectorStoreError(f"添加向量失败: {str(e)}")
    
    async def search_similar(self, query_vector: List[float], top_k: int = 5,
                           similarity_threshold: float = 0.0) -> List[SearchResult]:
        """搜索相似向量"""
        if not self._initialized:
            raise VectorStoreError("向量存储未初始化")
        
        if not query_vector or not isinstance(query_vector, list):
            raise VectorStoreError("查询向量无效")
        
        try:
            logger.debug(f"搜索相似向量，top_k={top_k}, threshold={similarity_threshold}")
            
            # 在线程池中执行查询
            results = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._collection.query(
                    query_embeddings=[query_vector],
                    n_results=top_k,
                    include=["metadatas", "distances", "documents"]
                )
            )
            
            # 处理结果
            search_results = []
            
            if results and results.get("ids") and len(results["ids"]) > 0:
                ids = results["ids"][0]
                distances = results.get("distances", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                documents = results.get("documents", [[]])[0]
                
                for i, vector_id in enumerate(ids):
                    # Chroma返回的是余弦距离，需要转换为相似度分数
                    # 余弦距离范围是[0, 2]，余弦相似度 = 1 - 余弦距离/2
                    distance = distances[i] if i < len(distances) else 2.0
                    similarity_score = max(0.0, 1.0 - distance / 2.0)
                    
                    # 应用相似度阈值
                    if similarity_score < similarity_threshold:
                        continue
                    
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    document = documents[i] if i < len(documents) else ""
                    
                    search_result = SearchResult(
                        chunk_id=vector_id,
                        document_id=metadata.get("document_id", ""),
                        content=document,
                        similarity_score=similarity_score,
                        metadata=metadata
                    )
                    search_results.append(search_result)
            
            logger.debug(f"找到 {len(search_results)} 个相似向量")
            return search_results
            
        except Exception as e:
            logger.error(f"搜索相似向量失败: {str(e)}")
            raise VectorStoreError(f"搜索失败: {str(e)}")
    
    async def delete_vectors(self, document_id: str) -> bool:
        """删除指定文档的所有向量"""
        if not self._initialized:
            raise VectorStoreError("向量存储未初始化")
        
        try:
            logger.info(f"删除文档 {document_id} 的所有向量")
            
            # 先查询要删除的向量
            results = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._collection.get(
                    where={"document_id": document_id},
                    include=["metadatas"]
                )
            )
            
            if results and results.get("ids"):
                ids_to_delete = results["ids"]
                
                # 删除向量
                await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    lambda: self._collection.delete(ids=ids_to_delete)
                )
                
                logger.info(f"成功删除 {len(ids_to_delete)} 个向量")
                return True
            else:
                logger.info(f"文档 {document_id} 没有找到向量")
                return True
            
        except Exception as e:
            logger.error(f"删除向量失败: {str(e)}")
            raise VectorStoreError(f"删除向量失败: {str(e)}")
    
    async def update_vectors(self, document_id: str, vectors: List[Vector]) -> bool:
        """更新指定文档的向量"""
        try:
            # 先删除旧向量
            await self.delete_vectors(document_id)
            
            # 添加新向量
            return await self.add_vectors(vectors)
            
        except Exception as e:
            logger.error(f"更新向量失败: {str(e)}")
            raise VectorStoreError(f"更新向量失败: {str(e)}")
    
    async def get_vector_count(self) -> int:
        """获取向量总数"""
        if not self._initialized:
            raise VectorStoreError("向量存储未初始化")
        
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._collection.count()
            )
            return result
            
        except Exception as e:
            logger.error(f"获取向量数量失败: {str(e)}")
            raise VectorStoreError(f"获取向量数量失败: {str(e)}")
    
    async def clear_all(self) -> bool:
        """清空所有向量"""
        if not self._initialized:
            raise VectorStoreError("向量存储未初始化")
        
        try:
            logger.warning("清空所有向量数据")
            
            # 删除集合
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._client.delete_collection(self.config.collection_name)
            )
            
            # 重新创建集合
            await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._client.create_collection(
                    name=self.config.collection_name,
                    metadata={"description": "RAG知识库向量存储"}
                )
            )
            
            self._collection = self._client.get_collection(self.config.collection_name)
            
            logger.info("成功清空所有向量数据")
            return True
            
        except Exception as e:
            logger.error(f"清空向量数据失败: {str(e)}")
            raise VectorStoreError(f"清空向量数据失败: {str(e)}")
    
    async def cleanup(self) -> None:
        """清理资源"""
        try:
            if self._executor:
                self._executor.shutdown(wait=True)
                self._executor = None
            
            self._collection = None
            self._client = None
            self._initialized = False
            
            logger.info("Chroma向量存储资源清理完成")
            
        except Exception as e:
            logger.error(f"清理资源失败: {str(e)}")
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """获取集合信息"""
        if not self._initialized:
            raise VectorStoreError("向量存储未初始化")
        
        try:
            count = await self.get_vector_count()
            
            return {
                "name": self.config.collection_name,
                "count": count,
                "persist_directory": self.config.persist_directory
            }
            
        except Exception as e:
            logger.error(f"获取集合信息失败: {str(e)}")
            raise VectorStoreError(f"获取集合信息失败: {str(e)}")
    
    async def batch_search(self, query_vectors: List[List[float]], top_k: int = 5,
                          similarity_threshold: float = 0.0) -> List[List[SearchResult]]:
        """批量搜索相似向量"""
        if not self._initialized:
            raise VectorStoreError("向量存储未初始化")
        
        try:
            logger.debug(f"批量搜索 {len(query_vectors)} 个查询向量")
            
            # 在线程池中执行批量查询
            results = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                lambda: self._collection.query(
                    query_embeddings=query_vectors,
                    n_results=top_k,
                    include=["metadatas", "distances", "documents"]
                )
            )
            
            # 处理批量结果
            batch_results = []
            
            if results and results.get("ids"):
                for query_idx in range(len(query_vectors)):
                    query_results = []
                    
                    if query_idx < len(results["ids"]):
                        ids = results["ids"][query_idx]
                        distances = results.get("distances", [])[query_idx] if query_idx < len(results.get("distances", [])) else []
                        metadatas = results.get("metadatas", [])[query_idx] if query_idx < len(results.get("metadatas", [])) else []
                        documents = results.get("documents", [])[query_idx] if query_idx < len(results.get("documents", [])) else []
                        
                        for i, vector_id in enumerate(ids):
                            distance = distances[i] if i < len(distances) else 1.0
                            similarity_score = max(0.0, 1.0 - distance)
                            
                            if similarity_score < similarity_threshold:
                                continue
                            
                            metadata = metadatas[i] if i < len(metadatas) else {}
                            document = documents[i] if i < len(documents) else ""
                            
                            search_result = SearchResult(
                                chunk_id=vector_id,
                                document_id=metadata.get("document_id", ""),
                                content=document,
                                similarity_score=similarity_score,
                                metadata=metadata
                            )
                            query_results.append(search_result)
                    
                    batch_results.append(query_results)
            
            logger.debug(f"批量搜索完成，返回 {len(batch_results)} 组结果")
            return batch_results
            
        except Exception as e:
            logger.error(f"批量搜索失败: {str(e)}")
            raise VectorStoreError(f"批量搜索失败: {str(e)}")