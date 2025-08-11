"""
配置管理API集成测试
测试任务8.3：配置管理API接口
"""
import pytest
import json
from fastapi.testclient import TestClient
from fastapi import FastAPI

from rag_system.api.config_api import router
from rag_system.models.config import AppConfig, DatabaseConfig, VectorStoreConfig, EmbeddingsConfig, LLMConfig, RetrievalConfig, APIConfig


@pytest.fixture
def app():
    """创建测试应用"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_config():
    """示例配置"""
    return AppConfig(
        name="Test RAG System",
        version="1.0.0",
        debug=True,
        database=DatabaseConfig(
            url="sqlite:///./test.db",
            echo=False
        ),
        vector_store=VectorStoreConfig(
            type="chroma",
            persist_directory="./test_chroma",
            collection_name="test_collection"
        ),
        embeddings=EmbeddingsConfig(
            provider="mock",
            model="test-embedding",
            chunk_size=500,
            chunk_overlap=50
        ),
        llm=LLMConfig(
            provider="mock",
            model="test-llm",
            temperature=0.5,
            max_tokens=500
        ),
        retrieval=RetrievalConfig(
            top_k=3,
            similarity_threshold=0.8
        ),
        api=APIConfig(
            host="127.0.0.1",
            port=8080,
            cors_origins=["http://localhost:3000"]
        )
    )


class TestConfigAPI:
    """配置API测试类"""
    
    def test_get_config_success(self, client):
        """测试获取配置成功"""
        response = client.get("/config/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "message" in data
        assert "config" in data
        assert isinstance(data["config"], dict)
    
    def test_get_config_section_success(self, client):
        """测试获取配置节成功"""
        sections = ["database", "vector_store", "embeddings", "llm", "retrieval", "api"]
        
        for section in sections:
            response = client.get(f"/config/{section}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert section in data["config"]
    
    def test_get_config_section_invalid(self, client):
        """测试获取无效配置节"""
        response = client.get("/config/invalid_section")
        
        assert response.status_code == 400
        data = response.json()
        assert "无效的配置节" in data["detail"]
    
    def test_validate_config_success(self, client):
        """测试配置验证成功"""
        valid_configs = [
            {
                "section": "database",
                "config": {
                    "url": "sqlite:///./test.db",
                    "echo": True
                }
            },
            {
                "section": "vector_store",
                "config": {
                    "type": "chroma",
                    "persist_directory": "./test_chroma",
                    "collection_name": "test"
                }
            },
            {
                "section": "embeddings",
                "config": {
                    "provider": "openai",
                    "model": "text-embedding-ada-002",
                    "chunk_size": 1000,
                    "chunk_overlap": 200
                }
            },
            {
                "section": "llm",
                "config": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "temperature": 0.1,
                    "max_tokens": 1000
                }
            },
            {
                "section": "retrieval",
                "config": {
                    "top_k": 5,
                    "similarity_threshold": 0.7
                }
            },
            {
                "section": "api",
                "config": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "cors_origins": ["http://localhost:3000"]
                }
            }
        ]
        
        for config_data in valid_configs:
            response = client.post("/config/validate", json=config_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["valid"] is True
            assert data["errors"] is None
    
    def test_validate_config_invalid_section(self, client):
        """测试验证无效配置节"""
        invalid_config = {
            "section": "invalid_section",
            "config": {"test": "value"}
        }
        
        response = client.post("/config/validate", json=invalid_config)
        
        assert response.status_code == 422  # Validation error from Pydantic
    
    def test_validate_config_invalid_data(self, client):
        """测试验证无效配置数据"""
        invalid_configs = [
            {
                "section": "database",
                "config": {
                    "echo": "not_boolean"  # 应该是布尔值
                }
            },
            {
                "section": "vector_store",
                "config": {
                    "type": "invalid_type"  # 不支持的类型
                }
            },
            {
                "section": "embeddings",
                "config": {
                    "provider": "invalid_provider",  # 不支持的提供商
                    "chunk_size": -1  # 负数
                }
            },
            {
                "section": "llm",
                "config": {
                    "provider": "invalid_provider",  # 不支持的提供商
                    "temperature": 3.0  # 超出范围
                }
            },
            {
                "section": "retrieval",
                "config": {
                    "top_k": 0,  # 应该是正整数
                    "similarity_threshold": 1.5  # 超出范围
                }
            },
            {
                "section": "api",
                "config": {
                    "port": 70000,  # 超出端口范围
                    "cors_origins": "not_a_list"  # 应该是列表
                }
            }
        ]
        
        for config_data in invalid_configs:
            response = client.post("/config/validate", json=config_data)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["valid"] is False
            assert data["errors"] is not None
            assert len(data["errors"]) > 0
    
    def test_update_config_section_success(self, client):
        """测试更新配置节成功"""
        # 测试更新数据库配置
        update_data = {
            "url": "sqlite:///./updated_test.db",
            "echo": True
        }
        
        response = client.put("/config/database", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "database" in data["config"]
        assert data["config"]["database"]["url"] == update_data["url"]
        assert data["config"]["database"]["echo"] == update_data["echo"]
    
    def test_update_config_section_invalid_section(self, client):
        """测试更新无效配置节"""
        update_data = {"test": "value"}
        
        response = client.put("/config/invalid_section", json=update_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "无效的配置节" in data["detail"]
    
    def test_update_config_section_invalid_data(self, client):
        """测试更新配置节时数据无效"""
        invalid_data = {
            "url": 123,  # 应该是字符串
            "echo": "not_boolean"  # 应该是布尔值
        }
        
        response = client.put("/config/database", json=invalid_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "配置验证失败" in data["detail"]
    
    def test_reload_configuration_success(self, client):
        """测试重新加载配置成功"""
        response = client.post("/config/reload")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] is True
        assert "重新加载成功" in data["message"]
        assert "config" in data
    
    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/config/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "config_api"
        assert data["version"] == "1.0.0"
    
    def test_get_config_schema_success(self, client):
        """测试获取配置Schema成功"""
        sections = ["database", "vector_store", "embeddings", "llm", "retrieval", "api"]
        
        for section in sections:
            response = client.get(f"/config/schema/{section}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["section"] == section
            assert "schema" in data
            assert data["schema"]["type"] == "object"
            assert "properties" in data["schema"]
    
    def test_get_config_schema_invalid_section(self, client):
        """测试获取无效配置节的Schema"""
        response = client.get("/config/schema/invalid_section")
        
        assert response.status_code == 400
        data = response.json()
        assert "无效的配置节" in data["detail"]


class TestConfigValidation:
    """配置验证测试类"""
    
    def test_database_config_validation(self, client):
        """测试数据库配置验证"""
        # 有效配置
        valid_config = {
            "section": "database",
            "config": {
                "url": "postgresql://user:pass@localhost/db",
                "echo": False
            }
        }
        
        response = client.post("/config/validate", json=valid_config)
        assert response.status_code == 200
        assert response.json()["valid"] is True
        
        # 无效配置 - 缺少URL
        invalid_config = {
            "section": "database",
            "config": {
                "echo": True
            }
        }
        
        response = client.post("/config/validate", json=invalid_config)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "url" in data["errors"]
    
    def test_embeddings_config_validation(self, client):
        """测试嵌入配置验证"""
        # 配置有警告
        config_with_warning = {
            "section": "embeddings",
            "config": {
                "provider": "openai",
                "model": "text-embedding-ada-002",
                "chunk_size": 9000,  # 过大，会产生警告
                "chunk_overlap": 200
            }
        }
        
        response = client.post("/config/validate", json=config_with_warning)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["warnings"] is not None
        assert "chunk_size" in data["warnings"]
    
    def test_retrieval_config_validation(self, client):
        """测试检索配置验证"""
        # 配置有警告
        config_with_warning = {
            "section": "retrieval",
            "config": {
                "top_k": 100,  # 过大，会产生警告
                "similarity_threshold": 0.5
            }
        }
        
        response = client.post("/config/validate", json=config_with_warning)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["warnings"] is not None
        assert "top_k" in data["warnings"]


class TestConfigIntegration:
    """配置集成测试类"""
    
    def test_full_config_workflow(self, client):
        """测试完整的配置工作流"""
        # 1. 获取当前配置
        response = client.get("/config/")
        assert response.status_code == 200
        original_config = response.json()["config"]
        
        # 2. 验证新配置
        new_config = {
            "section": "retrieval",
            "config": {
                "top_k": 10,
                "similarity_threshold": 0.9
            }
        }
        
        response = client.post("/config/validate", json=new_config)
        assert response.status_code == 200
        assert response.json()["valid"] is True
        
        # 3. 更新配置
        response = client.put("/config/retrieval", json=new_config["config"])
        assert response.status_code == 200
        updated_data = response.json()
        assert updated_data["success"] is True
        
        # 4. 验证更新后的配置
        response = client.get("/config/retrieval")
        assert response.status_code == 200
        current_config = response.json()["config"]["retrieval"]
        assert current_config["top_k"] == 10
        assert current_config["similarity_threshold"] == 0.9
        
        # 5. 重新加载配置
        response = client.post("/config/reload")
        assert response.status_code == 200
        assert response.json()["success"] is True
    
    def test_config_schema_validation_consistency(self, client):
        """测试配置Schema与验证的一致性"""
        sections = ["database", "vector_store", "embeddings", "llm", "retrieval", "api"]
        
        for section in sections:
            # 获取Schema
            response = client.get(f"/config/schema/{section}")
            assert response.status_code == 200
            schema = response.json()["schema"]
            
            # 验证Schema结构
            assert "type" in schema
            assert "properties" in schema
            assert schema["type"] == "object"
            
            # 如果有必需字段，验证缺少必需字段时验证失败
            if "required" in schema:
                incomplete_config = {
                    "section": section,
                    "config": {}  # 空配置
                }
                
                response = client.post("/config/validate", json=incomplete_config)
                assert response.status_code == 200
                
                # 如果有必需字段，验证应该失败
                if schema["required"]:
                    data = response.json()
                    assert data["valid"] is False or data["errors"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])