#!/usr/bin/env python3
"""
测试检索功能的三个配置参数实现状态：
1. 搜索模式 (search_mode)
2. 启用重排序 (enable_rerank) 
3. 启用检索缓存 (enable_cache)
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag_system.services.retrieval_service import RetrievalService
from rag_system.models.config import RetrievalConfig

async def test_search_mode_implementation():
    """测试搜索模式功能实现"""
    print("🔍 测试搜索模式功能实现...")
    
    # 检查RetrievalService是否有对应的方法
    service = RetrievalService()
    
    # 检查是否有不同搜索模式的方法
    has_semantic = hasattr(service, 'search_similar_documents')
    has_keyword = hasattr(service, 'search_by_keywords') 
    has_hybrid = hasattr(service, 'hybrid_search')
    
    print(f"  语义搜索方法: {'✅ 存在' if has_semantic else '❌ 缺失'}")
    print(f"  关键词搜索方法: {'✅ 存在' if has_keyword else '❌ 缺失'}")
    print(f"  混合搜索方法: {'✅ 存在' if has_hybrid else '❌ 缺失'}")
    
    # 检查是否有根据search_mode选择搜索方法的逻辑
    import inspect
    source = inspect.getsource(RetrievalService)
    
    has_mode_logic = 'search_mode' in source and ('semantic' in source or 'keyword' in source or 'hybrid' in source)
    print(f"  搜索模式选择逻辑: {'❌ 未实现' if not has_mode_logic else '⚠️  可能存在'}")
    
    return {
        'semantic_method': has_semantic,
        'keyword_method': has_keyword, 
        'hybrid_method': has_hybrid,
        'mode_selection_logic': has_mode_logic
    }

async def test_rerank_implementation():
    """测试重排序功能实现"""
    print("\\n🔄 测试重排序功能实现...")
    
    service = RetrievalService()
    
    # 检查是否有重排序相关的方法
    has_rerank_method = hasattr(service, 'rerank_results') or hasattr(service, '_rerank')
    print(f"  重排序方法: {'✅ 存在' if has_rerank_method else '❌ 缺失'}")
    
    # 检查源码中是否有重排序逻辑
    import inspect
    source = inspect.getsource(RetrievalService)
    
    has_rerank_logic = 'rerank' in source.lower() or 'enable_rerank' in source
    print(f"  重排序逻辑: {'✅ 存在' if has_rerank_logic else '❌ 缺失'}")
    
    # 检查是否有重排序相关的依赖
    try:
        # 常见的重排序库
        import sentence_transformers
        has_rerank_lib = True
    except ImportError:
        has_rerank_lib = False
    
    print(f"  重排序库依赖: {'✅ 已安装' if has_rerank_lib else '❌ 未安装'}")
    
    return {
        'rerank_method': has_rerank_method,
        'rerank_logic': has_rerank_logic,
        'rerank_library': has_rerank_lib
    }

async def test_cache_implementation():
    """测试缓存功能实现"""
    print("\\n💾 测试缓存功能实现...")
    
    service = RetrievalService()
    
    # 检查是否有缓存相关的属性或方法
    has_cache_attr = hasattr(service, 'cache') or hasattr(service, '_cache')
    has_cache_method = hasattr(service, 'get_cached_result') or hasattr(service, '_get_cache')
    
    print(f"  缓存属性: {'✅ 存在' if has_cache_attr else '❌ 缺失'}")
    print(f"  缓存方法: {'✅ 存在' if has_cache_method else '❌ 缺失'}")
    
    # 检查源码中是否有缓存逻辑
    import inspect
    source = inspect.getsource(RetrievalService)
    
    has_cache_logic = 'cache' in source.lower() or 'enable_cache' in source
    print(f"  缓存逻辑: {'✅ 存在' if has_cache_logic else '❌ 缺失'}")
    
    # 检查是否有缓存相关的依赖
    has_cache_lib = False
    cache_libs = ['redis', 'memcached', 'diskcache']
    
    for lib in cache_libs:
        try:
            __import__(lib)
            has_cache_lib = True
            print(f"  缓存库 {lib}: ✅ 已安装")
            break
        except ImportError:
            continue
    
    if not has_cache_lib:
        print(f"  缓存库依赖: ❌ 未安装常见缓存库")
    
    return {
        'cache_attribute': has_cache_attr,
        'cache_method': has_cache_method,
        'cache_logic': has_cache_logic,
        'cache_library': has_cache_lib
    }

async def test_config_usage():
    """测试配置参数的实际使用"""
    print("\\n⚙️  测试配置参数的实际使用...")
    
    # 创建不同配置的检索服务实例
    configs = [
        {'search_mode': 'semantic', 'enable_rerank': True, 'enable_cache': True},
        {'search_mode': 'keyword', 'enable_rerank': False, 'enable_cache': False},
        {'search_mode': 'hybrid', 'enable_rerank': True, 'enable_cache': True}
    ]
    
    config_usage_results = []
    
    for i, config in enumerate(configs):
        print(f"  测试配置 {i+1}: {config}")
        
        try:
            # 创建检索配置
            retrieval_config = RetrievalConfig.from_dict(config)
            print(f"    配置创建: ✅ 成功")
            
            # 检查配置是否被正确设置
            print(f"    search_mode: {retrieval_config.search_mode}")
            print(f"    enable_rerank: {retrieval_config.enable_rerank}")
            print(f"    enable_cache: {retrieval_config.enable_cache}")
            
            config_usage_results.append({
                'config': config,
                'creation_success': True,
                'values_correct': (
                    retrieval_config.search_mode == config['search_mode'] and
                    retrieval_config.enable_rerank == config['enable_rerank'] and
                    retrieval_config.enable_cache == config['enable_cache']
                )
            })
            
        except Exception as e:
            print(f"    配置创建: ❌ 失败 - {str(e)}")
            config_usage_results.append({
                'config': config,
                'creation_success': False,
                'error': str(e)
            })
    
    return config_usage_results

async def analyze_implementation_gaps():
    """分析实现缺口"""
    print("\\n📊 分析实现缺口...")
    
    # 运行所有测试
    search_mode_results = await test_search_mode_implementation()
    rerank_results = await test_rerank_implementation()
    cache_results = await test_cache_implementation()
    config_results = await test_config_usage()
    
    # 分析结果
    gaps = []
    
    # 搜索模式分析
    if not search_mode_results['mode_selection_logic']:
        gaps.append({
            'feature': '搜索模式选择',
            'issue': '缺少根据search_mode配置选择不同搜索方法的逻辑',
            'impact': '用户设置的搜索模式不会生效',
            'suggestion': '在检索服务中添加根据search_mode选择搜索方法的逻辑'
        })
    
    # 重排序分析
    if not rerank_results['rerank_logic']:
        gaps.append({
            'feature': '重排序功能',
            'issue': '缺少重排序功能的实现',
            'impact': 'enable_rerank配置不会生效',
            'suggestion': '实现重排序功能，可使用sentence-transformers等库'
        })
    
    # 缓存分析
    if not cache_results['cache_logic']:
        gaps.append({
            'feature': '检索缓存',
            'issue': '缺少缓存功能的实现',
            'impact': 'enable_cache配置不会生效，无法提高检索性能',
            'suggestion': '实现检索结果缓存，可使用Redis或内存缓存'
        })
    
    return gaps

async def main():
    """主函数"""
    print("🚀 开始检测检索功能的三个配置参数实现状态...")
    print("=" * 60)
    
    # 运行测试
    search_mode_results = await test_search_mode_implementation()
    rerank_results = await test_rerank_implementation()
    cache_results = await test_cache_implementation()
    config_results = await test_config_usage()
    
    # 分析实现缺口
    gaps = await analyze_implementation_gaps()
    
    print("\\n" + "=" * 60)
    print("📋 实现状态总结:")
    print("=" * 60)
    
    # 搜索模式状态
    search_mode_status = "🟡 部分实现" if search_mode_results['semantic_method'] and search_mode_results['keyword_method'] and search_mode_results['hybrid_method'] else "❌ 未实现"
    print(f"1. 搜索模式 (search_mode): {search_mode_status}")
    print(f"   - 语义搜索: {'✅' if search_mode_results['semantic_method'] else '❌'}")
    print(f"   - 关键词搜索: {'✅' if search_mode_results['keyword_method'] else '❌'}")
    print(f"   - 混合搜索: {'✅' if search_mode_results['hybrid_method'] else '❌'}")
    print(f"   - 模式选择逻辑: {'❌ 缺失' if not search_mode_results['mode_selection_logic'] else '⚠️  需确认'}")
    
    # 重排序状态
    rerank_status = "✅ 已实现" if rerank_results['rerank_logic'] else "❌ 未实现"
    print(f"\\n2. 重排序功能 (enable_rerank): {rerank_status}")
    print(f"   - 重排序方法: {'✅' if rerank_results['rerank_method'] else '❌'}")
    print(f"   - 重排序逻辑: {'✅' if rerank_results['rerank_logic'] else '❌'}")
    print(f"   - 依赖库: {'✅' if rerank_results['rerank_library'] else '❌'}")
    
    # 缓存状态
    cache_status = "✅ 已实现" if cache_results['cache_logic'] else "❌ 未实现"
    print(f"\\n3. 检索缓存 (enable_cache): {cache_status}")
    print(f"   - 缓存属性: {'✅' if cache_results['cache_attribute'] else '❌'}")
    print(f"   - 缓存方法: {'✅' if cache_results['cache_method'] else '❌'}")
    print(f"   - 缓存逻辑: {'✅' if cache_results['cache_logic'] else '❌'}")
    print(f"   - 依赖库: {'✅' if cache_results['cache_library'] else '❌'}")
    
    # 配置使用状态
    config_success = all(result['creation_success'] for result in config_results)
    print(f"\\n4. 配置参数使用: {'✅ 正常' if config_success else '❌ 异常'}")
    
    # 实现缺口
    if gaps:
        print("\\n" + "=" * 60)
        print("⚠️  发现的实现缺口:")
        print("=" * 60)
        
        for i, gap in enumerate(gaps, 1):
            print(f"\\n{i}. {gap['feature']}")
            print(f"   问题: {gap['issue']}")
            print(f"   影响: {gap['impact']}")
            print(f"   建议: {gap['suggestion']}")
    
    # 总结
    print("\\n" + "=" * 60)
    print("🎯 总结:")
    print("=" * 60)
    
    implemented_count = sum([
        1 if search_mode_results['mode_selection_logic'] else 0,
        1 if rerank_results['rerank_logic'] else 0,
        1 if cache_results['cache_logic'] else 0
    ])
    
    print(f"✅ 已实现功能: {implemented_count}/3")
    print(f"❌ 未实现功能: {3 - implemented_count}/3")
    
    if implemented_count == 3:
        print("\\n🎉 所有功能都已实现！")
    elif implemented_count > 0:
        print("\\n🟡 部分功能已实现，需要完善其余功能")
    else:
        print("\\n⚠️  三个功能都需要实现")
    
    print("\\n💡 建议:")
    print("   1. 优先实现搜索模式选择逻辑，这是用户最直观的功能")
    print("   2. 实现检索缓存可以显著提高性能")
    print("   3. 重排序功能可以提高检索准确性")

if __name__ == "__main__":
    asyncio.run(main())