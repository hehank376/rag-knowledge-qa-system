"""
问答模型单元测试
"""
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
import uuid

from rag_system.models.qa import SourceInfo, QAResponse, QAPair, Session, QAStatus


class TestSourceInfo:
    """SourceInfo模型测试"""

    def test_create_source_info(self):
        """测试创建源文档信息"""
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        source = SourceInfo(
            document_id=doc_id,
            document_name="test.pdf",
            chunk_id=chunk_id,
            chunk_content="This is test content",
            chunk_index=0,
            similarity_score=0.85
        )
        
        assert source.document_id == doc_id
        assert source.document_name == "test.pdf"
        assert source.chunk_id == chunk_id
        assert source.chunk_content == "This is test content"
        assert source.chunk_index == 0
        assert source.similarity_score == 0.85
        assert source.metadata == {}

    def test_document_name_validation(self):
        """测试文档名称验证"""
        # 测试空文档名称
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                document_id=doc_id,
                document_name="",
                chunk_id=chunk_id,
                chunk_content="content",
                chunk_index=0,
                similarity_score=0.5
            )
        assert "文档名称不能为空" in str(exc_info.value)
        
        # 测试只有空格的文档名称
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                document_id=doc_id,
                document_name="   ",
                chunk_id=chunk_id,
                chunk_content="content",
                chunk_index=0,
                similarity_score=0.5
            )
        assert "文档名称不能为空" in str(exc_info.value)
        
        # 测试文档名称自动去除空格
        source = SourceInfo(
            document_id=doc_id,
            document_name="  test.pdf  ",
            chunk_id=chunk_id,
            chunk_content="content",
            chunk_index=0,
            similarity_score=0.5
        )
        assert source.document_name == "test.pdf"

    def test_chunk_content_validation(self):
        """测试文本块内容验证"""
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        # 测试空内容
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                document_id=doc_id,
                document_name="test.pdf",
                chunk_id=chunk_id,
                chunk_content="",
                chunk_index=0,
                similarity_score=0.5
            )
        assert "文本块内容不能为空" in str(exc_info.value)
        
        # 测试只有空格的内容
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                document_id=doc_id,
                document_name="test.pdf",
                chunk_id=chunk_id,
                chunk_content="   ",
                chunk_index=0,
                similarity_score=0.5
            )
        assert "文本块内容不能为空" in str(exc_info.value)
        
        # 测试内容自动去除空格
        source = SourceInfo(
            document_id=doc_id,
            document_name="test.pdf",
            chunk_id=chunk_id,
            chunk_content="  test content  ",
            chunk_index=0,
            similarity_score=0.5
        )
        assert source.chunk_content == "test content"

    def test_similarity_score_validation(self):
        """测试相似度分数验证"""
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        # 测试负数相似度分数
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                document_id=doc_id,
                document_name="test.pdf",
                chunk_id=chunk_id,
                chunk_content="content",
                chunk_index=0,
                similarity_score=-0.1
            )
        assert "Input should be greater than or equal to 0" in str(exc_info.value)
        
        # 测试大于1的相似度分数
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                document_id=doc_id,
                document_name="test.pdf",
                chunk_id=chunk_id,
                chunk_content="content",
                chunk_index=0,
                similarity_score=1.1
            )
        assert "Input should be less than or equal to 1" in str(exc_info.value)
        
        # 测试精度限制
        source = SourceInfo(
            document_id=doc_id,
            document_name="test.pdf",
            chunk_id=chunk_id,
            chunk_content="content",
            chunk_index=0,
            similarity_score=0.123456789
        )
        assert source.similarity_score == 0.1235

    def test_id_validation(self):
        """测试ID验证"""
        chunk_id = str(uuid.uuid4())
        
        # 测试无效的document_id
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                document_id="invalid-uuid",
                document_name="test.pdf",
                chunk_id=chunk_id,
                chunk_content="content",
                chunk_index=0,
                similarity_score=0.5
            )
        assert "无效的ID格式" in str(exc_info.value)
        
        # 测试无效的chunk_id
        doc_id = str(uuid.uuid4())
        with pytest.raises(ValidationError) as exc_info:
            SourceInfo(
                document_id=doc_id,
                document_name="test.pdf",
                chunk_id="invalid-uuid",
                chunk_content="content",
                chunk_index=0,
                similarity_score=0.5
            )
        assert "无效的ID格式" in str(exc_info.value)

    def test_chunk_index_validation(self):
        """测试文本块索引验证"""
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        # 测试负数索引
        with pytest.raises(ValidationError):
            SourceInfo(
                document_id=doc_id,
                document_name="test.pdf",
                chunk_id=chunk_id,
                chunk_content="content",
                chunk_index=-1,
                similarity_score=0.5
            )
        
        # 测试零索引
        source = SourceInfo(
            document_id=doc_id,
            document_name="test.pdf",
            chunk_id=chunk_id,
            chunk_content="content",
            chunk_index=0,
            similarity_score=0.5
        )
        assert source.chunk_index == 0


