#!/usr/bin/env python3
"""
测试设置保存修复效果
"""

import requests
import json

def test_config_validation():
    """测试配置验证"""
    print("🔍 测试配置验证...")
    
    base_url = "http://localhost:8000"
    
    # 测试单个配置节验证
    llm_config = {
        "provider": "siliconflow",
        "model": "Qwen/Qwen2-7B-Instruct",
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/validate",
            json={"section": "llm", "config": llm_config},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ LLM配置验证成功: {result}")
        else:
            print(f"❌ LLM配置验证失败: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ LLM配置验证异常: {e}")
    
    # 测试全量配置验证
    all_config = {
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
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/validate",
            json={"section": "all", "config": all_config},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 全量配置验证成功: {result}")
            return True
        else:
            print(f"❌ 全量配置验证失败: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 全量配置验证异常: {e}")
        return False

def test_config_save():
    """测试配置保存"""
    print("\n🔍 测试配置保存...")
    
    base_url = "http://localhost:8000"
    
    # 测试保存LLM配置
    llm_config = {
        "provider": "siliconflow",
        "model": "Qwen/Qwen2-7B-Instruct",
        "temperature": 0.8,
        "max_tokens": 1800,
        "api_key": "test-key-save-fix"
    }
    
    try:
        response = requests.put(
            f"{base_url}/config/llm",
            json=llm_config,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ LLM配置保存成功: {result.get('message')}")
            return True
        else:
            print(f"❌ LLM配置保存失败: {response.status_code}")
            print(f"   错误详情: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ LLM配置保存异常: {e}")
        return False

def test_error_handling():
    """测试错误处理"""
    print("\n🔍 测试错误处理...")
    
    base_url = "http://localhost:8000"
    
    # 测试无效配置
    invalid_config = {
        "provider": "invalid_provider",  # 无效的提供商
        "model": "",  # 空模型名
        "temperature": 5.0,  # 超出范围的温度
        "max_tokens": -100  # 无效的令牌数
    }
    
    try:
        response = requests.post(
            f"{base_url}/config/validate",
            json={"section": "llm", "config": invalid_config},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if not result.get('valid'):
                print(f"✅ 错误处理正常，检测到配置错误:")
                if result.get('errors'):
                    for field, error in result['errors'].items():
                        print(f"   {field}: {error}")
                return True
            else:
                print("❌ 错误处理失败，应该检测到配置错误")
                return False
        else:
            print(f"❌ 错误处理测试失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 错误处理测试异常: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始测试设置保存修复效果...")
    
    # 运行测试
    validation_ok = test_config_validation()
    save_ok = test_config_save()
    error_handling_ok = test_error_handling()
    
    print(f"\n📊 测试结果:")
    print(f"  配置验证: {'✅ 通过' if validation_ok else '❌ 失败'}")
    print(f"  配置保存: {'✅ 通过' if save_ok else '❌ 失败'}")
    print(f"  错误处理: {'✅ 通过' if error_handling_ok else '❌ 失败'}")
    
    if all([validation_ok, save_ok, error_handling_ok]):
        print(f"\n🎉 所有测试通过！设置保存功能已修复")
    else:
        print(f"\n⚠️  部分测试失败，需要进一步调试")