#!/usr/bin/env python3
"""
统一模型管理器功能演示脚本

演示统一模型管理器的功能：
- 模型配置管理
- 模型加载和切换
- 健康检查和监控
- 统计信息收集
"""

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, Mock

from rag_system.services.model_manager import (
    ModelManager, 
    ModelConfig, 
    ModelType,
    initialize_global_model_manager,
    get_model_manager,
    cleanup_global_model_manager
)


async def create_demo_model_manager():
    """创建演示用的模型管理器"""
    config = {
        'auto_load_models': False,  # 手动控制加载
        'enable_model_switching': True,
        'model_cache_size': 3,
        'health_check_interval': 60,
        'default_embedding_models': [
            {
                'name': 'openai_embedding',
                'provider': 'openai',
                'model_name': 'text-embedding-ada-002',
                'config': {
                    'api_key': 'demo_key',
                    'batch_size': 100,
                    'max_tokens': 8192,
                    'timeout': 30
                },
                'enabled': True,
                'priority': 10
            },
            {
                'name': 'local_embedding',
                'provider': 'sentence_transformers',
                'model_name': 'all-MiniLM-L6-v2',
                'config': {
                    'device': 'cpu',
                    'batch_size': 64
                },
                'enabled': True,
                'priority': 8
            },
            {
                'name': 'fallback_embedding',
                'provider': 'mock',
                'model_name': 'mock-embedding',
                'config': {
                    'dimensions': 768,
                    'batch_size': 100
                },
                'enabled': True,
                'priority': 1
            }
        ],
        'default_reranking_models': [
            {
                'name': 'ms_marco_reranking',
                'provider': 'sentence_transformers',
                'model_name': 'cross-encoder/ms-marco-MiniLM-L-6-v2',
                'config': {
                    'max_length': 512,
                    'batch_size': 32,
                    'timeout': 30.0,
                    'device': 'cpu'
                },
                'enabled': True,
                'priority': 10
            },
            {
                'name': 'fast_reranking',
                'provider': 'sentence_transformers',
                'model_name': 'cross-encoder/ms-marco-TinyBERT-L-2-v2',
                'config': {
                    'max_length': 256,
                    'batch_size': 64,
                    'timeout': 15.0,
                    'device': 'cpu'
                },
                'enabled': True,
                'priority': 5
            }
        ]
    }
    
    manager = ModelManager(config)
    
    # 模拟模型加载方法
    async def mock_load_embedding_model(model_name, config):
        """模拟加载embedding模型"""
        print(f"  🔄 模拟加载embedding模型: {model_name} ({config.model_name})")
        await asyncio.sleep(0.1)  # 模拟加载时间
        
        # 创建模拟服务
        mock_service = AsyncMock()
        mock_service.test_embedding.return_value = {
            'success': True,
            'embedding_dimension': 768,
            'processing_time': 0.05
        }
        mock_service.get_service_stats.return_value = {
            'provider': config.provider,
            'model': config.model_name,
            'dimension': 768,
            'status': 'available'
        }
        
        manager.embedding_services[model_name] = mock_service
        return True
    
    async def mock_load_reranking_model(model_name, config):
        """模拟加载重排序模型"""
        print(f"  🔄 模拟加载重排序模型: {model_name} ({config.model_name})")
        await asyncio.sleep(0.2)  # 模拟加载时间
        
        # 创建模拟服务
        mock_service = Mock()
        mock_service.health_check = AsyncMock(return_value={
            'status': 'healthy',
            'model_loaded': True
        })
        mock_service.get_metrics.return_value = {
            'model_loaded': True,
            'model_name': config.model_name,
            'total_requests': 0,
            'successful_requests': 0,
            'success_rate': 0.0
        }
        mock_service.close = AsyncMock()
        
        manager.reranking_services[model_name] = mock_service
        return True
    
    # 替换加载方法
    manager._load_embedding_model = mock_load_embedding_model
    manager._load_reranking_model = mock_load_reranking_model
    
    return manager


