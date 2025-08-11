"""检索服务测试"""
import pytest
import pytest_asyncio
import tempfile
import uuid
from unittest.mock import Mock, AsyncMock, patch
from typing import List

from rag_system.services.retrieval_service import RetrievalService
from rag_system.models.vector import SearchResult, Vector
from rag_system.models.document import DocumentInfo, DocumentStatus
from rag_system.utils.exceptions import ProcessingError


@pytest_asyncio.fixture
async def retrieval_service():
    """检索服务fixture"""
    temp_dir = tempfile.mkdtemp()
    
    config = {
        'vector_store_type': 'chroma',
        'vector_store_path': temp_dir + '/chroma_db',
        'storage_dir': temp_dir + '/documents',
        'embedding_provider': 'mock',
        'embedding_model': 'test-model',
        'embedding_dimensions': 384,
        'default_top_k': 5,
        'similarity_threshold': 0.7,
        'max_results': 20
    }
    
    service = RetrievalService(config)
    
    # Mock各个子服务
    service.vector_service = Mock()
    service.vector_service.initialize = AsyncMock()
    service.vector_service.cleanup = AsyncMock()
    service.vector_service.search_similar = AsyncMock()
    service.vector_service.get_vectors_by_document = AsyncMock()
    service.vector_service.get_vector_count = AsyncMock(return_value=100)
    service.vector_service.config = Mock()
    service.vector_service.config.type = 'chroma'
    
    service.embedding_service = Mock()
    service.embedding_service.initialize = AsyncMock()
    service.embedding_service.cleanup = AsyncMock()
    service.embedding_service.vectorize_query = AsyncMock()
    service.embedding_service._embedding_config = Mock()
    service.embedding_service._embedding_config.provider = 'mock'
    service.embedding_service._embedding_config.model = 'test-model'
    
    service.document_service = Mock()
    service.document_service.initialize = AsyncMock()
    service.document_service.cleanup = AsyncMock()
    service.document_service.get_document = AsyncMock()
    service.document_service.get_service_stats = AsyncMock(return_value={
        'total_documents': 10,
        'ready_documents': 8
    })
    
    await service.initialize()
    
    yield service
    
    await service.cleanup()
    
    # 清理临时目录
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture
def sample_search_results():
    """示例搜索结果fixture"""
    return [
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content="这是第一个测试文档的内容，包含了相关信息。",
            similarity_score=0.95,
            metadata={"chunk_index": 0}
        ),
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content="这是第二个测试文档的内容，也包含了一些相关信息。",
            similarity_score=0.85,
            metadata={"chunk_index": 1}
        ),
        SearchResult(
            chunk_id=str(uuid.uuid4()),
            document_id=str(uuid.uuid4()),
            content="这是第三个测试文档的内容，相关性较低。",
            similarity_score=0.65,
            metadata={"chunk_index": 0}
        )
    ]


