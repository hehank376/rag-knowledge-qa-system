"""
测试健康检查API
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime

from rag_system.api.health_api import router, get_health_checker
from rag_system.utils.health_checker import ModelHealthChecker, ModelHealthStatus
from rag_system.models.health import HealthStatus


# 创建测试应用
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestHealthAPI:
    """测试健康检查API"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        # 重置全局健康检查器
        import rag_system.api.health_api
        rag_system.api.health_api._health_checker = None
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_system_health_success(self, mock_get_checker):
        """测试获取系统健康状态成功"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.generate_health_report.return_value = {
            "overall_status": "healthy",
            "last_check": "2025-08-03T10:00:00",
            "total_models": 2,
            "healthy_models": 2,
            "unhealthy_models": 0,
            "models": {
                "openai:llm:gpt-4": {
                    "provider": "openai",
                    "model_name": "gpt-4",
                    "model_type": "llm",
                    "is_healthy": True,
                    "response_time": 1.5,
                    "success_rate": 1.0,
                    "consecutive_failures": 0,
                    "total_checks": 10,
                    "last_check": "2025-08-03T10:00:00",
                    "error_message": None
                }
            },
            "providers": {
                "openai": {
                    "total": 1,
                    "healthy": 1,
                    "unhealthy": 0,
                    "avg_response_time": 1.5,
                    "models": []
                }
            },
            "alerts": []
        }
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["overall_status"] == "healthy"
        assert data["total_models"] == 2
        assert data["healthy_models"] == 2
        assert data["unhealthy_models"] == 0
        assert len(data["models"]) == 1
        assert len(data["providers"]) == 1
        assert len(data["alerts"]) == 0
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_system_health_error(self, mock_get_checker):
        """测试获取系统健康状态失败"""
        # Mock健康检查器抛出异常
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.generate_health_report.side_effect = Exception("Health check failed")
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/")
        
        # 验证响应
        assert response.status_code == 500
        assert "健康检查失败" in response.json()["detail"]
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_models_health_success(self, mock_get_checker):
        """测试获取模型健康状态成功"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_status = ModelHealthStatus(
            provider="openai",
            model_name="gpt-4",
            model_type="llm",
            is_healthy=True
        )
        mock_status.response_time = 1.5
        mock_status.success_rate = 0.95
        mock_status.consecutive_failures = 0
        mock_status.total_checks = 20
        mock_status.last_check = datetime.now()
        
        mock_checker.model_status = {
            "openai:llm:gpt-4": mock_status
        }
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/models")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider"] == "openai"
        assert data[0]["model_name"] == "gpt-4"
        assert data[0]["model_type"] == "llm"
        assert data[0]["is_healthy"] is True
        assert data[0]["response_time"] == 1.5
        assert data[0]["success_rate"] == 0.95
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_models_health_with_filters(self, mock_get_checker):
        """测试使用过滤器获取模型健康状态"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        
        # 创建多个模型状态
        llm_status = ModelHealthStatus(
            provider="openai",
            model_name="gpt-4",
            model_type="llm",
            is_healthy=True
        )
        embedding_status = ModelHealthStatus(
            provider="openai",
            model_name="text-embedding-ada-002",
            model_type="embedding",
            is_healthy=False
        )
        
        mock_checker.model_status = {
            "openai:llm:gpt-4": llm_status,
            "openai:embedding:text-embedding-ada-002": embedding_status
        }
        mock_get_checker.return_value = mock_checker
        
        # 测试按提供商过滤
        response = client.get("/health/models?provider=openai")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # 测试按模型类型过滤
        response = client.get("/health/models?model_type=llm")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["model_type"] == "llm"
        
        # 测试只返回健康模型
        response = client.get("/health/models?healthy_only=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_healthy"] is True
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_model_health_success(self, mock_get_checker):
        """测试获取特定模型健康状态成功"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_status = ModelHealthStatus(
            provider="openai",
            model_name="gpt-4",
            model_type="llm",
            is_healthy=True
        )
        mock_status.response_time = 1.5
        mock_status.success_rate = 0.95
        mock_status.last_check = datetime.now()
        
        mock_checker.get_model_status.return_value = mock_status
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/models/openai/gpt-4/llm")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "openai"
        assert data["model_name"] == "gpt-4"
        assert data["model_type"] == "llm"
        assert data["is_healthy"] is True
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_model_health_not_found(self, mock_get_checker):
        """测试获取不存在的模型健康状态"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.get_model_status.return_value = None
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/models/nonexistent/model/llm")
        
        # 验证响应
        assert response.status_code == 404
        assert "模型未找到" in response.json()["detail"]
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_provider_health_success(self, mock_get_checker):
        """测试获取提供商健康状态成功"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_status = ModelHealthStatus(
            provider="openai",
            model_name="gpt-4",
            model_type="llm",
            is_healthy=True
        )
        
        mock_checker.get_provider_status.return_value = {
            "openai:llm:gpt-4": mock_status
        }
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/providers/openai")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["provider"] == "openai"
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_provider_health_not_found(self, mock_get_checker):
        """测试获取不存在的提供商健康状态"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.get_provider_status.return_value = {}
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/providers/nonexistent")
        
        # 验证响应
        assert response.status_code == 404
        assert "提供商未找到" in response.json()["detail"]
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_health_alerts_success(self, mock_get_checker):
        """测试获取健康告警成功"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.generate_health_report.return_value = {
            "alerts": [
                {
                    "level": "error",
                    "message": "模型不健康",
                    "details": "Connection failed"
                },
                {
                    "level": "warning",
                    "message": "成功率较低",
                    "details": "Success rate: 70%"
                }
            ]
        }
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/alerts")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["total_alerts"] == 2
        assert data["error_count"] == 1
        assert data["warning_count"] == 1
        assert len(data["alerts"]) == 2
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_trigger_health_check_success(self, mock_get_checker):
        """测试手动触发健康检查成功"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.generate_health_report.return_value = {
            "last_check": "2025-08-03T10:00:00",
            "overall_status": "healthy"
        }
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.post("/health/check")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert "健康检查已触发" in data["message"]
        assert data["status"] == "healthy"
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_health_status_healthy(self, mock_get_checker):
        """测试获取健康状态 - 健康"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.get_overall_health_status.return_value = HealthStatus.HEALTHY
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/status")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["code"] == 200
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_health_status_unhealthy(self, mock_get_checker):
        """测试获取健康状态 - 不健康"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.get_overall_health_status.return_value = HealthStatus.UNHEALTHY
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/status")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["code"] == 503
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_health_status_degraded(self, mock_get_checker):
        """测试获取健康状态 - 降级"""
        # Mock健康检查器
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.get_overall_health_status.return_value = HealthStatus.DEGRADED
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/status")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["code"] == 200
    
    @patch('rag_system.api.health_api.get_health_checker')
    def test_get_health_status_error(self, mock_get_checker):
        """测试获取健康状态异常"""
        # Mock健康检查器抛出异常
        mock_checker = Mock(spec=ModelHealthChecker)
        mock_checker.get_overall_health_status.side_effect = Exception("Check failed")
        mock_get_checker.return_value = mock_checker
        
        # 发送请求
        response = client.get("/health/status")
        
        # 验证响应
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert data["code"] == 500
        assert "Check failed" in data["error"]