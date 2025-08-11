#!/usr/bin/env python3
"""
RAG Knowledge QA System API Test Script
测试后台API是否正常运行
"""

import requests
import json
import sys
from datetime import datetime

# API基础配置
API_BASE_URL = "http://localhost:8000"

def test_api_endpoint(endpoint, method="GET", data=None, description=""):
    """测试API端点"""
    url = f"{API_BASE_URL}{endpoint}"
    
    print(f"\n🧪 测试: {description or endpoint}")
    print(f"📡 请求: {method} {url}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            print(f"❌ 不支持的HTTP方法: {method}")
            return False
        
        print(f"📊 状态码: {response.status_code}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ 成功: {json.dumps(result, indent=2, ensure_ascii=False)[:200]}...")
                return True
            except json.JSONDecodeError:
                print(f"✅ 成功: {response.text[:200]}...")
                return True
        else:
            try:
                error_data = response.json()
                print(f"❌ 失败: {error_data}")
            except json.JSONDecodeError:
                print(f"❌ 失败: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ 连接错误: 无法连接到API服务器")
        print("💡 请确保后台API服务正在运行 (python -m uvicorn rag_system.api.main:app --reload)")
        return False
    except requests.exceptions.Timeout:
        print("❌ 超时错误: 请求超时")
        return False
    except Exception as e:
        print(f"❌ 未知错误: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("🚀 RAG知识问答系统 API测试")
    print("=" * 50)
    print(f"🕒 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API地址: {API_BASE_URL}")
    
    # 测试用例列表
    test_cases = [
        {
            "endpoint": "/",
            "method": "GET",
            "description": "根端点 - 系统信息"
        },
        {
            "endpoint": "/health",
            "method": "GET", 
            "description": "健康检查"
        },
        {
            "endpoint": "/docs",
            "method": "GET",
            "description": "API文档"
        },
        {
            "endpoint": "/api/documents/",
            "method": "GET",
            "description": "获取文档列表"
        },
        {
            "endpoint": "/api/documents/stats",
            "method": "GET",
            "description": "获取文档统计"
        },
        {
            "endpoint": "/api/sessions/",
            "method": "GET",
            "description": "获取会话列表"
        },
        {
            "endpoint": "/api/sessions/",
            "method": "POST",
            "data": {"title": "测试会话"},
            "description": "创建新会话"
        },
        {
            "endpoint": "/api/qa/ask",
            "method": "POST",
            "data": {
                "question": "这是一个测试问题，请回答。",
                "session_id": None
            },
            "description": "测试问答功能"
        },
        {
            "endpoint": "/api/config/",
            "method": "GET",
            "description": "获取系统配置"
        },
        {
            "endpoint": "/api/monitoring/health",
            "method": "GET",
            "description": "获取监控健康状态"
        }
    ]
    
    # 执行测试
    passed_tests = 0
    total_tests = len(test_cases)
    
    for test_case in test_cases:
        success = test_api_endpoint(
            endpoint=test_case["endpoint"],
            method=test_case["method"],
            data=test_case.get("data"),
            description=test_case["description"]
        )
        
        if success:
            passed_tests += 1
    
    # 测试结果汇总
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    print(f"✅ 通过测试: {passed_tests}/{total_tests}")
    print(f"❌ 失败测试: {total_tests - passed_tests}/{total_tests}")
    print(f"📈 成功率: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 所有测试通过！API服务运行正常。")
        return 0
    elif passed_tests > 0:
        print(f"\n⚠️ 部分测试通过。请检查失败的API端点。")
        return 1
    else:
        print(f"\n💔 所有测试失败。请检查API服务是否正在运行。")
        return 2

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 测试脚本出现错误: {str(e)}")
        sys.exit(1)