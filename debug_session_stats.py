#!/usr/bin/env python3
"""
调试会话统计问题
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.services.session_service import SessionService
from rag_system.models.qa import QAResponse, QAStatus
from rag_system.database.connection import DatabaseManager
from rag_system.database.crud import SessionCRUD, QAPairCRUD
from rag_system.models.config import DatabaseConfig


async def debug_session_stats():
    """调试会话统计问题"""
    print("🔍 开始调试会话统计问题...")
    
    try:
        # 1. 测试会话服务初始化
        print("\n1. 测试会话服务初始化...")
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
        
        # 2. 测试数据库连接
        print("\n2. 测试数据库连接...")
        db_config = DatabaseConfig(
            url='sqlite:///./database/rag_system.db',
            echo=False
        )
        db_manager = DatabaseManager(db_config)
        db_manager.initialize()
        print("✅ 数据库连接成功")
        
        # 3. 检查现有数据
        print("\n3. 检查现有数据...")
        with db_manager.get_session_context() as db_session:
            session_crud = SessionCRUD(db_session)
            qa_pair_crud = QAPairCRUD(db_session)
            
            total_sessions = session_crud.count_total_sessions()
            total_qa_pairs = qa_pair_crud.count_total_qa_pairs()
            
            print(f"   现有会话数: {total_sessions}")
            print(f"   现有问答对数: {total_qa_pairs}")
            
            # 列出所有会话
            sessions = session_crud.list_sessions(limit=10)
            print(f"   会话列表 (前10个):")
            for session in sessions:
                print(f"     - ID: {session.id}, 创建时间: {session.created_at}, QA数: {session.qa_count}")
        
        # 4. 创建测试会话和问答对
        print("\n4. 创建测试数据...")
        test_session_id = await session_service.create_session("test_user")
        print(f"   创建测试会话: {test_session_id}")
        
        # 创建测试问答对
        test_qa = QAResponse(
            question="这是一个测试问题",
            answer="这是一个测试答案",
            sources=[],
            confidence_score=0.8,
            processing_time=1.0,
            status=QAStatus.COMPLETED
        )
        
        save_success = await session_service.save_qa_pair(test_session_id, test_qa)
        print(f"   保存问答对: {'成功' if save_success else '失败'}")
        
        # 5. 重新检查统计
        print("\n5. 重新检查统计...")
        stats = await session_service.get_session_stats()
        print(f"   统计结果: {stats}")
        
        # 6. 测试API统计接口
        print("\n6. 测试API统计接口...")
        try:
            import requests
            response = requests.get("http://localhost:8000/sessions/stats/summary")
            if response.status_code == 200:
                api_stats = response.json()
                print(f"   API统计结果: {api_stats}")
            else:
                print(f"   API请求失败: {response.status_code}")
        except Exception as e:
            print(f"   API请求异常: {str(e)}")
        
        # 7. 清理测试数据
        print("\n7. 清理测试数据...")
        delete_success = await session_service.delete_session(test_session_id)
        print(f"   删除测试会话: {'成功' if delete_success else '失败'}")
        
        # 8. 最终统计
        print("\n8. 最终统计...")
        final_stats = await session_service.get_session_stats()
        print(f"   最终统计: {final_stats}")
        
        print("\n✅ 调试完成")
        
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_session_stats())