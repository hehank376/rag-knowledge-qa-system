"""
向后兼容性支持测试
"""
import pytest
import tempfile
import warnings
from pathlib import Path
from unittest.mock import patch

from rag_system.utils.compatibility import (
    CompatibilityManager, get_compatibility_manager, ensure_backward_compatibility,
    convert_legacy_llm_config, convert_legacy_embedding_config,
    deprecated_api, check_config_compatibility
)
from rag_system.llm.base import LLMConfig
from rag_system.embeddings.base import EmbeddingConfig
from rag_system.utils.model_exceptions import ModelConfigError


class TestCompatibilityManager:
    """兼容性管理器测试"""
    
    def test_compatibility_manager_initialization(self):
        """测试兼容性管理器初始化"""
        manager = CompatibilityManager()
        
        assert isinstance(manager.deprecated_warnings, list)
        assert isinstance(manager.migration_log, list)
        assert len(manager.deprecated_warnings) == 0
        assert len(manager.migration_log) == 0
    
    def test_convert_legacy_llm_config_basic(self):
        """测试基础LLM配置转换"""
        manager = CompatibilityManager()
        
        legacy_config = {
            'provider': 'openai',
            'model': 'gpt-4',
            'api_key': 'sk-test123',
            'temperature': 0.8,
            'max_tokens': 2000
        }
        
        converted = manager.convert_legacy_llm_config(legacy_config)
        
        assert isinstance(converted, LLMConfig)
        assert converted.provider == 'openai'
        assert converted.model == 'gpt-4'
        assert converted.api_key == 'sk-test123'
        assert converted.temperature == 0.8
        assert converted.max_tokens == 2000
    
    def test_convert_legacy_llm_config_with_deprecated_fields(self):
        """测试带弃用字段的LLM配置转换"""
        manager = CompatibilityManager()
        
        legacy_config = {
            'llm_provider': 'openai',  # 弃用字段
            'llm_model': 'gpt-3.5',    # 弃用字段和模型名
            'openai_api_key': 'sk-test123',  # 弃用字段
            'llm_temperature': 0.9,    # 弃用字段
            'max_length': 1500         # 弃用字段
        }
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            converted = manager.convert_legacy_llm_config(legacy_config)
            
            # 检查弃用警告
            assert len(w) > 0
            warning_messages = [str(warning.message) for warning in w]
            assert any('llm_provider' in msg for msg in warning_messages)
        
        assert converted.provider == 'openai'
        assert converted.model == 'gpt-3.5-turbo'  # 自动转换
        assert converted.api_key == 'sk-test123'
        assert converted.temperature == 0.9
        assert converted.max_tokens == 1500
    
    def test_convert_legacy_embedding_config_basic(self):
        """测试基础嵌入配置转换"""
        manager = CompatibilityManager()
        
        legacy_config = {
            'provider': 'openai',
            'model': 'text-embedding-ada-002',
            'api_key': 'sk-test123',
            'dimensions': 1536,
            'batch_size': 50
        }
        
        converted = manager.convert_legacy_embedding_config(legacy_config)
        
        assert isinstance(converted, EmbeddingConfig)
        assert converted.provider == 'openai'
        assert converted.model == 'text-embedding-ada-002'
        assert converted.api_key == 'sk-test123'
        assert converted.dimensions == 1536
        assert converted.batch_size == 50
    
    def test_convert_legacy_embedding_config_with_deprecated_fields(self):
        """测试带弃用字段的嵌入配置转换"""
        manager = CompatibilityManager()
        
        legacy_config = {
            'embedding_provider': 'openai',  # 弃用字段
            'embedding_model': 'ada-002',    # 弃用字段和模型名
            'openai_api_key': 'sk-test123',  # 弃用字段
            'vector_size': 1536,             # 弃用字段
            'batch_limit': 200               # 弃用字段
        }
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            converted = manager.convert_legacy_embedding_config(legacy_config)
            
            # 检查弃用警告
            assert len(w) > 0
        
        assert converted.provider == 'openai'
        assert converted.model == 'text-embedding-ada-002'  # 自动转换
        assert converted.api_key == 'sk-test123'
        assert converted.dimensions == 1536
        assert converted.batch_size == 200
    
    def test_auto_detect_openai_provider(self):
        """测试自动检测OpenAI提供商"""
        manager = CompatibilityManager()
        
        # LLM配置自动检测
        legacy_llm_config = {
            'model': 'gpt-4',
            'openai_api_key': 'sk-test123'
            # 没有显式设置provider
        }
        
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            converted_llm = manager.convert_legacy_llm_config(legacy_llm_config)
        
        assert converted_llm.provider == 'openai'
        
        # 嵌入配置自动检测
        legacy_embedding_config = {
            'model': 'text-embedding-ada-002',
            'openai_api_key': 'sk-test123'
            # 没有显式设置provider
        }
        
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            converted_embedding = manager.convert_legacy_embedding_config(legacy_embedding_config)
        
        assert converted_embedding.provider == 'openai'
    
    def test_infer_embedding_dimensions(self):
        """测试推断嵌入维度"""
        manager = CompatibilityManager()
        
        test_cases = [
            ('openai', 'text-embedding-ada-002', 1536),
            ('openai', 'text-embedding-3-small', 1536),
            ('openai', 'text-embedding-3-large', 3072),
            ('siliconflow', 'BAAI/bge-large-zh-v1.5', 1024),
            ('siliconflow', 'BAAI/bge-base-zh-v1.5', 768),
            ('unknown', 'unknown-model', None)
        ]
        
        for provider, model, expected_dim in test_cases:
            result = manager._infer_embedding_dimensions(model, provider)
            assert result == expected_dim
    
    def test_normalize_model_names(self):
        """测试模型名称标准化"""
        manager = CompatibilityManager()
        
        # LLM模型名称标准化
        llm_test_cases = [
            ('openai', 'gpt-3.5', 'gpt-3.5-turbo'),
            ('openai', 'gpt-35-turbo', 'gpt-3.5-turbo'),
            ('openai', 'text-davinci-003', 'gpt-3.5-turbo-instruct'),
            ('openai', 'gpt-4', 'gpt-4'),  # 不变
            ('siliconflow', 'Qwen/Qwen2-7B-Instruct', 'Qwen/Qwen2-7B-Instruct')  # 不变
        ]
        
        for provider, old_name, expected_name in llm_test_cases:
            result = manager._normalize_model_name(old_name, provider)
            assert result == expected_name
        
        # 嵌入模型名称标准化
        embedding_test_cases = [
            ('openai', 'ada-002', 'text-embedding-ada-002'),
            ('openai', 'text-embedding-ada-002', 'text-embedding-ada-002'),  # 不变
            ('siliconflow', 'BAAI/bge-large-zh-v1.5', 'BAAI/bge-large-zh-v1.5')  # 不变
        ]
        
        for provider, old_name, expected_name in embedding_test_cases:
            result = manager._normalize_embedding_model_name(old_name, provider)
            assert result == expected_name
    
    def test_normalize_base_url(self):
        """测试基础URL标准化"""
        manager = CompatibilityManager()
        
        test_cases = [
            ('https://api.openai.com/v1/', 'https://api.openai.com/v1'),  # 移除末尾斜杠
            ('https://api.openai.com', 'https://api.openai.com/v1'),      # 添加版本
            ('https://api.siliconflow.cn/v1', 'https://api.siliconflow.cn/v1'),  # 不变
            ('https://custom.api.com/', 'https://custom.api.com')         # 移除末尾斜杠
        ]
        
        for input_url, expected_url in test_cases:
            result = manager._normalize_base_url(input_url)
            assert result == expected_url
    
    def test_normalize_boolean(self):
        """测试布尔值标准化"""
        manager = CompatibilityManager()
        
        true_cases = [True, 'true', 'True', 'TRUE', '1', 'yes', 'YES', 'on', 'ON', 1, 1.0]
        false_cases = [False, 'false', 'False', 'FALSE', '0', 'no', 'NO', 'off', 'OFF', 0, 0.0, None, '']
        
        for value in true_cases:
            assert manager._normalize_boolean(value) is True
        
        for value in false_cases:
            assert manager._normalize_boolean(value) is False
    
    def test_convert_full_config(self):
        """测试完整配置转换"""
        manager = CompatibilityManager()
        
        legacy_config = {
            'app': {
                'name': 'Test App',
                'version': '1.0.0'
            },
            'llm': {
                'llm_provider': 'openai',
                'llm_model': 'gpt-3.5',
                'openai_api_key': 'sk-test123'
            },
            'embedding': {  # 使用旧的字段名
                'embedding_provider': 'openai',
                'embedding_model': 'ada-002',
                'openai_api_key': 'sk-test123',  # 添加API密钥
                'vector_size': 1536
            },
            'vector_db': {  # 使用旧的字段名
                'store_type': 'chroma',
                'persist_dir': './old_chroma_db'
            }
        }
        
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            converted = manager._convert_full_config(legacy_config)
        
        # 检查应用配置保持不变
        assert converted['app'] == legacy_config['app']
        
        # 检查LLM配置转换
        assert 'llm' in converted
        llm_config = converted['llm']
        assert llm_config['provider'] == 'openai'
        assert llm_config['model'] == 'gpt-3.5-turbo'
        
        # 检查嵌入配置转换
        assert 'embeddings' in converted
        embedding_config = converted['embeddings']
        assert embedding_config['provider'] == 'openai'
        assert embedding_config['model'] == 'text-embedding-ada-002'
        assert embedding_config['dimensions'] == 1536
        
        # 检查向量存储配置转换
        assert 'vector_store' in converted
        vector_config = converted['vector_store']
        assert vector_config['type'] == 'chroma'
        assert vector_config['persist_directory'] == './old_chroma_db'
    
    def test_convert_legacy_config_file(self):
        """测试配置文件转换"""
        manager = CompatibilityManager()
        
        legacy_config = {
            'llm': {
                'provider': 'openai',
                'model': 'gpt-4',
                'api_key': 'sk-test123'
            },
            'embeddings': {
                'provider': 'openai',
                'model': 'text-embedding-ada-002',
                'api_key': 'sk-test123'  # 添加API密钥
            }
        }
        
        # 创建临时配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.dump(legacy_config, f)
            temp_path = f.name
        
        try:
            converted = manager.convert_legacy_config_file(temp_path)
            
            assert 'llm' in converted
            assert 'embeddings' in converted
            assert converted['llm']['provider'] == 'openai'
            assert converted['embeddings']['provider'] == 'openai'
            
        finally:
            Path(temp_path).unlink()
    
    def test_save_converted_config(self):
        """测试保存转换后的配置"""
        manager = CompatibilityManager()
        
        converted_config = {
            'llm': {
                'provider': 'openai',
                'model': 'gpt-4'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            manager.save_converted_config(converted_config, temp_path)
            
            # 验证文件已保存
            assert Path(temp_path).exists()
            
            # 验证内容正确
            import yaml
            with open(temp_path, 'r') as f:
                saved_config = yaml.safe_load(f)
            
            assert saved_config == converted_config
            
        finally:
            Path(temp_path).unlink()
    
    def test_migration_report(self):
        """测试迁移报告"""
        manager = CompatibilityManager()
        
        # 执行一些转换操作
        legacy_config = {
            'llm_provider': 'openai',
            'llm_model': 'gpt-3.5',
            'api_key': 'sk-test123'  # 添加API密钥
        }
        
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            manager.convert_legacy_llm_config(legacy_config)
        
        report = manager.get_migration_report()
        
        assert 'migration_log' in report
        assert 'deprecated_warnings' in report
        assert 'total_warnings' in report
        assert 'migration_steps' in report
        
        assert report['total_warnings'] > 0
        assert report['migration_steps'] > 0
        assert len(report['deprecated_warnings']) == report['total_warnings']
    
    def test_clear_logs(self):
        """测试清理日志"""
        manager = CompatibilityManager()
        
        # 添加一些日志
        manager.migration_log.append("test log")
        manager.deprecated_warnings.append("test warning")
        
        assert len(manager.migration_log) > 0
        assert len(manager.deprecated_warnings) > 0
        
        manager.clear_logs()
        
        assert len(manager.migration_log) == 0
        assert len(manager.deprecated_warnings) == 0


class TestGlobalFunctions:
    """全局函数测试"""
    
    def test_get_compatibility_manager(self):
        """测试获取全局兼容性管理器"""
        manager1 = get_compatibility_manager()
        manager2 = get_compatibility_manager()
        
        # 应该是同一个实例
        assert manager1 is manager2
        assert isinstance(manager1, CompatibilityManager)
    
    def test_ensure_backward_compatibility(self):
        """测试确保向后兼容性"""
        legacy_config = {
            'llm': {
                'llm_provider': 'openai',
                'llm_model': 'gpt-4',
                'api_key': 'sk-test123'  # 添加API密钥
            }
        }
        
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            converted = ensure_backward_compatibility(legacy_config)
        
        assert 'llm' in converted
        assert converted['llm']['provider'] == 'openai'
        assert converted['llm']['model'] == 'gpt-4'
    
    def test_convert_legacy_llm_config_function(self):
        """测试转换旧版LLM配置函数"""
        legacy_config = {
            'provider': 'openai',
            'model': 'gpt-4',
            'api_key': 'sk-test123'
        }
        
        converted = convert_legacy_llm_config(legacy_config)
        
        assert isinstance(converted, LLMConfig)
        assert converted.provider == 'openai'
        assert converted.model == 'gpt-4'
    
    def test_convert_legacy_embedding_config_function(self):
        """测试转换旧版嵌入配置函数"""
        legacy_config = {
            'provider': 'openai',
            'model': 'text-embedding-ada-002',
            'api_key': 'sk-test123'
        }
        
        converted = convert_legacy_embedding_config(legacy_config)
        
        assert isinstance(converted, EmbeddingConfig)
        assert converted.provider == 'openai'
        assert converted.model == 'text-embedding-ada-002'


class TestDeprecatedAPI:
    """弃用API测试"""
    
    def test_deprecated_api_decorator(self):
        """测试弃用API装饰器"""
        
        @deprecated_api("这个函数已经过时", "2.0")
        def old_function():
            return "old result"
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = old_function()
            
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "old_function 已弃用" in str(w[0].message)
            assert "这个函数已经过时" in str(w[0].message)
            assert "版本 2.0" in str(w[0].message)
        
        assert result == "old result"
        assert "[已弃用]" in old_function.__doc__


class TestCompatibilityChecks:
    """兼容性检查测试"""
    
    def test_check_config_compatibility_valid(self):
        """测试有效配置的兼容性检查"""
        valid_config = {
            'llm': {
                'provider': 'openai',
                'model': 'gpt-4'
            },
            'embeddings': {
                'provider': 'openai',
                'model': 'text-embedding-ada-002'
            }
        }
        
        issues = check_config_compatibility(valid_config)
        assert len(issues) == 0
    
    def test_check_config_compatibility_missing_sections(self):
        """测试缺少配置节的兼容性检查"""
        invalid_config = {
            'app': {
                'name': 'Test App'
            }
            # 缺少llm和embeddings配置
        }
        
        issues = check_config_compatibility(invalid_config)
        assert len(issues) == 2
        assert any('llm' in issue for issue in issues)
        assert any('embeddings' in issue for issue in issues)
    
    def test_check_config_compatibility_missing_fields(self):
        """测试缺少字段的兼容性检查"""
        invalid_config = {
            'llm': {
                # 缺少provider和model
                'api_key': 'sk-test123'
            },
            'embeddings': {
                'provider': 'openai'
                # 缺少model
            }
        }
        
        issues = check_config_compatibility(invalid_config)
        assert len(issues) == 3
        assert any('LLM配置缺少provider字段' in issue for issue in issues)
        assert any('LLM配置缺少model字段' in issue for issue in issues)
        assert any('嵌入配置缺少model字段' in issue for issue in issues)
    
    def test_check_config_compatibility_with_legacy_embedding_field(self):
        """测试使用旧版嵌入字段名的兼容性检查"""
        config_with_legacy_field = {
            'llm': {
                'provider': 'openai',
                'model': 'gpt-4'
            },
            'embedding': {  # 使用旧的字段名
                'provider': 'openai',
                'model': 'text-embedding-ada-002'
            }
        }
        
        issues = check_config_compatibility(config_with_legacy_field)
        assert len(issues) == 0  # 应该能够处理旧字段名


class TestErrorHandling:
    """错误处理测试"""
    
    def test_invalid_config_conversion(self):
        """测试无效配置转换"""
        manager = CompatibilityManager()
        
        # 无效的LLM配置
        invalid_llm_config = {
            'provider': 'invalid_provider',
            'model': '',  # 空模型名
            'temperature': 'invalid_temperature'  # 无效温度
        }
        
        with pytest.raises(ModelConfigError):
            manager.convert_legacy_llm_config(invalid_llm_config)
    
    def test_nonexistent_config_file(self):
        """测试不存在的配置文件"""
        manager = CompatibilityManager()
        
        with pytest.raises(FileNotFoundError):
            manager.convert_legacy_config_file('/nonexistent/path/config.yaml')
    
    def test_invalid_config_file_format(self):
        """测试无效的配置文件格式"""
        manager = CompatibilityManager()
        
        # 创建无效的配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("invalid config content")
            temp_path = f.name
        
        try:
            with pytest.raises(ModelConfigError):
                manager.convert_legacy_config_file(temp_path)
        finally:
            Path(temp_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])