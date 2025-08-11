"""
数据库CRUD操作测试
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
import uuid

from rag_system.models.config import DatabaseConfig
from rag_system.models.document import DocumentInfo, DocumentStatus
from rag_system.models.qa import QAPair, SourceInfo, Session
from rag_system.database.connection import DatabaseManager
from rag_system.database.crud import DocumentCRUD, SessionCRUD, QAPairCRUD
from rag_system.utils.exceptions import DocumentError, SessionError


@pytest.fixture
def db_manager():
    """数据库管理器fixture"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    
    config = DatabaseConfig(url=f"sqlite:///{db_path}")
    manager = DatabaseManager(config)
    manager.initialize()
    
    yield manager
    
    manager.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def document_crud(db_manager):
    """文档CRUD fixture"""
    with db_manager.get_session_context() as session:
        yield DocumentCRUD(session)


@pytest.fixture
def session_crud(db_manager):
    """会话CRUD fixture"""
    with db_manager.get_session_context() as session:
        yield SessionCRUD(session)


@pytest.fixture
def qa_pair_crud(db_manager):
    """问答对CRUD fixture"""
    with db_manager.get_session_context() as session:
        yield QAPairCRUD(session)


class TestDocumentCRUD:
    """文档CRUD测试"""
    
    def test_create_document(self, document_crud):
        """测试创建文档"""
        doc_info = DocumentInfo(
            id=str(uuid.uuid4()),
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            upload_time=datetime.now(),
            status=DocumentStatus.PROCESSING
        )
        
        db_document = document_crud.create_document(doc_info)
        
        assert db_document.id == doc_info.id
        assert db_document.filename == doc_info.filename
        assert db_document.file_type == doc_info.file_type
        assert db_document.file_size == doc_info.file_size
        assert db_document.status.value == doc_info.status
    
    def test_get_document(self, document_crud):
        """测试获取文档"""
        # 创建文档
        doc_info = DocumentInfo(
            id=str(uuid.uuid4()),
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            upload_time=datetime.now(),
            status=DocumentStatus.READY
        )
        
        created_doc = document_crud.create_document(doc_info)
        
        # 获取文档
        retrieved_doc = document_crud.get_document(created_doc.id)
        
        assert retrieved_doc is not None
        assert retrieved_doc.id == created_doc.id
        assert retrieved_doc.filename == created_doc.filename
        
        # 测试获取不存在的文档
        non_existent = document_crud.get_document(str(uuid.uuid4()))
        assert non_existent is None
    
    def test_get_documents(self, document_crud):
        """测试获取文档列表"""
        # 创建多个文档
        docs = []
        for i in range(3):
            doc_info = DocumentInfo(
                id=str(uuid.uuid4()),
                filename=f"test{i}.pdf",
                file_type="pdf",
                file_size=1024 * (i + 1),
                upload_time=datetime.now() + timedelta(seconds=i),
                status=DocumentStatus.READY
            )
            docs.append(document_crud.create_document(doc_info))
        
        # 获取文档列表
        retrieved_docs = document_crud.get_documents()
        
        assert len(retrieved_docs) >= 3
        # 验证按上传时间倒序排列
        for i in range(len(retrieved_docs) - 1):
            assert retrieved_docs[i].upload_time >= retrieved_docs[i + 1].upload_time
    
    def test_update_document_status(self, document_crud):
        """测试更新文档状态"""
        # 创建文档
        doc_info = DocumentInfo(
            id=str(uuid.uuid4()),
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            upload_time=datetime.now(),
            status=DocumentStatus.PROCESSING
        )
        
        created_doc = document_crud.create_document(doc_info)
        
        # 更新状态为就绪
        from rag_system.database.models import DocumentStatus as DBDocumentStatus
        success = document_crud.update_document_status(
            created_doc.id, 
            DBDocumentStatus.READY
        )
        
        assert success is True
        
        # 验证状态已更新
        updated_doc = document_crud.get_document(created_doc.id)
        assert updated_doc.status == DBDocumentStatus.READY
        
        # 测试更新不存在的文档
        success = document_crud.update_document_status(
            str(uuid.uuid4()), 
            DBDocumentStatus.ERROR
        )
        assert success is False
    
    def test_delete_document(self, document_crud):
        """测试删除文档"""
        # 创建文档
        doc_info = DocumentInfo(
            id=str(uuid.uuid4()),
            filename="test.pdf",
            file_type="pdf",
            file_size=1024,
            upload_time=datetime.now(),
            status=DocumentStatus.READY
        )
        
        created_doc = document_crud.create_document(doc_info)
        
        # 删除文档
        success = document_crud.delete_document(created_doc.id)
        assert success is True
        
        # 验证文档已删除
        deleted_doc = document_crud.get_document(created_doc.id)
        assert deleted_doc is None
        
        # 测试删除不存在的文档
        success = document_crud.delete_document(str(uuid.uuid4()))
        assert success is False


