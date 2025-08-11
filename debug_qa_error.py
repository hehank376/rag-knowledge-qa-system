#!/usr/bin/env python3
"""
调试QA API错误
"""
import requests
import json


def debug_qa_error():
    """调试QA API错误"""
    print("🐛 调试QA API错误...")
    
    try:
        # 1. 测试最简单的请求
        print("\n1. 测试最简单的请求...")
        simple_request = {
            "question": "测试问题"
        }
        
        response = requests.post(
            "http://localhost:8000/qa/ask",
            json=simple_request,
            timeout=300
        )
        
        print(f"   状态码: {response.status_code}")
        print(f"   响应头: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"   错误响应: {response.text}")
            
            # 尝试解析JSON错误信息
            try:
                error_data = response.json()
                print(f"   错误详情: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
            except:
                print("   无法解析JSON错误信息")
        else:
            result = response.json()
            print(f"   ✅ 简单请求成功")
            print(f"   会话ID: {result.get('session_id', 'N/A')}")
        
        # 2. 测试带完整参数的请求
        print("\n2. 测试带完整参数的请求...")
        full_request = {
            "question": "什么是人工智能？",
            "session_id": None,
            "user_id": "debug_user",
            "top_k": 5,
            "temperature": 0.1,
            "max_tokens": 500
        }
        
        response2 = requests.post(
            "http://localhost:8000/qa/ask",
            json=full_request,
            timeout=300
        )
        
        print(f"   状态码: {response2.status_code}")
        
        if response2.status_code != 200:
            print(f"   错误响应: {response2.text}")
        else:
            result2 = response2.json()
            print(f"   ✅ 完整请求成功")
            print(f"   会话ID: {result2.get('session_id', 'N/A')}")
        
        # 3. 测试健康检查
        print("\n3. 测试健康检查...")
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"   健康检查状态: {health_response.status_code}")
        
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"   健康状态: {health_data}")
        
        # 4. 测试其他API端点
        print("\n4. 测试其他API端点...")
        
        # 测试文档API
        docs_response = requests.get("http://localhost:8000/documents/", timeout=5)
        print(f"   文档API状态: {docs_response.status_code}")
        
        # 测试会话API
        sessions_response = requests.get("http://localhost:8000/sessions/stats/summary", timeout=5)
        print(f"   会话API状态: {sessions_response.status_code}")
        
        print("\n✅ 调试完成")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确保服务器正在运行")
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")


if __name__ == "__main__":
    debug_qa_error()