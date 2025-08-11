#!/usr/bin/env python3
"""
测试会话创建逻辑
"""
import requests
import json


def test_session_creation():
    """测试会话创建逻辑"""
    print("🆕 测试会话创建逻辑...")
    
    try:
        # 1. 先检查当前统计
        print("\n1. 检查当前统计...")
        stats_response = requests.get("http://localhost:8000/sessions/stats/summary", timeout=10)
        if stats_response.status_code == 200:
            initial_stats = stats_response.json()
            print(f"   初始统计: {initial_stats}")
        
        # 2. 手动创建会话
        print("\n2. 手动创建会话...")
        create_response = requests.post(
            "http://localhost:8000/sessions/",
            json={"user_id": "test_user_manual"},
            timeout=10
        )
        
        if create_response.status_code == 200:
            session_data = create_response.json()
            print(f"   ✅ 手动创建会话成功: {session_data.get('session_id', 'N/A')}")
            manual_session_id = session_data.get('session_id')
        else:
            print(f"   ❌ 手动创建会话失败: {create_response.status_code}")
            print(f"   错误: {create_response.text}")
            manual_session_id = None
        
        # 3. 使用现有会话发送问答
        if manual_session_id:
            print(f"\n3. 使用现有会话发送问答 ({manual_session_id})...")
            qa_request = {
                "question": "什么是机器学习？",
                "session_id": manual_session_id,
                "user_id": "test_user_manual"
            }
            
            qa_response = requests.post(
                "http://localhost:8000/qa/ask",
                json=qa_request,
                timeout=60
            )
            
            if qa_response.status_code == 200:
                qa_result = qa_response.json()
                print(f"   ✅ 问答成功!")
                print(f"      返回的会话ID: {qa_result.get('session_id', 'N/A')}")
                print(f"      答案长度: {len(qa_result.get('answer', ''))}")
            else:
                print(f"   ❌ 问答失败: {qa_response.status_code}")
                print(f"   错误: {qa_response.text}")
        
        # 4. 检查更新后的统计
        print("\n4. 检查更新后的统计...")
        stats_response = requests.get("http://localhost:8000/sessions/stats/summary", timeout=10)
        if stats_response.status_code == 200:
            final_stats = stats_response.json()
            print(f"   最终统计: {final_stats}")
            
            # 比较变化
            if 'initial_stats' in locals():
                session_diff = final_stats.get('total_sessions', 0) - initial_stats.get('total_sessions', 0)
                qa_diff = final_stats.get('total_qa_pairs', 0) - initial_stats.get('total_qa_pairs', 0)
                print(f"   变化: 会话 +{session_diff}, 问答对 +{qa_diff}")
        
        # 5. 检查会话历史
        if manual_session_id:
            print(f"\n5. 检查会话历史 ({manual_session_id})...")
            history_response = requests.get(
                f"http://localhost:8000/sessions/{manual_session_id}/history",
                timeout=10
            )
            if history_response.status_code == 200:
                history_data = history_response.json()
                history = history_data.get('history', [])
                print(f"   ✅ 会话历史: {len(history)} 条记录")
                
                if history:
                    print(f"      最新记录:")
                    latest = history[0]
                    print(f"        问题: {latest.get('question', 'N/A')}")
                    print(f"        答案: {latest.get('answer', 'N/A')[:50]}...")
                    print(f"        时间: {latest.get('timestamp', 'N/A')}")
            else:
                print(f"   ❌ 获取会话历史失败: {history_response.status_code}")
        
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")


if __name__ == "__main__":
    test_session_creation()