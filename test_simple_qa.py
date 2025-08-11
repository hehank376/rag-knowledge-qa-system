#!/usr/bin/env python3
"""
测试简单问答功能
"""
import requests
import time


def test_simple_qa():
    """测试简单问答功能"""
    print("💬 测试简单问答功能...")
    
    try:
        # 1. 发送简单问答请求
        print("\n1. 发送问答请求...")
        qa_request = {
            "question": "什么是人工智能？",
            "session_id": None,  # 让系统自动创建会话
            "user_id": "test_user"
        }
        
        print(f"   请求数据: {qa_request}")
        
        response = requests.post(
            "http://localhost:8000/qa/ask",
            json=qa_request,
            timeout=60  # 增加超时时间
        )
        
        print(f"   响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ 问答成功!")
            print(f"      问题: {result.get('question', 'N/A')}")
            print(f"      答案: {result.get('answer', 'N/A')[:100]}...")
            print(f"      会话ID: {result.get('session_id', 'N/A')}")
            print(f"      置信度: {result.get('confidence_score', 0)}")
            
            session_id = result.get('session_id')
            
            # 2. 等待数据保存
            print("\n2. 等待数据保存...")
            time.sleep(2)
            
            # 3. 检查统计更新
            print("\n3. 检查统计更新...")
            stats_response = requests.get("http://localhost:8000/sessions/stats/summary", timeout=10)
            if stats_response.status_code == 200:
                stats = stats_response.json()
                print(f"   更新后统计:")
                print(f"      总会话数: {stats.get('total_sessions', 0)}")
                print(f"      总问答对数: {stats.get('total_qa_pairs', 0)}")
                print(f"      平均问答数: {stats.get('avg_qa_per_session', 0.0)}")
            
            # 4. 检查会话历史
            if session_id:
                print(f"\n4. 检查会话历史 ({session_id})...")
                history_response = requests.get(
                    f"http://localhost:8000/sessions/{session_id}/history",
                    timeout=10
                )
                if history_response.status_code == 200:
                    history_data = history_response.json()
                    history = history_data.get('history', [])
                    print(f"   ✅ 会话历史: {len(history)} 条记录")
                    
                    if history:
                        first_qa = history[0]
                        print(f"      第一条记录:")
                        print(f"        问题: {first_qa.get('question', 'N/A')}")
                        print(f"        答案: {first_qa.get('answer', 'N/A')[:50]}...")
                else:
                    print(f"   ❌ 获取会话历史失败: {history_response.status_code}")
            
        else:
            print(f"   ❌ 问答失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
        
        print("\n✅ 测试完成")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确保服务器正在运行")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")


if __name__ == "__main__":
    test_simple_qa()