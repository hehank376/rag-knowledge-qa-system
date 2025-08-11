#!/usr/bin/env python3
"""
测试API端点是否可访问
"""
import requests
import json

def test_endpoints():
    base_url = "http://localhost:8000"
    
    print("🔍 测试API端点可访问性...")
    
    # 测试根端点
    print("\n1. 测试根端点...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"GET / - 状态码: {response.status_code}")
        if response.status_code == 200:
            print("✓ 根端点可访问")
        else:
            print(f"✗ 根端点失败: {response.text}")
    except Exception as e:
        print(f"✗ 根端点异常: {e}")
    
    # 测试API文档
    print("\n2. 测试API文档...")
    try:
        response = requests.get(f"{base_url}/docs")
        print(f"GET /docs - 状态码: {response.status_code}")
        if response.status_code == 200:
            print("✓ API文档可访问")
        else:
            print(f"✗ API文档失败: {response.text}")
    except Exception as e:
        print(f"✗ API文档异常: {e}")
    
    # 测试配置端点
    print("\n3. 测试配置端点...")
    try:
        response = requests.get(f"{base_url}/config/")
        print(f"GET /config/ - 状态码: {response.status_code}")
        if response.status_code == 200:
            print("✓ 配置端点可访问")
        else:
            print(f"✗ 配置端点失败: {response.text}")
    except Exception as e:
        print(f"✗ 配置端点异常: {e}")
    
    # 测试连接测试端点（OPTIONS请求）
    print("\n4. 测试连接测试端点OPTIONS...")
    try:
        response = requests.options(f"{base_url}/config/test/llm")
        print(f"OPTIONS /config/test/llm - 状态码: {response.status_code}")
        print(f"允许的方法: {response.headers.get('Allow', 'N/A')}")
    except Exception as e:
        print(f"✗ OPTIONS请求异常: {e}")
    
    # 测试连接测试端点（POST请求）
    print("\n5. 测试LLM连接测试端点...")
    try:
        test_data = {"provider": "mock", "model": "test"}
        response = requests.post(f"{base_url}/config/test/llm", json=test_data)
        print(f"POST /config/test/llm - 状态码: {response.status_code}")
        if response.status_code == 200:
            print("✓ LLM连接测试端点可访问")
            result = response.json()
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ LLM连接测试失败: {response.text}")
    except Exception as e:
        print(f"✗ LLM连接测试异常: {e}")
    
    print("\n🎉 端点测试完成!")

if __name__ == "__main__":
    test_endpoints()