async def demonstrate_model_management():
    """演示模型管理功能"""
    print("🚀 统一模型管理器功能演示")
    print("=" * 60)
    
    # 创建模型管理器
    manager = await create_demo_model_manager()
    await manager.initialize()
    
    print(f"📋 模型管理器初始化完成")
    print(f"   - 总模型数: {manager.stats['total_models']}")
    print(f"   - 自动加载: {'启用' if manager.auto_load_models else '禁用'}")
    print(f"   - 模型切换: {'启用' if manager.enable_model_switching else '禁用'}")
    print()
    
    # 1. 显示所有模型配置
    print("1️⃣ 模型配置概览:")
    print("-" * 40)
    
    configs = manager.get_model_configs()
    embedding_configs = {k: v for k, v in configs.items() if v.model_type == ModelType.EMBEDDING}
    reranking_configs = {k: v for k, v in configs.items() if v.model_type == ModelType.RERANKING}
    
    print(f"📊 Embedding模型 ({len(embedding_configs)}个):")
    for name, config in embedding_configs.items():
        status = "✅ 启用" if config.enabled else "❌ 禁用"
        print(f"   - {name}: {config.provider}/{config.model_name} (优先级: {config.priority}) {status}")
    
    print(f"\n🔄 重排序模型 ({len(reranking_configs)}个):")
    for name, config in reranking_configs.items():
        status = "✅ 启用" if config.enabled else "❌ 禁用"
        print(f"   - {name}: {config.provider}/{config.model_name} (优先级: {config.priority}) {status}")
    print()
    
    # 2. 加载模型
    print("2️⃣ 模型加载演示:")
    print("-" * 40)
    
    # 加载高优先级的embedding模型
    print("🔄 加载embedding模型...")
    embedding_models = ['openai_embedding', 'local_embedding', 'fallback_embedding']
    for model_name in embedding_models:
        success = await manager.load_model(model_name)
        status = "✅ 成功" if success else "❌ 失败"
        print(f"   - {model_name}: {status}")
    
    print("\n🔄 加载重排序模型...")
    reranking_models = ['ms_marco_reranking', 'fast_reranking']
    for model_name in reranking_models:
        success = await manager.load_model(model_name)
        status = "✅ 成功" if success else "❌ 失败"
        print(f"   - {model_name}: {status}")
    print()
    
    # 3. 模型状态检查
    print("3️⃣ 模型状态检查:")
    print("-" * 40)
    
    all_statuses = manager.get_all_model_statuses()
    for name, status in all_statuses.items():
        health_icon = {"healthy": "💚", "unhealthy": "❤️", "unknown": "💛"}.get(status.health, "❓")
        status_icon = {"ready": "✅", "loading": "🔄", "error": "❌", "unloaded": "⏹️"}.get(status.status, "❓")
        load_time = f" ({status.load_time:.2f}s)" if status.load_time else ""
        print(f"   {status_icon} {name}: {status.status} {health_icon} {status.health}{load_time}")
    print()
    
    # 4. 设置活跃模型
    print("4️⃣ 设置活跃模型:")
    print("-" * 40)
    
    # 设置活跃embedding模型
    success = await manager.switch_active_model(ModelType.EMBEDDING, 'openai_embedding')
    print(f"🎯 设置活跃embedding模型: openai_embedding {'✅' if success else '❌'}")
    
    # 设置活跃重排序模型
    success = await manager.switch_active_model(ModelType.RERANKING, 'ms_marco_reranking')
    print(f"🎯 设置活跃重排序模型: ms_marco_reranking {'✅' if success else '❌'}")
    print()
    
    # 5. 获取活跃服务
    print("5️⃣ 活跃服务测试:")
    print("-" * 40)
    
    embedding_service = manager.get_active_embedding_service()
    reranking_service = manager.get_active_reranking_service()
    
    print(f"📊 活跃embedding服务: {'✅ 可用' if embedding_service else '❌ 不可用'}")
    if embedding_service:
        print(f"   - 服务类型: EmbeddingService")
        print(f"   - 请求统计: {manager.stats['embedding_requests']} 次")
    
    print(f"🔄 活跃重排序服务: {'✅ 可用' if reranking_service else '❌ 不可用'}")
    if reranking_service:
        print(f"   - 服务类型: RerankingService")
        print(f"   - 请求统计: {manager.stats['reranking_requests']} 次")
    print()
    
    # 6. 模型切换演示
    print("6️⃣ 模型切换演示:")
    print("-" * 40)
    
    print("🔄 切换到本地embedding模型...")
    success = await manager.switch_active_model(ModelType.EMBEDDING, 'local_embedding')
    print(f"   结果: {'✅ 成功' if success else '❌ 失败'}")
    print(f"   当前活跃模型: {manager.active_embedding_model}")
    
    print("🔄 切换到快速重排序模型...")
    success = await manager.switch_active_model(ModelType.RERANKING, 'fast_reranking')
    print(f"   结果: {'✅ 成功' if success else '❌ 失败'}")
    print(f"   当前活跃模型: {manager.active_reranking_model}")
    print()
    
    # 7. 健康检查
    print("7️⃣ 健康检查:")
    print("-" * 40)
    
    print("🏥 执行健康检查...")
    await manager._perform_health_checks()
    
    healthy_count = sum(1 for status in all_statuses.values() if status.health == 'healthy')
    total_count = len(all_statuses)
    
    print(f"📊 健康检查结果: {healthy_count}/{total_count} 个模型健康")
    
    for name, status in all_statuses.items():
        if status.health == 'unhealthy' and status.error_message:
            print(f"   ⚠️ {name}: {status.error_message}")
    print()
    
    # 8. 管理器统计
    print("8️⃣ 管理器统计:")
    print("-" * 40)
    
    stats = manager.get_manager_stats()
    print(f"📈 统计信息:")
    print(f"   - 总模型数: {stats['total_models']}")
    print(f"   - 已加载模型: {stats['loaded_models']}")
    print(f"   - 失败模型: {stats['failed_models']}")
    print(f"   - 模型切换次数: {stats['model_switches']}")
    print(f"   - 总请求数: {stats['total_requests']}")
    print(f"   - Embedding请求: {stats['embedding_requests']}")
    print(f"   - 重排序请求: {stats['reranking_requests']}")
    print()
    
    print(f"🎯 活跃模型:")
    print(f"   - Embedding: {stats['active_embedding_model']}")
    print(f"   - 重排序: {stats['active_reranking_model']}")
    print()
    
    # 9. 注册新模型
    print("9️⃣ 动态注册新模型:")
    print("-" * 40)
    
    new_config = ModelConfig(
        model_type=ModelType.EMBEDDING,
        name="custom_embedding",
        provider="huggingface",
        model_name="sentence-transformers/all-mpnet-base-v2",
        config={
            "device": "cpu",
            "batch_size": 32,
            "normalize_embeddings": True
        },
        enabled=True,
        priority=7
    )
    
    success = await manager.register_model(new_config)
    print(f"📝 注册新模型: custom_embedding {'✅ 成功' if success else '❌ 失败'}")
    
    if success:
        print(f"   - 模型类型: {new_config.model_type.value}")
        print(f"   - 提供商: {new_config.provider}")
        print(f"   - 模型名: {new_config.model_name}")
        print(f"   - 优先级: {new_config.priority}")
        
        # 尝试加载新模型
        load_success = await manager.load_model("custom_embedding")
        print(f"   - 加载结果: {'✅ 成功' if load_success else '❌ 失败'}")
    print()
    
    # 10. 综合状态报告
    print("🔟 综合状态报告:")
    print("-" * 40)
    
    comprehensive_status = await manager.get_comprehensive_status()
    
    print(f"📊 系统概览:")
    manager_stats = comprehensive_status['manager_stats']
    print(f"   - 模型总数: {manager_stats['total_models']}")
    print(f"   - Embedding服务: {manager_stats['total_embedding_services']}")
    print(f"   - 重排序服务: {manager_stats['total_reranking_services']}")
    
    active_models = comprehensive_status['active_models']
    print(f"   - 活跃Embedding: {active_models['embedding']}")
    print(f"   - 活跃重排序: {active_models['reranking']}")
    print()
    
    # 11. 资源清理
    print("1️⃣1️⃣ 资源清理:")
    print("-" * 40)
    
    print("🧹 开始清理模型管理器资源...")
    await manager.cleanup()
    
    print("✅ 资源清理完成")
    print(f"   - Embedding服务: {len(manager.embedding_services)} 个")
    print(f"   - 重排序服务: {len(manager.reranking_services)} 个")
    print(f"   - 模型状态: {len(manager.model_statuses)} 个")
    print()
    
    print("✅ 统一模型管理器功能演示完成！")
    print("=" * 60)


