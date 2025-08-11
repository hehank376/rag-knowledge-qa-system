"""
文档管理服务测试
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

from rag_system.services.document_service import DocumentService
from rag_system.models.document import DocumentInfo, DocumentStatus
from rag_system.utils.exceptions import DocumentError, ProcessingError


@pytest_asyncio.fixture
async def document_service():
    """文档服务fixture"""
    temp_dir = tempfile.mkdtemp()
    
    config = {
        'storage_dir': temp_dir,
        'vector_store_type': 'chroma',
        'vector_store_path': os.path.join(temp_dir, 'chroma_db'),
        'embedding_provider': 'mock',
        'embedding_model': 'test-model',
        'embedding_dimensions': 384
    }
    
    service = DocumentService(config)
    
    # Mock数据库管理器
    service.db_manager = Mock()
    service.db_manager.initialize = Mock()
    service.db_manager.get_session = Mock()
    service.db_manager.close = Mock()
    
    await service.initialize()
    
    # 在初始化后重新设置CRUD mock
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
def sample_upload_file():
    """示例上传文件fixture"""
    content = "这是一个测试文档的内容。\n包含多行文本用于测试文档处理功能。"
    file_content = BytesIO(content.encode('utf-8'))
    
    upload_file = UploadFile(
        filename="test_document.txt",
        file=file_content,
        size=len(content)
    )
    
    return upload_file


class TestDocumentService:
    """文档管理服务测试"""
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """测试服务初始化"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = {
                'storage_dir': temp_dir,
                'vector_store_type': 'chroma',
                'vector_store_path': os.path.join(temp_dir, 'chroma_db'),
                'embedding_provider': 'mock'
            }
            
            service = DocumentService(config)
            
            # Mock依赖
            service.db_manager = Mock()
            service.db_manager.initialize = Mock()
            service.db_manager.get_session = Mock()
            service.document_crud = Mock()
            
            await service.initialize()
            
            # 验证存储目录创建
            assert Path(temp_dir).exists()
            
            # 验证组件初始化
            service.db_manager.initialize.assert_called_once()
            
            await service.cleanup()
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_upload_document_success(self, document_service, sample_upload_file):
        """测试文档上传成功"""
        # Mock文档处理结果
        mock_result = Mock()
        mock_result.success = True
        mock_result.chunks = []
        mock_result.vectors = []
        mock_result.chunk_count = 2
        mock_result.processing_time = 1.5
        
        with patch.object(document_service.document_processor, 'process_document', 
                         return_value=mock_result):
            doc_info = await document_service.upload_document(sample_upload_file)
            
            # 验证返回的文档信息
            assert isinstance(doc_info, DocumentInfo)
            assert doc_info.filename == "test_document.txt"
            assert doc_info.file_type == "txt"
            # 由于异步处理，状态可能已经更新为READY
            assert doc_info.status in [DocumentStatus.PROCESSING, DocumentStatus.READY]
            
            # 验证数据库调用
            document_service.document_crud.create_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_upload_document_unsupported_format(self, document_service):
        """测试上传不支持的文件格式"""
        # 创建不支持的文件格式
        content = BytesIO(b"test content")
        upload_file = UploadFile(
            filename="test.xyz",
            file=content,
            size=12
        )
        
        with pytest.raises(DocumentError) as exc_info:
            await document_service.upload_document(upload_file)
        
        assert "不支持的文件格式" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_upload_document_empty_filename(self, document_service):
        """测试上传空文件名"""
        content = BytesIO(b"test content")
        upload_file = UploadFile(
            filename="",
            file=content,
            size=12
        )
        
        with pytest.raises(DocumentError) as exc_info:
            await document_service.upload_document(upload_file)
        
        assert "文件名不能为空" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_document_success(self, document_service):
        """测试删除文档成功"""
        doc_id = str(uuid.uuid4())
        
        # Mock文档信息
        mock_doc = DocumentInfo(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            file_path="/tmp/test.txt",
            status=DocumentStatus.READY,
            chunk_count=2
        )
        
        # Mock数据库模型对象
        from rag_system.database.models import DocumentModel, DocumentStatus as DBDocumentStatus
        
        mock_db_doc = Mock(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            upload_time=mock_doc.upload_time,
            status=DBDocumentStatus.READY,
            chunk_count=2,
            error_message=""
        )
        
        document_service.document_crud.get_document.return_value = mock_db_doc
        
        # Mock文件存在检查 - 需要patch Path.exists而不是os.path.exists
        from pathlib import Path
        with patch.object(Path, 'exists', return_value=True), \
             patch('os.remove') as mock_remove:
            
            result = await document_service.delete_document(doc_id)
            
            assert result is True
            
            # 验证调用
            document_service.document_crud.get_document.assert_called_once_with(doc_id)
            document_service.document_crud.delete_document.assert_called_once_with(doc_id)
            # 验证os.remove被调用，参数可能是Path对象或字符串
            mock_remove.assert_called_once()
            # 获取实际调用的参数
            call_args = mock_remove.call_args[0][0]
            expected_path = document_service.storage_dir / f"{doc_id}.txt"
            # 比较路径（转换为字符串进行比较）
            assert str(call_args) == str(expected_path)
    
    @pytest.mark.asyncio
    async def test_delete_document_not_found(self, document_service):
        """测试删除不存在的文档"""
        doc_id = str(uuid.uuid4())
        
        document_service.document_crud.get_document.return_value = None
        
        result = await document_service.delete_document(doc_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_documents(self, document_service):
        """测试获取文档列表"""
        # Mock文档列表
        mock_docs = [
            DocumentInfo(
                id=str(uuid.uuid4()),
                filename="doc1.txt",
                file_type="txt",
                file_size=100,
                status=DocumentStatus.READY,
                chunk_count=2
            ),
            DocumentInfo(
                id=str(uuid.uuid4()),
                filename="doc2.pdf",
                file_type="pdf",
                file_size=200,
                status=DocumentStatus.PROCESSING,
                chunk_count=0
            )
        ]
        
        # Mock数据库模型对象
        from rag_system.database.models import DocumentModel, DocumentStatus as DBDocumentStatus
        
        mock_db_docs = [
            Mock(
                id=mock_docs[0].id,
                filename=mock_docs[0].filename,
                file_type=mock_docs[0].file_type,
                file_size=mock_docs[0].file_size,
                upload_time=mock_docs[0].upload_time,
                status=DBDocumentStatus.READY,
                chunk_count=mock_docs[0].chunk_count,
                error_message=""
            ),
            Mock(
                id=mock_docs[1].id,
                filename=mock_docs[1].filename,
                file_type=mock_docs[1].file_type,
                file_size=mock_docs[1].file_size,
                upload_time=mock_docs[1].upload_time,
                status=DBDocumentStatus.PROCESSING,
                chunk_count=mock_docs[1].chunk_count,
                error_message=""
            )
        ]
        
        document_service.document_crud.get_documents.return_value = mock_db_docs
        
        documents = await document_service.list_documents()
        
        assert len(documents) == 2
        assert documents[0].filename == "doc1.txt"
        assert documents[1].filename == "doc2.pdf"
    
    @pytest.mark.asyncio
    async def test_get_document_success(self, document_service):
        """测试获取文档信息成功"""
        doc_id = str(uuid.uuid4())
        
        mock_doc = DocumentInfo(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            status=DocumentStatus.READY,
            chunk_count=2
        )
        
        # Mock数据库模型对象
        from rag_system.database.models import DocumentModel, DocumentStatus as DBDocumentStatus
        
        mock_db_doc = Mock(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            upload_time=mock_doc.upload_time,
            status=DBDocumentStatus.READY,
            chunk_count=2,
            error_message=""
        )
        
        document_service.document_crud.get_document.return_value = mock_db_doc
        
        doc_info = await document_service.get_document(doc_id)
        
        assert doc_info.id == doc_id
        assert doc_info.filename == "test.txt"
        assert doc_info.status == DocumentStatus.READY
    
    @pytest.mark.asyncio
    async def test_get_document_not_found(self, document_service):
        """测试获取不存在的文档"""
        doc_id = str(uuid.uuid4())
        
        document_service.document_crud.get_document.return_value = None
        
        with pytest.raises(DocumentError) as exc_info:
            await document_service.get_document(doc_id)
        
        assert "文档不存在" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_document_status(self, document_service):
        """测试获取文档状态"""
        doc_id = str(uuid.uuid4())
        
        mock_doc = DocumentInfo(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            status=DocumentStatus.PROCESSING,
            chunk_count=0
        )
        
        # Mock数据库模型对象
        from rag_system.database.models import DocumentModel, DocumentStatus as DBDocumentStatus
        
        mock_db_doc = Mock(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            upload_time=mock_doc.upload_time,
            status=DBDocumentStatus.PROCESSING,
            chunk_count=0,
            error_message=""
        )
        
        document_service.document_crud.get_document.return_value = mock_db_doc
        
        status = await document_service.get_document_status(doc_id)
        
        assert status == DocumentStatus.PROCESSING
    
    @pytest.mark.asyncio
    async def test_reprocess_document_success(self, document_service):
        """测试重新处理文档成功"""
        doc_id = str(uuid.uuid4())
        
        mock_doc = DocumentInfo(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            file_path="/tmp/test.txt",
            status=DocumentStatus.ERROR,
            chunk_count=0
        )
        
        # Mock数据库模型对象
        from rag_system.database.models import DocumentModel, DocumentStatus as DBDocumentStatus
        
        mock_db_doc = Mock(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            upload_time=mock_doc.upload_time,
            status=DBDocumentStatus.ERROR,
            chunk_count=0,
            error_message=""
        )
        
        document_service.document_crud.get_document.return_value = mock_db_doc
        
        # Mock文件存在和处理结果
        mock_result = Mock()
        mock_result.success = True
        mock_result.vectors = []
        mock_result.chunk_count = 2
        mock_result.processing_time = 1.0
        
        from pathlib import Path
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(document_service.document_processor, 'process_document', 
                         return_value=mock_result):
            
            result = await document_service.reprocess_document(doc_id)
            
            assert result is True
            
            # 验证状态更新调用
            assert document_service.document_crud.update_document_status.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_reprocess_document_file_not_found(self, document_service):
        """测试重新处理文档时文件不存在"""
        doc_id = str(uuid.uuid4())
        
        mock_doc = DocumentInfo(
            id=doc_id,
            filename="test.txt",
            file_type="txt",
            file_size=100,
            file_path="/tmp/nonexistent.txt",
            status=DocumentStatus.ERROR,
            chunk_count=0
        )
        
        document_service.document_crud.get_document.return_value = mock_doc
        
        with patch('os.path.exists', return_value=False):
            result = await document_service.reprocess_document(doc_id)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_service_stats(self, document_service):
        """测试获取服务统计信息"""
        # Mock文档列表
        mock_docs = [
            DocumentInfo(
                id=str(uuid.uuid4()),
                filename="doc1.txt",
                file_type="txt",
                file_size=100,
                status=DocumentStatus.READY,
                chunk_count=3
            ),
            DocumentInfo(
                id=str(uuid.uuid4()),
                filename="doc2.txt",
                file_type="txt",
                file_size=200,
                status=DocumentStatus.PROCESSING,
                chunk_count=0
            ),
            DocumentInfo(
                id=str(uuid.uuid4()),
                filename="doc3.txt",
                file_type="txt",
                file_size=150,
                status=DocumentStatus.ERROR,
                chunk_count=0
            )
        ]
        
        # Mock数据库模型对象
        from rag_system.database.models import DocumentModel, DocumentStatus as DBDocumentStatus
        
        mock_db_docs = [
            Mock(
                id=mock_docs[0].id,
                filename=mock_docs[0].filename,
                file_type=mock_docs[0].file_type,
                file_size=mock_docs[0].file_size,
                upload_time=mock_docs[0].upload_time,
                status=DBDocumentStatus.READY,
                chunk_count=mock_docs[0].chunk_count,
                error_message=""
            ),
            Mock(
                id=mock_docs[1].id,
                filename=mock_docs[1].filename,
                file_type=mock_docs[1].file_type,
                file_size=mock_docs[1].file_size,
                upload_time=mock_docs[1].upload_time,
                status=DBDocumentStatus.PROCESSING,
                chunk_count=mock_docs[1].chunk_count,
                error_message=""
            ),
            Mock(
                id=mock_docs[2].id,
                filename=mock_docs[2].filename,
                file_type=mock_docs[2].file_type,
                file_size=mock_docs[2].file_size,
                upload_time=mock_docs[2].upload_time,
                status=DBDocumentStatus.ERROR,
                chunk_count=mock_docs[2].chunk_count,
                error_message=""
            )
        ]
        
        document_service.document_crud.get_documents.return_value = mock_db_docs
        
        # Mock向量数量
        with patch.object(document_service.vector_service, 'get_vector_count', 
                         return_value=10):
            
            stats = await document_service.get_service_stats()
            
            assert stats['total_documents'] == 3
            assert stats['ready_documents'] == 1
            assert stats['processing_documents'] == 1
            assert stats['error_documents'] == 1
            assert stats['total_chunks'] == 3
            assert stats['vector_count'] == 10
            assert 'supported_formats' in stats


class TestDocumentServiceIntegration:
    """文档服务集成测试"""
    
    @pytest.mark.asyncio
    async def test_upload_and_process_workflow(self, document_service, sample_upload_file):
        """测试上传和处理工作流"""
        # Mock成功的处理结果
        mock_result = Mock()
        mock_result.success = True
        mock_result.chunks = [Mock(), Mock()]  # 2个块
        mock_result.vectors = [Mock(), Mock()]  # 2个向量
        mock_result.chunk_count = 2
        mock_result.processing_time = 2.0
        
        with patch.object(document_service.document_processor, 'process_document', 
                         return_value=mock_result):
            
            # 上传文档
            doc_info = await document_service.upload_document(sample_upload_file)
            
            # 验证初始状态
            assert doc_info.status == DocumentStatus.PROCESSING
            assert doc_info.chunk_count == 0
            
            # 验证文件被保存
            assert Path(doc_info.file_path).exists()
            
            # 验证数据库操作
            document_service.document_crud.create_document.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_during_processing(self, document_service, sample_upload_file):
        """测试处理过程中的错误处理"""
        # Mock处理失败
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "处理失败"
        mock_result.chunks = []
        mock_result.vectors = []
        mock_result.chunk_count = 0
        
        with patch.object(document_service.document_processor, 'process_document', 
                         return_value=mock_result):
            
            # 上传文档
            doc_info = await document_service.upload_document(sample_upload_file)
            
            # 验证初始状态
            assert doc_info.status == DocumentStatus.PROCESSING
            
            # 验证数据库创建调用
            document_service.document_crud.create_document.assert_called_once()


class TestDocumentServiceConfiguration:
    """文档服务配置测试"""
    
    @pytest.mark.asyncio
    async def test_custom_configuration(self):
        """测试自定义配置"""
        temp_dir = tempfile.mkdtemp()
        
        try:
            config = {
                'storage_dir': temp_dir,
                'chunk_size': 500,
                'chunk_overlap': 50,
                'embedding_provider': 'openai',
                'embedding_model': 'text-embedding-3-small',
                'vector_store_type': 'chroma',
                'collection_name': 'test_collection'
            }
            
            service = DocumentService(config)
            
            # Mock依赖
            service.db_connection = Mock()
            service.db_connection.initialize = AsyncMock()
            service.document_crud = Mock()
            
            await service.initialize()
            
            # 验证配置传递
            assert service.storage_dir == Path(temp_dir)
            assert service.vector_service.config.collection_name == 'test_collection'
            
            await service.cleanup()
            
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_default_configuration(self):
        """测试默认配置"""
        service = DocumentService()
        
        # Mock依赖
        service.db_connection = Mock()
        service.db_connection.initialize = AsyncMock()
        service.document_crud = Mock()
        
        await service.initialize()
        
        # 验证默认值
        assert service.storage_dir == Path('./documents')
        assert service.vector_service.config.type == 'chroma'
        
        await service.cleanup()