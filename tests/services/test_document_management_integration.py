"""
文档管理功能集成测试
专门测试任务5.2：文档列表和删除功能
"""
import pytest
import pytest_asyncio
import tempfile
import os
import uuid
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from fastapi import UploadFile
from io import BytesIO
from datetime import datetime

from rag_system.services.document_service import DocumentService
from rag_system.models.document import DocumentInfo, DocumentStatus
from rag_system.utils.exceptions import DocumentError, ProcessingError


@pytest_asyncio.fixture
async def document_management_service():
    """文档管理服务fixture - 专门用于集成测试"""
    temp_dir = tempfile.mkdtemp()
    
    config = {
        'storage_dir': temp_dir,
        'vector_store_type': 'chroma',
        'vector_store_path': os.path.join(temp_dir, 'chroma_db'),
        'embedding_provider': 'mock',
        'embedding_model': 'test-model',
        'embedding_dimensions': 384,
        'database_url': f'sqlite:///{temp_dir}/test.db'
    }
    
    service = DocumentService(config)
    
    # Mock数据库管理器和相关组件
    service.db_manager = Mock()
    service.db_manager.initialize = Mock()
    service.db_manager.get_session = Mock()
    service.db_manager.close = Mock()
    
    # Mock向量服务
    service.vector_service = Mock()
    service.vector_service.initialize = AsyncMock()
    service.vector_service.cleanup = AsyncMock()
    service.vector_service.add_vectors = AsyncMock()
    service.vector_service.delete_vectors = AsyncMock()
    service.vector_service.get_vector_count = AsyncMock(return_value=0)
    
    # Mock文档处理器
    service.document_processor = Mock()
    service.document_processor.initialize = AsyncMock()
    service.document_processor.cleanup = AsyncMock()
    service.document_processor.is_supported_file = Mock(return_value=True)
    service.document_processor.get_supported_formats = Mock(return_value=['txt', 'pdf', 'docx', 'md'])
    
    await service.initialize()
    
    # 在初始化后设置CRUD mock
    service.document_crud = Mock()
    service.document_crud.create_document = Mock()
    service.document_crud.update_document_status = Mock()
    service.document_crud.update_document_chunk_count = Mock()
    service.document_crud.get_document = Mock()
    service.document_crud.delete_document = Mock(return_value=True)
    service.document_crud.get_documents = Mock(return_value=[])
    
    yield service
    
    await service.cleanup()
    
    # 清理临时目录
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest_asyncio.fixture
def sample_documents():
    """示例文档数据fixture"""
    from rag_system.database.models import DocumentStatus as DBDocumentStatus
    
    docs = []
    for i in range(5):
        doc_id = str(uuid.uuid4())
        status = [DBDocumentStatus.READY, DBDocumentStatus.PROCESSING, DBDocumentStatus.ERROR][i % 3]
        
        mock_db_doc = Mock(
            id=doc_id,
            filename=f"document_{i+1}.txt",
            file_type="txt",
            file_size=100 * (i + 1),
            upload_time=datetime.now(),
            status=status,
            chunk_count=i + 1 if status == DBDocumentStatus.READY else 0,
            error_message="" if status != DBDocumentStatus.ERROR else "处理错误"
        )
        docs.append(mock_db_doc)
    
    return docs