class TestSessionCRUD:
    """会话CRUD测试"""
    
    def test_create_session(self, session_crud):
        """测试创建会话"""
        db_session = session_crud.create_session()
        
        assert db_session.id is not None
        assert db_session.created_at is not None
        assert db_session.last_activity is not None
        assert db_session.qa_count == 0
        
        # 验证UUID格式
        uuid.UUID(db_session.id)
    
    def test_create_session_with_id(self, session_crud):
        """测试使用指定ID创建会话"""
        session_id = str(uuid.uuid4())
        db_session = session_crud.create_session(session_id)
        
        assert db_session.id == session_id
    
    def test_get_session(self, session_crud):
        """测试获取会话"""
        # 创建会话
        created_session = session_crud.create_session()
        
        # 获取会话
        retrieved_session = session_crud.get_session(created_session.id)
        
        assert retrieved_session is not None
        assert retrieved_session.id == created_session.id
        
        # 测试获取不存在的会话
        non_existent = session_crud.get_session(str(uuid.uuid4()))
        assert non_existent is None
    
    def test_update_session_activity(self, session_crud):
        """测试更新会话活动时间"""
        # 创建会话
        created_session = session_crud.create_session()
        original_activity = created_session.last_activity
        
        # 等待一小段时间
        import time
        time.sleep(0.01)
        
        # 更新活动时间
        success = session_crud.update_session_activity(created_session.id)
        assert success is True
        
        # 验证活动时间已更新
        updated_session = session_crud.get_session(created_session.id)
        assert updated_session.last_activity > original_activity
    
    def test_increment_qa_count(self, session_crud):
        """测试增加问答数量"""
        # 创建会话
        created_session = session_crud.create_session()
        assert created_session.qa_count == 0
        
        # 增加问答数量
        success = session_crud.increment_qa_count(created_session.id)
        assert success is True
        
        # 验证数量已增加
        updated_session = session_crud.get_session(created_session.id)
        assert updated_session.qa_count == 1
        
        # 再次增加
        success = session_crud.increment_qa_count(created_session.id)
        assert success is True
        
        updated_session = session_crud.get_session(created_session.id)
        assert updated_session.qa_count == 2


class TestQAPairCRUD:
    """问答对CRUD测试"""
    
    def test_create_qa_pair(self, qa_pair_crud, session_crud):
        """测试创建问答对"""
        # 先创建会话
        session = session_crud.create_session()
        
        # 创建源文档信息
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        source = SourceInfo(
            document_id=doc_id,
            document_name="test.pdf",
            chunk_id=chunk_id,
            chunk_content="test content",
            chunk_index=0,
            similarity_score=0.8
        )
        
        # 创建问答对
        qa_pair = QAPair(
            session_id=session.id,
            question="What is this?",
            answer="This is a test",
            sources=[source],
            confidence_score=0.9,
            processing_time=1.5
        )
        
        db_qa_pair = qa_pair_crud.create_qa_pair(qa_pair)
        
        assert db_qa_pair.id == qa_pair.id
        assert db_qa_pair.session_id == qa_pair.session_id
        assert db_qa_pair.question == qa_pair.question
        assert db_qa_pair.answer == qa_pair.answer
        assert len(db_qa_pair.sources) == 1
        assert db_qa_pair.sources[0]["document_name"] == "test.pdf"
    
    def test_get_session_qa_pairs(self, qa_pair_crud, session_crud):
        """测试获取会话的问答对列表"""
        # 创建会话
        session = session_crud.create_session()
        
        # 创建多个问答对
        qa_pairs = []
        for i in range(3):
            qa_pair = QAPair(
                session_id=session.id,
                question=f"Question {i}?",
                answer=f"Answer {i}",
                timestamp=datetime.now() + timedelta(seconds=i)
            )
            qa_pairs.append(qa_pair_crud.create_qa_pair(qa_pair))
        
        # 获取会话的问答对列表
        retrieved_pairs = qa_pair_crud.get_session_qa_pairs(session.id)
        
        assert len(retrieved_pairs) == 3
        # 验证按时间戳倒序排列
        for i in range(len(retrieved_pairs) - 1):
            assert retrieved_pairs[i].timestamp >= retrieved_pairs[i + 1].timestamp
    
    def test_search_qa_pairs(self, qa_pair_crud, session_crud):
        """测试搜索问答对"""
        # 创建会话
        session = session_crud.create_session()
        
        # 创建包含特定关键词的问答对
        qa_pair1 = QAPair(
            session_id=session.id,
            question="What is machine learning?",
            answer="Machine learning is a subset of AI"
        )
        
        qa_pair2 = QAPair(
            session_id=session.id,
            question="How does deep learning work?",
            answer="Deep learning uses neural networks"
        )
        
        qa_pair_crud.create_qa_pair(qa_pair1)
        qa_pair_crud.create_qa_pair(qa_pair2)
        
        # 搜索包含"learning"的问答对
        results = qa_pair_crud.search_qa_pairs("learning")
        assert len(results) == 2
        
        # 搜索包含"machine"的问答对
        results = qa_pair_crud.search_qa_pairs("machine")
        assert len(results) == 1
        assert "machine learning" in results[0].question.lower()
    
    def test_delete_qa_pair(self, qa_pair_crud, session_crud):
        """测试删除问答对"""
        # 创建会话和问答对
        session = session_crud.create_session()
        qa_pair = QAPair(
            session_id=session.id,
            question="Test question",
            answer="Test answer"
        )
        
        created_pair = qa_pair_crud.create_qa_pair(qa_pair)
        
        # 删除问答对
        success = qa_pair_crud.delete_qa_pair(created_pair.id)
        assert success is True
        
        # 验证已删除
        deleted_pair = qa_pair_crud.get_qa_pair(created_pair.id)
        assert deleted_pair is None
        
        # 测试删除不存在的问答对
        success = qa_pair_crud.delete_qa_pair(str(uuid.uuid4()))
        assert success is False