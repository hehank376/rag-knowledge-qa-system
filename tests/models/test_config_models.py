"""
测试配置模型
"""
import pytest
import json
import yaml
from pydantic import ValidationError

from rag_system.llm.base import LLMConfig
from rag_system.embeddings.base import EmbeddingConfig


class TestLLMConfig:
    """测试LLM配置模型"""
    
    def test_basic_creation(self):
        """测试基本创建"""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-test123"
        )
        
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.api_key == "sk-test123"
        assert config.temperature == 0.7  # 默认值
        assert config.max_tokens == 1000  # 默认值
    
    def test_validation_provider(self):
        """测试提供商验证"""
        # 有效提供商
        config = LLMConfig(provider="openai", model="gpt-4", api_key="sk-test")
        assert config.provider == "openai"
        
        # 大小写转换
        config = LLMConfig(provider="OpenAI", model="gpt-4", api_key="sk-test")
        assert config.provider == "openai"
        
        # 无效提供商
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(provider="invalid_provider", model="gpt-4")
        assert "不支持的提供商" in str(exc_info.value)
    
    def test_validation_model(self):
        """测试模型名称验证"""
        # 有效模型名称
        config = LLMConfig(provider="openai", model="gpt-4", api_key="sk-test")
        assert config.model == "gpt-4"
        
        # 空模型名称
        with pytest.raises(ValidationError):
            LLMConfig(provider="openai", model="")
        
        # 空白模型名称
        with pytest.raises(ValidationError):
            LLMConfig(provider="openai", model="   ")
    
    def test_validation_api_key(self):
        """测试API密钥验证"""
        # Mock提供商不需要API密钥
        config = LLMConfig(provider="mock", model="test-model")
        assert config.api_key is None
        
        # OpenAI需要API密钥
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(provider="openai", model="gpt-4")
        assert "需要API密钥" in str(exc_info.value)
    
    def test_validation_temperature(self):
        """测试温度参数验证"""
        # 有效温度
        config = LLMConfig(provider="mock", model="test", temperature=0.5)
        assert config.temperature == 0.5
        
        # 温度过低
        with pytest.raises(ValidationError):
            LLMConfig(provider="mock", model="test", temperature=-0.1)
        
        # 温度过高
        with pytest.raises(ValidationError):
            LLMConfig(provider="mock", model="test", temperature=2.1)
    
    def test_validation_max_tokens(self):
        """测试最大令牌数验证"""
        # 有效令牌数
        config = LLMConfig(provider="mock", model="test", max_tokens=2000)
        assert config.max_tokens == 2000
        
        # 令牌数过小
        with pytest.raises(ValidationError):
            LLMConfig(provider="mock", model="test", max_tokens=0)
        
        # 令牌数过大
        with pytest.raises(ValidationError):
            LLMConfig(provider="mock", model="test", max_tokens=100001)
    
    def test_url_field_normalization(self):
        """测试URL字段标准化"""
        # 使用api_base
        config = LLMConfig(
            provider="mock", 
            model="test", 
            api_base="https://api.example.com"
        )
        assert config.base_url == "https://api.example.com"
        assert config.api_base == "https://api.example.com"
        
        # 使用base_url
        config = LLMConfig(
            provider="mock", 
            model="test", 
            base_url="https://api.example.com"
        )
        assert config.base_url == "https://api.example.com"
        assert config.api_base == "https://api.example.com"
    
    def test_provider_specific_validation(self):
        """测试提供商特定验证"""
        # SiliconFlow自动设置base_url
        config = LLMConfig(provider="siliconflow", model="test", api_key="test")
        assert config.base_url == "https://api.siliconflow.cn/v1"
    
    def test_serialization(self):
        """测试序列化"""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-test123",
            temperature=0.8
        )
        
        # 转换为字典
        data = config.to_dict()
        assert data["provider"] == "openai"
        assert data["model"] == "gpt-4"
        assert data["temperature"] == 0.8
        assert "api_key" in data
        
        # 转换为JSON
        json_str = config.to_json()
        parsed = json.loads(json_str)
        assert parsed["provider"] == "openai"
        
        # 转换为YAML
        yaml_str = config.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert parsed["provider"] == "openai"
    
    def test_deserialization(self):
        """测试反序列化"""
        data = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": "sk-test123",
            "temperature": 0.8
        }
        
        # 从字典创建
        config = LLMConfig.from_dict(data)
        assert config.provider == "openai"
        assert config.temperature == 0.8
        
        # 从JSON创建
        json_str = json.dumps(data)
        config = LLMConfig.from_json(json_str)
        assert config.provider == "openai"
        
        # 从YAML创建
        yaml_str = yaml.dump(data)
        config = LLMConfig.from_yaml(yaml_str)
        assert config.provider == "openai"
    
    def test_default_config(self):
        """测试默认配置"""
        # OpenAI默认配置
        config = LLMConfig.get_default_config("openai", "gpt-4")
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        
        # SiliconFlow默认配置
        config = LLMConfig.get_default_config("siliconflow", "test-model")
        assert config.provider == "siliconflow"
        assert config.base_url == "https://api.siliconflow.cn/v1"
        
        # Mock默认配置
        config = LLMConfig.get_default_config("mock", "test-model")
        assert config.provider == "mock"
        assert config.timeout == 10
        assert config.retry_attempts == 1
    
    def test_config_merge(self):
        """测试配置合并"""
        base_config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-test123",
            temperature=0.7
        )
        
        override_config = LLMConfig(
            provider="openai",
            model="gpt-4",
            api_key="sk-test123",
            temperature=0.9,
            max_tokens=2000
        )
        
        merged = base_config.merge_with(override_config)
        assert merged.temperature == 0.9  # 被覆盖
        assert merged.max_tokens == 2000  # 被覆盖
        assert merged.api_key == "sk-test123"  # 保持不变
    
    def test_compatibility_validation(self):
        """测试兼容性验证"""
        # 高温度警告
        config = LLMConfig(provider="mock", model="test", temperature=1.8)
        warnings = config.validate_compatibility()
        assert any("温度设置较高" in w for w in warnings)
        
        # 短超时警告
        config = LLMConfig(provider="mock", model="test", timeout=15)
        warnings = config.validate_compatibility()
        assert any("超时时间较短" in w for w in warnings)
    
    def test_extra_params(self):
        """测试额外参数"""
        config = LLMConfig(
            provider="mock",
            model="test",
            extra_params={"custom_param": "value"}
        )
        assert config.extra_params["custom_param"] == "value"
    
    def test_forbidden_extra_fields(self):
        """测试禁止额外字段"""
        with pytest.raises(ValidationError):
            LLMConfig(
                provider="mock",
                model="test",
                unknown_field="value"
            )


