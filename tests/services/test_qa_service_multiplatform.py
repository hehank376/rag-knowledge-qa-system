"""
多平台QA服务集成测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from rag_system.services.qa_service import QAService
from rag_system.llm.base import LLMConfig, LLMResponse
from rag_system.llm.factory import LLMFactory
from rag_system.models.vector import SearchResult
from rag_system.utils.exceptions import QAError
from rag_system.utils.model_exceptions import ModelConnectionError, ModelResponseError


class TestQAServiceMultiPlatform:
    """多平台QA服务测试"""
    
    @pytest.fixture
    def mock_retrieval_service(self):
        """模拟检索服务"""
        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.cleanup = AsyncMock()
        mock_service.search_similar_documents = AsyncMock()
        mock_service.get_service_stats = AsyncMock(return_value={
            "vector_count": 100,
            "document_count": 10
        })
        mock_service.similarity_threshold = 0.7
        mock_service.default_top_k = 5
        return mock_service
    
    @pytest.fixture
    def sample_search_results(self):
        """示例搜索结果"""
        return [
            SearchResult(
                document_id="12345678-1234-5678-9abc-123456789abc",
                chunk_id="87654321-4321-8765-cba9-987654321cba",
                content="这是一个关于人工智能的文档片段。",
                similarity_score=0.9,
                metadata={"document_name": "AI文档", "chunk_index": 0}
            ),
            SearchResult(
                document_id="11111111-2222-3333-4444-555555555555", 
                chunk_id="66666666-7777-8888-9999-aaaaaaaaaaaa",
                content="机器学习是人工智能的一个重要分支。",
                similarity_score=0.8,
                metadata={"document_name": "ML文档", "chunk_index": 1}
            )
        ]
    
    @pytest.fixture
    def qa_config(self):
        """QA服务配置"""
        return {
            'llm_provider': 'siliconflow',
            'llm_model': 'Qwen/Qwen2-7B-Instruct',
            'llm_api_key': 'test-key',
            'llm_base_url': 'https://api.siliconflow.cn/v1',
            'llm_temperature': 0.7,
            'llm_max_tokens': 1000,
            'llm_timeout': 30,
            'llm_retry_attempts': 3,
            'enable_llm_fallback': True,
            'max_context_length': 4000,
            'include_sources': True,
            'no_answer_threshold': 0.5,
            'debug': True
        }
    
    @pytest.mark.asyncio
    async def test_qa_service_initialization_with_multiplatform(self, qa_config, mock_retrieval_service):
        """测试多平台QA服务初始化"""
        with patch('rag_system.services.qa_service.RetrievalService', return_value=mock_retrieval_service):
            with patch.object(LLMFactory, 'create_llm') as mock_create_llm:
                # 模拟主要LLM
                mock_main_llm = AsyncMock()
                mock_main_llm.initialize = AsyncMock()
                mock_main_llm.cleanup = AsyncMock()
                
                # 模拟备用LLM
                mock_fallback_llm = AsyncMock()
                mock_fallback_llm.initialize = AsyncMock()
                mock_fallback_llm.cleanup = AsyncMock()
                
                # 根据配置返回不同的LLM实例
                def create_llm_side_effect(config):
                    if config.provider == 'siliconflow':
                        return mock_main_llm
                    elif config.provider == 'mock':
                        return mock_fallback_llm
                    return mock_main_llm
                
                mock_create_llm.side_effect = create_llm_side_effect
                
                qa_service = QAService(qa_config)
                await qa_service.initialize()
                
                # 验证初始化
                assert qa_service.llm is not None
                assert qa_service.fallback_llm is not None
                assert qa_service.llm_config.provider == 'siliconflow'
                assert qa_service.fallback_config.provider == 'mock'
                
                # 验证LLM初始化被调用
                mock_main_llm.initialize.assert_called_once()
                mock_fallback_llm.initialize.assert_called_once()
                
                await qa_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_answer_question_with_main_llm(self, qa_config, mock_retrieval_service, sample_search_results):
        """测试使用主要LLM回答问题"""
        with patch('rag_system.services.qa_service.RetrievalService', return_value=mock_retrieval_service):
            with patch.object(LLMFactory, 'create_llm') as mock_create_llm:
                # 模拟主要LLM
                mock_main_llm = AsyncMock()
                mock_main_llm.initialize = AsyncMock()
                mock_main_llm.cleanup = AsyncMock()
                mock_main_llm.generate_text = AsyncMock(return_value="这是一个关于人工智能的详细回答。")
                
                mock_create_llm.return_value = mock_main_llm
                mock_retrieval_service.search_similar_documents.return_value = sample_search_results
                
                qa_service = QAService(qa_config)
                await qa_service.initialize()
                
                # 测试问答
                response = await qa_service.answer_question("什么是人工智能？")
                
                # 验证响应
                assert response.question == "什么是人工智能？"
                assert "人工智能" in response.answer
                assert len(response.sources) == 2
                assert response.confidence_score > 0
                
                # 验证LLM被调用
                mock_main_llm.generate_text.assert_called_once()
                
                await qa_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_fallback_to_backup_llm_on_error(self, qa_config, mock_retrieval_service, sample_search_results):
        """测试主要LLM失败时切换到备用LLM"""
        with patch('rag_system.services.qa_service.RetrievalService', return_value=mock_retrieval_service):
            with patch.object(LLMFactory, 'create_llm') as mock_create_llm:
                # 模拟主要LLM（会失败）
                mock_main_llm = AsyncMock()
                mock_main_llm.initialize = AsyncMock()
                mock_main_llm.cleanup = AsyncMock()
                mock_main_llm.generate_text = AsyncMock(
                    side_effect=ModelConnectionError("连接失败", "siliconflow", "Qwen/Qwen2-7B-Instruct")
                )
                
                # 模拟备用LLM（成功）
                mock_fallback_llm = AsyncMock()
                mock_fallback_llm.initialize = AsyncMock()
                mock_fallback_llm.cleanup = AsyncMock()
                mock_fallback_llm.generate_text = AsyncMock(return_value="这是备用LLM的回答。")
                
                def create_llm_side_effect(config):
                    if config.provider == 'siliconflow':
                        return mock_main_llm
                    elif config.provider == 'mock':
                        return mock_fallback_llm
                    return mock_main_llm
                
                mock_create_llm.side_effect = create_llm_side_effect
                mock_retrieval_service.search_similar_documents.return_value = sample_search_results
                
                qa_service = QAService(qa_config)
                await qa_service.initialize()
                
                # 测试问答（应该切换到备用LLM）
                response = await qa_service.answer_question("什么是人工智能？")
                
                # 验证响应
                assert response.question == "什么是人工智能？"
                assert "备用LLM" in response.answer
                
                # 验证主要LLM被调用但失败
                mock_main_llm.generate_text.assert_called_once()
                # 验证备用LLM被调用
                mock_fallback_llm.generate_text.assert_called_once()
                
                await qa_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_fallback_answer_when_all_llms_fail(self, qa_config, mock_retrieval_service, sample_search_results):
        """测试所有LLM都失败时的降级回答"""
        with patch('rag_system.services.qa_service.RetrievalService', return_value=mock_retrieval_service):
            with patch.object(LLMFactory, 'create_llm') as mock_create_llm:
                # 模拟所有LLM都失败
                mock_llm = AsyncMock()
                mock_llm.initialize = AsyncMock()
                mock_llm.cleanup = AsyncMock()
                mock_llm.generate_text = AsyncMock(
                    side_effect=ModelConnectionError("连接失败", "test", "test-model")
                )
                
                mock_create_llm.return_value = mock_llm
                mock_retrieval_service.search_similar_documents.return_value = sample_search_results
                
                qa_service = QAService(qa_config)
                await qa_service.initialize()
                
                # 测试问答（应该返回降级回答）
                response = await qa_service.answer_question("什么是人工智能？")
                
                # 验证响应
                assert response.question == "什么是人工智能？"
                assert "根据文档内容" in response.answer
                assert "LLM服务不可用" in response.answer
                assert len(response.sources) == 2
                
                await qa_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_dynamic_llm_switching(self, qa_config, mock_retrieval_service):
        """测试动态LLM切换"""
        with patch('rag_system.services.qa_service.RetrievalService', return_value=mock_retrieval_service):
            with patch.object(LLMFactory, 'create_llm') as mock_create_llm:
                # 模拟不同的LLM实例
                mock_siliconflow_llm = AsyncMock()
                mock_siliconflow_llm.initialize = AsyncMock()
                mock_siliconflow_llm.cleanup = AsyncMock()
                
                mock_openai_llm = AsyncMock()
                mock_openai_llm.initialize = AsyncMock()
                mock_openai_llm.cleanup = AsyncMock()
                
                def create_llm_side_effect(config):
                    if config.provider == 'siliconflow':
                        return mock_siliconflow_llm
                    elif config.provider == 'openai':
                        return mock_openai_llm
                    return mock_siliconflow_llm
                
                mock_create_llm.side_effect = create_llm_side_effect
                
                qa_service = QAService(qa_config)
                await qa_service.initialize()
                
                # 验证初始配置
                assert qa_service.llm_config.provider == 'siliconflow'
                
                # 切换到OpenAI
                new_config = LLMConfig(
                    provider='openai',
                    model='gpt-4',
                    api_key='test-openai-key',
                    temperature=0.5,
                    max_tokens=2000
                )
                
                success = await qa_service.switch_llm_provider(new_config)
                
                # 验证切换成功
                assert success is True
                assert qa_service.llm_config.provider == 'openai'
                assert qa_service.llm_config.model == 'gpt-4'
                
                # 验证旧LLM被清理，新LLM被初始化
                mock_siliconflow_llm.cleanup.assert_called_once()
                mock_openai_llm.initialize.assert_called_once()
                
                await qa_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_llm_connection_testing(self, qa_config, mock_retrieval_service):
        """测试LLM连接测试功能"""
        with patch('rag_system.services.qa_service.RetrievalService', return_value=mock_retrieval_service):
            with patch.object(LLMFactory, 'create_llm') as mock_create_llm:
                # 模拟健康的LLM
                mock_healthy_llm = AsyncMock()
                mock_healthy_llm.initialize = AsyncMock()
                mock_healthy_llm.cleanup = AsyncMock()
                mock_healthy_llm.health_check = Mock(return_value=True)
                
                mock_create_llm.return_value = mock_healthy_llm
                
                qa_service = QAService(qa_config)
                await qa_service.initialize()
                
                # 测试当前LLM连接
                result = await qa_service.test_llm_connection()
                
                # 验证测试结果
                assert result['success'] is True
                assert result['provider'] == 'siliconflow'
                assert result['status'] == 'healthy'
                
                # 测试其他配置
                test_config = LLMConfig(
                    provider='openai',
                    model='gpt-3.5-turbo',
                    api_key='test-key'
                )
                
                result = await qa_service.test_llm_connection(test_config)
                assert result['provider'] == 'openai'
                
                await qa_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_service_stats_with_multiplatform_info(self, qa_config, mock_retrieval_service):
        """测试多平台服务统计信息"""
        with patch('rag_system.services.qa_service.RetrievalService', return_value=mock_retrieval_service):
            with patch.object(LLMFactory, 'create_llm') as mock_create_llm:
                with patch.object(LLMFactory, 'get_available_providers', return_value=['openai', 'siliconflow', 'mock']):
                    mock_llm = AsyncMock()
                    mock_llm.initialize = AsyncMock()
                    mock_llm.cleanup = AsyncMock()
                    
                    mock_create_llm.return_value = mock_llm
                    
                    qa_service = QAService(qa_config)
                    await qa_service.initialize()
                    
                    # 获取服务统计
                    stats = await qa_service.get_service_stats()
                    
                    # 验证统计信息
                    assert stats['service_name'] == 'QAService'
                    assert 'main_llm' in stats
                    assert stats['main_llm']['provider'] == 'siliconflow'
                    assert stats['main_llm']['model'] == 'Qwen/Qwen2-7B-Instruct'
                    assert stats['main_llm']['status'] == 'available'
                    
                    assert 'fallback_llm' in stats
                    assert stats['fallback_llm']['provider'] == 'mock'
                    assert stats['fallback_llm']['enabled'] is True
                    
                    assert 'available_llm_providers' in stats
                    assert 'openai' in stats['available_llm_providers']
                    assert 'siliconflow' in stats['available_llm_providers']
                    
                    assert stats['fallback_enabled'] is True
                    
                    await qa_service.cleanup()
    
    @pytest.mark.asyncio
    async def test_response_formatting(self, qa_config, mock_retrieval_service, sample_search_results):
        """测试响应格式化"""
        with patch('rag_system.services.qa_service.RetrievalService', return_value=mock_retrieval_service):
            with patch.object(LLMFactory, 'create_llm') as mock_create_llm:
                # 模拟返回LLMResponse对象的LLM
                mock_llm = AsyncMock()
                mock_llm.initialize = AsyncMock()
                mock_llm.cleanup = AsyncMock()
                
                # 模拟LLMResponse对象
                mock_response = LLMResponse(
                    content="这是一个格式化的回答。",
                    usage={"prompt_tokens": 50, "completion_tokens": 30},
                    model="Qwen/Qwen2-7B-Instruct",
                    provider="siliconflow"
                )
                mock_llm.generate_text = AsyncMock(return_value=mock_response)
                
                mock_create_llm.return_value = mock_llm
                mock_retrieval_service.search_similar_documents.return_value = sample_search_results
                
                qa_service = QAService(qa_config)
                await qa_service.initialize()
                
                # 测试问答
                response = await qa_service.answer_question("测试问题")
                
                # 验证响应格式化
                assert "格式化的回答" in response.answer
                # 在调试模式下应该包含提供商信息
                assert "[Generated by: siliconflow]" in response.answer
                
                await qa_service.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])