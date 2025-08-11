"""
增强问答API测试
测试问答API的所有功能，包括会话管理
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, MagicMock, patch

from rag_system.api.qa_api import router
from rag_system.models.qa import QAResponse, QAStatus, SourceInfo


@pytest.fixture
def app():
    """创建测试应用"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_qa_service():
    """模拟QA服务"""
    service = AsyncMock()
    
    # 模拟问答响应
    source_info = SourceInfo(
        document_id="12345678-1234-1234-1234-123456789012",
        document_name="AI文档.pdf",
        chunk_id="87654321-4321-4321-4321-210987654321",
        chunk_content="人工智能定义...",
        chunk_index=0,
        similarity_score=0.9
    )
    
    qa_response = QAResponse(
        question="什么是人工智能？",
        answer="人工智能是计算机科学的一个分支，致力于创建能够执行通常需要人类智能的任务的系统。",
        sources=[source_info],
        confidence_score=0.85,
        processing_time=1.2,
        status=QAStatus.COMPLETED
    )
    
    service.answer_question.return_value = qa_response
    service.get_service_stats.return_value = {
        "questions_processed": 100,
        "average_processing_time": 1.5,
        "success_rate": 0.95
    }
    service.test_qa.return_value = {
        "success": True,
        "message": "QA服务测试成功"
    }
    
    return service


@pytest.fixture
def mock_result_processor():
    """模拟结果处理器"""
    processor = MagicMock()
    
    processor.format_qa_response.return_value = {
        "id": "qa_123",
        "question": "什么是人工智能？",
        "answer": "人工智能是计算机科学的一个分支...",
        "sources": [{"document_id": "doc1", "content": "...", "score": 0.9}],
        "has_sources": True,
        "source_count": 1,
        "confidence_score": 0.85,
        "processing_time": 1.2,
        "status": "completed",
        "timestamp": "2024-01-01T12:00:00",
        "metadata": {}
    }
    
    processor.create_no_answer_response.return_value = {
        "answer": "抱歉，我无法找到相关信息来回答您的问题。",
        "reason": "no_relevant_content",
        "suggestions": ["尝试使用不同的关键词", "检查文档是否已上传"],
        "has_answer": False,
        "confidence_score": 0.0
    }
    
    processor.get_service_stats.return_value = {
        "responses_formatted": 50,
        "average_format_time": 0.1
    }
    
    return processor


@pytest.fixture
def mock_session_service():
    """模拟会话服务"""
    service = AsyncMock()
    
    service.create_session.return_value = "session_123"
    service.save_qa_pair.return_value = None
    service.update_session_activity.return_value = None
    service.get_session_history.return_value = []
    service.get_session_statistics.return_value = {
        "total_qa_pairs": 5,
        "session_duration": 3600
    }
    service.get_recent_qa_pairs.return_value = []
    service.search_qa_pairs.return_value = []
    
    return service