class TestRetrievalService:
    """检索服务测试"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试服务初始化"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = {
                'vector_store_type': 'chroma',
                'vector_store_path': temp_dir + '/chroma_db',
                'embedding_provider': 'mock'
            }
            
            service = RetrievalService(config)
            
            # Mock子服务
            service.vector_service = Mock()
            service.vector_service.initialize = AsyncMock()
            service.embedding_service = Mock()
            service.embedding_service.initialize = AsyncMock()
            service.document_service = Mock()
            service.document_service.initialize = AsyncMock()
            
            await service.initialize()
            
            # 验证子服务初始化
            service.vector_service.initialize.assert_called_once()
            service.embedding_service.initialize.assert_called_once()
            service.document_service.initialize.assert_called_once()
            
            await service.cleanup()
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_search_similar_documents(self, retrieval_service, sample_search_results):
        """测试相似文档搜索"""
        query = "测试查询文本"
        query_vector = [0.1] * 384
        
        # Mock嵌入服务
        retrieval_service.embedding_service.vectorize_query.return_value = query_vector
        
        # Mock向量搜索
        retrieval_service.vector_service.search_similar.return_value = sample_search_results
        
        results = await retrieval_service.search_similar_documents(
            query=query,
            top_k=3,
            similarity_threshold=0.7
        )
        
        # 验证结果
        assert len(results) == 2  # 只有2个结果超过0.7阈值
        assert results[0].similarity_score == 0.95
        assert results[1].similarity_score == 0.85
        
        # 验证调用
        retrieval_service.embedding_service.vectorize_query.assert_called_once_with(query)
        retrieval_service.vector_service.search_similar.assert_called_once_with(
            query_vector=query_vector,
            top_k=3,
            document_ids=None
        )
    
    @pytest.mark.asyncio
    async def test_search_similar_documents_empty_query(self, retrieval_service):
        """测试空查询搜索"""
        with pytest.raises(ProcessingError) as exc_info:
            await retrieval_service.search_similar_documents("")
        
        assert "查询内容不能为空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_by_keywords(self, retrieval_service, sample_search_results):
        """测试关键词搜索"""
        keywords = ["测试", "文档", "内容"]
        
        # Mock相似度搜索
        retrieval_service.embedding_service.vectorize_query.return_value = [0.1] * 384
        retrieval_service.vector_service.search_similar.return_value = sample_search_results
        
        results = await retrieval_service.search_by_keywords(
            keywords=keywords,
            top_k=3
        )
        
        # 验证结果
        assert len(results) == 2  # 过滤后的结果
        
        # 验证调用了相似度搜索
        retrieval_service.embedding_service.vectorize_query.assert_called_once_with("测试 文档 内容")
    
    @pytest.mark.asyncio
    async def test_search_by_keywords_empty(self, retrieval_service):
        """测试空关键词搜索"""
        with pytest.raises(ProcessingError) as exc_info:
            await retrieval_service.search_by_keywords([])
        
        assert "关键词列表不能为空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_search_by_document(self, retrieval_service, sample_search_results):
        """测试基于文档的相似度搜索"""
        document_id = str(uuid.uuid4())
        
        # Mock文档信息
        mock_document = DocumentInfo(
            id=document_id,
            filename="test.txt",
            file_path="/test/test.txt",
            file_size=1000,
            file_type="txt",
            status=DocumentStatus.READY
        )
        retrieval_service.document_service.get_document.return_value = mock_document
        
        # Mock文档向量
        mock_vectors = [
            Vector(
                id=str(uuid.uuid4()),
                document_id=document_id,
                chunk_id=str(uuid.uuid4()),
                embedding=[0.1] * 384,
                metadata={"content": "测试内容"}
            )
        ]
        retrieval_service.vector_service.get_vectors_by_document.return_value = mock_vectors
        
        # Mock搜索结果
        retrieval_service.vector_service.search_similar.return_value = sample_search_results
        
        results = await retrieval_service.search_by_document(
            document_id=document_id,
            top_k=2,
            exclude_self=True
        )
        
        # 验证结果
        assert len(results) == 2
        
        # 验证调用
        retrieval_service.document_service.get_document.assert_called_once_with(document_id)
        retrieval_service.vector_service.get_vectors_by_document.assert_called_once_with(document_id)
    
    @pytest.mark.asyncio
    async def test_search_by_document_no_vectors(self, retrieval_service):
        """测试文档无向量数据的情况"""
        document_id = str(uuid.uuid4())
        
        # Mock文档信息
        mock_document = DocumentInfo(
            id=document_id,
            filename="test.txt",
            file_path="/test/test.txt",
            file_size=1000,
            file_type="txt",
            status=DocumentStatus.READY
        )
        retrieval_service.document_service.get_document.return_value = mock_document
        
        # Mock空向量列表
        retrieval_service.vector_service.get_vectors_by_document.return_value = []
        
        with pytest.raises(ProcessingError) as exc_info:
            await retrieval_service.search_by_document(document_id)
        
        assert "没有向量数据" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_relevant_chunks(self, retrieval_service, sample_search_results):
        """测试获取相关文本块"""
        query = "测试查询"
        
        # Mock搜索
        retrieval_service.embedding_service.vectorize_query.return_value = [0.1] * 384
        retrieval_service.vector_service.search_similar.return_value = sample_search_results
        
        results = await retrieval_service.get_relevant_chunks(
            query=query,
            top_k=3
        )
        
        # 验证结果
        assert len(results) == 2  # 过滤后的结果
        assert all(isinstance(result, SearchResult) for result in results)
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self, retrieval_service, sample_search_results):
        """测试混合搜索"""
        query = "测试混合搜索查询"
        
        # Mock嵌入和搜索
        retrieval_service.embedding_service.vectorize_query.return_value = [0.1] * 384
        retrieval_service.vector_service.search_similar.return_value = sample_search_results
        
        results = await retrieval_service.hybrid_search(
            query=query,
            top_k=3,
            semantic_weight=0.7,
            keyword_weight=0.3
        )
        
        # 验证结果
        assert len(results) <= 3
        assert all(isinstance(result, SearchResult) for result in results)
        
        # 验证调用了两次搜索（语义搜索和关键词搜索）
        assert retrieval_service.vector_service.search_similar.call_count == 2
    
    @pytest.mark.asyncio
    async def test_hybrid_search_invalid_weights(self, retrieval_service):
        """测试混合搜索权重无效的情况"""
        with pytest.raises(ProcessingError) as exc_info:
            await retrieval_service.hybrid_search(
                query="测试",
                semantic_weight=0.8,
                keyword_weight=0.3  # 总和不等于1.0
            )
        
        assert "权重之和必须等于1.0" in str(exc_info.value)
    
    def test_extract_keywords(self, retrieval_service):
        """测试关键词提取"""
        text = "这是一个测试文档，包含了重要的信息和数据。"
        
        keywords = retrieval_service._extract_keywords(text, max_keywords=3)
        
        # 验证结果
        assert isinstance(keywords, list)
        assert len(keywords) <= 3
        assert all(isinstance(keyword, str) for keyword in keywords)
        
        # 验证过滤了停用词
        stop_words = {'的', '了', '在', '是', '我', '有', '和'}
        assert not any(word in stop_words for word in keywords)
    
    def test_merge_search_results(self, retrieval_service):
        """测试搜索结果合并"""
        # 创建测试数据
        chunk_id1 = str(uuid.uuid4())
        chunk_id2 = str(uuid.uuid4())
        chunk_id3 = str(uuid.uuid4())
        
        semantic_results = [
            SearchResult(
                chunk_id=chunk_id1,
                document_id=str(uuid.uuid4()),
                content="内容1",
                similarity_score=0.9,
                metadata={}
            ),
            SearchResult(
                chunk_id=chunk_id2,
                document_id=str(uuid.uuid4()),
                content="内容2",
                similarity_score=0.8,
                metadata={}
            )
        ]
        
        keyword_results = [
            SearchResult(
                chunk_id=chunk_id1,  # 重复的chunk_id
                document_id=str(uuid.uuid4()),
                content="内容1",
                similarity_score=0.7,
                metadata={}
            ),
            SearchResult(
                chunk_id=chunk_id3,  # 新的chunk_id
                document_id=str(uuid.uuid4()),
                content="内容3",
                similarity_score=0.6,
                metadata={}
            )
        ]
        
        merged_results = retrieval_service._merge_search_results(
            semantic_results, keyword_results, 0.7, 0.3
        )
        
        # 验证结果
        assert len(merged_results) == 3
        
        # 验证分数合并（chunk_id1应该有合并的分数）
        chunk1_result = next(r for r in merged_results if r.chunk_id == chunk_id1)
        expected_score = 0.9 * 0.7 + 0.7 * 0.3  # 语义分数 * 权重 + 关键词分数 * 权重
        assert abs(chunk1_result.similarity_score - expected_score) < 0.01
        
        # 验证排序（按相似度降序）
        assert merged_results[0].similarity_score >= merged_results[1].similarity_score >= merged_results[2].similarity_score
    
    @pytest.mark.asyncio
    async def test_get_document_statistics(self, retrieval_service):
        """测试获取文档统计信息"""
        document_id = str(uuid.uuid4())
        
        # Mock文档信息
        from datetime import datetime
        mock_document = DocumentInfo(
            id=document_id,
            filename="test.txt",
            file_path="/test/test.txt",
            file_size=1000,
            file_type="txt",
            status=DocumentStatus.READY,
            upload_time=datetime.now()
        )
        retrieval_service.document_service.get_document.return_value = mock_document
        
        # Mock向量数据
        mock_vectors = [
            Vector(
                id=str(uuid.uuid4()),
                document_id=document_id,
                chunk_id=str(uuid.uuid4()),
                embedding=[0.1] * 384,
                metadata={"content": "测试内容1"}
            ),
            Vector(
                id=str(uuid.uuid4()),
                document_id=document_id,
                chunk_id=str(uuid.uuid4()),
                embedding=[0.2] * 384,
                metadata={"content": "测试内容2"}
            )
        ]
        retrieval_service.vector_service.get_vectors_by_document.return_value = mock_vectors
        
        stats = await retrieval_service.get_document_statistics(document_id)
        
        # 验证统计信息
        assert stats["document_id"] == document_id
        assert stats["filename"] == "test.txt"
        assert stats["chunk_count"] == 2
        assert stats["embedding_dimensions"] == 384
        assert "created_at" in stats
    
    @pytest.mark.asyncio
    async def test_get_service_stats(self, retrieval_service):
        """测试获取服务统计信息"""
        stats = await retrieval_service.get_service_stats()
        
        # 验证统计信息
        assert stats["service_name"] == "RetrievalService"
        assert "vector_count" in stats
        assert "document_count" in stats
        assert "ready_documents" in stats
        assert "default_top_k" in stats
        assert "similarity_threshold" in stats
        assert "embedding_provider" in stats
        assert "vector_store_type" in stats
    
    @pytest.mark.asyncio
    async def test_test_search(self, retrieval_service, sample_search_results):
        """测试搜索功能测试"""
        # Mock搜索
        retrieval_service.embedding_service.vectorize_query.return_value = [0.1] * 384
        retrieval_service.vector_service.search_similar.return_value = sample_search_results
        
        result = await retrieval_service.test_search("测试查询")
        
        # 验证测试结果
        assert result["success"] is True
        assert result["test_query"] == "测试查询"
        assert result["result_count"] == 2  # 过滤后的结果数
        assert "processing_time" in result
        assert "top_similarity" in result
        assert "service_stats" in result
    
    @pytest.mark.asyncio
    async def test_search_with_document_filter(self, retrieval_service, sample_search_results):
        """测试带文档过滤的搜索"""
        query = "测试查询"
        document_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
        
        # Mock搜索
        retrieval_service.embedding_service.vectorize_query.return_value = [0.1] * 384
        retrieval_service.vector_service.search_similar.return_value = sample_search_results
        
        results = await retrieval_service.search_similar_documents(
            query=query,
            top_k=5,
            document_ids=document_ids
        )
        
        # 验证调用参数
        retrieval_service.vector_service.search_similar.assert_called_once_with(
            query_vector=[0.1] * 384,
            top_k=5,
            document_ids=document_ids
        )
    
    @pytest.mark.asyncio
    async def test_max_results_limit(self, retrieval_service, sample_search_results):
        """测试最大结果数限制"""
        query = "测试查询"
        
        # Mock搜索
        retrieval_service.embedding_service.vectorize_query.return_value = [0.1] * 384
        retrieval_service.vector_service.search_similar.return_value = sample_search_results
        
        # 请求超过最大限制的结果数
        results = await retrieval_service.search_similar_documents(
            query=query,
            top_k=100  # 超过max_results=20
        )
        
        # 验证调用时使用了限制后的数量
        retrieval_service.vector_service.search_similar.assert_called_once_with(
            query_vector=[0.1] * 384,
            top_k=20,  # 应该被限制为max_results
            document_ids=None
        )
    
    @pytest.mark.asyncio
    async def test_error_handling(self, retrieval_service):
        """测试错误处理"""
        query = "测试查询"
        
        # Mock嵌入服务抛出异常
        retrieval_service.embedding_service.vectorize_query.side_effect = Exception("嵌入服务错误")
        
        with pytest.raises(ProcessingError) as exc_info:
            await retrieval_service.search_similar_documents(query)
        
        assert "相似度搜索失败" in str(exc_info.value)
        assert "嵌入服务错误" in str(exc_info.value)