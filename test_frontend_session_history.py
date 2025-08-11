#!/usr/bin/env python3
"""
测试前端会话历史功能
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_frontend_session_history():
    """测试前端会话历史功能"""
    print("🔍 测试前端会话历史功能...")
    
    # 1. 创建一个会话并进行问答
    print("\n1. 创建会话并进行问答...")
    
    # 发送第一个问题（会自动创建会话）
    qa_response1 = requests.post(f"{BASE_URL}/qa/ask", json={
        "question": "什么是人工智能？"
    })
    
    if qa_response1.status_code != 200:
        print(f"❌ 第一次问答失败: {qa_response1.status_code}")
        print(qa_response1.text)
        return
    
    qa_data1 = qa_response1.json()
    session_id = qa_data1.get('session_id')
    print(f"✅ 第一次问答成功，会话ID: {session_id}")
    print(f"   答案长度: {len(qa_data1.get('answer', ''))}")
    
    # 发送第二个问题到同一会话
    qa_response2 = requests.post(f"{BASE_URL}/qa/ask", json={
        "question": "深度学习有什么特点？",
        "session_id": session_id
    })
    
    if qa_response2.status_code != 200:
        print(f"❌ 第二次问答失败: {qa_response2.status_code}")
        return
    
    qa_data2 = qa_response2.json()
    print(f"✅ 第二次问答成功")
    print(f"   答案长度: {len(qa_data2.get('answer', ''))}")
    
    # 2. 测试会话历史API
    print(f"\n2. 测试会话历史API...")
    
    history_response = requests.get(f"{BASE_URL}/sessions/{session_id}/history")
    
    if history_response.status_code != 200:
        print(f"❌ 获取会话历史失败: {history_response.status_code}")
        print(history_response.text)
        return
    
    history_data = history_response.json()
    print(f"✅ 获取会话历史成功")
    print(f"   历史记录数量: {len(history_data)}")
    
    for i, qa in enumerate(history_data, 1):
        print(f"   记录 {i}:")
        print(f"     问题: {qa.get('question', '')[:50]}...")
        print(f"     答案: {qa.get('answer', '')[:50]}...")
        print(f"     时间: {qa.get('created_at', '')}")
    
    # 3. 测试会话列表API
    print(f"\n3. 测试会话列表API...")
    
    sessions_response = requests.get(f"{BASE_URL}/sessions/recent")
    
    if sessions_response.status_code != 200:
        print(f"❌ 获取会话列表失败: {sessions_response.status_code}")
        print(sessions_response.text)
        return
    
    sessions_data = sessions_response.json()
    print(f"✅ 获取会话列表成功")
    print(f"   会话数量: {len(sessions_data.get('sessions', []))}")
    
    # 查找我们创建的会话
    target_session = None
    for session in sessions_data.get('sessions', []):
        if session.get('session_id') == session_id:
            target_session = session
            break
    
    if target_session:
        print(f"   找到目标会话:")
        print(f"     会话ID: {target_session.get('session_id')}")
        print(f"     标题: {target_session.get('title', 'N/A')}")
        print(f"     问答对数: {target_session.get('qa_count', 0)}")
        print(f"     创建时间: {target_session.get('created_at', '')}")
        print(f"     最后活动: {target_session.get('last_activity', '')}")
    else:
        print(f"   ⚠️ 未找到目标会话 {session_id}")
    
    # 4. 测试会话统计API
    print(f"\n4. 测试会话统计API...")
    
    stats_response = requests.get(f"{BASE_URL}/sessions/stats/summary")
    
    if stats_response.status_code != 200:
        print(f"❌ 获取会话统计失败: {stats_response.status_code}")
        print(stats_response.text)
        return
    
    stats_data = stats_response.json()
    print(f"✅ 获取会话统计成功")
    print(f"   总会话数: {stats_data.get('total_sessions', 0)}")
    print(f"   活跃会话数: {stats_data.get('active_sessions', 0)}")
    print(f"   总问答对数: {stats_data.get('total_qa_pairs', 0)}")
    print(f"   平均问答对数: {stats_data.get('avg_qa_per_session', 0)}")
    
    print(f"\n✅ 前端会话历史功能测试完成")
    print(f"📝 测试结果:")
    print(f"   - 会话创建: ✅")
    print(f"   - 多轮对话: ✅")
    print(f"   - 历史记录获取: ✅")
    print(f"   - 会话列表获取: ✅")
    print(f"   - 统计信息获取: ✅")
    
    return session_id

def test_frontend_api_endpoints():
    """测试前端需要的所有API端点"""
    print("\n🔍 测试前端API端点...")
    
    endpoints = [
        ("GET", "/sessions/recent", "会话列表"),
        ("GET", "/sessions/stats/summary", "会话统计"),
        ("GET", "/documents/stats/summary", "文档统计"),
    ]
    
    for method, endpoint, description in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}")
            else:
                response = requests.post(f"{BASE_URL}{endpoint}")
            
            if response.status_code == 200:
                print(f"   ✅ {description}: {endpoint}")
            else:
                print(f"   ❌ {description}: {endpoint} - {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ {description}: {endpoint} - {str(e)}")

if __name__ == "__main__":
    try:
        session_id = test_frontend_session_history()
        test_frontend_api_endpoints()
        
        print(f"\n🎯 前端测试建议:")
        print(f"1. 打开浏览器访问 http://localhost:8000")
        print(f"2. 在历史记录页面查看会话 {session_id}")
        print(f"3. 点击'继续对话'按钮测试会话切换")
        print(f"4. 检查QA页面是否正确加载历史记录")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")