class TestEmbeddingConfig:
    """测试嵌入配置模型"""
    
    def test_basic_creation(self):
        """测试基本创建"""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="sk-test123"
        )
        
        assert config.provider == "openai"
        assert config.model == "text-embedding-ada-002"
        assert config.api_key == "sk-test123"
        assert config.max_tokens == 8192  # 默认值
        assert config.batch_size == 100  # 默认值
    
    def test_validation_provider(self):
        """测试提供商验证"""
        # 有效提供商
        config = EmbeddingConfig(provider="openai", model="text-embedding-ada-002", api_key="sk-test")
        assert config.provider == "openai"
        
        # 无效提供商
        with pytest.raises(ValidationError) as exc_info:
            EmbeddingConfig(provider="invalid_provider", model="test")
        assert "不支持的嵌入提供商" in str(exc_info.value)
    
    def test_validation_api_key(self):
        """测试API密钥验证"""
        # Mock提供商不需要API密钥
        config = EmbeddingConfig(provider="mock", model="test-model")
        assert config.api_key is None
        
        # OpenAI需要API密钥
        with pytest.raises(ValidationError) as exc_info:
            EmbeddingConfig(provider="openai", model="text-embedding-ada-002")
        assert "需要API密钥" in str(exc_info.value)
    
    def test_validation_batch_size(self):
        """测试批处理大小验证"""
        # 有效批处理大小
        config = EmbeddingConfig(provider="mock", model="test", batch_size=50)
        assert config.batch_size == 50
        
        # 批处理大小过小
        with pytest.raises(ValidationError):
            EmbeddingConfig(provider="mock", model="test", batch_size=0)
        
        # 批处理大小过大
        with pytest.raises(ValidationError):
            EmbeddingConfig(provider="mock", model="test", batch_size=1001)
    
    def test_dimension_field_normalization(self):
        """测试维度字段标准化"""
        # 使用dimensions
        config = EmbeddingConfig(
            provider="mock", 
            model="test", 
            dimensions=768
        )
        assert config.dimensions == 768
        assert config.dimension == 768
        
        # 使用dimension
        config = EmbeddingConfig(
            provider="mock", 
            model="test", 
            dimension=1024
        )
        assert config.dimensions == 1024
        assert config.dimension == 1024
    
    def test_provider_specific_validation(self):
        """测试提供商特定验证"""
        # OpenAI自动设置维度
        config = EmbeddingConfig(
            provider="openai", 
            model="text-embedding-ada-002",
            api_key="test"
        )
        assert config.dimensions == 1536
        
        # SiliconFlow自动设置base_url
        config = EmbeddingConfig(
            provider="siliconflow", 
            model="test",
            api_key="test"
        )
        assert config.base_url == "https://api.siliconflow.cn/v1"
        
        # Mock自动设置维度
        config = EmbeddingConfig(provider="mock", model="test")
        assert config.dimensions == 768
    
    def test_encoding_format_validation(self):
        """测试编码格式验证"""
        # 有效编码格式
        config = EmbeddingConfig(
            provider="mock", 
            model="test", 
            encoding_format="float"
        )
        assert config.encoding_format == "float"
        
        # 无效编码格式
        with pytest.raises(ValidationError):
            EmbeddingConfig(
                provider="mock", 
                model="test", 
                encoding_format="invalid"
            )
    
    def test_truncate_validation(self):
        """测试截断策略验证"""
        # 有效截断策略
        config = EmbeddingConfig(
            provider="mock", 
            model="test", 
            truncate="end"
        )
        assert config.truncate == "end"
        
        # 无效截断策略
        with pytest.raises(ValidationError):
            EmbeddingConfig(
                provider="mock", 
                model="test", 
                truncate="invalid"
            )
    
    def test_serialization(self):
        """测试序列化"""
        config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="sk-test123",
            batch_size=50
        )
        
        # 转换为字典
        data = config.to_dict()
        assert data["provider"] == "openai"
        assert data["batch_size"] == 50
        
        # 转换为JSON
        json_str = config.to_json()
        parsed = json.loads(json_str)
        assert parsed["provider"] == "openai"
        
        # 转换为YAML
        yaml_str = config.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert parsed["provider"] == "openai"
    
    def test_deserialization(self):
        """测试反序列化"""
        data = {
            "provider": "openai",
            "model": "text-embedding-ada-002",
            "api_key": "sk-test123",
            "batch_size": 50
        }
        
        # 从字典创建
        config = EmbeddingConfig.from_dict(data)
        assert config.provider == "openai"
        assert config.batch_size == 50
        
        # 从JSON创建
        json_str = json.dumps(data)
        config = EmbeddingConfig.from_json(json_str)
        assert config.provider == "openai"
        
        # 从YAML创建
        yaml_str = yaml.dump(data)
        config = EmbeddingConfig.from_yaml(yaml_str)
        assert config.provider == "openai"
    
    def test_default_config(self):
        """测试默认配置"""
        # OpenAI默认配置
        config = EmbeddingConfig.get_default_config("openai", "text-embedding-ada-002")
        assert config.provider == "openai"
        assert config.model == "text-embedding-ada-002"
        assert config.max_tokens == 8192
        assert config.batch_size == 100
        
        # Mock默认配置
        config = EmbeddingConfig.get_default_config("mock", "test-model")
        assert config.provider == "mock"
        assert config.timeout == 10
        assert config.dimensions == 768
    
    def test_config_merge(self):
        """测试配置合并"""
        base_config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="sk-test123",
            batch_size=100
        )
        
        override_config = EmbeddingConfig(
            provider="openai",
            model="text-embedding-ada-002",
            api_key="sk-test123",
            batch_size=200,
            max_tokens=4096
        )
        
        merged = base_config.merge_with(override_config)
        assert merged.batch_size == 200  # 被覆盖
        assert merged.max_tokens == 4096  # 被覆盖
        assert merged.api_key == "sk-test123"  # 保持不变
    
    def test_compatibility_validation(self):
        """测试兼容性验证"""
        # 大批处理大小警告
        config = EmbeddingConfig(provider="mock", model="test", batch_size=600)
        warnings = config.validate_compatibility()
        assert any("批处理大小较大" in w for w in warnings)
        
        # 短超时警告
        config = EmbeddingConfig(provider="mock", model="test", timeout=15)
        warnings = config.validate_compatibility()
        assert any("超时时间较短" in w for w in warnings)
        
        # 高维度警告
        config = EmbeddingConfig(provider="mock", model="test", dimensions=5000)
        warnings = config.validate_compatibility()
        assert any("向量维度较高" in w for w in warnings)
    
    def test_extra_params(self):
        """测试额外参数"""
        config = EmbeddingConfig(
            provider="mock",
            model="test",
            extra_params={"custom_param": "value"}
        )
        assert config.extra_params["custom_param"] == "value"
    
    def test_forbidden_extra_fields(self):
        """测试禁止额外字段"""
        with pytest.raises(ValidationError):
            EmbeddingConfig(
                provider="mock",
                model="test",
                unknown_field="value"
            )