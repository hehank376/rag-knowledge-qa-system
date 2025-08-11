"""
测试配置加载器的基本功能
"""
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from rag_system.config.loader import ConfigLoader
from rag_system.utils.exceptions import ConfigurationError


class TestConfigLoaderBasic:
    """测试配置加载器基本功能"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
    
    def teardown_method(self):
        """每个测试方法后的清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_basic_config(self):
        """测试加载基本配置"""
        config_content = '''app:
  name: "Test RAG System"
  version: "1.0.0"
  debug: true

database:
  url: "sqlite:///test.db"
  echo: false

llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.1
  max_tokens: 1000

embeddings:
  provider: "openai"
  model: "text-embedding-ada-002"
  chunk_size: 1000
  chunk_overlap: 200
'''
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            loader = ConfigLoader(str(self.config_path))
            config = loader.load_config()
        
        assert config.name == "Test RAG System"
        assert config.version == "1.0.0"
        assert config.debug is True
        assert config.database.url == "sqlite:///test.db"
        assert config.llm.provider == "openai"
        assert config.llm.model == "gpt-4"
        assert config.embeddings.provider == "openai"
    
    def test_env_variable_replacement(self):
        """测试环境变量替换"""
        config_content = '''app:
  name: "${APP_NAME:Default App}"
  debug: ${APP_DEBUG:false}

database:
  url: "${DATABASE_URL}"

llm:
  provider: "${LLM_PROVIDER:openai}"
  model: "${LLM_MODEL}"
'''
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        env_vars = {
            "APP_NAME": "Test App",
            "APP_DEBUG": "true",
            "DATABASE_URL": "sqlite:///test.db",
            "LLM_MODEL": "gpt-3.5-turbo",
            "OPENAI_API_KEY": "test-api-key"
        }
        
        with patch.dict(os.environ, env_vars):
            loader = ConfigLoader(str(self.config_path))
            config = loader.load_config()
        
        assert config.name == "Test App"
        assert config.debug is True
        assert config.database.url == "sqlite:///test.db"
        assert config.llm.model == "gpt-3.5-turbo"
    
    def test_config_validation_unsupported_provider(self):
        """测试不支持的提供商验证"""
        config_content = '''llm:
  provider: "unsupported_provider"
  model: "some-model"
'''
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        loader = ConfigLoader(str(self.config_path))
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load_config()
        
        assert "不支持的LLM提供商" in str(exc_info.value)
        assert "unsupported_provider" in str(exc_info.value)
    
    def test_config_validation_missing_api_key(self):
        """测试缺少API密钥的验证"""
        config_content = '''llm:
  provider: "openai"
  model: "gpt-4"

embeddings:
  provider: "siliconflow"
  model: "some-model"
'''
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        loader = ConfigLoader(str(self.config_path))
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load_config()
        
        error_msg = str(exc_info.value)
        assert "需要API密钥" in error_msg
    
    def test_missing_config_file(self):
        """测试配置文件不存在"""
        non_existent_path = str(Path(self.temp_dir) / "non_existent.yaml")
        
        # 设置必要的环境变量以通过验证
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            loader = ConfigLoader(non_existent_path)
            
            # 应该使用默认配置，不抛出异常
            config = loader.load_config()
            assert config.name == "RAG Knowledge QA System"
    
    def test_multi_platform_config(self):
        """测试多平台配置"""
        config_content = '''app:
  name: "Multi-Platform RAG"

database:
  url: "sqlite:///multi_platform.db"

llm:
  provider: "siliconflow"
  model: "Qwen/Qwen2.5-7B-Instruct"
  temperature: 0.7
  max_tokens: 2000

embeddings:
  provider: "siliconflow"
  model: "BAAI/bge-large-zh-v1.5"
  batch_size: 50
  dimensions: 1024

vector_store:
  type: "chroma"
  persist_directory: "./multi_platform_chroma"
'''
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        env_vars = {
            "SILICONFLOW_API_KEY": "test-siliconflow-key"
        }
        
        with patch.dict(os.environ, env_vars):
            loader = ConfigLoader(str(self.config_path))
            config = loader.load_config()
        
        assert config.name == "Multi-Platform RAG"
        assert config.llm.provider == "siliconflow"
        assert config.llm.model == "Qwen/Qwen2.5-7B-Instruct"
        assert config.embeddings.provider == "siliconflow"
        assert config.embeddings.model == "BAAI/bge-large-zh-v1.5"
        assert config.embeddings.batch_size == 50
        assert config.embeddings.dimensions == 1024