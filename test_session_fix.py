#!/usr/bin/env python3
"""
测试会话修复
"""
import asyncio
import sys
import os
import requests
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.services.session_service import SessionService


async def test_session_fix():
    """测试会话修复"""
    print("🔧 测试会话修复...")
    
    try:
        # 1. 创建会话服务实例（使用正确的数据库）
        print("\n1. 初始化会话服务...")
        config = {
            'max_sessions_per_user': 100,
            'session_timeout_hours': 24,
            'max_qa_pairs_per_session': 1000,
            'cleanup_interval_hours': 6,
            'auto_cleanup_enabled': True,
            'database_url': 'sqlite:///./database/rag_system.db'
        }
        
        session_service = SessionService(config)
        await session_service.initialize()
        print("✅ 会话服务初始化成功")
        
        # 2. 检查初始统计
        print("\n2. 检查初始统计...")
        initial_stats = await session_service.get_session_stats()
        print(f"   初始统计: {initial_stats}")
        
        # 3. 测试通过API创建会话和问答
        print("\n3. 测试API问答功能...")
        try:
            # 发送问答请求
            qa_request = {
                "question": "什么是人工智能？",
                "session_id": None,  # 让系统自动创建会话
                "user_id": "test_user"
            }
            
            response = requests.post(
                "http://localhost:8000/qa/ask",
                json=qa_request,
                timeout=30
            )
            
            if response.status_code == 200:
                qa_result = response.json()
                session_id = qa_result.get('session_id')
                print(f"   ✅ API问答成功，会话ID: {session_id}")
                
                # 等待一下让数据保存
                time.sleep(1)
                
                # 4. 检查统计是否更新
                print("\n4. 检查统计更新...")
                updated_stats = await session_service.get_session_stats()
                print(f"   更新后统计: {updated_stats}")
                
                # 5. 通过API检查统计
                print("\n5. 通过API检查统计...")
                stats_response = requests.get("http://localhost:8000/sessions/stats/summary")
                if stats_response.status_code == 200:
                    api_stats = stats_response.json()
                    print(f"   API统计: {api_stats}")
                    
                    # 比较统计数据
                    if (updated_stats['total_sessions'] == api_stats['total_sessions'] and
                        updated_stats['total_qa_pairs'] == api_stats['total_qa_pairs']):
                        print("   ✅ 统计数据一致！")
                    else:
                        print("   ❌ 统计数据不一致")
                        print(f"      服务统计: {updated_stats}")
                        print(f"      API统计: {api_stats}")
                else:
                    print(f"   ❌ API统计请求失败: {stats_response.status_code}")
                
                # 6. 测试会话历史
                print("\n6. 测试会话历史...")
                history_response = requests.get(f"http://localhost:8000/sessions/{session_id}/history")
                if history_response.status_code == 200:
                    history = history_response.json()
                    print(f"   ✅ 会话历史获取成功，记录数: {len(history.get('history', []))}")
                else:
                    print(f"   ❌ 会话历史获取失败: {history_response.status_code}")
                
            else:
                print(f"   ❌ API问答失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ API请求异常: {str(e)}")
            print("   请确保服务器正在运行 (python start_rag_system.py)")
        
        # 7. 最终统计
        print("\n7. 最终统计...")
        final_stats = await session_service.get_session_stats()
        print(f"   最终统计: {final_stats}")
        
        print("\n✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_session_fix())