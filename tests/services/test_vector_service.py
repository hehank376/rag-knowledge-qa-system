"""
向量存储服务测试
"""
import pytest
import pytest_asyncio
import tempfile
import shutil
import os
import uuid
from typing import List

from rag_system.models.config import VectorStoreConfig
from rag_system.models.vector import Vector, SearchResult
from rag_system.services.vector_service import VectorStoreService
from rag_system.utils.exceptions import VectorStoreError, ConfigurationError


@pytest_asyncio.fixture
async def vector_service():
    """向量存储服务fixture"""
    temp_dir = tempfile.mkdtemp()
    
    config = VectorStoreConfig(
        type="chroma",
        persist_directory=temp_dir,
        collection_name="test_service"
    )
    
    service = VectorStoreService(config)
    await service.initialize()
    
    yield service
    
    await service.cleanup()
    # 等待一段时间确保文件被释放
    import time
    time.sleep(0.1)
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except PermissionError:
        # 在Windows上可能会有文件锁定问题，忽略清理错误
        pass


@pytest.fixture
def sample_vectors():
    """示例向量数据"""
    doc_id = str(uuid.uuid4())
    
    vectors = []
    for i in range(3):
        vector = Vector(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            chunk_id=str(uuid.uuid4()),
            embedding=[0.1 * (i + 1), 0.2 * (i + 1), 0.3 * (i + 1)],
            metadata={"chunk_index": i}
        )
        vectors.append(vector)
    
    return vectors