class TestQAAPI:
    """问答API测试类"""
    
    @patch('rag_system.api.qa_api.get_qa_service')
    @patch('rag_system.api.qa_api.get_result_processor')
    def test_ask_question_basic(self, mock_get_processor, mock_get_service, 
                               client, mock_qa_service, mock_result_processor):
        """测试基础问答功能"""
        mock_get_service.return_value = mock_qa_service
        mock_get_processor.return_value = mock_result_processor
        
        response = client.post(
            "/qa/ask",
            json={
                "question": "什么是人工智能？",
                "top_k": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "什么是人工智能？"
        assert data["has_sources"] is True
        assert data["source_count"] == 1
        assert data["confidence_score"] == 0.85
    
    @patch('rag_system.api.qa_api.get_qa_service')
    @patch('rag_system.api.qa_api.get_result_processor')
    @patch('rag_system.api.qa_api.get_session_service')
    def test_ask_question_with_session(self, mock_get_session, mock_get_processor, 
                                     mock_get_service, client, mock_qa_service, 
                                     mock_result_processor, mock_session_service):
        """测试带会话的问答功能"""
        mock_get_service.return_value = mock_qa_service
        mock_get_processor.return_value = mock_result_processor
        mock_get_session.return_value = mock_session_service
        
        response = client.post(
            "/qa/ask-with-session",
            json={
                "question": "什么是机器学习？"
            },
            params={"user_id": "user_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "qa_response" in data
        assert "session_info" in data
        assert data["session_info"]["session_id"] == "session_123"
        assert data["session_info"]["created_new_session"] is True
    
    @patch('rag_system.api.qa_api.get_qa_service')
    @patch('rag_system.api.qa_api.get_result_processor')
    def test_ask_question_with_timeout(self, mock_get_processor, mock_get_service,
                                     client, mock_qa_service, mock_result_processor):
        """测试带超时的问答功能"""
        mock_get_service.return_value = mock_qa_service
        mock_get_processor.return_value = mock_result_processor
        
        response = client.post(
            "/qa/ask-with-timeout",
            json={
                "question": "什么是深度学习？",
                "timeout": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "什么是深度学习？"
    
    @patch('rag_system.api.qa_api.get_session_service')
    def test_get_session_history(self, mock_get_session, client, mock_session_service):
        """测试获取会话历史"""
        mock_get_session.return_value = mock_session_service
        
        response = client.get("/qa/session/session_123/history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "session_123"
        assert "history" in data
        assert "session_stats" in data
    
    @patch('rag_system.api.qa_api.get_session_service')
    def test_get_recent_qa_pairs(self, mock_get_session, client, mock_session_service):
        """测试获取最近问答对"""
        mock_get_session.return_value = mock_session_service
        
        response = client.get("/qa/sessions/recent", params={"limit": 10})
        
        assert response.status_code == 200
        data = response.json()
        assert "recent_qa_pairs" in data
        assert data["total_count"] == 0
    
    @patch('rag_system.api.qa_api.get_session_service')
    def test_search_qa_pairs(self, mock_get_session, client, mock_session_service):
        """测试搜索问答对"""
        mock_get_session.return_value = mock_session_service
        
        response = client.get("/qa/search", params={"query": "人工智能"})
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "人工智能"
        assert "results" in data
    
    def test_search_qa_pairs_empty_query(self, client):
        """测试空查询搜索"""
        response = client.get("/qa/search", params={"query": ""})
        
        assert response.status_code == 400
        assert "搜索查询不能为空" in response.json()["detail"]
    
    @patch('rag_system.api.qa_api.get_result_processor')
    def test_no_answer_help(self, mock_get_processor, client, mock_result_processor):
        """测试无答案帮助"""
        mock_get_processor.return_value = mock_result_processor
        
        response = client.post(
            "/qa/no-answer-help",
            params={
                "question": "这是一个测试问题",
                "reason": "no_relevant_content"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_answer"] is False
        assert data["reason"] == "no_relevant_content"
        assert len(data["suggestions"]) > 0
    
    @patch('rag_system.api.qa_api.get_qa_service')
    @patch('rag_system.api.qa_api.get_result_processor')
    def test_get_stats(self, mock_get_processor, mock_get_service,
                      client, mock_qa_service, mock_result_processor):
        """测试获取统计信息"""
        mock_get_service.return_value = mock_qa_service
        mock_get_processor.return_value = mock_result_processor
        
        response = client.get("/qa/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "qa_service_stats" in data
        assert "result_processor_stats" in data
    
    @patch('rag_system.api.qa_api.get_qa_service')
    @patch('rag_system.api.qa_api.get_result_processor')
    def test_test_qa_system(self, mock_get_processor, mock_get_service,
                           client, mock_qa_service, mock_result_processor):
        """测试问答系统测试接口"""
        mock_get_service.return_value = mock_qa_service
        mock_get_processor.return_value = mock_result_processor
        
        response = client.post("/qa/test")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["system_status"] == "healthy"
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/qa/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "qa_api"
    
    def test_ask_question_empty_question(self, client):
        """测试空问题"""
        response = client.post(
            "/qa/ask",
            json={"question": ""}
        )
        
        assert response.status_code == 400
        assert "问题不能为空" in response.json()["detail"]


class TestStreamingAPI:
    """流式API测试类"""
    
    @patch('rag_system.api.qa_api.get_qa_service')
    @patch('rag_system.api.qa_api.get_result_processor')
    def test_ask_question_stream(self, mock_get_processor, mock_get_service,
                                client, mock_qa_service, mock_result_processor):
        """测试流式问答"""
        mock_get_service.return_value = mock_qa_service
        mock_get_processor.return_value = mock_result_processor
        
        response = client.post(
            "/qa/ask-stream",
            json={
                "question": "什么是人工智能？",
                "timeout": 5
            }
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        # 检查流式响应内容
        content = response.text
        assert "data:" in content
        assert "start" in content or "complete" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])