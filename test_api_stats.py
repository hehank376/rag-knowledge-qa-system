#!/usr/bin/env python3
"""
测试API统计接口
"""
import requests
import time


def test_api_stats():
    """测试API统计接口"""
    print("📊 测试API统计接口...")
    
    try:
        # 1. 测试会话统计
        print("\n1. 测试会话统计...")
        response = requests.get("http://localhost:8000/sessions/stats/summary", timeout=10)
        
        if response.status_code == 200:
            stats = response.json()
            print(f"   ✅ 会话统计获取成功:")
            print(f"      总会话数: {stats.get('total_sessions', 0)}")
            print(f"      活跃会话数: {stats.get('active_sessions', 0)}")
            print(f"      总问答对数: {stats.get('total_qa_pairs', 0)}")
            print(f"      平均问答数: {stats.get('avg_qa_per_session', 0.0)}")
        else:
            print(f"   ❌ 会话统计获取失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
        
        # 2. 测试会话列表
        print("\n2. 测试会话列表...")
        response = requests.get("http://localhost:8000/sessions/", timeout=10)
        
        if response.status_code == 200:
            sessions_data = response.json()
            sessions = sessions_data.get('sessions', [])
            print(f"   ✅ 会话列表获取成功，共 {len(sessions)} 个会话")
            
            for i, session in enumerate(sessions[:3]):  # 只显示前3个
                print(f"      会话 {i+1}: ID={session.get('session_id', 'N/A')[:8]}..., QA数={session.get('qa_count', 0)}")
        else:
            print(f"   ❌ 会话列表获取失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
        
        # 3. 测试最近会话
        print("\n3. 测试最近会话...")
        response = requests.get("http://localhost:8000/sessions/recent?limit=5", timeout=10)
        
        if response.status_code == 200:
            recent_data = response.json()
            recent_sessions = recent_data.get('sessions', [])
            print(f"   ✅ 最近会话获取成功，共 {len(recent_sessions)} 个会话")
        else:
            print(f"   ❌ 最近会话获取失败: {response.status_code}")
            print(f"   错误信息: {response.text}")
        
        # 4. 测试健康检查
        print("\n4. 测试健康检查...")
        response = requests.get("http://localhost:8000/sessions/health", timeout=5)
        
        if response.status_code == 200:
            health = response.json()
            print(f"   ✅ 健康检查通过: {health}")
        else:
            print(f"   ❌ 健康检查失败: {response.status_code}")
        
        print("\n✅ API统计测试完成")
        
    except requests.exceptions.Timeout:
        print("❌ 请求超时，服务器可能正在处理其他请求")
    except requests.exceptions.ConnectionError:
        print("❌ 连接失败，请确保服务器正在运行")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")


if __name__ == "__main__":
    test_api_stats()