class TestQAResponse:
    """QAResponse模型测试"""

    def test_create_qa_response(self):
        """测试创建问答响应"""
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        sources = [
            SourceInfo(
                document_id=doc_id,
                document_name="test.pdf",
                chunk_id=chunk_id,
                chunk_content="content",
                chunk_index=0,
                similarity_score=0.8
            )
        ]
        
        response = QAResponse(
            question="What is this?",
            answer="This is the answer",
            sources=sources,
            confidence_score=0.9,
            processing_time=1.5
        )
        
        assert response.question == "What is this?"
        assert response.answer == "This is the answer"
        assert len(response.sources) == 1
        assert response.confidence_score == 0.9
        assert response.processing_time == 1.5
        assert response.status == QAStatus.COMPLETED
        assert response.error_message is None
        # 验证ID是有效的UUID
        uuid.UUID(response.id)

    def test_answer_validation(self):
        """测试答案验证"""
        # 测试空答案
        with pytest.raises(ValidationError) as exc_info:
            QAResponse(
                question="What?",
                answer="",
                confidence_score=0.5,
                processing_time=1.0
            )
        assert "问题和答案不能为空" in str(exc_info.value)
        
        # 测试只有空格的答案
        with pytest.raises(ValidationError) as exc_info:
            QAResponse(
                question="What?",
                answer="   ",
                confidence_score=0.5,
                processing_time=1.0
            )
        assert "问题和答案不能为空" in str(exc_info.value)
        
        # 测试答案自动去除空格
        response = QAResponse(
            question="What?",
            answer="  test answer  ",
            confidence_score=0.5,
            processing_time=1.0
        )
        assert response.answer == "test answer"

    def test_confidence_score_validation(self):
        """测试置信度分数验证"""
        # 测试负数置信度分数
        with pytest.raises(ValidationError) as exc_info:
            QAResponse(
                question="What?",
                answer="answer",
                confidence_score=-0.1,
                processing_time=1.0
            )
        assert "Input should be greater than or equal to 0" in str(exc_info.value)
        
        # 测试大于1的置信度分数
        with pytest.raises(ValidationError) as exc_info:
            QAResponse(
                question="What?",
                answer="answer",
                confidence_score=1.1,
                processing_time=1.0
            )
        assert "Input should be less than or equal to 1" in str(exc_info.value)
        
        # 测试精度限制
        response = QAResponse(
            question="What?",
            answer="answer",
            confidence_score=0.123456789,
            processing_time=1.0
        )
        assert response.confidence_score == 0.1235

    def test_processing_time_validation(self):
        """测试处理时间验证"""
        # 测试负数处理时间
        with pytest.raises(ValidationError) as exc_info:
            QAResponse(
                question="What?",
                answer="answer",
                confidence_score=0.5,
                processing_time=-1.0
            )
        assert "Input should be greater than or equal to 0" in str(exc_info.value)
        
        # 测试零处理时间
        response = QAResponse(
            question="What?",
            answer="answer",
            confidence_score=0.5,
            processing_time=0.0
        )
        assert response.processing_time == 0.0
        
        # 测试精度限制
        response = QAResponse(
            question="What?",
            answer="answer",
            confidence_score=0.5,
            processing_time=1.123456789
        )
        assert response.processing_time == 1.123

    def test_status_and_error_handling(self):
        """测试状态和错误处理"""
        # 测试默认状态
        response = QAResponse(
            question="What?",
            answer="answer",
            confidence_score=0.5,
            processing_time=1.0
        )
        assert response.status == QAStatus.COMPLETED
        assert response.error_message is None
        
        # 测试失败状态
        response = QAResponse(
            question="What?",
            answer="answer",
            confidence_score=0.5,
            processing_time=1.0,
            status=QAStatus.FAILED,
            error_message="Processing failed"
        )
        assert response.status == QAStatus.FAILED
        assert response.error_message == "Processing failed"


