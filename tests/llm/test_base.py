"""
测试LLM基础类
"""
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from rag_system.llm.base import BaseLLM, LLMConfig, LLMResponse


class MockLLM(BaseLLM):
    """用于测试的Mock LLM实现"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.test_response = "Test response"
        self.should_fail = False
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> LLMResponse:
        if self.should_fail:
            raise Exception("Mock generation failed")
        
        return LLMResponse(
            content=self.test_response,
            model=self.config.model,
            provider=self.config.provider,
            confidence=0.8
        )
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        if self.should_fail:
            raise Exception("Mock text generation failed")
        return self.test_response
    
    def generate_with_context(self, question: str, context: str, **kwargs) -> Dict[str, Any]:
        if self.should_fail:
            raise Exception("Mock context generation failed")
        
        return {
            'answer': f"Answer for: {question}",
            'model': self.config.model,
            'provider': self.config.provider,
            'confidence': 0.7
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            'provider': self.config.provider,
            'model': self.config.model,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature
        }
    
    def health_check(self) -> bool:
        return not self.should_fail


class TestLLMConfig:
    """测试LLM配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = LLMConfig(provider="test", model="test-model")
        
        assert config.provider == "test"
        assert config.model == "test-model"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.timeout == 60
        assert config.retry_attempts == 3
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="test-key",
            base_url="https://api.test.com",
            temperature=0.5,
            max_tokens=2000,
            timeout=30
        )
        
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == "test-key"
        assert config.base_url == "https://api.test.com"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000
        assert config.timeout == 30


class TestLLMResponse:
    """测试LLM响应类"""
    
    def test_basic_response(self):
        """测试基础响应"""
        response = LLMResponse(
            content="Test content",
            model="test-model",
            provider="test-provider"
        )
        
        assert response.content == "Test content"
        assert response.model == "test-model"
        assert response.provider == "test-provider"
        assert response.confidence == 0.0
        assert response.usage == {}
    
    def test_full_response(self):
        """测试完整响应"""
        usage = {"prompt_tokens": 10, "completion_tokens": 20}
        response = LLMResponse(
            content="Full test content",
            usage=usage,
            model="gpt-4",
            finish_reason="stop",
            provider="openai",
            confidence=0.9
        )
        
        assert response.content == "Full test content"
        assert response.usage == usage
        assert response.model == "gpt-4"
        assert response.finish_reason == "stop"
        assert response.provider == "openai"
        assert response.confidence == 0.9


class TestBaseLLM:
    """测试LLM基础类"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return LLMConfig(provider="test", model="test-model")
    
    @pytest.fixture
    def mock_llm(self, config):
        """Mock LLM实例"""
        return MockLLM(config)
    
    def test_initialization(self, mock_llm, config):
        """测试初始化"""
        assert mock_llm.config == config
        assert mock_llm.logger is not None
        assert not mock_llm.is_initialized()
    
    @pytest.mark.asyncio
    async def test_initialize(self, mock_llm):
        """测试初始化方法"""
        await mock_llm.initialize()
        assert mock_llm.is_initialized()
    
    @pytest.mark.asyncio
    async def test_cleanup(self, mock_llm):
        """测试清理方法"""
        await mock_llm.initialize()
        assert mock_llm.is_initialized()
        
        await mock_llm.cleanup()
        assert not mock_llm.is_initialized()
    
    @pytest.mark.asyncio
    async def test_generate(self, mock_llm):
        """测试生成方法"""
        messages = [{"role": "user", "content": "Hello"}]
        response = await mock_llm.generate(messages)
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.provider == "test"
    
    @pytest.mark.asyncio
    async def test_generate_text(self, mock_llm):
        """测试文本生成方法"""
        result = await mock_llm.generate_text("Hello")
        assert result == "Test response"
    
    def test_generate_with_context(self, mock_llm):
        """测试上下文生成方法"""
        result = mock_llm.generate_with_context("What is AI?", "AI is artificial intelligence")
        
        assert isinstance(result, dict)
        assert "answer" in result
        assert "model" in result
        assert "provider" in result
        assert "confidence" in result
        assert result["answer"] == "Answer for: What is AI?"
    
    def test_get_model_info(self, mock_llm):
        """测试获取模型信息"""
        info = mock_llm.get_model_info()
        
        assert isinstance(info, dict)
        assert info["provider"] == "test"
        assert info["model"] == "test-model"
        assert "max_tokens" in info
        assert "temperature" in info
    
    def test_health_check(self, mock_llm):
        """测试健康检查"""
        assert mock_llm.health_check() is True
        
        mock_llm.should_fail = True
        assert mock_llm.health_check() is False
    
    def test_estimate_confidence(self, mock_llm):
        """测试置信度估算"""
        # 短回答
        confidence = mock_llm._estimate_confidence("Hi", "context")
        assert confidence == 0.1
        
        # 不知道类回答
        confidence = mock_llm._estimate_confidence("我不知道", "context")
        assert confidence == 0.3
        
        # 长回答
        confidence = mock_llm._estimate_confidence("This is a very long answer with lots of details", "context")
        assert confidence == 0.7
        
        # 中等回答
        confidence = mock_llm._estimate_confidence("Medium answer", "context")
        assert confidence == 0.5
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_llm):
        """测试错误处理"""
        mock_llm.should_fail = True
        
        with pytest.raises(Exception, match="Mock generation failed"):
            await mock_llm.generate([{"role": "user", "content": "Hello"}])
        
        with pytest.raises(Exception, match="Mock text generation failed"):
            await mock_llm.generate_text("Hello")
        
        with pytest.raises(Exception, match="Mock context generation failed"):
            mock_llm.generate_with_context("Question", "Context")