class TestVectorStoreService:
    """向量存储服务测试"""
    
    @pytest.mark.asyncio
    async def test_initialization_chroma(self):
        """测试Chroma初始化"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = VectorStoreConfig(
                type="chroma",
                persist_directory=temp_dir,
                collection_name="test_init"
            )
            
            service = VectorStoreService(config)
            await service.initialize()
            
            # 验证服务可以正常工作
            count = await service.get_vector_count()
            assert count == 0
            
            await service.cleanup()
            
        finally:
            # 等待一段时间确保文件被释放
            import time
            time.sleep(0.1)
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except PermissionError:
                # 在Windows上可能会有文件锁定问题，忽略清理错误
                pass
    
    @pytest.mark.asyncio
    async def test_initialization_unsupported_type(self):
        """测试不支持的向量存储类型"""
        config = VectorStoreConfig(
            type="unsupported",
            persist_directory="./test",
            collection_name="test"
        )
        
        service = VectorStoreService(config)
        
        with pytest.raises(VectorStoreError):
            await service.initialize()
    
    @pytest.mark.asyncio
    async def test_add_vectors(self, vector_service, sample_vectors):
        """测试添加向量"""
        result = await vector_service.add_vectors(sample_vectors)
        assert result is True
        
        # 验证向量数量
        count = await vector_service.get_vector_count()
        assert count == len(sample_vectors)
    
    @pytest.mark.asyncio
    async def test_add_empty_vectors(self, vector_service):
        """测试添加空向量列表"""
        result = await vector_service.add_vectors([])
        assert result is True  # 空列表应该返回True但不做任何操作
    
    @pytest.mark.asyncio
    async def test_search_similar(self, vector_service, sample_vectors):
        """测试相似向量搜索"""
        # 添加向量
        await vector_service.add_vectors(sample_vectors)
        
        # 搜索相似向量
        query_vector = [0.1, 0.2, 0.3]
        results = await vector_service.search_similar(query_vector, top_k=2)
        
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)
        
        # 验证结果按相似度排序
        if len(results) > 1:
            assert results[0].similarity_score >= results[1].similarity_score
    
    @pytest.mark.asyncio
    async def test_search_with_threshold(self, vector_service, sample_vectors):
        """测试带阈值的搜索"""
        await vector_service.add_vectors(sample_vectors)
        
        # 使用阈值搜索
        query_vector = [0.1, 0.2, 0.3]
        results = await vector_service.search_similar(
            query_vector, 
            top_k=5, 
            similarity_threshold=0.5
        )
        
        # 所有结果的相似度都应该高于阈值
        for result in results:
            assert result.similarity_score >= 0.5
    
    @pytest.mark.asyncio
    async def test_search_invalid_parameters(self, vector_service):
        """测试无效搜索参数"""
        # 空查询向量
        with pytest.raises(VectorStoreError):
            await vector_service.search_similar([], top_k=5)
        
        # 无效top_k
        with pytest.raises(VectorStoreError):
            await vector_service.search_similar([0.1, 0.2], top_k=0)
        
        with pytest.raises(VectorStoreError):
            await vector_service.search_similar([0.1, 0.2], top_k=-1)
    
    @pytest.mark.asyncio
    async def test_delete_vectors(self, vector_service, sample_vectors):
        """测试删除向量"""
        # 添加向量
        await vector_service.add_vectors(sample_vectors)
        
        # 验证向量已添加
        count_before = await vector_service.get_vector_count()
        assert count_before == len(sample_vectors)
        
        # 删除向量
        document_id = sample_vectors[0].document_id
        result = await vector_service.delete_vectors(document_id)
        assert result is True
        
        # 验证向量已删除
        count_after = await vector_service.get_vector_count()
        assert count_after == 0
    
    @pytest.mark.asyncio
    async def test_delete_empty_document_id(self, vector_service):
        """测试删除空文档ID"""
        with pytest.raises(VectorStoreError):
            await vector_service.delete_vectors("")
    
    @pytest.mark.asyncio
    async def test_update_vectors(self, vector_service, sample_vectors):
        """测试更新向量"""
        # 添加初始向量
        await vector_service.add_vectors(sample_vectors)
        
        # 创建新向量
        document_id = sample_vectors[0].document_id
        new_vectors = [
            Vector(
                id=str(uuid.uuid4()),
                document_id=document_id,
                chunk_id=str(uuid.uuid4()),
                embedding=[0.5, 0.6, 0.7],
                metadata={"updated": True}
            )
        ]
        
        # 更新向量
        result = await vector_service.update_vectors(document_id, new_vectors)
        assert result is True
        
        # 验证向量数量
        count = await vector_service.get_vector_count()
        assert count == len(new_vectors)
    
    @pytest.mark.asyncio
    async def test_update_with_empty_vectors(self, vector_service, sample_vectors):
        """测试用空向量列表更新"""
        # 添加初始向量
        await vector_service.add_vectors(sample_vectors)
        
        # 用空列表更新（应该删除所有向量）
        document_id = sample_vectors[0].document_id
        result = await vector_service.update_vectors(document_id, [])
        assert result is True
        
        # 验证向量已删除
        count = await vector_service.get_vector_count()
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_update_empty_document_id(self, vector_service):
        """测试更新空文档ID"""
        with pytest.raises(VectorStoreError):
            await vector_service.update_vectors("", [])
    
    @pytest.mark.asyncio
    async def test_get_vector_count(self, vector_service, sample_vectors):
        """测试获取向量数量"""
        # 初始数量
        count = await vector_service.get_vector_count()
        assert count == 0
        
        # 添加向量后
        await vector_service.add_vectors(sample_vectors)
        count = await vector_service.get_vector_count()
        assert count == len(sample_vectors)
    
    @pytest.mark.asyncio
    async def test_clear_all_vectors(self, vector_service, sample_vectors):
        """测试清空所有向量"""
        # 添加向量
        await vector_service.add_vectors(sample_vectors)
        
        # 清空
        result = await vector_service.clear_all_vectors()
        assert result is True
        
        # 验证已清空
        count = await vector_service.get_vector_count()
        assert count == 0
    
    @pytest.mark.asyncio
    async def test_get_store_info(self, vector_service):
        """测试获取存储信息"""
        info = await vector_service.get_store_info()
        
        assert isinstance(info, dict)
        assert "count" in info
        assert isinstance(info["count"], int)
    
    @pytest.mark.asyncio
    async def test_batch_search(self, vector_service, sample_vectors):
        """测试批量搜索"""
        # 添加向量
        await vector_service.add_vectors(sample_vectors)
        
        # 批量搜索
        query_vectors = [
            [0.1, 0.2, 0.3],
            [0.2, 0.4, 0.6]
        ]
        
        results = await vector_service.batch_search(query_vectors, top_k=2)
        
        assert len(results) == len(query_vectors)
        for result_list in results:
            assert isinstance(result_list, list)
            assert len(result_list) <= 2
    
    @pytest.mark.asyncio
    async def test_batch_search_empty(self, vector_service):
        """测试空批量搜索"""
        results = await vector_service.batch_search([])
        assert results == []
    
    @pytest.mark.asyncio
    async def test_operations_without_initialization(self):
        """测试未初始化时的操作"""
        config = VectorStoreConfig(
            type="chroma",
            persist_directory="./test",
            collection_name="test"
        )
        
        service = VectorStoreService(config)
        
        # 未初始化时的操作应该抛出异常
        with pytest.raises(VectorStoreError):
            await service.add_vectors([])
        
        with pytest.raises(VectorStoreError):
            await service.search_similar([0.1, 0.2], top_k=1)
        
        with pytest.raises(VectorStoreError):
            await service.get_vector_count()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, vector_service):
        """测试资源清理"""
        # 添加一些数据
        vectors = [
            Vector(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                chunk_id=str(uuid.uuid4()),
                embedding=[0.1, 0.2, 0.3],
                metadata={}
            )
        ]
        
        await vector_service.add_vectors(vectors)
        
        # 清理资源
        await vector_service.cleanup()
        
        # 清理后操作应该失败
        with pytest.raises(VectorStoreError):
            await vector_service.get_vector_count()


class TestVectorStoreInterface:
    """向量存储接口测试（向后兼容性）"""
    
    def test_deprecated_interface(self):
        """测试已弃用的接口"""
        from rag_system.services.vector_service import VectorStoreInterface
        
        # 应该发出弃用警告
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            interface = VectorStoreInterface()
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "已弃用" in str(w[0].message)