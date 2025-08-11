"""
多平台模型集成测试
"""
import pytest
import asyncio
import tempfile
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from rag_system.llm.factory import LLMFactory
from rag_system.llm.base import LLMConfig
from rag_system.embeddings.factory import EmbeddingFactory
from rag_system.embeddings.base import EmbeddingConfig
from rag_system.utils.model_exceptions import ModelConfigError, ModelConnectionError


class TestMultiPlatformIntegration:
    """多平台模型集成测试"""
    
    def setup_method(self):
        """设置测试环境"""
        pass
    
    def test_llm_factory_multiplatform_creation(self):
        """测试LLM工厂多平台模型创建"""
        factory = LLMFactory()
        
        # 测试SiliconFlow LLM创建
        siliconflow_config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key"
        )
        
        llm = factory.create_llm(siliconflow_config)
        assert llm is not None
        assert llm.config.provider == "siliconflow"
        assert llm.config.model == "Qwen/Qwen2-7B-Instruct"
        
        # 测试OpenAI LLM创建（向后兼容）
        openai_config = LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-key"
        )
        
        llm = factory.create_llm(openai_config)
        assert llm is not None
        assert llm.config.provider == "openai"
        assert llm.config.model == "gpt-3.5-turbo"
    
    def test_embedding_factory_multiplatform_creation(self):
        """测试嵌入模型工厂多平台创建"""
        factory = EmbeddingFactory()
        
        # 测试SiliconFlow嵌入模型创建
        siliconflow_config = EmbeddingConfig(
            provider="siliconflow",
            model="BAAI/bge-large-zh-v1.5",
            api_key="test-key",
            dimensions=1024
        )
        
        embedding = factory.create_embedding(siliconflow_config)
        assert embedding is not None
        assert embedding.config.provider == "siliconflow"
        assert embedding.config.model == "BAAI/bge-large-zh-v1.5"
        assert embedding.config.dimensions == 1024
        
        # 测试OpenAI嵌入模型创建（向后兼容）
        openai_config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="test-key",
            dimensions=1536
        )
        
        embedding = factory.create_embedding(openai_config)
        assert embedding is not None
        assert embedding.config.provider == "openai"
        assert embedding.config.model == "text-embedding-ada-002"
        assert embedding.config.dimensions == 1536
    
    def test_llm_config_validation(self):
        """测试LLM配置验证"""
        # 测试有效配置
        valid_config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key"
        )
        
        assert valid_config.provider == "siliconflow"
        assert valid_config.model == "Qwen/Qwen2-7B-Instruct"
        assert valid_config.api_key == "test-key"
        
        # 测试默认值
        assert valid_config.temperature == 0.7
        assert valid_config.max_tokens == 1000
        assert valid_config.timeout == 60
    
    def test_embedding_config_validation(self):
        """测试嵌入配置验证"""
        # 测试有效配置
        valid_config = EmbeddingConfig(
            provider="siliconflow",
            model="BAAI/bge-large-zh-v1.5",
            api_key="test-key",
            dimensions=1024
        )
        
        assert valid_config.provider == "siliconflow"
        assert valid_config.model == "BAAI/bge-large-zh-v1.5"
        assert valid_config.api_key == "test-key"
        assert valid_config.dimensions == 1024
        
        # 测试默认值
        assert valid_config.batch_size == 100
        assert valid_config.timeout == 60
    
    def test_model_switching_scenario(self):
        """测试模型切换场景"""
        factory = LLMFactory()
        
        # 初始配置：SiliconFlow
        config1 = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key1"
        )
        
        llm1 = factory.create_llm(config1)
        assert llm1.config.provider == "siliconflow"
        
        # 切换配置：OpenAI
        config2 = LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            api_key="test-key2"
        )
        
        llm2 = factory.create_llm(config2)
        assert llm2.config.provider == "openai"
        
        # 验证两个模型是不同的实例
        assert llm1 is not llm2
        assert llm1.config.provider != llm2.config.provider
    
    def test_error_recovery_scenario(self):
        """测试错误恢复场景"""
        factory = LLMFactory()
        
        # 测试不支持的提供商 - 使用pydantic验证错误
        with pytest.raises(Exception):  # pydantic会抛出ValidationError
            invalid_config = LLMConfig(
                provider="invalid_provider",
                model="test-model",
                api_key="test-key"
            )
        
        # 测试缺少必需参数 - 这里用pydantic验证错误
        with pytest.raises(Exception):  # pydantic会抛出ValidationError
            incomplete_config = LLMConfig(
                provider="siliconflow",
                model="Qwen/Qwen2-7B-Instruct"
                # 缺少api_key - pydantic会在创建时验证
            )
    
    def test_config_serialization(self):
        """测试配置序列化"""
        # 测试LLM配置序列化
        llm_config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key",
            temperature=0.8,
            max_tokens=2000
        )
        
        # 转换为字典
        config_dict = llm_config.to_dict()
        assert config_dict["provider"] == "siliconflow"
        assert config_dict["model"] == "Qwen/Qwen2-7B-Instruct"
        assert config_dict["temperature"] == 0.8
        
        # 从字典重建
        rebuilt_config = LLMConfig.from_dict(config_dict)
        assert rebuilt_config.provider == llm_config.provider
        assert rebuilt_config.model == llm_config.model
        assert rebuilt_config.temperature == llm_config.temperature
    
    def test_config_merging(self):
        """测试配置合并"""
        base_config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key",
            temperature=0.7
        )
        
        override_config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key",
            temperature=0.9,
            max_tokens=2000
        )
        
        merged_config = base_config.merge_with(override_config)
        
        assert merged_config.provider == "siliconflow"
        assert merged_config.temperature == 0.9  # 被覆盖
        assert merged_config.max_tokens == 2000  # 新增
    
    def test_concurrent_requests_handling(self):
        """测试并发请求处理"""
        factory = LLMFactory()
        
        # 创建多个LLM实例
        configs = [
            LLMConfig(
                provider="siliconflow",
                model="Qwen/Qwen2-7B-Instruct",
                api_key=f"test-key-{i}"
            )
            for i in range(5)
        ]
        
        llms = []
        for config in configs:
            llm = factory.create_llm(config)
            llms.append(llm)
        
        # 验证所有实例都创建成功
        assert len(llms) == 5
        for i, llm in enumerate(llms):
            assert llm.config.provider == "siliconflow"
            assert llm.config.api_key == f"test-key-{i}"
    
    def test_provider_support_validation(self):
        """测试提供商支持验证"""
        factory = LLMFactory()
        
        # 测试支持的提供商
        supported_providers = ["openai", "siliconflow", "mock"]
        
        for provider in supported_providers:
            config = LLMConfig(
                provider=provider,
                model="test-model",
                api_key="test-key"
            )
            
            # 应该能够创建实例（即使可能在运行时失败）
            llm = factory.create_llm(config)
            assert llm is not None
            assert llm.config.provider == provider


