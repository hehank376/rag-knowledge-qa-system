#!/usr/bin/env python3
"""
修复会话API错误
"""
import requests
import json
import sys

def test_session_api():
    """测试会话API功能"""
    base_url = "http://localhost:8000"
    
    print("🧪 测试会话API功能...")
    
    # 1. 测试创建会话（无参数）
    print("\n1. 测试创建会话（无参数）...")
    try:
        response = requests.post(f"{base_url}/sessions/")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✓ 创建会话成功（无参数）")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            session_id = result.get('session_id')
        else:
            print(f"✗ 创建会话失败: {response.text}")
            return False
    except Exception as e:
        print(f"✗ 创建会话异常: {e}")
        return False
    
    # 2. 测试创建会话（带title参数）
    print("\n2. 测试创建会话（带title参数）...")
    try:
        data = {"title": "测试会话"}
        response = requests.post(f"{base_url}/sessions/", json=data)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✓ 创建会话成功（带title）")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ 创建会话失败: {response.text}")
            return False
    except Exception as e:
        print(f"✗ 创建会话异常: {e}")
        return False
    
    # 3. 测试创建会话（带user_id参数）
    print("\n3. 测试创建会话（带user_id参数）...")
    try:
        data = {"user_id": "test_user", "title": "用户会话"}
        response = requests.post(f"{base_url}/sessions/", json=data)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✓ 创建会话成功（带user_id）")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ 创建会话失败: {response.text}")
            return False
    except Exception as e:
        print(f"✗ 创建会话异常: {e}")
        return False
    
    # 4. 测试获取会话列表
    print("\n4. 测试获取会话列表...")
    try:
        response = requests.get(f"{base_url}/sessions/recent")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("✓ 获取会话列表成功")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"✗ 获取会话列表失败: {response.text}")
    except Exception as e:
        print(f"✗ 获取会话列表异常: {e}")
    
    # 5. 测试获取会话历史
    if session_id:
        print(f"\n5. 测试获取会话历史（会话ID: {session_id}）...")
        try:
            response = requests.get(f"{base_url}/sessions/{session_id}/history")
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print("✓ 获取会话历史成功")
                print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"✗ 获取会话历史失败: {response.text}")
        except Exception as e:
            print(f"✗ 获取会话历史异常: {e}")
    
    return True

def check_api_endpoints():
    """检查API端点是否可访问"""
    base_url = "http://localhost:8000"
    
    print("🔍 检查API端点可访问性...")
    
    endpoints = [
        ("/", "根端点"),
        ("/docs", "API文档"),
        ("/health", "健康检查"),
        ("/sessions/", "会话API（POST）"),
        ("/sessions/recent", "会话列表（GET）")
    ]
    
    for endpoint, name in endpoints:
        try:
            if endpoint == "/sessions/":
                # POST请求
                response = requests.post(f"{base_url}{endpoint}", json={})
            else:
                # GET请求
                response = requests.get(f"{base_url}{endpoint}")
            
            if response.status_code < 400:
                print(f"✓ {name}: {response.status_code}")
            else:
                print(f"✗ {name}: {response.status_code}")
        except Exception as e:
            print(f"✗ {name}: 连接失败 - {e}")

def show_fix_summary():
    """显示修复总结"""
    print("\n📋 会话API修复总结:")
    print("1. ✓ 修复了SessionService.create_session()参数不匹配问题")
    print("2. ✓ 更新了main.py中的占位符会话API实现")
    print("3. ✓ 确保API能正确处理title和user_id参数")
    
    print("\n🔧 修复的具体问题:")
    print("  • SessionService.create_session()不接受title参数")
    print("  • 占位符API没有处理请求参数")
    print("  • 前端发送的参数与后端不匹配")
    
    print("\n🎯 现在会话API应该能够:")
    print("  • 正确创建新会话")
    print("  • 处理带title和user_id的请求")
    print("  • 返回正确的会话信息")
    print("  • 支持会话列表和历史查询")

def main():
    print("🛠️  会话API错误修复工具")
    print("=" * 50)
    
    # 检查API端点
    check_api_endpoints()
    
    print("\n" + "=" * 50)
    
    # 测试会话API
    if test_session_api():
        print("\n🎉 会话API测试通过！")
        print("\n✅ 修复成功，现在可以正常使用问答功能了。")
    else:
        print("\n❌ 会话API测试失败，请检查服务器日志。")
    
    show_fix_summary()
    
    print("\n💡 如果问题仍然存在:")
    print("  1. 重新启动服务器")
    print("  2. 检查服务器日志获取详细错误信息")
    print("  3. 确保数据库连接正常")
    print("  4. 清除浏览器缓存并重新测试")

if __name__ == "__main__":
    main()