class TestDocumentListingFunctionality:
    """文档列表功能测试"""
    
    @pytest.mark.asyncio
    async def test_list_empty_documents(self, document_management_service):
        """测试空文档列表"""
        document_management_service.document_crud.get_documents.return_value = []
        
        documents = await document_management_service.list_documents()
        
        assert len(documents) == 0
        assert isinstance(documents, list)
        document_management_service.document_crud.get_documents.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_multiple_documents(self, document_management_service, sample_documents):
        """测试多个文档列表"""
        document_management_service.document_crud.get_documents.return_value = sample_documents
        
        documents = await document_management_service.list_documents()
        
        assert len(documents) == 5
        
        # 验证文档信息正确转换
        for i, doc in enumerate(documents):
            assert isinstance(doc, DocumentInfo)
            assert doc.filename == f"document_{i+1}.txt"
            assert doc.file_type == "txt"
            assert doc.file_size == 100 * (i + 1)
            
            # 验证状态转换
            expected_status = [DocumentStatus.READY, DocumentStatus.PROCESSING, DocumentStatus.ERROR][i % 3]
            assert doc.status == expected_status
    
    @pytest.mark.asyncio
    async def test_list_documents_with_different_statuses(self, document_management_service):
        """测试不同状态的文档列表"""
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        
        mock_docs = [
            Mock(
                id=str(uuid.uuid4()),
                filename="ready_doc.txt",
                file_type="txt",
                file_size=100,
                upload_time=datetime.now(),
                status=DBDocumentStatus.READY,
                chunk_count=5,
                error_message=""
            ),
            Mock(
                id=str(uuid.uuid4()),
                filename="processing_doc.pdf",
                file_type="pdf",
                file_size=200,
                upload_time=datetime.now(),
                status=DBDocumentStatus.PROCESSING,
                chunk_count=0,
                error_message=""
            ),
            Mock(
                id=str(uuid.uuid4()),
                filename="error_doc.docx",
                file_type="docx",
                file_size=300,
                upload_time=datetime.now(),
                status=DBDocumentStatus.ERROR,
                chunk_count=0,
                error_message="处理失败"
            )
        ]
        
        document_management_service.document_crud.get_documents.return_value = mock_docs
        
        documents = await document_management_service.list_documents()
        
        assert len(documents) == 3
        
        # 验证READY状态文档
        ready_doc = next(d for d in documents if d.filename == "ready_doc.txt")
        assert ready_doc.status == DocumentStatus.READY
        assert ready_doc.chunk_count == 5
        
        # 验证PROCESSING状态文档
        processing_doc = next(d for d in documents if d.filename == "processing_doc.pdf")
        assert processing_doc.status == DocumentStatus.PROCESSING
        assert processing_doc.chunk_count == 0
        
        # 验证ERROR状态文档
        error_doc = next(d for d in documents if d.filename == "error_doc.docx")
        assert error_doc.status == DocumentStatus.ERROR
        assert error_doc.chunk_count == 0
    
    @pytest.mark.asyncio
    async def test_list_documents_database_error(self, document_management_service):
        """测试数据库错误时的文档列表"""
        document_management_service.document_crud.get_documents.side_effect = Exception("数据库连接失败")
        
        with pytest.raises(DocumentError) as exc_info:
            await document_management_service.list_documents()
        
        assert "获取文档列表失败" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_list_documents_performance(self, document_management_service):
        """测试大量文档的列表性能"""
        # 创建大量文档数据
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        
        large_doc_list = []
        for i in range(100):
            mock_doc = Mock(
                id=str(uuid.uuid4()),
                filename=f"doc_{i}.txt",
                file_type="txt",
                file_size=100,
                upload_time=datetime.now(),
                status=DBDocumentStatus.READY,
                chunk_count=1,
                error_message=""
            )
            large_doc_list.append(mock_doc)
        
        document_management_service.document_crud.get_documents.return_value = large_doc_list
        
        import time
        start_time = time.time()
        
        documents = await document_management_service.list_documents()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert len(documents) == 100
        assert processing_time < 1.0  # 应该在1秒内完成
        
        # 验证所有文档都正确转换
        for i, doc in enumerate(documents):
            assert doc.filename == f"doc_{i}.txt"
            assert doc.status == DocumentStatus.READY


