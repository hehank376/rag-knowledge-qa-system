"""
文档管理API测试
测试任务5.2：文档列表查询API和文档删除功能
"""
import pytest
import pytest_asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime

from rag_system.api.document_api import router, get_document_service
from rag_system.models.document import DocumentInfo, DocumentStatus
from rag_system.utils.exceptions import DocumentError


# 创建测试应用
app = FastAPI()
app.include_router(router)


@pytest_asyncio.fixture
def mock_document_service():
    """Mock文档服务fixture"""
    service = Mock()
    service.initialize = AsyncMock()
    service.cleanup = AsyncMock()
    service.list_documents = AsyncMock()
    service.get_document = AsyncMock()
    service.delete_document = AsyncMock()
    service.reprocess_document = AsyncMock()
    service.get_service_stats = AsyncMock()
    return service


@pytest_asyncio.fixture
def sample_documents():
    """示例文档数据fixture"""
    return [
        DocumentInfo(
            id=str(uuid.uuid4()),
            filename="document1.txt",
            file_type="txt",
            file_size=100,
            file_path="/tmp/doc1.txt",
            upload_time=datetime.now(),
            status=DocumentStatus.READY,
            chunk_count=3
        ),
        DocumentInfo(
            id=str(uuid.uuid4()),
            filename="document2.pdf",
            file_type="pdf",
            file_size=200,
            file_path="/tmp/doc2.pdf",
            upload_time=datetime.now(),
            status=DocumentStatus.PROCESSING,
            chunk_count=0
        ),
        DocumentInfo(
            id=str(uuid.uuid4()),
            filename="document3.docx",
            file_type="docx",
            file_size=150,
            file_path="/tmp/doc3.docx",
            upload_time=datetime.now(),
            status=DocumentStatus.ERROR,
            chunk_count=0
        )
    ]


class TestDocumentListAPI:
    """文档列表API测试"""
    
    def test_list_documents_success(self, mock_document_service, sample_documents):
        """测试成功获取文档列表"""
        mock_document_service.list_documents.return_value = sample_documents
        
        # 覆盖依赖
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get("/documents/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_count"] == 3
            assert data["ready_count"] == 1
            assert data["processing_count"] == 1
            assert data["error_count"] == 1
            assert len(data["documents"]) == 3
            
            # 验证文档信息
            assert data["documents"][0]["filename"] == "document1.txt"
            assert data["documents"][0]["status"] == "ready"
            
        finally:
            app.dependency_overrides.clear()
    
    def test_list_documents_with_status_filter(self, mock_document_service, sample_documents):
        """测试带状态过滤器的文档列表"""
        mock_document_service.list_documents.return_value = sample_documents
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get("/documents/?status_filter=ready")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_count"] == 1
            assert data["ready_count"] == 1
            assert data["processing_count"] == 0
            assert data["error_count"] == 0
            assert len(data["documents"]) == 1
            assert data["documents"][0]["status"] == "ready"
            
        finally:
            app.dependency_overrides.clear()
    
    def test_list_documents_invalid_status_filter(self, mock_document_service):
        """测试无效状态过滤器"""
        mock_document_service.list_documents.return_value = []
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get("/documents/?status_filter=invalid")
            
            assert response.status_code == 400
            assert "无效的状态过滤器" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_list_documents_empty(self, mock_document_service):
        """测试空文档列表"""
        mock_document_service.list_documents.return_value = []
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get("/documents/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_count"] == 0
            assert data["ready_count"] == 0
            assert data["processing_count"] == 0
            assert data["error_count"] == 0
            assert len(data["documents"]) == 0
            
        finally:
            app.dependency_overrides.clear()
    
    def test_list_documents_service_error(self, mock_document_service):
        """测试服务错误"""
        mock_document_service.list_documents.side_effect = DocumentError("数据库连接失败")
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get("/documents/")
            
            assert response.status_code == 500
            assert "获取文档列表失败" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()


