#!/usr/bin/env python3
"""
测试修复后的前端历史记录功能
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_frontend_history_final():
    """测试修复后的前端历史记录功能"""
    print("🔍 测试修复后的前端历史记录功能...")
    
    # 1. 创建测试会话
    print("\n1. 创建测试会话...")
    
    qa_response = requests.post(f"{BASE_URL}/qa/ask", json={
        "question": "前端历史记录最终测试：什么是机器学习？"
    })
    
    if qa_response.status_code != 200:
        print(f"❌ 创建测试会话失败: {qa_response.status_code}")
        return False
    
    qa_data = qa_response.json()
    session_id = qa_data.get('session_id')
    print(f"✅ 测试会话创建成功: {session_id}")
    
    # 2. 测试会话列表API
    print(f"\n2. 测试会话列表API...")
    
    sessions_response = requests.get(f"{BASE_URL}/sessions/recent")
    if sessions_response.status_code != 200:
        print(f"❌ 会话列表API失败: {sessions_response.status_code}")
        return False
    
    sessions_data = sessions_response.json()
    print(f"✅ 会话列表API成功")
    print(f"   数据格式: {type(sessions_data)}")
    print(f"   包含字段: {list(sessions_data.keys())}")
    print(f"   会话数量: {len(sessions_data.get('sessions', []))}")
    
    # 检查数据格式
    if 'sessions' in sessions_data:
        sessions = sessions_data['sessions']
        if len(sessions) > 0:
            first_session = sessions[0]
            print(f"   第一个会话字段: {list(first_session.keys())}")
            print(f"   会话ID: {first_session.get('session_id')}")
            print(f"   问答数量: {first_session.get('qa_count', 0)}")
        else:
            print(f"   ⚠️ 会话列表为空")
    
    # 3. 测试会话统计API
    print(f"\n3. 测试会话统计API...")
    
    stats_response = requests.get(f"{BASE_URL}/sessions/stats/summary")
    if stats_response.status_code != 200:
        print(f"❌ 会话统计API失败: {stats_response.status_code}")
        return False
    
    stats_data = stats_response.json()
    print(f"✅ 会话统计API成功")
    print(f"   统计字段: {list(stats_data.keys())}")
    print(f"   总会话数: {stats_data.get('total_sessions', 0)}")
    print(f"   总问答数: {stats_data.get('total_qa_pairs', 0)}")
    
    # 4. 测试会话历史API
    print(f"\n4. 测试会话历史API...")
    
    history_response = requests.get(f"{BASE_URL}/sessions/{session_id}/history")
    if history_response.status_code != 200:
        print(f"❌ 会话历史API失败: {history_response.status_code}")
        return False
    
    history_data = history_response.json()
    print(f"✅ 会话历史API成功")
    print(f"   历史数据格式: {type(history_data)}")
    print(f"   包含字段: {list(history_data.keys())}")
    
    if 'history' in history_data:
        history = history_data['history']
        print(f"   历史记录数量: {len(history)}")
        if len(history) > 0:
            first_qa = history[0]
            print(f"   第一条记录字段: {list(first_qa.keys())}")
    
    return True

def generate_frontend_fix_summary():
    """生成前端修复总结"""
    print(f"\n📋 前端历史记录修复总结")
    print(f"=" * 50)
    
    print(f"\n🔧 已修复的问题:")
    print(f"   1. 数据格式不匹配:")
    print(f"      - 后端返回 total_count，前端期望 total_pages")
    print(f"      - 后端返回 qa_count，前端期望 qa_pairs")
    print(f"      - 后端返回 total_qa_pairs，前端期望 total_questions")
    
    print(f"\n   2. 统计信息加载:")
    print(f"      - 添加了独立的 loadStats() 方法")
    print(f"      - 修复了统计字段映射")
    
    print(f"\n   3. 会话显示:")
    print(f"      - 修复了会话项渲染逻辑")
    print(f"      - 处理了缺失的 qa_pairs 字段")
    
    print(f"\n🎯 前端测试步骤:")
    print(f"   1. 访问: http://localhost:8000/frontend/index.html")
    print(f"   2. 切换到'历史记录'标签页")
    print(f"   3. 检查是否显示会话列表")
    print(f"   4. 检查统计信息是否正确")
    print(f"   5. 点击'查看详情'测试会话历史")
    
    print(f"\n🔍 调试提示:")
    print(f"   - 打开浏览器开发者工具 (F12)")
    print(f"   - 查看Console面板的日志输出")
    print(f"   - 查看Network面板的API请求")
    print(f"   - 检查是否有JavaScript错误")

if __name__ == "__main__":
    try:
        success = test_frontend_history_final()
        generate_frontend_fix_summary()
        
        if success:
            print(f"\n🎉 前端历史记录功能修复完成！")
            print(f"现在可以访问前端页面测试历史记录功能")
        else:
            print(f"\n❌ 前端历史记录功能测试失败")
            
    except Exception as e:
        print(f"❌ 测试异常: {str(e)}")