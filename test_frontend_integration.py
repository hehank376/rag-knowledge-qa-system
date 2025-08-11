#!/usr/bin/env python3
"""
前端集成测试 - 模拟用户在设置页面的操作
"""

import requests
import json
import time

def test_frontend_settings_flow():
    """测试前端设置页面的完整流程"""
    print("🌐 测试前端设置页面集成...")
    
    base_url = "http://localhost:8000"
    
    # 1. 获取当前配置
    print("\n📋 1. 获取当前配置...")
    try:
        response = requests.get(f"{base_url}/config")
        if response.status_code == 200:
            current_config = response.json()
            print("✅ 成功获取当前配置")
            print(f"   当前检索配置: {current_config.get('retrieval', {})}")
        else:
            print(f"❌ 获取配置失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 获取配置异常: {e}")
        return False
    
    # 2. 模拟前端表单数据
    print("\n📝 2. 模拟前端表单提交...")
    frontend_form_data = {
        "app": {
            "name": "RAG Knowledge QA System (Test)",
            "debug": True
        },
        "llm": {
            "provider": "siliconflow",
            "model": "Qwen/Qwen2-7B-Instruct",
            "temperature": 0.7,
            "max_tokens": 2000,
            "api_key": "sk-test-key"
        },
        "embeddings": {
            "provider": "siliconflow", 
            "model": "BAAI/bge-large-zh-v1.5",
            "chunk_size": 400,
            "chunk_overlap": 50,
            "api_key": "sk-test-key"
        },
        "retrieval": {
            "top_k": 8,
            "similarity_threshold": 0.75,
            "search_mode": "hybrid",  # 测试新字段
            "enable_rerank": True,
            "enable_cache": False
        },
        "api": {
            "host": "0.0.0.0",
            "port": 8000,
            "cors_origins": ["http://localhost:3000"]
        }
    }
    
    # 3. 验证配置
    print("\n🔍 3. 验证配置...")
    try:
        response = requests.post(
            f"{base_url}/config/validate",
            json={"section": "all", "config": frontend_form_data},
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('valid'):
                print("✅ 配置验证通过")
            else:
                print(f"❌ 配置验证失败: {result.get('errors')}")
                return False
        else:
            print(f"❌ 验证请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 验证异常: {e}")
        return False
    
    # 4. 保存配置
    print("\n💾 4. 保存配置...")
    try:
        response = requests.put(
            f"{base_url}/config/all",
            json=frontend_form_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 配置保存成功: {result.get('message')}")
        else:
            print(f"❌ 配置保存失败: {response.status_code}")
            print(f"   错误详情: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 保存异常: {e}")
        return False
    
    # 5. 验证保存结果
    print("\n🔍 5. 验证保存结果...")
    try:
        response = requests.get(f"{base_url}/config")
        if response.status_code == 200:
            saved_config = response.json()
            retrieval_config = saved_config.get('retrieval', {})
            
            # 检查关键字段
            if retrieval_config.get('search_mode') == 'hybrid':
                print("✅ search_mode字段保存正确")
            else:
                print(f"❌ search_mode字段保存错误: {retrieval_config.get('search_mode')}")
                return False
                
            if retrieval_config.get('top_k') == 8:
                print("✅ top_k字段保存正确")
            else:
                print(f"❌ top_k字段保存错误: {retrieval_config.get('top_k')}")
                return False
                
            print("✅ 所有字段保存验证通过")
            return True
        else:
            print(f"❌ 获取保存后配置失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 验证保存结果异常: {e}")
        return False

def test_search_mode_options():
    """测试所有搜索模式选项"""
    print("\n🔍 测试所有搜索模式选项...")
    
    base_url = "http://localhost:8000"
    search_modes = ["semantic", "keyword", "hybrid"]
    
    for mode in search_modes:
        print(f"\n   测试搜索模式: {mode}")
        
        test_config = {
            "top_k": 5,
            "similarity_threshold": 0.7,
            "search_mode": mode,
            "enable_rerank": True,
            "enable_cache": True
        }
        
        try:
            # 验证配置
            response = requests.post(
                f"{base_url}/config/validate",
                json={"section": "retrieval", "config": test_config},
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('valid'):
                    print(f"   ✅ {mode}模式验证通过")
                else:
                    print(f"   ❌ {mode}模式验证失败: {result.get('errors')}")
                    return False
            else:
                print(f"   ❌ {mode}模式验证请求失败: {response.status_code}")
                return False
                
            # 保存配置
            response = requests.put(
                f"{base_url}/config/retrieval",
                json=test_config,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                print(f"   ✅ {mode}模式保存成功")
            else:
                print(f"   ❌ {mode}模式保存失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ {mode}模式测试异常: {e}")
            return False
    
    print("✅ 所有搜索模式测试通过")
    return True

def test_error_handling():
    """测试错误处理"""
    print("\n⚠️  测试错误处理...")
    
    base_url = "http://localhost:8000"
    
    # 测试无效的搜索模式
    invalid_configs = [
        {
            "name": "无效搜索模式",
            "config": {
                "top_k": 5,
                "similarity_threshold": 0.7,
                "search_mode": "invalid_mode",
                "enable_rerank": True,
                "enable_cache": True
            },
            "expected_error": "search_mode"
        },
        {
            "name": "top_k超出范围",
            "config": {
                "top_k": 100,
                "similarity_threshold": 0.7,
                "search_mode": "semantic",
                "enable_rerank": True,
                "enable_cache": True
            },
            "expected_error": "top_k"
        },
        {
            "name": "similarity_threshold超出范围",
            "config": {
                "top_k": 5,
                "similarity_threshold": 1.5,
                "search_mode": "semantic",
                "enable_rerank": True,
                "enable_cache": True
            },
            "expected_error": "similarity_threshold"
        }
    ]
    
    for test_case in invalid_configs:
        print(f"\n   测试: {test_case['name']}")
        
        try:
            response = requests.post(
                f"{base_url}/config/validate",
                json={"section": "retrieval", "config": test_case['config']},
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                if not result.get('valid') and test_case['expected_error'] in str(result.get('errors', {})):
                    print(f"   ✅ 正确检测到{test_case['expected_error']}错误")
                else:
                    print(f"   ❌ 未能正确检测错误: {result}")
                    return False
            else:
                print(f"   ❌ 验证请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ 错误处理测试异常: {e}")
            return False
    
    print("✅ 错误处理测试通过")
    return True

if __name__ == "__main__":
    print("🚀 开始前端集成测试...")
    
    # 运行所有测试
    frontend_flow_ok = test_frontend_settings_flow()
    search_modes_ok = test_search_mode_options()
    error_handling_ok = test_error_handling()
    
    print(f"\n📊 测试结果总结:")
    print(f"  前端设置流程: {'✅ 通过' if frontend_flow_ok else '❌ 失败'}")
    print(f"  搜索模式选项: {'✅ 通过' if search_modes_ok else '❌ 失败'}")
    print(f"  错误处理: {'✅ 通过' if error_handling_ok else '❌ 失败'}")
    
    if all([frontend_flow_ok, search_modes_ok, error_handling_ok]):
        print(f"\n🎉 所有集成测试通过！")
        print(f"💡 前端设置页面现在可以完全正常工作")
        print(f"🔧 用户可以:")
        print(f"   - 选择任意搜索模式 (semantic/keyword/hybrid)")
        print(f"   - 保存完整的检索配置")
        print(f"   - 获得准确的错误提示")
        print(f"   - 验证配置的有效性")
    else:
        print(f"\n⚠️  部分测试失败，需要进一步调试")