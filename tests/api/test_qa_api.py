"""
问答API测试
"""
import pytest
import pytest_asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime

from rag_system.api.qa_api import router, get_qa_service, get_result_processor
from rag_system.models.qa import QAResponse, SourceInfo, QAStatus
from rag_system.utils.exceptions import QAError

# 创建测试应用
app = FastAPI()
app.include_router(router)

@pytest_asyncio.fixture
def mock_qa_service():
    """Mock QA服务fixture"""
    service = Mock()
    service.initialize = AsyncMock()
    service.cleanup = AsyncMock()
    service.answer_question = AsyncMock()
    service.test_qa = AsyncMock()
    service.get_service_stats = AsyncMock()
    return service

@pytest_asyncio.fixture
def mock_result_processor():
    """Mock结果处理器fixture"""
    processor = Mock()
    processor.initialize = AsyncMock()
    processor.cleanup = AsyncMock()
    processor.format_qa_response = Mock()
    processor.create_no_answer_response = Mock()
    processor.get_service_stats = Mock()
    return processor

@pytest_asyncio.fixture
def sample_qa_response():
    """示例QA响应fixture"""
    return QAResponse(
        question="什么是人工智能？",
        answer="人工智能是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。",
        sources=[
            SourceInfo(
                document_id=str(uuid.uuid4()),
                document_name="AI基础知识",
                chunk_id=str(uuid.uuid4()),
                chunk_content="人工智能的定义和基本概念",
                chunk_index=0,
                similarity_score=0.9
            )
        ],
        confidence_score=0.85,
        processing_time=1.2,
        status=QAStatus.COMPLETED
    )

@pytest_asyncio.fixture
def sample_formatted_response():
    """示例格式化响应fixture"""
    return {
        "id": str(uuid.uuid4()),
        "question": "什么是人工智能？",
        "answer": "人工智能是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。",
        "sources": [
            {
                "document_id": str(uuid.uuid4()),
                "document_name": "AI基础知识",
                "chunk_id": str(uuid.uuid4()),
                "chunk_content": "人工智能的定义和基本概念",
                "chunk_index": 0,
                "similarity_score": 0.9
            }
        ],
        "has_sources": True,
        "source_count": 1,
        "confidence_score": 0.85,
        "processing_time": 1.2,
        "status": "completed",
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "model_used": "gpt-3.5-turbo",
            "retrieval_method": "semantic_search"
        }
    }

