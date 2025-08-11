#!/usr/bin/env python3
"""
会话管理和历史记录功能演示
演示任务7.1和7.2的功能实现
"""
import asyncio
import sys
import os
from datetime import datetime
from typing import List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag_system.services.session_service import SessionService
from rag_system.models.qa import QAResponse, QAStatus, SourceInfo


async def demo_session_management():
    """演示会话管理功能"""
    print("=" * 60)
    print("会话管理功能演示")
    print("=" * 60)
    
    # 初始化会话管理服务
    config = {
        'max_sessions_per_user': 10,
        'session_timeout_hours': 24,
        'max_qa_pairs_per_session': 100,
        'auto_cleanup_enabled': True,
        'cleanup_interval_hours': 6,
        'database_url': 'sqlite:///./demo_sessions.db'
    }
    
    service = SessionService(config)
    await service.initialize()
    
    print(f"✓ 会话管理服务初始化完成")
    print(f"  - 最大用户会话数: {config['max_sessions_per_user']}")
    print(f"  - 会话超时时间: {config['session_timeout_hours']} 小时")
    print(f"  - 最大问答对数: {config['max_qa_pairs_per_session']}")
    print(f"  - 自动清理: {config['auto_cleanup_enabled']}")
    print()
    
    # 演示1: 创建多个会话
    print("📝 演示1: 创建用户会话")
    user_sessions = []
    for i in range(3):
        session_id = await service.create_session(f"user_{i+1}")
        user_sessions.append((f"user_{i+1}", session_id))
        print(f"  创建会话 {i+1}: {session_id} (用户: user_{i+1})")
    print()
    
    # 演示2: 保存问答对到不同会话
    print("💬 演示2: 保存问答对到会话")
    sample_questions = [
        "什么是人工智能？",
        "机器学习的基本原理是什么？",
        "深度学习有哪些应用？"
    ]
    
    sample_answers = [
        "人工智能是计算机科学的一个分支，旨在创建能够执行通常需要人类智能的任务的系统。",
        "机器学习是一种人工智能技术，通过算法让计算机从数据中学习模式，无需明确编程。",
        "深度学习在图像识别、自然语言处理、语音识别等领域有广泛应用。"
    ]
    
    for i, (user_id, session_id) in enumerate(user_sessions):
        # 创建示例源信息
        import uuid
        source = SourceInfo(
            document_id=str(uuid.uuid4()),
            document_name=f"AI教程_{i+1}.pdf",
            chunk_id=str(uuid.uuid4()),
            chunk_content=sample_answers[i][:50] + "...",
            chunk_index=0,
            similarity_score=0.9 - i * 0.05
        )
        
        qa_response = QAResponse(
            question=sample_questions[i],
            answer=sample_answers[i],
            sources=[source],
            confidence_score=0.9 - i * 0.05,
            processing_time=1.0 + i * 0.2,
            status=QAStatus.COMPLETED
        )
        
        await service.save_qa_pair(session_id, qa_response)
        print(f"  保存问答对到会话 {session_id[:8]}...")
        print(f"    问题: {sample_questions[i][:30]}...")
        print(f"    置信度: {qa_response.confidence_score}")
    print()
    
    # 演示3: 获取会话历史
    print("📚 演示3: 获取会话历史")
    for user_id, session_id in user_sessions:
        history = await service.get_session_history(session_id)
        print(f"  用户 {user_id} 的会话历史:")
        print(f"    会话ID: {session_id}")
        print(f"    问答对数量: {len(history)}")
        
        if history:
            latest_qa = history[0]  # 最新的问答对
            print(f"    最新问题: {latest_qa.question[:40]}...")
            print(f"    最新答案: {latest_qa.answer[:40]}...")
            print(f"    时间戳: {latest_qa.timestamp}")
        print()
    
    # 演示4: 会话活动更新
    print("🔄 演示4: 更新会话活动")
    test_session_id = user_sessions[0][1]
    update_result = await service.update_session_activity(test_session_id)
    print(f"  更新会话活动: {update_result}")
    
    # 获取更新后的会话信息
    updated_session = await service.get_session(test_session_id)
    if updated_session:
        print(f"  更新后的最后活动时间: {updated_session.last_activity}")
    print()
    
    # 演示5: 列出用户会话
    print("📋 演示5: 列出用户会话")
    for user_id in ["user_1", "user_2", "user_3"]:
        sessions = await service.list_sessions(user_id)
        print(f"  用户 {user_id} 的会话:")
        for session in sessions:
            print(f"    - 会话ID: {session.id}")
            print(f"      创建时间: {session.created_at}")
            print(f"      问答对数量: {session.qa_count}")
    print()
    
    # 演示6: 服务统计信息
    print("📊 演示6: 服务统计信息")
    stats = await service.get_service_stats()
    print(f"  服务名称: {stats['service_name']}")
    print(f"  总会话数: {stats['total_sessions']}")
    print(f"  总问答对数: {stats['total_qa_pairs']}")
    print(f"  已创建会话数: {stats['sessions_created']}")
    print(f"  已保存问答对数: {stats['qa_pairs_saved']}")
    print(f"  配置信息:")
    for key, value in stats['config'].items():
        print(f"    - {key}: {value}")
    print()
    
    # 演示7: 内置测试功能
    print("🧪 演示7: 内置测试功能")
    test_result = await service.test_session_management("演示测试问题")
    print(f"  测试结果: {'成功' if test_result['success'] else '失败'}")
    if test_result['success']:
        print(f"  测试会话ID: {test_result['session_created']}")
        print(f"  会话检索: {test_result['session_retrieved']}")
        print(f"  问答对保存: {test_result['qa_pair_saved']}")
        print(f"  历史记录数量: {test_result['history_count']}")
        print(f"  会话删除: {test_result['session_deleted']}")
    else:
        print(f"  错误信息: {test_result.get('error', 'Unknown error')}")
    print()
    
    # 演示8: 历史记录查询和管理
    print("🔍 演示8: 历史记录查询和管理")
    
    # 搜索问答对
    print("  8.1 搜索问答对:")
    search_results = await service.search_qa_pairs("人工智能", limit=10)
    print(f"    搜索'人工智能'结果: {len(search_results)} 个")
    
    if search_results:
        for i, qa in enumerate(search_results[:2], 1):
            print(f"    结果 {i}:")
            print(f"      问题: {qa.question[:30]}...")
            print(f"      置信度: {qa.confidence_score}")
            print(f"      时间: {qa.timestamp}")
    
    # 获取最近的问答对
    print("  8.2 获取最近问答对:")
    recent_qa = await service.get_recent_qa_pairs(limit=5)
    print(f"    最近 {len(recent_qa)} 个问答对:")
    
    for i, qa in enumerate(recent_qa, 1):
        print(f"    {i}. {qa.question[:25]}... (置信度: {qa.confidence_score})")
    
    # 获取会话统计信息
    print("  8.3 会话统计信息:")
    test_session_id = user_sessions[0][1]
    session_stats = await service.get_session_statistics(test_session_id)
    print(f"    会话ID: {test_session_id[:8]}...")
    print(f"    总问答对数: {session_stats['total_qa_pairs']}")
    print(f"    平均置信度: {session_stats['average_confidence_score']:.3f}")
    print(f"    平均处理时间: {session_stats['average_processing_time']:.3f}秒")
    print(f"    会话持续时间: {session_stats['session_duration_hours']:.2f}小时")
    
    # 删除单个问答对
    print("  8.4 删除单个问答对:")
    history = await service.get_session_history(test_session_id)
    if history:
        qa_to_delete = history[0]
        print(f"    删除问答对: {qa_to_delete.question[:30]}...")
        delete_result = await service.delete_qa_pair(qa_to_delete.id)
        print(f"    删除结果: {delete_result}")
        
        # 验证删除后的数量
        updated_history = await service.get_session_history(test_session_id)
        print(f"    删除后历史记录数量: {len(updated_history)}")
    print()
    
    # 演示9: 清理演示数据
    print("🧹 演示9: 清理演示数据")
    deleted_count = 0
    for user_id, session_id in user_sessions:
        delete_result = await service.delete_session(session_id)
        if delete_result:
            deleted_count += 1
            print(f"  删除会话: {session_id[:8]}... (用户: {user_id})")
    
    print(f"  总共删除了 {deleted_count} 个会话")
    print()
    
    # 最终统计
    print("📈 最终统计:")
    final_stats = await service.get_service_stats()
    print(f"  当前总会话数: {final_stats['total_sessions']}")
    print(f"  当前总问答对数: {final_stats['total_qa_pairs']}")
    print()
    
    # 清理资源
    await service.cleanup()
    
    print("=" * 60)
    print("演示完成！")
    print("=" * 60)
    print()
    print("💡 功能总结:")
    print("  ✓ 会话创建和管理")
    print("  ✓ 问答对保存和检索")
    print("  ✓ 会话历史记录管理")
    print("  ✓ 用户会话列表")
    print("  ✓ 会话活动更新")
    print("  ✓ 服务统计信息")
    print("  ✓ 内置测试功能")
    print("  ✓ 历史记录查询和搜索")
    print("  ✓ 单个问答对删除")
    print("  ✓ 会话统计分析")
    print("  ✓ 数据清理和资源管理")


if __name__ == "__main__":
    print("🚀 启动会话管理功能演示...")
    
    # 运行演示
    asyncio.run(demo_session_management())
    
    print("\n🎉 演示程序执行完成！")
    print("\n💡 提示:")
    print("  - 会话管理服务支持多用户")
    print("  - 自动清理过期会话")
    print("  - 支持会话数量和问答对数量限制")
    print("  - 提供完整的统计和监控功能")
    print("  - 支持历史记录搜索和分页")
    print("  - 支持单个问答对的精确删除")
    print("  - 提供详细的会话统计分析")
    print("  - 所有操作都经过全面测试")