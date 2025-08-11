#!/usr/bin/env python3
"""
测试前端主页面功能
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_frontend_main_page():
    """测试前端主页面功能"""
    print("🔍 测试前端主页面功能...")
    
    # 1. 测试页面访问
    print("\n1. 测试页面访问...")
    
    try:
        response = requests.get(f"{BASE_URL}/frontend/index.html")
        if response.status_code == 200:
            print(f"✅ 主页面访问成功: {BASE_URL}/frontend/index.html")
            print(f"   页面大小: {len(response.content)} 字节")
        else:
            print(f"❌ 主页面访问失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 主页面访问异常: {str(e)}")
        return False
    
    # 2. 测试JavaScript文件访问
    print("\n2. 测试JavaScript文件访问...")
    
    js_files = [
        "js/utils.js",
        "js/api.js", 
        "js/theme.js",
        "js/notifications.js",
        "js/document-manager.js",
        "js/qa.js",
        "js/history.js",
        "js/settings.js",
        "js/main.js"
    ]
    
    for js_file in js_files:
        try:
            response = requests.head(f"{BASE_URL}/frontend/{js_file}")
            if response.status_code == 200:
                print(f"   ✅ {js_file}")
            else:
                print(f"   ❌ {js_file} - {response.status_code}")
        except Exception as e:
            print(f"   ❌ {js_file} - 异常: {str(e)}")
    
    # 3. 测试CSS文件访问
    print("\n3. 测试CSS文件访问...")
    
    css_files = [
        "styles/main.css",
        "styles/themes.css",
        "styles/components.css",
        "styles/document-manager.css",
        "styles/qa-interface.css",
        "styles/history-interface.css",
        "styles/settings-interface.css"
    ]
    
    for css_file in css_files:
        try:
            response = requests.head(f"{BASE_URL}/frontend/{css_file}")
            if response.status_code == 200:
                print(f"   ✅ {css_file}")
            else:
                print(f"   ❌ {css_file} - {response.status_code}")
        except Exception as e:
            print(f"   ❌ {css_file} - 异常: {str(e)}")
    
    # 4. 测试API端点（前端依赖的）
    print("\n4. 测试前端依赖的API端点...")
    
    api_endpoints = [
        ("/qa/ask", "POST", "问答接口"),
        ("/sessions/recent", "GET", "会话列表"),
        ("/sessions/stats/summary", "GET", "会话统计"),
        ("/documents/stats/summary", "GET", "文档统计"),
    ]
    
    for endpoint, method, description in api_endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                # POST请求用简单的测试数据
                if endpoint == "/qa/ask":
                    response = requests.post(f"{BASE_URL}{endpoint}", json={"question": "测试问题"})
                else:
                    response = requests.post(f"{BASE_URL}{endpoint}")
            
            if response.status_code in [200, 201]:
                print(f"   ✅ {description}: {endpoint}")
            else:
                print(f"   ❌ {description}: {endpoint} - {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {description}: {endpoint} - 异常: {str(e)}")
    
    # 5. 创建测试会话并检查历史记录功能
    print("\n5. 测试历史记录功能...")
    
    try:
        # 创建测试会话
        qa_response = requests.post(f"{BASE_URL}/qa/ask", json={
            "question": "前端测试问题：什么是人工智能？"
        })
        
        if qa_response.status_code == 200:
            qa_data = qa_response.json()
            session_id = qa_data.get('session_id')
            print(f"   ✅ 测试会话创建成功: {session_id}")
            
            # 测试会话历史获取
            history_response = requests.get(f"{BASE_URL}/sessions/{session_id}/history")
            if history_response.status_code == 200:
                history_data = history_response.json()
                print(f"   ✅ 会话历史获取成功")
                print(f"   📊 历史记录格式: {type(history_data)}")
                if isinstance(history_data, dict) and 'history' in history_data:
                    print(f"   📊 历史记录数量: {len(history_data['history'])}")
                    print(f"   ✅ 数据格式正确，前端应该能正常处理")
                else:
                    print(f"   ⚠️ 数据格式可能有问题")
            else:
                print(f"   ❌ 会话历史获取失败: {history_response.status_code}")
        else:
            print(f"   ❌ 测试会话创建失败: {qa_response.status_code}")
            
    except Exception as e:
        print(f"   ❌ 历史记录功能测试异常: {str(e)}")
    
    return True

def generate_frontend_diagnosis():
    """生成前端诊断报告"""
    print(f"\n📋 前端页面诊断报告")
    print(f"=" * 50)
    
    print(f"\n🌐 访问地址:")
    print(f"   主页面: http://localhost:8000/frontend/index.html")
    print(f"   测试页面: http://localhost:8000/static/test_frontend_history_fix.html")
    
    print(f"\n🔧 可能的问题:")
    print(f"   1. 检查浏览器控制台是否有JavaScript错误")
    print(f"   2. 检查网络面板是否有资源加载失败")
    print(f"   3. 确认API端点是否正常响应")
    print(f"   4. 检查前端JavaScript是否正确处理API返回数据")
    
    print(f"\n🎯 调试建议:")
    print(f"   1. 打开浏览器开发者工具 (F12)")
    print(f"   2. 查看Console面板的错误信息")
    print(f"   3. 查看Network面板的网络请求")
    print(f"   4. 在QA页面尝试问答，观察是否有错误")
    print(f"   5. 在历史记录页面检查是否能正常显示")

if __name__ == "__main__":
    try:
        success = test_frontend_main_page()
        generate_frontend_diagnosis()
        
        if success:
            print(f"\n🎉 前端页面基础功能测试完成")
            print(f"如果页面仍有问题，请检查浏览器控制台的具体错误信息")
        else:
            print(f"\n❌ 前端页面测试失败")
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")