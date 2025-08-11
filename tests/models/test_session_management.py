"""
会话管理相关数据模型测试
"""
import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
import uuid

from rag_system.models.qa import Session, QAPair, SourceInfo


class TestSessionManagement:
    """会话管理功能测试"""

    def test_session_qa_pair_relationship(self):
        """测试会话和问答对的关系"""
        # 创建会话
        session = Session()
        session_id = session.id
        
        # 创建问答对
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        sources = [
            SourceInfo(
                document_id=doc_id,
                document_name="test.pdf",
                chunk_id=chunk_id,
                chunk_content="test content",
                chunk_index=0,
                similarity_score=0.8
            )
        ]
        
        qa_pair = QAPair(
            session_id=session_id,
            question="What is this?",
            answer="This is a test",
            sources=sources
        )
        
        assert qa_pair.session_id == session_id
        assert len(qa_pair.sources) == 1
        assert qa_pair.sources[0].document_name == "test.pdf"

    def test_session_activity_tracking(self):
        """测试会话活动跟踪"""
        session = Session()
        original_activity = session.last_activity
        
        # 模拟时间流逝
        import time
        time.sleep(0.01)
        
        # 更新活动时间
        session.update_activity()
        assert session.last_activity > original_activity
        
        # 验证创建时间没有改变
        assert session.created_at < session.last_activity

    def test_session_qa_count_management(self):
        """测试会话问答数量管理"""
        session = Session()
        assert session.qa_count == 0
        
        # 模拟增加问答对
        session.qa_count += 1
        session.update_activity()
        assert session.qa_count == 1
        
        # 模拟再次增加
        session.qa_count += 1
        session.update_activity()
        assert session.qa_count == 2

    def test_multiple_qa_pairs_in_session(self):
        """测试一个会话中的多个问答对"""
        session = Session()
        session_id = session.id
        
        doc_id = str(uuid.uuid4())
        chunk_id = str(uuid.uuid4())
        
        # 创建多个问答对
        qa_pairs = []
        for i in range(3):
            sources = [
                SourceInfo(
                    document_id=doc_id,
                    document_name=f"test{i}.pdf",
                    chunk_id=chunk_id,
                    chunk_content=f"content {i}",
                    chunk_index=i,
                    similarity_score=0.8 - i * 0.1
                )
            ]
            
            qa_pair = QAPair(
                session_id=session_id,
                question=f"Question {i}?",
                answer=f"Answer {i}",
                sources=sources
            )
            qa_pairs.append(qa_pair)
        
        # 验证所有问答对都属于同一个会话
        for qa_pair in qa_pairs:
            assert qa_pair.session_id == session_id
        
        # 验证问答对的内容不同
        assert qa_pairs[0].question != qa_pairs[1].question
        assert qa_pairs[0].sources[0].document_name != qa_pairs[1].sources[0].document_name

    def test_session_serialization_with_metadata(self):
        """测试会话序列化包含元数据"""
        session = Session(qa_count=5)
        
        # 测试基本序列化
        json_data = session.model_dump()
        assert json_data["qa_count"] == 5
        assert "id" in json_data
        assert "created_at" in json_data
        assert "last_activity" in json_data
        
        # 验证UUID格式
        uuid.UUID(json_data["id"])
        
        # 验证时间戳类型
        assert isinstance(json_data["created_at"], datetime)
        assert isinstance(json_data["last_activity"], datetime)