class TestDocumentGetAPI:
    """单个文档获取API测试"""
    
    def test_get_document_success(self, mock_document_service, sample_documents):
        """测试成功获取单个文档"""
        document = sample_documents[0]
        mock_document_service.get_document.return_value = document
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get(f"/documents/{document.id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["id"] == document.id
            assert data["filename"] == document.filename
            assert data["status"] == "ready"
            
        finally:
            app.dependency_overrides.clear()
    
    def test_get_document_not_found(self, mock_document_service):
        """测试获取不存在的文档"""
        doc_id = str(uuid.uuid4())
        mock_document_service.get_document.side_effect = DocumentError("文档不存在")
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get(f"/documents/{doc_id}")
            
            assert response.status_code == 404
            assert "文档不存在" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_get_document_service_error(self, mock_document_service):
        """测试服务错误"""
        doc_id = str(uuid.uuid4())
        mock_document_service.get_document.side_effect = DocumentError("数据库错误")
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get(f"/documents/{doc_id}")
            
            assert response.status_code == 500
            assert "获取文档信息失败" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()


class TestDocumentDeleteAPI:
    """文档删除API测试"""
    
    def test_delete_document_success(self, mock_document_service, sample_documents):
        """测试成功删除文档"""
        document = sample_documents[0]
        mock_document_service.get_document.return_value = document
        mock_document_service.delete_document.return_value = True
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.delete(f"/documents/{document.id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["document_id"] == document.id
            assert document.filename in data["message"]
            
            # 验证服务方法被调用
            mock_document_service.get_document.assert_called_once_with(document.id)
            mock_document_service.delete_document.assert_called_once_with(document.id)
            
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_document_not_found(self, mock_document_service):
        """测试删除不存在的文档"""
        doc_id = str(uuid.uuid4())
        mock_document_service.get_document.side_effect = DocumentError("文档不存在")
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.delete(f"/documents/{doc_id}")
            
            assert response.status_code == 404
            assert "文档不存在" in response.json()["detail"]
            
            # 验证删除方法没有被调用
            mock_document_service.delete_document.assert_not_called()
            
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_document_service_failure(self, mock_document_service, sample_documents):
        """测试删除服务失败"""
        document = sample_documents[0]
        mock_document_service.get_document.return_value = document
        mock_document_service.delete_document.return_value = False
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.delete(f"/documents/{document.id}")
            
            assert response.status_code == 500
            assert "文档删除失败" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()


class TestDocumentReprocessAPI:
    """文档重新处理API测试"""
    
    def test_reprocess_document_success(self, mock_document_service, sample_documents):
        """测试成功重新处理文档"""
        document = sample_documents[2]  # 错误状态的文档
        mock_document_service.get_document.return_value = document
        mock_document_service.reprocess_document.return_value = True
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.post(f"/documents/{document.id}/reprocess")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["document_id"] == document.id
            assert document.filename in data["message"]
            
            # 验证服务方法被调用
            mock_document_service.reprocess_document.assert_called_once_with(document.id)
            
        finally:
            app.dependency_overrides.clear()
    
    def test_reprocess_document_not_found(self, mock_document_service):
        """测试重新处理不存在的文档"""
        doc_id = str(uuid.uuid4())
        mock_document_service.get_document.side_effect = DocumentError("文档不存在")
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.post(f"/documents/{doc_id}/reprocess")
            
            assert response.status_code == 404
            assert "文档不存在" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_reprocess_document_service_failure(self, mock_document_service, sample_documents):
        """测试重新处理服务失败"""
        document = sample_documents[2]
        mock_document_service.get_document.return_value = document
        mock_document_service.reprocess_document.return_value = False
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.post(f"/documents/{document.id}/reprocess")
            
            assert response.status_code == 500
            assert "文档重新处理失败" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()


class TestDocumentStatsAPI:
    """文档统计API测试"""
    
    def test_get_document_stats_success(self, mock_document_service):
        """测试成功获取文档统计"""
        stats = {
            'total_documents': 10,
            'ready_documents': 7,
            'processing_documents': 2,
            'error_documents': 1,
            'total_chunks': 25,
            'vector_count': 25,
            'storage_directory': '/tmp/documents',
            'supported_formats': ['txt', 'pdf', 'docx', 'md']
        }
        mock_document_service.get_service_stats.return_value = stats
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get("/documents/stats/summary")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_documents"] == 10
            assert data["ready_documents"] == 7
            assert data["processing_documents"] == 2
            assert data["error_documents"] == 1
            assert data["total_chunks"] == 25
            assert data["vector_count"] == 25
            assert data["storage_directory"] == '/tmp/documents'
            assert data["supported_formats"] == ['txt', 'pdf', 'docx', 'md']
            
        finally:
            app.dependency_overrides.clear()
    
    def test_get_document_stats_service_error(self, mock_document_service):
        """测试统计服务错误"""
        mock_document_service.get_service_stats.return_value = {"error": "数据库连接失败"}
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.get("/documents/stats/summary")
            
            assert response.status_code == 500
            assert "获取统计信息失败" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()


class TestDocumentBatchDeleteAPI:
    """批量删除API测试"""
    
    def test_delete_all_documents_success(self, mock_document_service, sample_documents):
        """测试成功批量删除所有文档"""
        mock_document_service.list_documents.return_value = sample_documents
        mock_document_service.delete_document.return_value = True
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.delete("/documents/?confirm=true")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["deleted_count"] == 3
            assert data["failed_count"] == 0
            
            # 验证删除方法被调用3次
            assert mock_document_service.delete_document.call_count == 3
            
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_all_documents_without_confirm(self, mock_document_service):
        """测试未确认的批量删除"""
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.delete("/documents/")
            
            assert response.status_code == 400
            assert "必须设置 confirm=true" in response.json()["detail"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_all_documents_empty_list(self, mock_document_service):
        """测试删除空文档列表"""
        mock_document_service.list_documents.return_value = []
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.delete("/documents/?confirm=true")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert data["deleted_count"] == 0
            assert data["failed_count"] == 0
            assert "没有文档需要删除" in data["message"]
            
        finally:
            app.dependency_overrides.clear()
    
    def test_delete_all_documents_partial_failure(self, mock_document_service, sample_documents):
        """测试部分删除失败"""
        mock_document_service.list_documents.return_value = sample_documents
        
        # 模拟第二个文档删除失败
        def mock_delete(doc_id):
            if doc_id == sample_documents[1].id:
                return False
            return True
        
        mock_document_service.delete_document.side_effect = mock_delete
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            response = client.delete("/documents/?confirm=true")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is False
            assert data["deleted_count"] == 2
            assert data["failed_count"] == 1
            assert "failed_documents" in data
            
        finally:
            app.dependency_overrides.clear()


class TestDocumentAPIIntegration:
    """文档API集成测试"""
    
    def test_complete_document_management_workflow(self, mock_document_service, sample_documents):
        """测试完整的文档管理工作流"""
        # 设置mock服务
        mock_document_service.list_documents.return_value = sample_documents
        mock_document_service.get_document.return_value = sample_documents[0]
        mock_document_service.delete_document.return_value = True
        
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            
            # 1. 获取文档列表
            response = client.get("/documents/")
            assert response.status_code == 200
            assert response.json()["total_count"] == 3
            
            # 2. 获取单个文档
            doc_id = sample_documents[0].id
            response = client.get(f"/documents/{doc_id}")
            assert response.status_code == 200
            assert response.json()["id"] == doc_id
            
            # 3. 删除文档
            response = client.delete(f"/documents/{doc_id}")
            assert response.status_code == 200
            assert response.json()["success"] is True
            
            # 4. 获取统计信息
            mock_document_service.get_service_stats.return_value = {
                'total_documents': 2,
                'ready_documents': 1,
                'processing_documents': 1,
                'error_documents': 0,
                'total_chunks': 3,
                'vector_count': 3,
                'storage_directory': '/tmp',
                'supported_formats': ['txt', 'pdf']
            }
            
            response = client.get("/documents/stats/summary")
            assert response.status_code == 200
            assert response.json()["total_documents"] == 2
            
        finally:
            app.dependency_overrides.clear()
    
    def test_error_handling_consistency(self, mock_document_service):
        """测试错误处理的一致性"""
        app.dependency_overrides[get_document_service] = lambda: mock_document_service
        
        try:
            client = TestClient(app)
            
            # 测试各种404错误
            doc_id = str(uuid.uuid4())
            mock_document_service.get_document.side_effect = DocumentError("文档不存在")
            
            # GET请求404
            response = client.get(f"/documents/{doc_id}")
            assert response.status_code == 404
            
            # DELETE请求404
            response = client.delete(f"/documents/{doc_id}")
            assert response.status_code == 404
            
            # POST请求404
            response = client.post(f"/documents/{doc_id}/reprocess")
            assert response.status_code == 404
            
        finally:
            app.dependency_overrides.clear()