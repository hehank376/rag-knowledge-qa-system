"""
测试SiliconFlow LLM实现
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import httpx

from rag_system.llm.siliconflow_llm import SiliconFlowLLM
from rag_system.llm.base import LLMConfig, LLMResponse
from rag_system.utils.exceptions import ProcessingError
from rag_system.utils.model_exceptions import (
    ModelConnectionError, ModelResponseError, ModelAuthenticationError,
    ModelRateLimitError, ModelTimeoutError
)


class TestSiliconFlowLLM:
    """测试SiliconFlow LLM"""
    
    @pytest.fixture
    def config(self):
        """测试配置"""
        return LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-api-key",
            base_url="https://api.siliconflow.cn/v1",
            max_tokens=1000,
            temperature=0.7,
            timeout=60
        )
    
    @pytest.fixture
    def llm(self, config):
        """SiliconFlow LLM实例"""
        return SiliconFlowLLM(config)
    
    def test_initialization(self, config):
        """测试初始化"""
        llm = SiliconFlowLLM(config)
        
        assert llm.api_key == "test-api-key"
        assert llm.base_url == "https://api.siliconflow.cn/v1"
        assert llm.model == "Qwen/Qwen2-7B-Instruct"
        assert llm.max_tokens == 1000
        assert llm.temperature == 0.7
        assert llm.timeout == 60
    
    def test_initialization_without_api_key(self):
        """测试没有API密钥的初始化"""
        config = LLMConfig(provider="siliconflow", model="test-model")
        
        with pytest.raises(ValueError, match="SiliconFlow API key is required"):
            SiliconFlowLLM(config)
    
    def test_default_values(self):
        """测试默认值"""
        config = LLMConfig(
            provider="siliconflow",
            model="test-model",
            api_key="test-key"
        )
        llm = SiliconFlowLLM(config)
        
        assert llm.base_url == "https://api.siliconflow.cn/v1"
        assert llm.model == "test-model"
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, llm):
        """测试成功初始化"""
        with patch.object(llm, '_test_connection', new_callable=AsyncMock):
            await llm.initialize()
            
            assert llm.is_initialized()
            assert llm._client is not None
    
    @pytest.mark.asyncio
    async def test_initialize_with_test_key(self, config):
        """测试使用测试密钥初始化（跳过连接测试）"""
        config.api_key = "test-skip-connection"
        llm = SiliconFlowLLM(config)
        
        await llm.initialize()
        assert llm.is_initialized()
    
    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self):
        """测试初始化时连接失败"""
        config = LLMConfig(
            provider="siliconflow",
            model="test-model",
            api_key="real-api-key",  # 不以test-开头，会触发连接测试
            base_url="https://api.siliconflow.cn/v1"
        )
        llm = SiliconFlowLLM(config)
        
        with patch.object(llm, '_test_connection', side_effect=ModelConnectionError("Connection failed", "siliconflow", "test")):
            with pytest.raises(ProcessingError, match="SiliconFlow LLM初始化失败"):
                await llm.initialize()
    
    @pytest.mark.asyncio
    async def test_generate_success(self, llm):
        """测试成功生成"""
        # Mock响应数据
        mock_response = {
            'choices': [{
                'message': {'content': 'Test response'},
                'finish_reason': 'stop'
            }],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 20},
            'model': 'Qwen/Qwen2-7B-Instruct'
        }
        
        with patch.object(llm, '_create_completion', return_value=mock_response):
            llm._initialized = True
            
            messages = [{"role": "user", "content": "Hello"}]
            response = await llm.generate(messages)
            
            assert isinstance(response, LLMResponse)
            assert response.content == "Test response"
            assert response.model == "Qwen/Qwen2-7B-Instruct"
            assert response.provider == "siliconflow"
            assert response.finish_reason == "stop"
            assert response.usage == {'prompt_tokens': 10, 'completion_tokens': 20}
    
    @pytest.mark.asyncio
    async def test_generate_not_initialized(self, llm):
        """测试未初始化时生成"""
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ProcessingError, match="SiliconFlow LLM未初始化"):
            await llm.generate(messages)
    
    @pytest.mark.asyncio
    async def test_generate_text(self, llm):
        """测试文本生成"""
        mock_response = LLMResponse(
            content="Generated text",
            model="test-model",
            provider="siliconflow"
        )
        
        with patch.object(llm, 'generate', return_value=mock_response):
            result = await llm.generate_text("Test prompt")
            assert result == "Generated text"
    
    @pytest.mark.asyncio
    async def test_create_completion_success(self, llm):
        """测试成功创建完成"""
        mock_response_data = {
            'choices': [{'message': {'content': 'Response'}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 5, 'completion_tokens': 10}
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        llm._client = mock_client
        
        messages = [{"role": "user", "content": "Hello"}]
        result = await llm._create_completion(messages)
        
        assert result == mock_response_data
        mock_client.post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_completion_auth_error(self, llm):
        """测试认证错误"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        llm._client = mock_client
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ModelAuthenticationError):
            await llm._create_completion(messages)
    
    @pytest.mark.asyncio
    async def test_create_completion_rate_limit(self, llm):
        """测试限流错误"""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        llm._client = mock_client
        llm.retry_attempts = 1  # 减少重试次数以加快测试
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ModelRateLimitError):
            await llm._create_completion(messages)
    
    @pytest.mark.asyncio
    async def test_create_completion_timeout(self, llm):
        """测试超时错误"""
        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("Timeout")
        llm._client = mock_client
        llm.retry_attempts = 1  # 减少重试次数
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ModelTimeoutError):
            await llm._create_completion(messages)
    
    @pytest.mark.asyncio
    async def test_create_completion_retry_success(self, llm):
        """测试重试成功"""
        mock_response_data = {
            'choices': [{'message': {'content': 'Response'}, 'finish_reason': 'stop'}]
        }
        
        # 第一次失败，第二次成功
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Server error"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = mock_response_data
        
        mock_client = AsyncMock()
        mock_client.post.side_effect = [mock_response_fail, mock_response_success]
        llm._client = mock_client
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('asyncio.sleep'):  # 跳过等待时间
            result = await llm._create_completion(messages)
            assert result == mock_response_data
    
    def test_generate_with_context(self, llm):
        """测试基于上下文生成"""
        with patch('asyncio.run', return_value="Context-based answer"):
            result = llm.generate_with_context("What is AI?", "AI is artificial intelligence")
            
            assert isinstance(result, dict)
            assert result['answer'] == "Context-based answer"
            assert result['model'] == "Qwen/Qwen2-7B-Instruct"
            assert result['provider'] == "siliconflow"
            assert 'confidence' in result
    
    def test_generate_with_context_error(self, llm):
        """测试上下文生成错误"""
        with patch('asyncio.run', side_effect=Exception("Generation failed")):
            result = llm.generate_with_context("Question", "Context")
            
            assert "抱歉，生成回答时出现错误" in result['answer']
            assert result['confidence'] == 0.0
    
    def test_estimate_confidence(self, llm):
        """测试置信度估算"""
        # 无法回答
        confidence = llm._estimate_confidence("无法回答这个问题", "context")
        assert confidence == 0.3
        
        # 基于上下文
        confidence = llm._estimate_confidence("根据上下文，答案是...", "context")
        assert confidence == 0.9
        
        # 长回答且与上下文相关（使用英文测试词汇匹配）
        confidence = llm._estimate_confidence("This is a detailed answer with information and content", "information content detailed")
        assert confidence == 0.8
        
        # 长回答但无上下文匹配（长度不够50，所以是0.6）
        confidence = llm._estimate_confidence("这是一个很长的回答，但是与上下文缺乏关联的内容", "完全不同的上下文")
        assert confidence == 0.6
        
        # 中等长度回答（长度不够30，所以是0.6）
        confidence = llm._estimate_confidence("这是一个中等长度的回答", "context")
        assert confidence == 0.6
        
        # 短回答
        confidence = llm._estimate_confidence("短回答", "context")
        assert confidence == 0.6
    
    def test_get_model_info(self, llm):
        """测试获取模型信息"""
        info = llm.get_model_info()
        
        assert info['provider'] == 'siliconflow'
        assert info['model'] == 'Qwen/Qwen2-7B-Instruct'
        assert info['base_url'] == 'https://api.siliconflow.cn/v1'
        assert info['max_tokens'] == 1000
        assert info['temperature'] == 0.7
        assert info['timeout'] == 60
    
    def test_health_check_success(self, llm):
        """测试健康检查成功"""
        with patch('asyncio.run', return_value="Health check response"):
            assert llm.health_check() is True
    
    def test_health_check_failure(self, llm):
        """测试健康检查失败"""
        with patch('asyncio.run', side_effect=Exception("Health check failed")):
            assert llm.health_check() is False
    
    @pytest.mark.asyncio
    async def test_cleanup(self, llm):
        """测试资源清理"""
        mock_client = AsyncMock()
        llm._client = mock_client
        llm._initialized = True
        
        await llm.cleanup()
        
        mock_client.aclose.assert_called_once()
        assert llm._client is None
        assert not llm.is_initialized()
    
    def test_get_available_models(self, llm):
        """测试获取可用模型列表"""
        models = llm.get_available_models()
        
        assert isinstance(models, list)
        assert len(models) > 0
        assert 'Qwen/Qwen2-7B-Instruct' in models
        assert 'deepseek-ai/DeepSeek-V3' in models
    
    @pytest.mark.asyncio
    async def test_payload_construction(self, llm):
        """测试请求载荷构造"""
        mock_response_data = {
            'choices': [{'message': {'content': 'Response'}, 'finish_reason': 'stop'}]
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        llm._client = mock_client
        
        messages = [{"role": "user", "content": "Hello"}]
        await llm._create_completion(
            messages, 
            max_tokens=500, 
            temperature=0.5,
            top_p=0.9,
            frequency_penalty=0.1
        )
        
        # 验证调用参数
        call_args = mock_client.post.call_args
        payload = call_args[1]['json']
        
        assert payload['model'] == 'Qwen/Qwen2-7B-Instruct'
        assert payload['messages'] == messages
        assert payload['max_tokens'] == 500
        assert payload['temperature'] == 0.5
        assert payload['top_p'] == 0.9
        assert payload['frequency_penalty'] == 0.1
        assert payload['stream'] is False