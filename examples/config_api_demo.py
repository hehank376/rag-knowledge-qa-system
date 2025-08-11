#!/usr/bin/env python3
"""
配置管理API演示脚本
演示任务8.3：配置管理API接口的使用
"""
import asyncio
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient

from rag_system.api.config_api import router


def create_demo_app():
    """创建演示应用"""
    app = FastAPI(title="RAG System Config API Demo")
    app.include_router(router)
    return app


def demo_config_api():
    """演示配置管理API功能"""
    print("=" * 60)
    print("RAG系统配置管理API演示")
    print("=" * 60)
    
    # 创建测试客户端
    app = create_demo_app()
    client = TestClient(app)
    
    # 1. 健康检查
    print("\n1. 健康检查")
    print("-" * 30)
    response = client.get("/config/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    # 2. 获取完整配置
    print("\n2. 获取完整系统配置")
    print("-" * 30)
    response = client.get("/config/")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        config_data = response.json()
        print(f"成功: {config_data['success']}")
        print(f"消息: {config_data['message']}")
        print("配置节数量:", len(config_data['config']))
        for section in config_data['config']:
            if config_data['config'][section]:
                print(f"  - {section}: 已配置")
            else:
                print(f"  - {section}: 未配置")
    
    # 3. 获取特定配置节
    print("\n3. 获取数据库配置节")
    print("-" * 30)
    response = client.get("/config/database")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"成功: {data['success']}")
        print(f"数据库配置: {json.dumps(data['config'], indent=2, ensure_ascii=False)}")
    
    # 4. 配置验证 - 有效配置
    print("\n4. 验证有效的数据库配置")
    print("-" * 30)
    valid_config = {
        "section": "database",
        "config": {
            "url": "postgresql://user:pass@localhost/testdb",
            "echo": True
        }
    }
    response = client.post("/config/validate", json=valid_config)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"配置有效: {data['valid']}")
        if data['errors']:
            print(f"错误: {data['errors']}")
        if data['warnings']:
            print(f"警告: {data['warnings']}")
    
    # 5. 配置验证 - 无效配置
    print("\n5. 验证无效的数据库配置")
    print("-" * 30)
    invalid_config = {
        "section": "database",
        "config": {
            "echo": "not_boolean"  # 应该是布尔值
        }
    }
    response = client.post("/config/validate", json=invalid_config)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"配置有效: {data['valid']}")
        if data['errors']:
            print(f"错误: {json.dumps(data['errors'], indent=2, ensure_ascii=False)}")
    
    # 6. 更新配置节
    print("\n6. 更新检索配置")
    print("-" * 30)
    update_config = {
        "top_k": 10,
        "similarity_threshold": 0.85
    }
    response = client.put("/config/retrieval", json=update_config)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"更新成功: {data['success']}")
        print(f"消息: {data['message']}")
        print(f"更新后配置: {json.dumps(data['config'], indent=2, ensure_ascii=False)}")
    
    # 7. 获取配置Schema
    print("\n7. 获取嵌入配置的Schema")
    print("-" * 30)
    response = client.get("/config/schema/embeddings")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"配置节: {data['section']}")
        schema = data['schema']
        print(f"类型: {schema['type']}")
        print("属性:")
        for prop, details in schema['properties'].items():
            print(f"  - {prop}: {details.get('description', '无描述')}")
        print(f"必需字段: {schema.get('required', [])}")
    
    # 8. 重新加载配置
    print("\n8. 重新加载配置")
    print("-" * 30)
    response = client.post("/config/reload")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"重新加载成功: {data['success']}")
        print(f"消息: {data['message']}")
    
    # 9. 测试错误处理
    print("\n9. 测试错误处理 - 无效配置节")
    print("-" * 30)
    response = client.get("/config/invalid_section")
    print(f"状态码: {response.status_code}")
    if response.status_code == 400:
        data = response.json()
        print(f"错误消息: {data['detail']}")
    
    print("\n" + "=" * 60)
    print("配置管理API演示完成")
    print("=" * 60)


def demo_config_validation():
    """演示配置验证功能"""
    print("\n" + "=" * 60)
    print("配置验证功能演示")
    print("=" * 60)
    
    app = create_demo_app()
    client = TestClient(app)
    
    # 测试各种配置验证场景
    test_cases = [
        {
            "name": "LLM配置 - 温度过高",
            "config": {
                "section": "llm",
                "config": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "temperature": 3.0,  # 超出范围
                    "max_tokens": 1000
                }
            }
        },
        {
            "name": "嵌入配置 - 块大小过大",
            "config": {
                "section": "embeddings",
                "config": {
                    "provider": "openai",
                    "model": "text-embedding-ada-002",
                    "chunk_size": 10000,  # 会产生警告
                    "chunk_overlap": 200
                }
            }
        },
        {
            "name": "API配置 - 端口无效",
            "config": {
                "section": "api",
                "config": {
                    "host": "0.0.0.0",
                    "port": 70000,  # 超出端口范围
                    "cors_origins": ["http://localhost:3000"]
                }
            }
        },
        {
            "name": "向量存储配置 - 缺少必需字段",
            "config": {
                "section": "vector_store",
                "config": {
                    "persist_directory": "./chroma_db"
                    # 缺少 type 字段
                }
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)
        
        response = client.post("/config/validate", json=test_case['config'])
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"配置有效: {data['valid']}")
            
            if data['errors']:
                print("错误:")
                for field, error in data['errors'].items():
                    print(f"  - {field}: {error}")
            
            if data['warnings']:
                print("警告:")
                for field, warning in data['warnings'].items():
                    print(f"  - {field}: {warning}")
        else:
            print(f"请求失败: {response.json()}")


if __name__ == "__main__":
    try:
        demo_config_api()
        demo_config_validation()
    except Exception as e:
        print(f"演示过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()