"""
测试模型健康检查器
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

from rag_system.utils.health_checker import (
    ModelHealthChecker, ModelHealthStatus, ModelHealthCheckConfig
)
from rag_system.models.health import HealthStatus
from rag_system.llm.base import LLMConfig
from rag_system.embeddings.base import EmbeddingConfig


class TestModelHealthStatus:
    """测试模型健康状态"""
    
    def test_initial_status(self):
        """测试初始状态"""
        status = ModelHealthStatus(
            provider="openai",
            model_name="gpt-4",
            model_type="llm",
            is_healthy=False
        )
        
        assert status.provider == "openai"
        assert status.model_name == "gpt-4"
        assert status.model_type == "llm"
        assert not status.is_healthy
        assert status.consecutive_failures == 0
        assert status.total_checks == 0
        assert status.success_rate == 0.0
    
    def test_update_success(self):
        """测试更新成功状态"""
        status = ModelHealthStatus(
            provider="openai",
            model_name="gpt-4",
            model_type="llm",
            is_healthy=False
        )
        
        status.update_success(1.5)
        
        assert status.is_healthy
        assert status.response_time == 1.5
        assert status.error_message is None
        assert status.consecutive_failures == 0
        assert status.total_checks == 1
        assert status.success_rate == 1.0
        assert status.last_check is not None
    
    def test_update_failure(self):
        """测试更新失败状态"""
        status = ModelHealthStatus(
            provider="openai",
            model_name="gpt-4",
            model_type="llm",
            is_healthy=True
        )
        
        status.update_failure("Connection failed")
        
        assert not status.is_healthy
        assert status.response_time is None
        assert status.error_message == "Connection failed"
        assert status.consecutive_failures == 1
        assert status.total_checks == 1
        assert status.success_rate == 0.0
        assert status.last_check is not None
    
    def test_success_rate_calculation(self):
        """测试成功率计算"""
        status = ModelHealthStatus(
            provider="openai",
            model_name="gpt-4",
            model_type="llm",
            is_healthy=False
        )
        
        # 3次成功，2次失败
        status.update_success(1.0)
        status.update_success(1.1)
        status.update_success(0.9)
        status.update_failure("Error 1")
        status.update_failure("Error 2")
        
        assert status.total_checks == 5
        assert status.success_rate == 0.6  # 3/5
        assert status.consecutive_failures == 2


class TestModelHealthCheckConfig:
    """测试模型健康检查配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ModelHealthCheckConfig()
        
        assert config.check_interval == 300
        assert config.timeout == 30
        assert config.max_consecutive_failures == 3
        assert config.test_prompt == "Hello, this is a health check test."
        assert config.test_text == "This is a test document for embedding health check."
        assert config.enable_startup_check is True
        assert config.enable_periodic_check is True
        assert config.failure_threshold == 0.8
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = ModelHealthCheckConfig(
            check_interval=600,
            timeout=60,
            max_consecutive_failures=5,
            test_prompt="Custom test prompt",
            enable_startup_check=False
        )
        
        assert config.check_interval == 600
        assert config.timeout == 60
        assert config.max_consecutive_failures == 5
        assert config.test_prompt == "Custom test prompt"
        assert config.enable_startup_check is False