class TestDocumentDeletionFunctionality:
    """文档删除功能测试"""
    
    @pytest.mark.asyncio
    async def test_delete_existing_document(self, document_management_service):
        """测试删除存在的文档"""
        doc_id = str(uuid.uuid4())
        
        # Mock文档存在
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        mock_db_doc = Mock(
            id=doc_id,
            filename="test_doc.txt",
            file_type="txt",
            file_size=100,
            upload_time=datetime.now(),
            status=DBDocumentStatus.READY,
            chunk_count=2,
            error_message=""
        )
        
        document_management_service.document_crud.get_document.return_value = mock_db_doc
        document_management_service.document_crud.delete_document.return_value = True
        
        # Mock文件存在
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.remove') as mock_remove:
            
            result = await document_management_service.delete_document(doc_id)
            
            assert result is True
            
            # 验证调用顺序和参数
            document_management_service.document_crud.get_document.assert_called_once_with(doc_id)
            document_management_service.vector_service.delete_vectors.assert_called_once_with(doc_id)
            mock_remove.assert_called_once()
            document_management_service.document_crud.delete_document.assert_called_once_with(doc_id)
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_document(self, document_management_service):
        """测试删除不存在的文档"""
        doc_id = str(uuid.uuid4())
        
        document_management_service.document_crud.get_document.return_value = None
        
        result = await document_management_service.delete_document(doc_id)
        
        assert result is False
        
        # 验证没有进行删除操作
        document_management_service.vector_service.delete_vectors.assert_not_called()
        document_management_service.document_crud.delete_document.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_delete_document_file_not_found(self, document_management_service):
        """测试删除文档时文件不存在"""
        doc_id = str(uuid.uuid4())
        
        # Mock文档存在但文件不存在
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        mock_db_doc = Mock(
            id=doc_id,
            filename="missing_file.txt",
            file_type="txt",
            file_size=100,
            upload_time=datetime.now(),
            status=DBDocumentStatus.READY,
            chunk_count=2,
            error_message=""
        )
        
        document_management_service.document_crud.get_document.return_value = mock_db_doc
        document_management_service.document_crud.delete_document.return_value = True
        
        # Mock文件不存在
        with patch.object(Path, 'exists', return_value=False), \
             patch('os.remove') as mock_remove:
            
            result = await document_management_service.delete_document(doc_id)
            
            assert result is True  # 仍然应该成功，因为数据库记录被删除了
            
            # 验证文件删除没有被调用
            mock_remove.assert_not_called()
            
            # 但向量和数据库删除应该被调用
            document_management_service.vector_service.delete_vectors.assert_called_once_with(doc_id)
            document_management_service.document_crud.delete_document.assert_called_once_with(doc_id)
    
    @pytest.mark.asyncio
    async def test_delete_document_vector_deletion_fails(self, document_management_service):
        """测试删除文档时向量删除失败"""
        doc_id = str(uuid.uuid4())
        
        # Mock文档存在
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        mock_db_doc = Mock(
            id=doc_id,
            filename="test_doc.txt",
            file_type="txt",
            file_size=100,
            upload_time=datetime.now(),
            status=DBDocumentStatus.READY,
            chunk_count=2,
            error_message=""
        )
        
        document_management_service.document_crud.get_document.return_value = mock_db_doc
        document_management_service.document_crud.delete_document.return_value = True
        
        # Mock向量删除失败
        from rag_system.utils.exceptions import VectorStoreError
        document_management_service.vector_service.delete_vectors.side_effect = VectorStoreError("向量删除失败")
        
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.remove') as mock_remove:
            
            result = await document_management_service.delete_document(doc_id)
            
            # 即使向量删除失败，整个删除操作仍应继续
            assert result is True
            
            # 验证文件和数据库删除仍然被执行
            mock_remove.assert_called_once()
            document_management_service.document_crud.delete_document.assert_called_once_with(doc_id)
    
    @pytest.mark.asyncio
    async def test_delete_document_database_deletion_fails(self, document_management_service):
        """测试删除文档时数据库删除失败"""
        doc_id = str(uuid.uuid4())
        
        # Mock文档存在
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        mock_db_doc = Mock(
            id=doc_id,
            filename="test_doc.txt",
            file_type="txt",
            file_size=100,
            upload_time=datetime.now(),
            status=DBDocumentStatus.READY,
            chunk_count=2,
            error_message=""
        )
        
        document_management_service.document_crud.get_document.return_value = mock_db_doc
        document_management_service.document_crud.delete_document.return_value = False  # 删除失败
        
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.remove') as mock_remove:
            
            result = await document_management_service.delete_document(doc_id)
            
            assert result is False
            
            # 验证其他清理操作仍然被执行
            document_management_service.vector_service.delete_vectors.assert_called_once_with(doc_id)
            mock_remove.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_delete_multiple_documents(self, document_management_service):
        """测试批量删除文档"""
        doc_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Mock所有文档存在
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        
        def mock_get_document(doc_id):
            return Mock(
                id=doc_id,
                filename=f"doc_{doc_id[:8]}.txt",
                file_type="txt",
                file_size=100,
                upload_time=datetime.now(),
                status=DBDocumentStatus.READY,
                chunk_count=1,
                error_message=""
            )
        
        document_management_service.document_crud.get_document.side_effect = mock_get_document
        document_management_service.document_crud.delete_document.return_value = True
        
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.remove') as mock_remove:
            
            results = []
            for doc_id in doc_ids:
                result = await document_management_service.delete_document(doc_id)
                results.append(result)
            
            # 验证所有删除都成功
            assert all(results)
            
            # 验证调用次数
            assert document_management_service.document_crud.get_document.call_count == 3
            assert document_management_service.vector_service.delete_vectors.call_count == 3
            assert mock_remove.call_count == 3
            assert document_management_service.document_crud.delete_document.call_count == 3