class TestQAAPI:
    """问答API测试类"""

    @pytest.fixture(autouse=True)
    def setup_method(self, mock_qa_service, mock_result_processor):
        """设置测试方法"""
        self.mock_qa_service = mock_qa_service
        self.mock_result_processor = mock_result_processor
        self.client = TestClient(app)

    def test_ask_question_success(self, sample_qa_response, sample_formatted_response):
        """测试成功的问答请求"""
        # 设置mock返回值
        self.mock_qa_service.answer_question.return_value = sample_qa_response
        self.mock_result_processor.format_qa_response.return_value = sample_formatted_response

        # 覆盖依赖
        app.dependency_overrides[get_qa_service] = lambda: self.mock_qa_service
        app.dependency_overrides[get_result_processor] = lambda: self.mock_result_processor

        # 发送请求
        response = self.client.post(
            "/qa/ask",
            json={
                "question": "什么是人工智能？",
                "top_k": 5,
                "temperature": 0.7
            }
        )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "什么是人工智能？"
        assert data["has_sources"] is True
        assert data["source_count"] == 1
        assert data["confidence_score"] == 0.85

        # 验证服务调用
        self.mock_qa_service.answer_question.assert_called_once()
        self.mock_result_processor.format_qa_response.assert_called_once()

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_ask_question_empty_question(self):
        """测试空问题请求"""
        # 覆盖依赖
        app.dependency_overrides[get_qa_service] = lambda: self.mock_qa_service
        app.dependency_overrides[get_result_processor] = lambda: self.mock_result_processor

        # 发送空问题请求
        response = self.client.post(
            "/qa/ask",
            json={"question": ""}
        )

        # 验证响应
        assert response.status_code == 400
        assert "问题不能为空" in response.json()["detail"]

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_ask_question_qa_error(self):
        """测试QA服务错误"""
        # 设置mock抛出异常
        self.mock_qa_service.answer_question.side_effect = QAError("QA服务错误")

        # 覆盖依赖
        app.dependency_overrides[get_qa_service] = lambda: self.mock_qa_service
        app.dependency_overrides[get_result_processor] = lambda: self.mock_result_processor

        # 发送请求
        response = self.client.post(
            "/qa/ask",
            json={"question": "测试问题"}
        )

        # 验证响应
        assert response.status_code == 500
        assert "问答处理失败" in response.json()["detail"]

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_get_no_answer_help(self):
        """测试获取无答案帮助"""
        # 设置mock返回值
        no_answer_response = {
            "answer": "抱歉，我无法找到相关信息来回答您的问题。",
            "reason": "no_relevant_content",
            "suggestions": ["尝试使用不同的关键词", "检查问题的拼写"],
            "has_answer": False,
            "confidence_score": 0.0
        }
        self.mock_result_processor.create_no_answer_response.return_value = no_answer_response

        # 覆盖依赖
        app.dependency_overrides[get_result_processor] = lambda: self.mock_result_processor

        # 发送请求
        response = self.client.post(
            "/qa/no-answer-help",
            params={
                "question": "测试问题",
                "reason": "no_relevant_content"
            }
        )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["has_answer"] is False
        assert data["reason"] == "no_relevant_content"
        assert len(data["suggestions"]) > 0

        # 验证服务调用
        self.mock_result_processor.create_no_answer_response.assert_called_once_with(
            "测试问题", "no_relevant_content"
        )

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_get_qa_stats(self):
        """测试获取问答统计"""
        # 设置mock返回值
        qa_stats = {
            "total_questions": 100,
            "average_response_time": 1.5,
            "success_rate": 0.95
        }
        processor_stats = {
            "total_processed": 100,
            "average_processing_time": 0.3,
            "format_success_rate": 0.99
        }
        self.mock_qa_service.get_service_stats.return_value = qa_stats
        self.mock_result_processor.get_service_stats.return_value = processor_stats

        # 覆盖依赖
        app.dependency_overrides[get_qa_service] = lambda: self.mock_qa_service
        app.dependency_overrides[get_result_processor] = lambda: self.mock_result_processor

        # 发送请求
        response = self.client.get("/qa/stats")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "qa_service_stats" in data
        assert "result_processor_stats" in data
        assert data["qa_service_stats"]["total_questions"] == 100
        assert data["result_processor_stats"]["total_processed"] == 100

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_test_qa_system_success(self):
        """测试问答系统测试接口成功"""
        # 设置mock返回值
        qa_test_result = {
            "success": True,
            "response_time": 1.2,
            "components_status": {"llm": "healthy", "vector_store": "healthy"}
        }
        self.mock_qa_service.test_qa.return_value = qa_test_result
        
        # 设置结果处理器mock
        formatted_test = {
            "id": str(uuid.uuid4()),
            "question": "测试问题",
            "answer": "这是一个测试答案，用于验证结果处理功能。",
            "sources": [],
            "has_sources": False,
            "source_count": 0,
            "confidence_score": 0.8,
            "processing_time": 1.0,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "metadata": {}
        }
        self.mock_result_processor.format_qa_response.return_value = formatted_test

        # 覆盖依赖
        app.dependency_overrides[get_qa_service] = lambda: self.mock_qa_service
        app.dependency_overrides[get_result_processor] = lambda: self.mock_result_processor

        # 发送请求
        response = self.client.post(
            "/qa/test",
            params={"test_question": "测试问题"}
        )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["system_status"] == "healthy"
        assert "qa_test" in data
        assert "formatting_test" in data

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_test_qa_system_failure(self):
        """测试问答系统测试接口失败"""
        # 设置mock返回值
        qa_test_result = {
            "success": False,
            "error": "LLM服务不可用"
        }
        self.mock_qa_service.test_qa.return_value = qa_test_result

        # 覆盖依赖
        app.dependency_overrides[get_qa_service] = lambda: self.mock_qa_service
        app.dependency_overrides[get_result_processor] = lambda: self.mock_result_processor

        # 发送请求
        response = self.client.post("/qa/test")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["system_status"] == "unhealthy"

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_format_qa_response(self, sample_formatted_response):
        """测试格式化QA响应接口"""
        # 设置mock返回值
        self.mock_result_processor.format_qa_response.return_value = sample_formatted_response

        # 覆盖依赖
        app.dependency_overrides[get_result_processor] = lambda: self.mock_result_processor

        # 准备请求数据
        qa_response_data = {
            "question": "什么是人工智能？",
            "answer": "人工智能是计算机科学的一个分支。",
            "sources": [],
            "confidence_score": 0.85,
            "processing_time": 1.2,
            "status": "completed"
        }

        # 发送请求
        response = self.client.post(
            "/qa/format-response",
            json=qa_response_data
        )

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "什么是人工智能？"
        assert data["confidence_score"] == 0.85

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_format_qa_response_invalid_data(self):
        """测试格式化QA响应接口无效数据"""
        # 覆盖依赖
        app.dependency_overrides[get_result_processor] = lambda: self.mock_result_processor

        # 发送无效数据
        response = self.client.post(
            "/qa/format-response",
            json={"invalid": "data"}
        )

        # 验证响应
        assert response.status_code == 400
        assert "格式化响应失败" in response.json()["detail"]

        # 清理依赖覆盖
        app.dependency_overrides.clear()

    def test_health_check(self):
        """测试健康检查接口"""
        response = self.client.get("/qa/health")

        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "qa_api"
        assert data["version"] == "1.0.0"