class TestModelHealthChecker:
    """测试模型健康检查器"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.config = ModelHealthCheckConfig(
            check_interval=10,
            timeout=5,
            enable_periodic_check=False  # 测试时禁用定期检查
        )
        self.checker = ModelHealthChecker(self.config)
    
    def test_get_model_key(self):
        """测试模型键生成"""
        key = self.checker._get_model_key("openai", "gpt-4", "llm")
        assert key == "openai:llm:gpt-4"
    
    @pytest.mark.asyncio
    async def test_check_llm_health_success(self):
        """测试LLM健康检查成功"""
        llm_config = LLMConfig(
            provider="mock",
            model="test-model",
            api_key="test-key"
        )
        
        # Mock LLM实例
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Test response"
        
        with patch('rag_system.utils.health_checker.LLMFactory.create_llm', return_value=mock_llm):
            status = await self.checker.check_llm_health(llm_config)
        
        assert status.is_healthy
        assert status.provider == "mock"
        assert status.model_name == "test-model"
        assert status.model_type == "llm"
        assert status.response_time is not None
        assert status.error_message is None
        assert status.consecutive_failures == 0
        assert status.total_checks == 1
        assert status.success_rate == 1.0
    
    @pytest.mark.asyncio
    async def test_check_llm_health_failure(self):
        """测试LLM健康检查失败"""
        llm_config = LLMConfig(
            provider="mock",
            model="test-model",
            api_key="test-key"
        )
        
        # Mock LLM实例抛出异常
        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = Exception("Connection failed")
        
        with patch('rag_system.utils.health_checker.LLMFactory.create_llm', return_value=mock_llm):
            status = await self.checker.check_llm_health(llm_config)
        
        assert not status.is_healthy
        assert status.provider == "mock"
        assert status.model_name == "test-model"
        assert status.model_type == "llm"
        assert status.response_time is None
        assert "Connection failed" in status.error_message
        assert status.consecutive_failures == 1
        assert status.total_checks == 1
        assert status.success_rate == 0.0
    
    @pytest.mark.asyncio
    async def test_check_llm_health_empty_response(self):
        """测试LLM返回空响应"""
        llm_config = LLMConfig(
            provider="mock",
            model="test-model",
            api_key="test-key"
        )
        
        # Mock LLM返回空响应
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = ""
        
        with patch('rag_system.utils.health_checker.LLMFactory.create_llm', return_value=mock_llm):
            status = await self.checker.check_llm_health(llm_config)
        
        assert not status.is_healthy
        assert "LLM返回空响应" in status.error_message
    
    @pytest.mark.asyncio
    async def test_check_embedding_health_success(self):
        """测试嵌入模型健康检查成功"""
        embedding_config = EmbeddingConfig(
            provider="mock",
            model="test-embedding",
            api_key="test-key"
        )
        
        # Mock嵌入模型实例
        mock_embedding = AsyncMock()
        mock_embedding.embed_text.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        with patch('rag_system.utils.health_checker.EmbeddingFactory.create_embedding', return_value=mock_embedding):
            status = await self.checker.check_embedding_health(embedding_config)
        
        assert status.is_healthy
        assert status.provider == "mock"
        assert status.model_name == "test-embedding"
        assert status.model_type == "embedding"
        assert status.response_time is not None
        assert status.error_message is None
    
    @pytest.mark.asyncio
    async def test_check_embedding_health_failure(self):
        """测试嵌入模型健康检查失败"""
        embedding_config = EmbeddingConfig(
            provider="mock",
            model="test-embedding",
            api_key="test-key"
        )
        
        # Mock嵌入模型抛出异常
        mock_embedding = AsyncMock()
        mock_embedding.embed_text.side_effect = Exception("API error")
        
        with patch('rag_system.utils.health_checker.EmbeddingFactory.create_embedding', return_value=mock_embedding):
            status = await self.checker.check_embedding_health(embedding_config)
        
        assert not status.is_healthy
        assert "API error" in status.error_message
    
    @pytest.mark.asyncio
    async def test_check_embedding_health_invalid_response(self):
        """测试嵌入模型返回无效响应"""
        embedding_config = EmbeddingConfig(
            provider="mock",
            model="test-embedding",
            api_key="test-key"
        )
        
        # Mock嵌入模型返回无效响应
        mock_embedding = AsyncMock()
        mock_embedding.embed_text.return_value = []
        
        with patch('rag_system.utils.health_checker.EmbeddingFactory.create_embedding', return_value=mock_embedding):
            status = await self.checker.check_embedding_health(embedding_config)
        
        assert not status.is_healthy
        assert "嵌入模型返回空向量" in status.error_message
    
    @pytest.mark.asyncio
    async def test_check_all_models(self):
        """测试检查所有模型"""
        llm_configs = [
            LLMConfig(provider="mock", model="llm1", api_key="key1"),
            LLMConfig(provider="mock", model="llm2", api_key="key2")
        ]
        
        embedding_configs = [
            EmbeddingConfig(provider="mock", model="emb1", api_key="key1")
        ]
        
        # Mock成功的LLM和嵌入模型
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Test response"
        
        mock_embedding = AsyncMock()
        mock_embedding.embed_text.return_value = [0.1, 0.2, 0.3]
        
        with patch('rag_system.utils.health_checker.LLMFactory.create_llm', return_value=mock_llm), \
             patch('rag_system.utils.health_checker.EmbeddingFactory.create_embedding', return_value=mock_embedding):
            
            results = await self.checker.check_all_models(llm_configs, embedding_configs)
        
        assert len(results) == 3  # 2个LLM + 1个嵌入模型
        assert all(status.is_healthy for status in results.values())
        
        # 验证模型状态已保存
        assert len(self.checker.model_status) == 3
    
    def test_get_model_status(self):
        """测试获取特定模型状态"""
        # 添加一个模型状态
        status = ModelHealthStatus(
            provider="openai",
            model_name="gpt-4",
            model_type="llm",
            is_healthy=True
        )
        self.checker.model_status["openai:llm:gpt-4"] = status
        
        # 测试获取存在的模型
        result = self.checker.get_model_status("openai", "gpt-4", "llm")
        assert result is not None
        assert result.provider == "openai"
        assert result.model_name == "gpt-4"
        
        # 测试获取不存在的模型
        result = self.checker.get_model_status("openai", "gpt-3", "llm")
        assert result is None
    
    def test_get_overall_health_status(self):
        """测试获取整体健康状态"""
        # 测试空状态
        assert self.checker.get_overall_health_status() == HealthStatus.UNKNOWN
        
        # 测试全部健康
        self.checker.model_status["model1"] = ModelHealthStatus(
            provider="p1", model_name="m1", model_type="llm", is_healthy=True
        )
        self.checker.model_status["model2"] = ModelHealthStatus(
            provider="p1", model_name="m2", model_type="llm", is_healthy=True
        )
        assert self.checker.get_overall_health_status() == HealthStatus.HEALTHY
        
        # 测试部分健康
        self.checker.model_status["model3"] = ModelHealthStatus(
            provider="p1", model_name="m3", model_type="llm", is_healthy=False
        )
        assert self.checker.get_overall_health_status() == HealthStatus.DEGRADED
        
        # 测试全部不健康
        self.checker.model_status["model1"].is_healthy = False
        self.checker.model_status["model2"].is_healthy = False
        assert self.checker.get_overall_health_status() == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_startup_health_check_success(self):
        """测试启动时健康检查成功"""
        llm_configs = [LLMConfig(provider="mock", model="test", api_key="key")]
        embedding_configs = []
        
        # Mock成功的LLM
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Test response"
        
        with patch('rag_system.utils.health_checker.LLMFactory.create_llm', return_value=mock_llm):
            result = await self.checker.startup_health_check(llm_configs, embedding_configs)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_startup_health_check_disabled(self):
        """测试禁用启动时健康检查"""
        config = ModelHealthCheckConfig(enable_startup_check=False)
        checker = ModelHealthChecker(config)
        
        result = await checker.startup_health_check([], [])
        assert result is True  # 禁用时应该返回True


class TestBackwardCompatibility:
    """测试向后兼容性"""
    
    def test_original_health_checker_still_works(self):
        """测试原始健康检查器仍然可用"""
        from rag_system.utils.health_checker import HealthChecker
        
        checker = HealthChecker()
        
        def dummy_check():
            return {"status": "ok"}
        
        checker.register_component("test", dummy_check)
        assert "test" in checker.components