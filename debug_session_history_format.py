#!/usr/bin/env python3
"""
调试会话历史数据格式
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def debug_session_history():
    """调试会话历史数据格式"""
    print("🔍 调试会话历史数据格式...")
    
    # 1. 创建会话并问答
    print("\n1. 创建会话并问答...")
    qa_response = requests.post(f"{BASE_URL}/qa/ask", json={
        "question": "什么是机器学习？"
    })
    
    if qa_response.status_code != 200:
        print(f"❌ 问答失败: {qa_response.status_code}")
        return
    
    qa_data = qa_response.json()
    session_id = qa_data.get('session_id')
    print(f"✅ 问答成功，会话ID: {session_id}")
    
    # 2. 获取会话历史
    print(f"\n2. 获取会话历史...")
    history_response = requests.get(f"{BASE_URL}/sessions/{session_id}/history")
    
    if history_response.status_code != 200:
        print(f"❌ 获取历史失败: {history_response.status_code}")
        print(history_response.text)
        return
    
    history_data = history_response.json()
    print(f"✅ 获取历史成功")
    print(f"📊 原始数据类型: {type(history_data)}")
    print(f"📊 数据长度: {len(history_data) if isinstance(history_data, (list, dict)) else 'N/A'}")
    
    # 3. 详细分析数据结构
    print(f"\n3. 详细数据结构分析:")
    print(f"原始数据: {json.dumps(history_data, indent=2, ensure_ascii=False)}")
    
    if isinstance(history_data, list):
        print(f"✅ 数据是列表格式")
        for i, item in enumerate(history_data):
            print(f"   项目 {i+1}: 类型={type(item)}")
            if isinstance(item, dict):
                print(f"     键: {list(item.keys())}")
            else:
                print(f"     值: {item}")
    elif isinstance(history_data, dict):
        print(f"✅ 数据是字典格式")
        print(f"   键: {list(history_data.keys())}")
    else:
        print(f"⚠️ 数据格式未知: {type(history_data)}")

if __name__ == "__main__":
    debug_session_history()