class TestMultiPlatformPerformance:
    """多平台模型性能测试"""
    
    def setup_method(self):
        """设置性能测试环境"""
        self.performance_data = []
    
    def test_factory_creation_performance(self):
        """测试工厂创建性能"""
        import time
        
        factory = LLMFactory()
        
        # 测试批量创建性能
        creation_times = []
        
        for i in range(10):
            config = LLMConfig(
                provider="siliconflow",
                model="Qwen/Qwen2-7B-Instruct",
                api_key=f"test-key-{i}"
            )
            
            start_time = time.time()
            llm = factory.create_llm(config)
            end_time = time.time()
            
            creation_times.append(end_time - start_time)
            assert llm is not None
        
        # 验证创建时间合理
        avg_creation_time = sum(creation_times) / len(creation_times)
        assert avg_creation_time < 1.0  # 平均创建时间不超过1秒
        
        # 验证创建时间相对稳定
        max_time = max(creation_times)
        min_time = min(creation_times)
        assert (max_time - min_time) < 0.5  # 时间差异不超过0.5秒
    
    def test_memory_usage_monitoring(self):
        """测试内存使用监控"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # 创建多个模型实例
        factory = LLMFactory()
        llms = []
        
        for i in range(10):
            config = LLMConfig(
                provider="siliconflow",
                model="Qwen/Qwen2-7B-Instruct",
                api_key=f"test-key-{i}"
            )
            llm = factory.create_llm(config)
            llms.append(llm)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # 验证内存增长在合理范围内（每个实例不超过1MB）
        assert memory_increase < 10 * 1024 * 1024  # 10MB总增长
        
        # 清理引用
        del llms
    
    def test_concurrent_performance(self):
        """测试并发性能"""
        import threading
        import time
        
        factory = LLMFactory()
        results = []
        errors = []
        
        def create_llm_worker(worker_id):
            try:
                config = LLMConfig(
                    provider="siliconflow",
                    model="Qwen/Qwen2-7B-Instruct",
                    api_key=f"test-key-{worker_id}"
                )
                
                start_time = time.time()
                llm = factory.create_llm(config)
                end_time = time.time()
                
                results.append({
                    "worker_id": worker_id,
                    "creation_time": end_time - start_time,
                    "success": True
                })
            except Exception as e:
                errors.append({
                    "worker_id": worker_id,
                    "error": str(e)
                })
        
        # 创建10个并发线程
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_llm_worker, args=(i,))
            threads.append(thread)
        
        # 启动所有线程
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # 验证结果
        assert len(errors) == 0, f"并发创建出现错误: {errors}"
        assert len(results) == 10
        
        # 验证并发性能
        avg_creation_time = sum(r["creation_time"] for r in results) / len(results)
        assert total_time < 5.0  # 总时间不超过5秒
        assert avg_creation_time < 1.0  # 平均创建时间不超过1秒


if __name__ == "__main__":
    pytest.main([__file__, "-v"])