class TestQAPair:
    """QAPair模型测试"""

    def test_create_qa_pair_with_defaults(self):
        """测试使用默认值创建问答对"""
        session_id = str(uuid.uuid4())
        
        qa_pair = QAPair(
            session_id=session_id,
            question="What is AI?",
            answer="AI is artificial intelligence"
        )
        
        assert qa_pair.session_id == session_id
        assert qa_pair.question == "What is AI?"
        assert qa_pair.answer == "AI is artificial intelligence"
        assert qa_pair.sources == []
        assert isinstance(qa_pair.timestamp, datetime)
        # 验证ID是有效的UUID
        uuid.UUID(qa_pair.id)

    def test_create_qa_pair_with_all_fields(self):
        """测试创建包含所有字段的问答对"""
        qa_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        timestamp = datetime.now()
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        sources = [
            SourceInfo(
                document_id=doc_id,
                document_name="test.pdf",
                chunk_id=chunk_id,
                chunk_content="content",
                chunk_index=0,
                similarity_score=0.8
            )
        ]
        
        qa_pair = QAPair(
            id=qa_id,
            session_id=session_id,
            question="Test question",
            answer="Test answer",
            sources=sources,
            timestamp=timestamp
        )
        
        assert qa_pair.id == qa_id
        assert qa_pair.session_id == session_id
        assert qa_pair.question == "Test question"
        assert qa_pair.answer == "Test answer"
        assert len(qa_pair.sources) == 1
        assert qa_pair.timestamp == timestamp

    def test_qa_content_validation(self):
        """测试问答内容验证"""
        session_id = str(uuid.uuid4())
        
        # 测试空问题
        with pytest.raises(ValidationError) as exc_info:
            QAPair(
                session_id=session_id,
                question="",
                answer="answer"
            )
        assert "问题和答案不能为空" in str(exc_info.value)
        
        # 测试空答案
        with pytest.raises(ValidationError) as exc_info:
            QAPair(
                session_id=session_id,
                question="question",
                answer=""
            )
        assert "问题和答案不能为空" in str(exc_info.value)
        
        # 测试内容自动去除空格
        qa_pair = QAPair(
            session_id=session_id,
            question="  test question  ",
            answer="  test answer  "
        )
        assert qa_pair.question == "test question"
        assert qa_pair.answer == "test answer"

    def test_session_id_validation(self):
        """测试会话ID验证"""
        # 测试无效的会话ID
        with pytest.raises(ValidationError) as exc_info:
            QAPair(
                session_id="invalid-uuid",
                question="question",
                answer="answer"
            )
        assert "无效的会话ID格式" in str(exc_info.value)
        
        # 测试有效的会话ID
        session_id = str(uuid.uuid4())
        qa_pair = QAPair(
            session_id=session_id,
            question="question",
            answer="answer"
        )
        assert qa_pair.session_id == session_id


class TestSession:
    """Session模型测试"""

    def test_create_session_with_defaults(self):
        """测试使用默认值创建会话"""
        session = Session()
        
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_activity, datetime)
        assert session.qa_count == 0
        # 验证ID是有效的UUID
        uuid.UUID(session.id)

    def test_create_session_with_all_fields(self):
        """测试创建包含所有字段的会话"""
        session_id = str(uuid.uuid4())
        created_at = datetime.now()
        last_activity = created_at + timedelta(minutes=30)
        
        session = Session(
            id=session_id,
            created_at=created_at,
            last_activity=last_activity,
            qa_count=5
        )
        
        assert session.id == session_id
        assert session.created_at == created_at
        assert session.last_activity == last_activity
        assert session.qa_count == 5

    def test_last_activity_validation(self):
        """测试最后活动时间验证"""
        created_at = datetime.now()
        
        # 测试最后活动时间早于创建时间
        with pytest.raises(ValidationError) as exc_info:
            Session(
                created_at=created_at,
                last_activity=created_at - timedelta(minutes=10)
            )
        assert "最后活动时间不能早于创建时间" in str(exc_info.value)
        
        # 测试有效的最后活动时间
        session = Session(
            created_at=created_at,
            last_activity=created_at + timedelta(minutes=10)
        )
        assert session.last_activity > session.created_at

    def test_qa_count_validation(self):
        """测试问答对数量验证"""
        # 测试负数问答对数量
        with pytest.raises(ValidationError) as exc_info:
            Session(qa_count=-1)
        assert "Input should be greater than or equal to 0" in str(exc_info.value)
        
        # 测试零问答对数量
        session = Session(qa_count=0)
        assert session.qa_count == 0
        
        # 测试正数问答对数量
        session = Session(qa_count=10)
        assert session.qa_count == 10

    def test_update_activity(self):
        """测试更新活动时间"""
        session = Session()
        original_activity = session.last_activity
        
        # 等待一小段时间确保时间戳不同
        import time
        time.sleep(0.01)
        
        session.update_activity()
        assert session.last_activity > original_activity

    def test_json_serialization(self):
        """测试JSON序列化"""
        session = Session(qa_count=5)
        json_data = session.model_dump()
        
        assert "id" in json_data
        assert "created_at" in json_data
        assert "last_activity" in json_data
        assert json_data["qa_count"] == 5
        # 验证时间戳类型（在Pydantic v2中，model_dump()返回原始类型）
        assert isinstance(json_data["created_at"], datetime)
        assert isinstance(json_data["last_activity"], datetime)


class TestQAStatus:
    """QAStatus枚举测试"""

    def test_qa_status_values(self):
        """测试问答状态枚举值"""
        assert QAStatus.PENDING == "pending"
        assert QAStatus.PROCESSING == "processing"
        assert QAStatus.COMPLETED == "completed"
        assert QAStatus.FAILED == "failed"

    def test_qa_status_in_model(self):
        """测试在模型中使用问答状态"""
        response = QAResponse(
            question="What?",
            answer="answer",
            confidence_score=0.5,
            processing_time=1.0,
            status=QAStatus.PROCESSING
        )
        assert response.status == QAStatus.PROCESSING
        
        # 测试序列化后的值
        json_data = response.model_dump()
        assert json_data["status"] == "processing"