class TestDocumentManagementWorkflow:
    """文档管理工作流集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_document_lifecycle(self, document_management_service):
        """测试完整的文档生命周期：上传 -> 列表 -> 删除"""
        # 1. 模拟上传文档
        content = BytesIO(b"Test document content")
        upload_file = UploadFile(filename="test.txt", file=content, size=20)
        
        # Mock处理成功
        mock_result = Mock()
        mock_result.success = True
        mock_result.vectors = [Mock(), Mock()]
        mock_result.chunk_count = 2
        mock_result.processing_time = 1.0
        
        with patch.object(document_management_service.document_processor, 'process_document', 
                         return_value=mock_result):
            
            # 上传文档
            doc_info = await document_management_service.upload_document(upload_file)
            doc_id = doc_info.id
            
            # 验证上传成功
            assert doc_info.filename == "test.txt"
            assert doc_info.status == DocumentStatus.PROCESSING
        
        # 2. 模拟文档在列表中
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        mock_db_doc = Mock(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=20,
            upload_time=doc_info.upload_time,
            status=DBDocumentStatus.READY,  # 假设处理完成
            chunk_count=2,
            error_message=""
        )
        
        document_management_service.document_crud.get_documents.return_value = [mock_db_doc]
        
        # 获取文档列表
        documents = await document_management_service.list_documents()
        
        assert len(documents) == 1
        assert documents[0].id == doc_id
        assert documents[0].status == DocumentStatus.READY
        assert documents[0].chunk_count == 2
        
        # 3. 删除文档
        document_management_service.document_crud.get_document.return_value = mock_db_doc
        document_management_service.document_crud.delete_document.return_value = True
        
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.remove'):
            
            delete_result = await document_management_service.delete_document(doc_id)
            
            assert delete_result is True
        
        # 4. 验证删除后列表为空
        document_management_service.document_crud.get_documents.return_value = []
        
        documents_after_delete = await document_management_service.list_documents()
        assert len(documents_after_delete) == 0
    
    @pytest.mark.asyncio
    async def test_document_management_with_errors(self, document_management_service):
        """测试包含错误处理的文档管理流程"""
        # 创建包含不同状态的文档列表
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        
        mock_docs = [
            Mock(
                id=str(uuid.uuid4()),
                filename="success_doc.txt",
                file_type="txt",
                file_size=100,
                upload_time=datetime.now(),
                status=DBDocumentStatus.READY,
                chunk_count=3,
                error_message=""
            ),
            Mock(
                id=str(uuid.uuid4()),
                filename="processing_doc.txt",
                file_type="txt",
                file_size=150,
                upload_time=datetime.now(),
                status=DBDocumentStatus.PROCESSING,
                chunk_count=0,
                error_message=""
            ),
            Mock(
                id=str(uuid.uuid4()),
                filename="error_doc.txt",
                file_type="txt",
                file_size=200,
                upload_time=datetime.now(),
                status=DBDocumentStatus.ERROR,
                chunk_count=0,
                error_message="处理失败：文件损坏"
            )
        ]
        
        document_management_service.document_crud.get_documents.return_value = mock_docs
        
        # 获取文档列表
        documents = await document_management_service.list_documents()
        
        assert len(documents) == 3
        
        # 验证不同状态的文档
        success_doc = next(d for d in documents if d.filename == "success_doc.txt")
        assert success_doc.status == DocumentStatus.READY
        assert success_doc.chunk_count == 3
        
        processing_doc = next(d for d in documents if d.filename == "processing_doc.txt")
        assert processing_doc.status == DocumentStatus.PROCESSING
        assert processing_doc.chunk_count == 0
        
        error_doc = next(d for d in documents if d.filename == "error_doc.txt")
        assert error_doc.status == DocumentStatus.ERROR
        assert error_doc.chunk_count == 0
        
        # 尝试删除错误状态的文档
        error_doc_id = error_doc.id
        document_management_service.document_crud.get_document.return_value = mock_docs[2]
        document_management_service.document_crud.delete_document.return_value = True
        
        with patch.object(Path, 'exists', return_value=False):  # 文件可能不存在
            delete_result = await document_management_service.delete_document(error_doc_id)
            
            # 即使文件不存在，删除操作也应该成功（清理数据库记录）
            assert delete_result is True
    
    @pytest.mark.asyncio
    async def test_concurrent_document_operations(self, document_management_service):
        """测试并发文档操作"""
        import asyncio
        
        # 准备多个文档
        doc_ids = [str(uuid.uuid4()) for _ in range(5)]
        
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        mock_docs = []
        for i, doc_id in enumerate(doc_ids):
            mock_doc = Mock(
                id=doc_id,
                filename=f"concurrent_doc_{i}.txt",
                file_type="txt",
                file_size=100 * (i + 1),
                upload_time=datetime.now(),
                status=DBDocumentStatus.READY,
                chunk_count=i + 1,
                error_message=""
            )
            mock_docs.append(mock_doc)
        
        document_management_service.document_crud.get_documents.return_value = mock_docs
        
        # 并发获取文档列表
        async def get_documents():
            return await document_management_service.list_documents()
        
        # 执行多个并发请求
        tasks = [get_documents() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有请求都返回相同的结果
        for result in results:
            assert len(result) == 5
            assert all(isinstance(doc, DocumentInfo) for doc in result)
        
        # 验证数据库调用次数（应该被调用10次）
        assert document_management_service.document_crud.get_documents.call_count == 10


class TestDocumentManagementStatistics:
    """文档管理统计功能测试"""
    
    @pytest.mark.asyncio
    async def test_service_statistics_with_documents(self, document_management_service, sample_documents):
        """测试包含文档的服务统计"""
        document_management_service.document_crud.get_documents.return_value = sample_documents
        document_management_service.vector_service.get_vector_count.return_value = 15
        
        stats = await document_management_service.get_service_stats()
        
        assert stats['total_documents'] == 5
        assert stats['ready_documents'] == 2  # 状态为READY的文档数
        assert stats['processing_documents'] == 2  # 状态为PROCESSING的文档数
        assert stats['error_documents'] == 1  # 状态为ERROR的文档数
        assert stats['vector_count'] == 15
        assert 'supported_formats' in stats
        assert 'storage_directory' in stats
    
    @pytest.mark.asyncio
    async def test_service_statistics_empty(self, document_management_service):
        """测试空服务的统计"""
        document_management_service.document_crud.get_documents.return_value = []
        document_management_service.vector_service.get_vector_count.return_value = 0
        
        stats = await document_management_service.get_service_stats()
        
        assert stats['total_documents'] == 0
        assert stats['ready_documents'] == 0
        assert stats['processing_documents'] == 0
        assert stats['error_documents'] == 0
        assert stats['total_chunks'] == 0
        assert stats['vector_count'] == 0
    
    @pytest.mark.asyncio
    async def test_document_statistics_calculation(self, document_management_service):
        """测试文档统计计算的准确性"""
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        
        # 创建具有不同块数的文档
        mock_docs = [
            Mock(
                id=str(uuid.uuid4()),
                filename="doc1.txt",
                file_type="txt",
                file_size=100,
                upload_time=datetime.now(),
                status=DBDocumentStatus.READY,
                chunk_count=5,
                error_message=""
            ),
            Mock(
                id=str(uuid.uuid4()),
                filename="doc2.txt",
                file_type="txt",
                file_size=200,
                upload_time=datetime.now(),
                status=DBDocumentStatus.READY,
                chunk_count=3,
                error_message=""
            ),
            Mock(
                id=str(uuid.uuid4()),
                filename="doc3.txt",
                file_type="txt",
                file_size=150,
                upload_time=datetime.now(),
                status=DBDocumentStatus.PROCESSING,
                chunk_count=0,
                error_message=""
            )
        ]
        
        document_management_service.document_crud.get_documents.return_value = mock_docs
        document_management_service.vector_service.get_vector_count.return_value = 8
        
        stats = await document_management_service.get_service_stats()
        
        assert stats['total_documents'] == 3
        assert stats['ready_documents'] == 2
        assert stats['processing_documents'] == 1
        assert stats['error_documents'] == 0
        assert stats['total_chunks'] == 8  # 5 + 3 + 0
        assert stats['vector_count'] == 8