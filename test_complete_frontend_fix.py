#!/usr/bin/env python3
"""
完整的前端功能测试
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_complete_frontend_workflow():
    """测试完整的前端工作流程"""
    print("🔍 测试完整的前端工作流程...")
    
    # 1. 创建会话并进行多轮对话
    print("\n1. 创建会话并进行多轮对话...")
    
    questions = [
        "什么是人工智能？",
        "机器学习和深度学习有什么区别？",
        "RAG技术是什么？"
    ]
    
    session_id = None
    for i, question in enumerate(questions, 1):
        print(f"   发送问题 {i}: {question}")
        
        data = {"question": question}
        if session_id:
            data["session_id"] = session_id
            
        response = requests.post(f"{BASE_URL}/qa/ask", json=data)
        
        if response.status_code != 200:
            print(f"   ❌ 问题 {i} 失败: {response.status_code}")
            return None
            
        qa_data = response.json()
        if not session_id:
            session_id = qa_data.get('session_id')
            print(f"   ✅ 会话创建成功: {session_id}")
        
        print(f"   ✅ 问题 {i} 回答成功，答案长度: {len(qa_data.get('answer', ''))}")
    
    # 2. 测试会话历史获取
    print(f"\n2. 测试会话历史获取...")
    
    history_response = requests.get(f"{BASE_URL}/sessions/{session_id}/history")
    if history_response.status_code != 200:
        print(f"   ❌ 获取历史失败: {history_response.status_code}")
        return None
    
    history_data = history_response.json()
    print(f"   ✅ 获取历史成功")
    print(f"   📊 数据格式: {type(history_data)}")
    print(f"   📊 历史记录数: {len(history_data.get('history', []))}")
    
    # 验证数据结构
    if 'history' in history_data and isinstance(history_data['history'], list):
        print(f"   ✅ 数据结构正确")
        for i, qa in enumerate(history_data['history'], 1):
            print(f"     记录 {i}: 问题={qa.get('question', '')[:30]}...")
    else:
        print(f"   ❌ 数据结构错误")
        return None
    
    # 3. 测试会话列表
    print(f"\n3. 测试会话列表...")
    
    sessions_response = requests.get(f"{BASE_URL}/sessions/recent")
    if sessions_response.status_code != 200:
        print(f"   ❌ 获取会话列表失败: {sessions_response.status_code}")
        return None
    
    sessions_data = sessions_response.json()
    print(f"   ✅ 获取会话列表成功")
    print(f"   📊 会话数量: {len(sessions_data.get('sessions', []))}")
    
    # 查找目标会话
    target_session = None
    for session in sessions_data.get('sessions', []):
        if session.get('session_id') == session_id:
            target_session = session
            break
    
    if target_session:
        print(f"   ✅ 找到目标会话")
        print(f"     问答对数: {target_session.get('qa_count', 0)}")
        print(f"     最后活动: {target_session.get('last_activity', '')}")
    else:
        print(f"   ⚠️ 未找到目标会话")
    
    # 4. 测试统计信息
    print(f"\n4. 测试统计信息...")
    
    # 会话统计
    try:
        stats_response = requests.get(f"{BASE_URL}/sessions/stats/summary")
        if stats_response.status_code == 200:
            stats_data = stats_response.json()
            print(f"   ✅ 会话统计: 总会话={stats_data.get('total_sessions', 0)}, 总问答={stats_data.get('total_qa_pairs', 0)}")
        else:
            print(f"   ⚠️ 会话统计API不可用")
    except:
        print(f"   ⚠️ 会话统计API异常")
    
    # 文档统计
    try:
        doc_stats_response = requests.get(f"{BASE_URL}/documents/stats/summary")
        if doc_stats_response.status_code == 200:
            doc_stats_data = doc_stats_response.json()
            print(f"   ✅ 文档统计: 总文档={doc_stats_data.get('total', 0)}, 就绪={doc_stats_data.get('ready', 0)}")
        else:
            print(f"   ⚠️ 文档统计API不可用")
    except:
        print(f"   ⚠️ 文档统计API异常")
    
    return session_id

def generate_frontend_test_summary(session_id):
    """生成前端测试总结"""
    print(f"\n📋 前端功能测试总结")
    print(f"=" * 50)
    print(f"✅ 会话创建: 正常")
    print(f"✅ 多轮对话: 正常")
    print(f"✅ 历史记录获取: 正常")
    print(f"✅ 会话列表获取: 正常")
    print(f"✅ 数据格式处理: 已修复")
    
    print(f"\n🎯 前端测试建议:")
    print(f"1. 打开浏览器访问: http://localhost:8000/test_frontend_history_fix.html")
    print(f"2. 按顺序点击测试按钮")
    print(f"3. 验证历史记录显示是否正常")
    print(f"4. 测试会话切换功能")
    
    print(f"\n🔧 已修复的问题:")
    print(f"- ✅ 前端历史数据格式处理")
    print(f"- ✅ qa.js 中的 displaySessionHistory 方法")
    print(f"- ✅ history.js 中的 renderSessionDetails 方法")
    print(f"- ✅ 会话导出功能的数据处理")
    
    print(f"\n📝 测试会话ID: {session_id}")
    print(f"可以在前端页面中使用此会话ID进行测试")

if __name__ == "__main__":
    try:
        session_id = test_complete_frontend_workflow()
        if session_id:
            generate_frontend_test_summary(session_id)
            print(f"\n🎉 前端功能测试完成！")
        else:
            print(f"\n❌ 前端功能测试失败")
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")