"""
测试增强的配置模型
"""
import json
import tempfile
import pytest
from pathlib import Path

from rag_system.models.config import (
    DatabaseConfig, VectorStoreConfig, EmbeddingsConfig, 
    LLMConfig, RetrievalConfig, APIConfig, AppConfig
)


class TestDatabaseConfig:
    """测试数据库配置"""
    
    def test_default_values(self):
        """测试默认值"""
        config = DatabaseConfig()
        assert config.url == "sqlite:///./database/rag_system.db"
        assert config.echo is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = DatabaseConfig(url="sqlite:///test.db", echo=True)
        data = config.to_dict()
        
        assert data == {
            "url": "sqlite:///test.db",
            "echo": True
        }
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {"url": "sqlite:///test.db", "echo": True}
        config = DatabaseConfig.from_dict(data)
        
        assert config.url == "sqlite:///test.db"
        assert config.echo is True
    
    def test_validate_success(self):
        """测试验证成功"""
        config = DatabaseConfig(url="sqlite:///test.db")
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validate_empty_url(self):
        """测试验证空URL"""
        config = DatabaseConfig(url="")
        errors = config.validate()
        assert len(errors) == 1
        assert "数据库URL不能为空" in errors[0]


class TestVectorStoreConfig:
    """测试向量存储配置"""
    
    def test_default_values(self):
        """测试默认值"""
        config = VectorStoreConfig()
        assert config.type == "chroma"
        assert config.persist_directory == "./chroma_db"
        assert config.collection_name == "knowledge_base"
    
    def test_validate_success(self):
        """测试验证成功"""
        config = VectorStoreConfig(type="chroma")
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validate_unsupported_type(self):
        """测试验证不支持的类型"""
        config = VectorStoreConfig(type="unsupported")
        errors = config.validate()
        assert len(errors) == 1
        assert "不支持的向量存储类型" in errors[0]
    
    def test_validate_pinecone_missing_config(self):
        """测试Pinecone缺少配置"""
        config = VectorStoreConfig(type="pinecone")
        errors = config.validate()
        assert len(errors) == 3  # 缺少API密钥、环境和索引名称
        assert any("需要API密钥" in error for error in errors)
        assert any("需要环境配置" in error for error in errors)
        assert any("需要索引名称" in error for error in errors)


class TestEmbeddingsConfig:
    """测试嵌入模型配置"""
    
    def test_default_values(self):
        """测试默认值"""
        config = EmbeddingsConfig()
        assert config.provider == "openai"
        assert config.model == "text-embedding-ada-002"
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.batch_size == 100
    
    def test_validate_success(self):
        """测试验证成功"""
        config = EmbeddingsConfig(
            provider="openai",
            chunk_size=1000,
            chunk_overlap=200,
            batch_size=50
        )
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validate_unsupported_provider(self):
        """测试验证不支持的提供商"""
        config = EmbeddingsConfig(provider="unsupported")
        errors = config.validate()
        assert len(errors) == 1
        assert "不支持的嵌入模型提供商" in errors[0]
    
    def test_validate_invalid_chunk_size(self):
        """测试验证无效分块大小"""
        config = EmbeddingsConfig(chunk_size=0)
        errors = config.validate()
        assert any("分块大小必须大于0" in error for error in errors)
    
    def test_validate_invalid_chunk_overlap(self):
        """测试验证无效分块重叠"""
        config = EmbeddingsConfig(chunk_size=1000, chunk_overlap=1000)
        errors = config.validate()
        assert any("分块重叠不能大于或等于分块大小" in error for error in errors)
    
    def test_validate_negative_chunk_overlap(self):
        """测试验证负数分块重叠"""
        config = EmbeddingsConfig(chunk_overlap=-100)
        errors = config.validate()
        assert any("分块重叠不能为负数" in error for error in errors)
    
    def test_validate_invalid_batch_size(self):
        """测试验证无效批处理大小"""
        config = EmbeddingsConfig(batch_size=0)
        errors = config.validate()
        assert any("批处理大小必须大于0" in error for error in errors)
    
    def test_validate_invalid_timeout(self):
        """测试验证无效超时时间"""
        config = EmbeddingsConfig(timeout=0)
        errors = config.validate()
        assert any("超时时间必须大于0" in error for error in errors)
    
    def test_validate_invalid_dimensions(self):
        """测试验证无效维度"""
        config = EmbeddingsConfig(dimensions=0)
        errors = config.validate()
        assert any("嵌入向量维度必须大于0" in error for error in errors)


