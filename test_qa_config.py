#!/usr/bin/env python3
"""
测试QA API配置
"""

import requests

def test_qa_config():
    """测试QA配置"""
    print("🔍 测试QA API配置")
    print("=" * 30)
    
    try:
        # 测试QA健康检查
        response = requests.get("http://localhost:8000/qa/health", timeout=10)
        
        if response.status_code == 200:
            print("✓ QA API健康检查通过")
        else:
            print(f"✗ QA API健康检查失败: {response.status_code}")
        
        # 测试QA统计信息
        response = requests.get("http://localhost:8000/qa/stats", timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            print("✓ QA统计信息获取成功")
            print(f"  QA服务统计: {bool(stats.get('qa_service_stats'))}")
            print(f"  结果处理器统计: {bool(stats.get('result_processor_stats'))}")
        else:
            print(f"✗ QA统计信息获取失败: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                error = response.json()
                print(f"  错误详情: {error.get('detail', '未知错误')}")
        
        # 测试QA系统测试接口
        response = requests.post(
            "http://localhost:8000/qa/test",
            params={"test_question": "测试问题"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✓ QA系统测试成功")
            print(f"  测试成功: {result.get('success', False)}")
            print(f"  系统状态: {result.get('system_status', 'unknown')}")
        else:
            print(f"✗ QA系统测试失败: {response.status_code}")
            if response.headers.get('content-type', '').startswith('application/json'):
                error = response.json()
                print(f"  错误详情: {error.get('detail', '未知错误')}")
        
    except Exception as e:
        print(f"✗ 测试异常: {str(e)}")

if __name__ == "__main__":
    test_qa_config()