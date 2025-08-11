#!/usr/bin/env python3
"""
测试配置API的脚本
"""
import requests
import json
import sys

def test_config_api():
    base_url = "http://localhost:8000"
    
    print("🧪 测试配置API...")
    
    # 测试获取配置
    print("\n1. 测试获取配置...")
    try:
        response = requests.get(f"{base_url}/config/")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            config = response.json()
            print("✓ 获取配置成功")
            print(f"配置内容: {json.dumps(config, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ 获取配置失败: {response.text}")
    except Exception as e:
        print(f"✗ 获取配置异常: {e}")
    
    # 测试LLM连接测试
    print("\n2. 测试LLM连接...")
    try:
        llm_config = {
            "provider": "mock",
            "model": "test-model",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        response = requests.post(f"{base_url}/config/test/llm", json=llm_config)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✓ LLM连接测试成功")
            print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ LLM连接测试失败: {response.text}")
    except Exception as e:
        print(f"✗ LLM连接测试异常: {e}")
    
    # 测试嵌入模型连接测试
    print("\n3. 测试嵌入模型连接...")
    try:
        embedding_config = {
            "provider": "mock",
            "model": "test-embedding",
            "chunk_size": 1000,
            "chunk_overlap": 200
        }
        response = requests.post(f"{base_url}/config/test/embedding", json=embedding_config)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✓ 嵌入模型连接测试成功")
            print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ 嵌入模型连接测试失败: {response.text}")
    except Exception as e:
        print(f"✗ 嵌入模型连接测试异常: {e}")
    
    # 测试存储连接测试
    print("\n4. 测试存储连接...")
    try:
        storage_config = {
            "type": "chroma",
            "persist_directory": "./data/chroma",
            "collection_name": "test_collection"
        }
        response = requests.post(f"{base_url}/config/test/storage", json=storage_config)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✓ 存储连接测试成功")
            print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ 存储连接测试失败: {response.text}")
    except Exception as e:
        print(f"✗ 存储连接测试异常: {e}")
    
    # 测试配置更新
    print("\n5. 测试配置更新...")
    try:
        update_config = {
            "llm": {
                "provider": "mock",
                "model": "updated-model",
                "temperature": 0.8,
                "max_tokens": 1500
            },
            "embeddings": {
                "provider": "mock",
                "model": "updated-embedding",
                "chunk_size": 1200,
                "chunk_overlap": 250
            }
        }
        response = requests.put(f"{base_url}/config/all", json=update_config)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✓ 配置更新成功")
            print(f"更新结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ 配置更新失败: {response.text}")
    except Exception as e:
        print(f"✗ 配置更新异常: {e}")
    
    print("\n🎉 配置API测试完成!")

if __name__ == "__main__":
    test_config_api()