class TestLLMConfig:
    """测试LLM配置"""
    
    def test_default_values(self):
        """测试默认值"""
        config = LLMConfig()
        assert config.provider == "openai"
        assert config.model == "gpt-4"
        assert config.temperature == 0.1
        assert config.max_tokens == 1000
        assert config.stream is False
    
    def test_validate_success(self):
        """测试验证成功"""
        config = LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.5,
            max_tokens=2000
        )
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validate_unsupported_provider(self):
        """测试验证不支持的提供商"""
        config = LLMConfig(provider="unsupported")
        errors = config.validate()
        assert len(errors) == 1
        assert "不支持的LLM提供商" in errors[0]
    
    def test_validate_empty_model(self):
        """测试验证空模型名称"""
        config = LLMConfig(model="")
        errors = config.validate()
        assert any("LLM模型名称不能为空" in error for error in errors)
    
    def test_validate_mock_provider_empty_model(self):
        """测试Mock提供商允许空模型名称"""
        config = LLMConfig(provider="mock", model="")
        errors = config.validate()
        # Mock提供商不应该报告模型名称为空的错误
        assert not any("LLM模型名称不能为空" in error for error in errors)
    
    def test_validate_invalid_temperature(self):
        """测试验证无效温度"""
        config = LLMConfig(temperature=3.0)
        errors = config.validate()
        assert any("温度参数必须在0-2之间" in error for error in errors)
        
        config = LLMConfig(temperature=-0.1)
        errors = config.validate()
        assert any("温度参数必须在0-2之间" in error for error in errors)
    
    def test_validate_invalid_max_tokens(self):
        """测试验证无效最大令牌数"""
        config = LLMConfig(max_tokens=0)
        errors = config.validate()
        assert any("最大令牌数必须大于0" in error for error in errors)
    
    def test_validate_invalid_timeout(self):
        """测试验证无效超时时间"""
        config = LLMConfig(timeout=0)
        errors = config.validate()
        assert any("超时时间必须大于0" in error for error in errors)
    
    def test_validate_negative_retry_attempts(self):
        """测试验证负数重试次数"""
        config = LLMConfig(retry_attempts=-1)
        errors = config.validate()
        assert any("重试次数不能为负数" in error for error in errors)


class TestRetrievalConfig:
    """测试检索配置"""
    
    def test_default_values(self):
        """测试默认值"""
        config = RetrievalConfig()
        assert config.top_k == 5
        assert config.similarity_threshold == 0.7
    
    def test_validate_success(self):
        """测试验证成功"""
        config = RetrievalConfig(top_k=10, similarity_threshold=0.8)
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validate_invalid_top_k(self):
        """测试验证无效top_k"""
        config = RetrievalConfig(top_k=0)
        errors = config.validate()
        assert any("检索数量必须大于0" in error for error in errors)
    
    def test_validate_invalid_similarity_threshold(self):
        """测试验证无效相似度阈值"""
        config = RetrievalConfig(similarity_threshold=1.5)
        errors = config.validate()
        assert any("相似度阈值必须在0-1之间" in error for error in errors)
        
        config = RetrievalConfig(similarity_threshold=-0.1)
        errors = config.validate()
        assert any("相似度阈值必须在0-1之间" in error for error in errors)


class TestAPIConfig:
    """测试API配置"""
    
    def test_default_values(self):
        """测试默认值"""
        config = APIConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.cors_origins == ["http://localhost:3000"]
    
    def test_validate_success(self):
        """测试验证成功"""
        config = APIConfig(host="localhost", port=8080)
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validate_invalid_port(self):
        """测试验证无效端口"""
        config = APIConfig(port=0)
        errors = config.validate()
        assert any("端口号必须在1-65535之间" in error for error in errors)
        
        config = APIConfig(port=70000)
        errors = config.validate()
        assert any("端口号必须在1-65535之间" in error for error in errors)
    
    def test_validate_empty_host(self):
        """测试验证空主机地址"""
        config = APIConfig(host="")
        errors = config.validate()
        assert any("主机地址不能为空" in error for error in errors)


