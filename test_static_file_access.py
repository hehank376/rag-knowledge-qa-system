#!/usr/bin/env python3
"""
测试静态文件访问
"""

import requests

BASE_URL = "http://localhost:8000"

def test_static_file_access():
    """测试静态文件访问"""
    print("🔍 测试静态文件访问...")
    
    # 测试文件列表
    test_files = [
        "test_frontend_history_fix.html",
        "simple_test.html",
        "debug_frontend.html"
    ]
    
    for filename in test_files:
        try:
            # 测试 /static/ 路径
            static_url = f"{BASE_URL}/static/{filename}"
            response = requests.head(static_url)
            
            if response.status_code == 200:
                print(f"✅ {filename}: {static_url}")
            else:
                print(f"❌ {filename}: {static_url} - {response.status_code}")
                
        except Exception as e:
            print(f"❌ {filename}: 访问异常 - {str(e)}")
    
    print(f"\n🎯 正确的访问地址:")
    print(f"📄 前端历史记录测试: {BASE_URL}/static/test_frontend_history_fix.html")
    print(f"📄 简单测试页面: {BASE_URL}/static/simple_test.html")
    print(f"📄 调试前端页面: {BASE_URL}/static/debug_frontend.html")

if __name__ == "__main__":
    test_static_file_access()