async def demonstrate_global_model_manager():
    """演示全局模型管理器"""
    print("\n🌍 全局模型管理器演示:")
    print("-" * 40)
    
    # 清理可能存在的全局实例
    await cleanup_global_model_manager()
    
    # 初始化全局模型管理器
    config = {
        'auto_load_models': False,
        'default_embedding_models': [
            {
                'name': 'global_embedding',
                'provider': 'mock',
                'model_name': 'global-mock-embedding',
                'config': {'dimensions': 512},
                'enabled': True,
                'priority': 10
            }
        ]
    }
    
    print("🔄 初始化全局模型管理器...")
    global_manager = await initialize_global_model_manager(config)
    
    print(f"✅ 全局管理器初始化完成")
    print(f"   - 管理器实例: {type(global_manager).__name__}")
    print(f"   - 模型配置数: {len(global_manager.model_configs)}")
    
    # 获取全局管理器
    retrieved_manager = get_model_manager()
    print(f"🔍 获取全局管理器: {'✅ 成功' if retrieved_manager is global_manager else '❌ 失败'}")
    
    # 清理全局管理器
    print("🧹 清理全局模型管理器...")
    await cleanup_global_model_manager()
    
    final_manager = get_model_manager()
    print(f"✅ 清理完成: {'✅ 成功' if final_manager is None else '❌ 失败'}")


async def main():
    """主函数"""
    try:
        await demonstrate_model_management()
        await demonstrate_global_model_manager()
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())