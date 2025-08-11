#!/usr/bin/env python3
"""
测试自动创建会话功能
"""
import requests


def test_auto_session():
    """测试自动创建会话功能"""
    print("🤖 测试自动创建会话功能...")
    
    try:
        # 1. 检查初始统计
        print("\n1. 检查初始统计...")
        stats_response = requests.get("http://localhost:8000/sessions/stats/summary", timeout=10)
        if stats_response.status_code == 200:
            initial_stats = stats_response.json()
            print(f"   初始统计: {initial_stats}")
        
        # 2. 发送不带session_id的问答请求
        print("\n2. 发送不带session_id的问答请求...")
        qa_request = {
            "question": "什么是深度学习？",
            "session_id": None,  # 明确设置为None
            "user_id": "test_user_auto"
        }
        
        qa_response = requests.post(
            "http://localhost:8000/qa/ask",
            json=qa_request,
            timeout=60
        )
        
        print(f"   响应状态码: {qa_response.status_code}")
        
        if qa_response.status_code == 200:
            qa_result = qa_response.json()
            print(f"   ✅ 问答成功!")
            print(f"      问题: {qa_result.get('question', 'N/A')}")
            print(f"      答案长度: {len(qa_result.get('answer', ''))}")
            print(f"      自动创建的会话ID: {qa_result.get('session_id', 'N/A')}")
            print(f"      置信度: {qa_result.get('confidence_score', 0)}")
            
            auto_session_id = qa_result.get('session_id')
            
            # 3. 检查统计更新
            print("\n3. 检查统计更新...")
            stats_response = requests.get("http://localhost:8000/sessions/stats/summary", timeout=10)
            if stats_response.status_code == 200:
                updated_stats = stats_response.json()
                print(f"   更新后统计: {updated_stats}")
                
                if 'initial_stats' in locals():
                    session_diff = updated_stats.get('total_sessions', 0) - initial_stats.get('total_sessions', 0)
                    qa_diff = updated_stats.get('total_qa_pairs', 0) - initial_stats.get('total_qa_pairs', 0)
                    print(f"   变化: 会话 +{session_diff}, 问答对 +{qa_diff}")
            
            # 4. 验证会话历史
            if auto_session_id and auto_session_id != 'N/A':
                print(f"\n4. 验证自动创建的会话历史 ({auto_session_id})...")
                history_response = requests.get(
                    f"http://localhost:8000/sessions/{auto_session_id}/history",
                    timeout=10
                )
                
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    history = history_data.get('history', [])
                    print(f"   ✅ 会话历史: {len(history)} 条记录")
                    
                    if history:
                        record = history[0]
                        print(f"      记录详情:")
                        print(f"        问题: {record.get('question', 'N/A')}")
                        print(f"        答案: {record.get('answer', 'N/A')[:50]}...")
                        print(f"        置信度: {record.get('confidence_score', 0)}")
                        print(f"        时间: {record.get('timestamp', 'N/A')}")
                else:
                    print(f"   ❌ 获取会话历史失败: {history_response.status_code}")
            else:
                print("   ❌ 没有获得有效的会话ID")
            
            # 5. 再次使用同一会话发送问题
            if auto_session_id and auto_session_id != 'N/A':
                print(f"\n5. 使用同一会话发送第二个问题...")
                qa_request2 = {
                    "question": "深度学习和机器学习有什么区别？",
                    "session_id": auto_session_id,
                    "user_id": "test_user_auto"
                }
                
                qa_response2 = requests.post(
                    "http://localhost:8000/qa/ask",
                    json=qa_request2,
                    timeout=60
                )
                
                if qa_response2.status_code == 200:
                    qa_result2 = qa_response2.json()
                    print(f"   ✅ 第二次问答成功!")
                    print(f"      会话ID: {qa_result2.get('session_id', 'N/A')}")
                    
                    # 检查会话历史是否有2条记录
                    history_response2 = requests.get(
                        f"http://localhost:8000/sessions/{auto_session_id}/history",
                        timeout=10
                    )
                    
                    if history_response2.status_code == 200:
                        history_data2 = history_response2.json()
                        history2 = history_data2.get('history', [])
                        print(f"   ✅ 会话历史现在有: {len(history2)} 条记录")
                else:
                    print(f"   ❌ 第二次问答失败: {qa_response2.status_code}")
        
        else:
            print(f"   ❌ 问答失败: {qa_response.status_code}")
            print(f"   错误信息: {qa_response.text}")
        
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")


if __name__ == "__main__":
    test_auto_session()