#!/usr/bin/env python3
"""
测试API路由注册情况
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from rag_system.api.main import app

def test_api_routes():
    """测试API路由"""
    client = TestClient(app)
    
    print("🧪 测试API路由注册情况")
    print("=" * 50)
    
    # 测试基本路由
    routes_to_test = [
        ("GET", "/", "根路径"),
        ("GET", "/health", "健康检查"),
        ("GET", "/config/", "配置获取"),
        ("GET", "/config/health", "配置健康检查"),
        ("GET", "/config/models/status", "模型状态"),
        ("GET", "/config/models/metrics", "模型指标"),
        ("POST", "/config/models/switch-active", "模型切换"),
        ("POST", "/config/models/add-model", "添加模型"),
        ("POST", "/config/models/test-model", "测试模型"),
        ("POST", "/config/models/health-check", "模型健康检查"),
        ("POST", "/config/models/update-config", "更新模型配置")
    ]
    
    results = []
    
    for method, path, description in routes_to_test:
        try:
            if method == "GET":
                response = client.get(path)
            else:
                # 对于POST请求，发送空的JSON数据
                response = client.post(path, json={})
            
            # 检查是否返回501 (Not Implemented)
            if response.status_code == 501:
                status = "❌ 501 - 方法不支持"
                success = False
            elif response.status_code == 404:
                status = "❌ 404 - 路由不存在"
                success = False
            elif response.status_code in [200, 400, 422]:  # 200=成功, 400/422=请求错误但路由存在
                status = f"✅ {response.status_code} - 路由存在"
                success = True
            else:
                status = f"⚠️ {response.status_code} - 其他状态"
                success = True
            
            results.append((description, success, status))
            print(f"{status} {method} {path} - {description}")
            
        except Exception as e:
            results.append((description, False, f"异常: {str(e)}"))
            print(f"❌ 异常 {method} {path} - {description}: {str(e)}")
    
    # 统计结果
    print("\n" + "=" * 50)
    print("📊 测试结果统计")
    print("=" * 50)
    
    total_tests = len(results)
    successful_tests = sum(1 for _, success, _ in results if success)
    failed_tests = total_tests - successful_tests
    
    print(f"总测试数: {total_tests}")
    print(f"成功: {successful_tests}")
    print(f"失败: {failed_tests}")
    print(f"成功率: {successful_tests/total_tests*100:.1f}%")
    
    # 显示失败的测试
    if failed_tests > 0:
        print(f"\n❌ 失败的测试:")
        for description, success, status in results:
            if not success:
                print(f"  - {description}: {status}")
    
    return successful_tests == total_tests


def list_all_routes():
    """列出所有注册的路由"""
    print("\n🗺️ 所有注册的路由")
    print("=" * 50)
    
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(route.methods)
            print(f"{methods:10} {route.path}")
        elif hasattr(route, 'path'):
            print(f"{'MOUNT':10} {route.path}")


if __name__ == "__main__":
    print("🚀 API路由测试")
    print(f"测试时间: {Path(__file__).stat().st_mtime}")
    
    # 列出所有路由
    list_all_routes()
    
    # 测试路由
    success = test_api_routes()
    
    if success:
        print("\n🎉 所有API路由测试通过！")
    else:
        print("\n⚠️ 部分API路由测试失败，请检查路由注册。")
    
    print("\n💡 如果看到501错误，说明路由没有正确注册到FastAPI应用中。")
    print("请检查main.py中的路由器导入和注册。")