#!/usr/bin/env python3
"""
QA API修复测试脚本
测试问答API的各个端点是否正常工作
"""

import requests
import json
import time

def test_qa_api():
    """测试QA API功能"""
    base_url = "http://localhost:8000"
    
    print("🧪 QA API修复测试工具")
    print("=" * 50)
    
    # 测试基本连接
    print("🔍 检查API端点可访问性...")
    
    endpoints_to_test = [
        ("/", "根端点"),
        ("/docs", "API文档"),
        ("/health", "健康检查"),
        ("/qa/health", "QA健康检查"),
        ("/sessions/health", "会话健康检查")
    ]
    
    for endpoint, name in endpoints_to_test:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"✓ {name}: {response.status_code}")
            else:
                print(f"✗ {name}: {response.status_code}")
        except Exception as e:
            print(f"✗ {name}: 连接失败 - {str(e)}")
    
    print("\n" + "=" * 50)
    print("🧪 测试QA API功能...")
    
    # 1. 测试问答接口
    print("\n1. 测试问答接口...")
    try:
        qa_data = {
            "question": "公司的考勤制度是什么？",
            "session_id": None,
            "top_k": 5
        }
        
        response = requests.post(
            f"{base_url}/qa/ask",
            json=qa_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ 问答请求成功")
            print(f"问题: {result.get('question', 'N/A')}")
            print(f"答案: {result.get('answer', 'N/A')[:100]}...")
            print(f"置信度: {result.get('confidence_score', 'N/A')}")
            print(f"处理时间: {result.get('processing_time', 'N/A')}秒")
            print(f"源文档数量: {len(result.get('sources', []))}")
        else:
            error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"✗ 问答请求失败: {error_detail}")
            
    except Exception as e:
        print(f"✗ 问答请求异常: {str(e)}")
    
    # 2. 测试会话创建
    print("\n2. 测试会话创建...")
    session_id = None
    try:
        session_data = {
            "title": "测试会话",
            "user_id": "test_user"
        }
        
        response = requests.post(
            f"{base_url}/sessions/",
            json=session_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            session_id = result.get('session_id')
            print("✓ 会话创建成功")
            print(f"会话ID: {session_id}")
            print(f"标题: {result.get('title', 'N/A')}")
            print(f"用户ID: {result.get('user_id', 'N/A')}")
        else:
            error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"✗ 会话创建失败: {error_detail}")
            
    except Exception as e:
        print(f"✗ 会话创建异常: {str(e)}")
    
    # 3. 测试带会话的问答
    if session_id:
        print("\n3. 测试带会话的问答...")
        try:
            qa_data = {
                "question": "高考志愿填报有什么建议？",
                "session_id": session_id,
                "top_k": 3
            }
            
            response = requests.post(
                f"{base_url}/qa/ask",
                json=qa_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 带会话问答成功")
                print(f"问题: {result.get('question', 'N/A')}")
                print(f"答案: {result.get('answer', 'N/A')[:100]}...")
                print(f"会话ID: {session_id}")
            else:
                error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
                print(f"✗ 带会话问答失败: {error_detail}")
                
        except Exception as e:
            print(f"✗ 带会话问答异常: {str(e)}")
        
        # 4. 测试会话历史
        print("\n4. 测试会话历史...")
        try:
            response = requests.get(
                f"{base_url}/sessions/{session_id}/history",
                timeout=10
            )
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("✓ 获取会话历史成功")
                print(f"会话ID: {result.get('session_id', 'N/A')}")
                print(f"历史记录数量: {result.get('total_count', 0)}")
                
                history = result.get('history', [])
                if history:
                    print("最近的问答记录:")
                    for i, qa in enumerate(history[:2]):  # 只显示前2条
                        print(f"  {i+1}. Q: {qa.get('question', 'N/A')[:50]}...")
                        print(f"     A: {qa.get('answer', 'N/A')[:50]}...")
            else:
                error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
                print(f"✗ 获取会话历史失败: {error_detail}")
                
        except Exception as e:
            print(f"✗ 获取会话历史异常: {str(e)}")
    
    # 5. 测试QA统计
    print("\n5. 测试QA统计...")
    try:
        response = requests.get(f"{base_url}/qa/stats", timeout=10)
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ 获取QA统计成功")
            print(f"QA服务统计: {bool(result.get('qa_service_stats'))}")
            print(f"结果处理器统计: {bool(result.get('result_processor_stats'))}")
            print(f"总处理问题数: {result.get('total_questions_processed', 0)}")
        else:
            error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"✗ 获取QA统计失败: {error_detail}")
            
    except Exception as e:
        print(f"✗ 获取QA统计异常: {str(e)}")
    
    # 6. 测试QA系统测试接口
    print("\n6. 测试QA系统测试接口...")
    try:
        response = requests.post(
            f"{base_url}/qa/test",
            params={"test_question": "测试问题：什么是深度学习？"},
            timeout=30
        )
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✓ QA系统测试成功")
            print(f"测试成功: {result.get('success', False)}")
            print(f"系统状态: {result.get('system_status', 'unknown')}")
            
            qa_test = result.get('qa_test', {})
            if qa_test:
                print(f"QA测试结果: {qa_test.get('success', False)}")
        else:
            error_detail = response.json().get('detail', '未知错误') if response.headers.get('content-type', '').startswith('application/json') else response.text
            print(f"✗ QA系统测试失败: {error_detail}")
            
    except Exception as e:
        print(f"✗ QA系统测试异常: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🎉 QA API测试完成！")
    
    print("\n📋 QA API修复总结:")
    print("1. ✓ 修复了前端API路径不匹配问题")
    print("2. ✓ 统一了API端点路径（去掉多余的/api前缀）")
    print("3. ✓ 确保QA API能正确处理问答请求")
    
    print("\n🔧 修复的具体问题:")
    print("  • 前端调用/api/qa/ask，但后端是/qa/ask")
    print("  • 前端调用/api/qa/history/{id}，但后端是/qa/session/{id}/history")
    print("  • 其他会话API路径不一致问题")
    
    print("\n🎯 现在QA API应该能够:")
    print("  • 正确处理问答请求")
    print("  • 支持会话管理")
    print("  • 保存问答历史记录")
    print("  • 返回格式化的响应")
    
    print("\n💡 如果问题仍然存在:")
    print("  1. 重新启动服务器")
    print("  2. 检查服务器日志获取详细错误信息")
    print("  3. 确保所有依赖服务正常运行")
    print("  4. 清除浏览器缓存并重新测试")

if __name__ == "__main__":
    test_qa_api()