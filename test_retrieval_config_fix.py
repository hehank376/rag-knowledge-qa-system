#!/usr/bin/env python3
"""
测试检索配置修复
"""

import requests
import json

def test_retrieval_config():
    """测试检索配置"""
    print("🔍 测试检索配置...")
    
    base_url = "http://localhost:8000"
    
    # 测试包含新字段的检索配置
    retrieval_config = {
        "top_k": 5,
        "similarity_threshold": 0.7,
        "search_mode": "semantic",
        "enable_rerank": True,
        "enable_cache": False
    }
    
    try:
        # 验证配置
        response = requests.post(
            f"{base_url}/config/validate",
            json={"section": "retrieval", "config": retrieval_config},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 检索配置验证成功: {result}")
        else:
            print(f"❌ 检索配置验证失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 检索配置验证异常: {e}")
        return False
    
    # 测试保存配置
    try:
        response = requests.put(
            f"{base_url}/config/retrieval",
            json=retrieval_config,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 检索配置保存成功: {result.get('message')}")
            return True
        else:
            print(f"❌ 检索配置保存失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 检索配置保存异常: {e}")
        return False

def test_full_config_with_retrieval():
    """测试包含检索配置的完整配置"""
    print("\n🔍 测试完整配置...")
    
    base_url = "http://localhost:8000"
    
    # 完整配置，包含检索配置
    full_config = {
        "app": {
            "name": "RAG Knowledge QA System (Dev)",
            "debug": True
        },
        "llm": {
            "provider": "siliconflow",
            "model": "Qwen/Qwen2-7B-Instruct",
            "temperature": 0.7,
            "max_tokens": 2000
        },
        "embeddings": {
            "provider": "siliconflow",
            "model": "BAAI/bge-large-zh-v1.5",
            "chunk_size": 400,
            "chunk_overlap": 50
        },
        "retrieval": {
            "top_k": 5,
            "similarity_threshold": 0.7,
            "search_mode": "semantic",
            "enable_rerank": True,
            "enable_cache": False
        }
    }
    
    try:
        # 验证完整配置
        response = requests.post(
            f"{base_url}/config/validate",
            json={"section": "all", "config": full_config},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('valid'):
                print(f"✅ 完整配置验证成功")
            else:
                print(f"❌ 完整配置验证失败: {result.get('errors')}")
                return False
        else:
            print(f"❌ 完整配置验证失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 完整配置验证异常: {e}")
        return False
    
    # 测试保存完整配置
    try:
        response = requests.put(
            f"{base_url}/config/all",
            json=full_config,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 完整配置保存成功: {result.get('message')}")
            return True
        else:
            print(f"❌ 完整配置保存失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 完整配置保存异常: {e}")
        return False

def test_invalid_retrieval_config():
    """测试无效的检索配置"""
    print("\n🔍 测试无效检索配置...")
    
    base_url = "http://localhost:8000"
    
    # 无效的检索配置
    invalid_config = {
        "top_k": -1,  # 无效值
        "similarity_threshold": 2.0,  # 超出范围
        "search_mode": "invalid_mode",  # 无效模式
        "enable_rerank": "not_boolean",  # 非布尔值
        "enable_cache": "also_not_boolean"  # 非布尔值
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/validate",
            json={"section": "retrieval", "config": invalid_config},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if not result.get('valid'):
                print(f"✅ 正确检测到配置错误:")
                if result.get('errors'):
                    for field, error in result['errors'].items():
                        print(f"   {field}: {error}")
                return True
            else:
                print(f"❌ 应该检测到配置错误")
                return False
        else:
            print(f"❌ 验证请求失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 验证异常: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试检索配置修复...")
    
    # 运行测试
    retrieval_ok = test_retrieval_config()
    full_config_ok = test_full_config_with_retrieval()
    invalid_config_ok = test_invalid_retrieval_config()
    
    print(f"\n📊 测试结果:")
    print(f"  检索配置: {'✅ 通过' if retrieval_ok else '❌ 失败'}")
    print(f"  完整配置: {'✅ 通过' if full_config_ok else '❌ 失败'}")
    print(f"  错误检测: {'✅ 通过' if invalid_config_ok else '❌ 失败'}")
    
    if all([retrieval_ok, full_config_ok, invalid_config_ok]):
        print(f"\n🎉 所有测试通过！检索配置问题已修复")
        print(f"💡 现在可以在设置页面正常保存包含检索配置的设置了")
    else:
        print(f"\n⚠️  部分测试失败，需要进一步调试")