class TestAppConfig:
    """测试应用配置"""
    
    def test_default_values(self):
        """测试默认值"""
        config = AppConfig()
        assert config.name == "RAG Knowledge QA System"
        assert config.version == "1.0.0"
        assert config.debug is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = AppConfig(
            name="Test App",
            version="2.0.0",
            debug=True,
            database=DatabaseConfig(url="sqlite:///test.db"),
            llm=LLMConfig(provider="openai", model="gpt-3.5-turbo")
        )
        
        data = config.to_dict()
        assert data["name"] == "Test App"
        assert data["version"] == "2.0.0"
        assert data["debug"] is True
        assert data["database"]["url"] == "sqlite:///test.db"
        assert data["llm"]["provider"] == "openai"
        assert data["llm"]["model"] == "gpt-3.5-turbo"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "name": "Test App",
            "version": "2.0.0",
            "debug": True,
            "database": {"url": "sqlite:///test.db", "echo": False},
            "llm": {"provider": "openai", "model": "gpt-3.5-turbo", "temperature": 0.5, "max_tokens": 1000}
        }
        
        config = AppConfig.from_dict(data)
        assert config.name == "Test App"
        assert config.version == "2.0.0"
        assert config.debug is True
        assert isinstance(config.database, DatabaseConfig)
        assert config.database.url == "sqlite:///test.db"
        assert isinstance(config.llm, LLMConfig)
        assert config.llm.provider == "openai"
        assert config.llm.model == "gpt-3.5-turbo"
    
    def test_to_json(self):
        """测试转换为JSON"""
        config = AppConfig(name="Test App", version="2.0.0")
        json_str = config.to_json()
        
        # 验证是有效的JSON
        data = json.loads(json_str)
        assert data["name"] == "Test App"
        assert data["version"] == "2.0.0"
    
    def test_from_json(self):
        """测试从JSON创建"""
        json_str = '''
        {
            "name": "Test App",
            "version": "2.0.0",
            "debug": true,
            "database": {
                "url": "sqlite:///test.db",
                "echo": false
            }
        }
        '''
        
        config = AppConfig.from_json(json_str)
        assert config.name == "Test App"
        assert config.version == "2.0.0"
        assert config.debug is True
        assert isinstance(config.database, DatabaseConfig)
        assert config.database.url == "sqlite:///test.db"
    
    def test_to_yaml(self):
        """测试转换为YAML"""
        config = AppConfig(name="Test App", version="2.0.0")
        yaml_str = config.to_yaml()
        
        # 验证包含预期内容
        assert "name: Test App" in yaml_str
        assert "version: 2.0.0" in yaml_str
    
    def test_from_yaml(self):
        """测试从YAML创建"""
        yaml_str = '''
        name: Test App
        version: 2.0.0
        debug: true
        database:
          url: sqlite:///test.db
          echo: false
        llm:
          provider: openai
          model: gpt-3.5-turbo
        '''
        
        config = AppConfig.from_yaml(yaml_str)
        assert config.name == "Test App"
        assert config.version == "2.0.0"
        assert config.debug is True
        assert isinstance(config.database, DatabaseConfig)
        assert config.database.url == "sqlite:///test.db"
        assert isinstance(config.llm, LLMConfig)
        assert config.llm.provider == "openai"
    
    def test_save_to_file_yaml(self):
        """测试保存为YAML文件"""
        config = AppConfig(name="Test App", version="2.0.0")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            config.save_to_file(temp_path, format='yaml')
            
            # 验证文件存在且内容正确
            assert Path(temp_path).exists()
            
            loaded_config = AppConfig.load_from_file(temp_path)
            assert loaded_config.name == "Test App"
            assert loaded_config.version == "2.0.0"
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_save_to_file_json(self):
        """测试保存为JSON文件"""
        config = AppConfig(name="Test App", version="2.0.0")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config.save_to_file(temp_path, format='json')
            
            # 验证文件存在且内容正确
            assert Path(temp_path).exists()
            
            loaded_config = AppConfig.load_from_file(temp_path)
            assert loaded_config.name == "Test App"
            assert loaded_config.version == "2.0.0"
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_save_to_file_unsupported_format(self):
        """测试保存为不支持的格式"""
        config = AppConfig()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="不支持的格式"):
                config.save_to_file(temp_path, format='txt')
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_load_from_file_not_exists(self):
        """测试加载不存在的文件"""
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            AppConfig.load_from_file("non_existent_file.yaml")
    
    def test_validate_success(self):
        """测试验证成功"""
        config = AppConfig(
            name="Test App",
            version="1.0.0",
            database=DatabaseConfig(url="sqlite:///test.db"),
            llm=LLMConfig(provider="openai", model="gpt-4"),
            embeddings=EmbeddingsConfig(provider="openai"),
            retrieval=RetrievalConfig(top_k=5),
            api=APIConfig(port=8000)
        )
        
        errors = config.validate()
        assert len(errors) == 0
    
    def test_validate_empty_name(self):
        """测试验证空应用名称"""
        config = AppConfig(name="")
        errors = config.validate()
        assert any("应用名称不能为空" in error for error in errors)
    
    def test_validate_empty_version(self):
        """测试验证空应用版本"""
        config = AppConfig(version="")
        errors = config.validate()
        assert any("应用版本不能为空" in error for error in errors)
    
    def test_validate_nested_config_errors(self):
        """测试验证嵌套配置错误"""
        config = AppConfig(
            name="Test App",
            version="1.0.0",
            database=DatabaseConfig(url=""),  # 无效URL
            llm=LLMConfig(temperature=3.0),   # 无效温度
            embeddings=EmbeddingsConfig(chunk_size=0),  # 无效分块大小
            retrieval=RetrievalConfig(top_k=0),  # 无效top_k
            api=APIConfig(port=0)  # 无效端口
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("数据库配置" in error for error in errors)
        assert any("LLM配置" in error for error in errors)
        assert any("嵌入模型配置" in error for error in errors)
        assert any("检索配置" in error for error in errors)
        assert any("API配置" in error for error in errors)
    
    def test_get_default_config(self):
        """测试获取默认配置"""
        config = AppConfig()
        default_config = config.get_default_config()
        
        assert default_config.name == "RAG Knowledge QA System"
        assert default_config.version == "1.0.0"
        assert default_config.debug is False
        assert isinstance(default_config.database, DatabaseConfig)
        assert isinstance(default_config.vector_store, VectorStoreConfig)
        assert isinstance(default_config.embeddings, EmbeddingsConfig)
        assert isinstance(default_config.llm, LLMConfig)
        assert isinstance(default_config.retrieval, RetrievalConfig)
        assert isinstance(default_config.api, APIConfig)