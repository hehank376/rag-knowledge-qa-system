"""
Chroma向量存储测试
"""
import pytest
import pytest_asyncio
import tempfile
import shutil
import os
import uuid
from typing import List
import asyncio

from rag_system.models.config import VectorStoreConfig
from rag_system.models.vector import Vector, SearchResult
from rag_system.vector_store.chroma_store import ChromaVectorStore
from rag_system.utils.exceptions import VectorStoreError


@pytest_asyncio.fixture
async def chroma_store():
    """Chroma向量存储fixture"""
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    
    config = VectorStoreConfig(
        type="chroma",
        persist_directory=temp_dir,
        collection_name="test_collection"
    )
    
    store = ChromaVectorStore(config)
    await store.initialize()
    
    yield store
    
    # 清理
    await store.cleanup()
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
            embedding=[0.1 * i, 0.2 * i, 0.3 * i, 0.4 * i],  # 4维向量
            metadata={"chunk_index": i, "content": f"test content {i}"}
        )
        vectors.append(vector)
    
    return vectors


class TestChromaVectorStore:
    """Chroma向量存储测试"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试初始化"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = VectorStoreConfig(
                type="chroma",
                persist_directory=temp_dir,
                collection_name="test_init"
            )
            
            store = ChromaVectorStore(config)
            assert not store.is_initialized()
            
            await store.initialize()
            assert store.is_initialized()
            
            await store.cleanup()
            
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
    async def test_add_vectors(self, chroma_store, sample_vectors):
        """测试添加向量"""
        result = await chroma_store.add_vectors(sample_vectors)
        assert result is True
        
        # 验证向量数量
        count = await chroma_store.get_vector_count()
        assert count == len(sample_vectors)
    
    @pytest.mark.asyncio
    async def test_add_empty_vectors(self, chroma_store):
        """测试添加空向量列表"""
        result = await chroma_store.add_vectors([])
        assert result is False
    
    @pytest.mark.asyncio
    async def test_search_similar(self, chroma_store, sample_vectors):
        """测试相似向量搜索"""
        # 先添加向量
        await chroma_store.add_vectors(sample_vectors)
        
        # 搜索相似向量
        query_vector = [0.1, 0.2, 0.3, 0.4]  # 与第一个向量相似
        results = await chroma_store.search_similar(query_vector, top_k=2)
        
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)
        
        # 验证结果按相似度排序
        if len(results) > 1:
            assert results[0].similarity_score >= results[1].similarity_score
    
    @pytest.mark.asyncio
    async def test_search_with_threshold(self, chroma_store, sample_vectors):
        """测试带阈值的搜索"""
        await chroma_store.add_vectors(sample_vectors)
        
        # 使用高阈值搜索
        query_vector = [0.1, 0.2, 0.3, 0.4]
        results = await chroma_store.search_similar(
            query_vector, 
            top_k=5, 
            similarity_threshold=0.9
        )
        
        # 所有结果的相似度都应该高于阈值
        for result in results:
            assert result.similarity_score >= 0.9
    
    @pytest.mark.asyncio
    async def test_delete_vectors(self, chroma_store, sample_vectors):
        """测试删除向量"""
        # 添加向量
        await chroma_store.add_vectors(sample_vectors)
        
        # 验证向量已添加
        count_before = await chroma_store.get_vector_count()
        assert count_before == len(sample_vectors)
        
        # 删除指定文档的向量
        document_id = sample_vectors[0].document_id
        result = await chroma_store.delete_vectors(document_id)
        assert result is True
        
        # 验证向量已删除
        count_after = await chroma_store.get_vector_count()
        assert count_after == 0
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_vectors(self, chroma_store):
        """测试删除不存在的向量"""
        result = await chroma_store.delete_vectors(str(uuid.uuid4()))
        assert result is True  # 删除不存在的向量应该返回True
    
    @pytest.mark.asyncio
    async def test_update_vectors(self, chroma_store, sample_vectors):
        """测试更新向量"""
        # 添加初始向量
        await chroma_store.add_vectors(sample_vectors)
        
        # 创建新的向量用于更新
        document_id = sample_vectors[0].document_id
        new_vectors = [
            Vector(
                id=str(uuid.uuid4()),
                document_id=document_id,
                chunk_id=str(uuid.uuid4()),
                embedding=[0.5, 0.6, 0.7, 0.8],
                metadata={"updated": True}
            )
        ]
        
        # 更新向量
        result = await chroma_store.update_vectors(document_id, new_vectors)
        assert result is True
        
        # 验证向量数量
        count = await chroma_store.get_vector_count()
        assert count == len(new_vectors)
        
        # 验证新向量可以被搜索到
        results = await chroma_store.search_similar([0.5, 0.6, 0.7, 0.8], top_k=1)
        assert len(results) == 1
        assert results[0].metadata.get("updated") is True
    
    @pytest.mark.asyncio
    async def test_get_vector_count(self, chroma_store, sample_vectors):
        """测试获取向量数量"""
        # 初始数量应该为0
        count = await chroma_store.get_vector_count()
        assert count == 0
        
        # 添加向量后数量应该增加
        await chroma_store.add_vectors(sample_vectors)
        count = await chroma_store.get_vector_count()
        assert count == len(sample_vectors)
    
    @pytest.mark.asyncio
    async def test_clear_all(self, chroma_store, sample_vectors):
        """测试清空所有向量"""
        # 添加向量
        await chroma_store.add_vectors(sample_vectors)
        
        # 验证向量已添加
        count_before = await chroma_store.get_vector_count()
        assert count_before > 0
        
        # 清空所有向量
        result = await chroma_store.clear_all()
        assert result is True
        
        # 验证向量已清空
        count_after = await chroma_store.get_vector_count()
        assert count_after == 0
    
    @pytest.mark.asyncio
    async def test_get_collection_info(self, chroma_store):
        """测试获取集合信息"""
        info = await chroma_store.get_collection_info()
        
        assert "name" in info
        assert "count" in info
        assert "persist_directory" in info
        assert info["name"] == "test_collection"
        assert isinstance(info["count"], int)
    
    @pytest.mark.asyncio
    async def test_batch_search(self, chroma_store, sample_vectors):
        """测试批量搜索"""
        # 添加向量
        await chroma_store.add_vectors(sample_vectors)
        
        # 准备多个查询向量
        query_vectors = [
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.4, 0.6, 0.8]
        ]
        
        # 批量搜索
        results = await chroma_store.batch_search(query_vectors, top_k=2)
        
        assert len(results) == len(query_vectors)
        for result_list in results:
            assert isinstance(result_list, list)
            assert len(result_list) <= 2
            for result in result_list:
                assert isinstance(result, SearchResult)
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, chroma_store):
        """测试空查询向量"""
        with pytest.raises(VectorStoreError):
            await chroma_store.search_similar([], top_k=5)
    
    @pytest.mark.asyncio
    async def test_search_invalid_query(self, chroma_store):
        """测试无效查询向量"""
        with pytest.raises(VectorStoreError):
            await chroma_store.search_similar(None, top_k=5)
    
    @pytest.mark.asyncio
    async def test_operations_without_initialization(self):
        """测试未初始化时的操作"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = VectorStoreConfig(
                type="chroma",
                persist_directory=temp_dir,
                collection_name="test_uninit"
            )
            
            store = ChromaVectorStore(config)
            
            # 未初始化时的操作应该抛出异常
            with pytest.raises(VectorStoreError):
                await store.add_vectors([])
            
            with pytest.raises(VectorStoreError):
                await store.search_similar([0.1, 0.2], top_k=1)
            
            with pytest.raises(VectorStoreError):
                await store.get_vector_count()
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_vector_validation(self, chroma_store):
        """测试向量验证"""
        # 测试无效向量
        invalid_vectors = [
            Vector(
                id="",  # 空ID
                document_id=str(uuid.uuid4()),
                chunk_id=str(uuid.uuid4()),
                embedding=[0.1, 0.2],
                metadata={}
            )
        ]
        
        result = await chroma_store.add_vectors(invalid_vectors)
        assert result is False
        
        # 测试空嵌入向量
        invalid_vectors2 = [
            Vector(
                id=str(uuid.uuid4()),
                document_id=str(uuid.uuid4()),
                chunk_id=str(uuid.uuid4()),
                embedding=[],  # 空嵌入
                metadata={}
            )
        ]
        
        result = await chroma_store.add_vectors(invalid_vectors2)
        assert result is False