class TestQAAPIIntegration:
    """问答API集成测试类"""

    def test_complete_qa_workflow(self, sample_qa_response, sample_formatted_response):
        """测试完整的问答工作流程"""
        # 设置mock服务
        mock_qa_service = Mock()
        mock_qa_service.answer_question = AsyncMock(return_value=sample_qa_response)

        mock_processor = Mock()
        mock_processor.format_qa_response.return_value = sample_formatted_response

        # 覆盖依赖
        app.dependency_overrides[get_qa_service] = lambda: mock_qa_service
        app.dependency_overrides[get_result_processor] = lambda: mock_processor

        try:
            # 创建测试客户端
            client = TestClient(app)

            # 发送问答请求
            response = client.post(
                "/qa/ask",
                json={
                    "question": "什么是人工智能？",
                    "top_k": 5
                }
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["question"] == "什么是人工智能？"
            assert data["has_sources"] is True

            # 验证服务调用
            mock_qa_service.answer_question.assert_called_once()
            mock_processor.format_qa_response.assert_called_once()
        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_error_handling_workflow(self):
        """测试错误处理工作流程"""
        # 设置mock服务抛出异常
        mock_qa_service = Mock()
        mock_qa_service.answer_question = AsyncMock(side_effect=QAError("服务错误"))

        mock_processor = Mock()

        # 覆盖依赖
        app.dependency_overrides[get_qa_service] = lambda: mock_qa_service
        app.dependency_overrides[get_result_processor] = lambda: mock_processor

        try:
            # 创建测试客户端
            client = TestClient(app)

            # 发送问答请求
            response = client.post(
                "/qa/ask",
                json={"question": "测试问题"}
            )

            # 验证错误响应
            assert response.status_code == 500
            assert "问答处理失败" in response.json()["detail"]
        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()