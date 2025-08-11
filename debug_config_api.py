#!/usr/bin/env python3
"""
调试配置API问题
"""

import requests
import json
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config_api():
    """测试配置API"""
    base_url = "http://localhost:8000"
    
    print("🔍 测试配置API...")
    
    # 1. 测试获取配置
    print("\n1. 测试获取配置 GET /config/")
    try:
        response = requests.get(f"{base_url}/config/")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            config_data = response.json()
            print("✅ 配置获取成功:")
            print(json.dumps(config_data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 配置获取失败: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 2. 测试获取LLM配置节
    print("\n2. 测试获取LLM配置节 GET /config/llm")
    try:
        response = requests.get(f"{base_url}/config/llm")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            llm_config = response.json()
            print("✅ LLM配置获取成功:")
            print(json.dumps(llm_config, indent=2, ensure_ascii=False))
        else:
            print(f"❌ LLM配置获取失败: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 3. 测试获取嵌入配置节
    print("\n3. 测试获取嵌入配置节 GET /config/embeddings")
    try:
        response = requests.get(f"{base_url}/config/embeddings")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            embedding_config = response.json()
            print("✅ 嵌入配置获取成功:")
            print(json.dumps(embedding_config, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 嵌入配置获取失败: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")
    
    # 4. 测试健康检查
    print("\n4. 测试健康检查 GET /config/health")
    try:
        response = requests.get(f"{base_url}/config/health")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print("✅ 健康检查成功:")
            print(json.dumps(health_data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 健康检查失败: {response.text}")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_config_loading():
    """测试配置加载"""
    print("\n🔍 测试配置加载...")
    
    try:
        from rag_system.config.loader import ConfigLoader
        
        loader = ConfigLoader()
        print(f"配置文件路径: {loader.config_path}")
        
        config = loader.load_config()
        print("✅ 配置加载成功:")
        print(f"应用名称: {config.name}")
        print(f"版本: {config.version}")
        print(f"调试模式: {config.debug}")
        
        if config.llm:
            print(f"LLM提供商: {config.llm.provider}")
            print(f"LLM模型: {config.llm.model}")
            print(f"LLM温度: {config.llm.temperature}")
        
        if config.embeddings:
            print(f"嵌入提供商: {config.embeddings.provider}")
            print(f"嵌入模型: {config.embeddings.model}")
            print(f"块大小: {config.embeddings.chunk_size}")
        
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        import traceback
        traceback.print_exc()

def test_frontend_api():
    """测试前端API调用"""
    print("\n🔍 测试前端API调用...")
    
    # 模拟前端API调用
    base_url = "http://localhost:8000"
    
    # 前端使用的路径
    frontend_paths = [
        "/config/",
        "/api/config/",
        "/config/llm",
        "/api/config/llm",
        "/config/embeddings",
        "/api/config/embeddings"
    ]
    
    for path in frontend_paths:
        print(f"\n测试路径: {path}")
        try:
            response = requests.get(f"{base_url}{path}")
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                print("✅ 成功")
            else:
                print(f"❌ 失败: {response.text}")
        except Exception as e:
            print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    print("🚀 开始调试配置API...")
    
    # 测试配置加载
    test_config_loading()
    
    # 测试API端点
    test_config_api()
    
    # 测试前端API路径
    test_frontend_api()
    
    print("\n🏁 调试完成!")