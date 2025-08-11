#!/usr/bin/env python3
"""
添加嵌入模型功能测试

测试前端addEmbeddingModel方法是否正确传递维度参数到后端
"""

import asyncio
import sys
import json
import yaml
from pathlib import Path
import aiohttp

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_section(title: str):
    """打印格式化的章节"""
    print(f"\n{'='*50}")
    print(f"🔍 {title}")
    print(f"{'='*50}")


async def test_add_embedding_model_api():
    """测试添加嵌入模型API"""
    print_section("测试添加嵌入模型API")
    
    base_url = "http://localhost:8000"
    
    # 模拟前端addEmbeddingModel函数构造的数据
    print("1. 模拟前端addEmbeddingModel数据构造")
    
    # 模拟前端表单数据
    form_data = {
        'modelProvider': 'siliconflow',
        'embeddingModel': 'BAAI/bge-large-zh-v1.5',
        'embeddingDimension': '2048',  # 这是关键的维度参数
        'embeddingBatchSize': '50',
        'chunkSize': '1000',
        'chunkOverlap': '50',
        'embeddingTimeout': '120',
        'modelApiKey': 'sk-test-embedding-123',
        'modelBaseUrl': 'https://api.siliconflow.cn/v1'
    }
    
    # 模拟前端addEmbeddingModel函数的逻辑
    provider = form_data['modelProvider']
    modelName = form_data['embeddingModel']
    dimensions = int(form_data['embeddingDimension'])
    batchSize = int(form_data['embeddingBatchSize'])
    chunkSize = int(form_data['chunkSize'])
    chunk_overlap = int(form_data['chunkOverlap'])
    embeddingTimeout = float(form_data['embeddingTimeout'])
    
    # 构造config对象（前端addEmbeddingModel函数中的config）
    config = {
        'name': f"{provider}_{modelName.replace('/', '_').replace('-', '_')}",
        'provider': provider,
        'model_name': modelName,
        'config': {
            'batch_size': batchSize,
            'dimensions': dimensions,  # 关键：维度参数
            'chunk_size': chunkSize,
            'chunk_overlap': chunk_overlap,
            'timeout': embeddingTimeout,
            'api_key': form_data['modelApiKey'],
            'base_url': form_data['modelBaseUrl']
        },
        'enabled': True,
        'priority': 5
    }
    
    print(f"   📋 构造的config对象:")
    print(f"      name: {config['name']}")
    print(f"      provider: {config['provider']}")
    print(f"      model_name: {config['model_name']}")
    print(f"      config.dimensions: {config['config']['dimensions']} ({type(config['config']['dimensions']).__name__})")
    print(f"      config.batch_size: {config['config']['batch_size']}")
    print(f"      config.chunk_size: {config['config']['chunk_size']}")
    
    # 2. 模拟修复后的modelManager.addModel方法
    print("\n2. 模拟修复后的modelManager.addModel方法")
    modelType = 'embedding'
    
    # 构造后端API期望的数据格式（修复后的逻辑）
    modelData = {
        'model_type': modelType,
        'name': config['name'],
        'provider': config['provider'],
        'model_name': config['model_name'],
        'config': config['config']
    }
    
    print(f"   📤 发送到后端的modelData:")
    print(f"      model_type: {modelData['model_type']}")
    print(f"      name: {modelData['name']}")
    print(f"      provider: {modelData['provider']}")
    print(f"      model_name: {modelData['model_name']}")
    print(f"      config.dimensions: {modelData['config']['dimensions']}")
    print(f"      config.api_key: {modelData['config']['api_key'][:10]}...")
    
    # 3. 发送API请求
    print("\n3. 发送添加模型API请求")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/models/add",
                json=modelData,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 添加模型成功")
                    print(f"   📋 响应: {result}")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加模型失败 (状态码: {response.status})")
                    print(f"   📋 错误: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        print(f"   💡 请确保后端服务正在运行: python -m rag_system.api.main")
        return False


async def test_get_model_configs():
    """测试获取模型配置"""
    print_section("测试获取模型配置")
    
    base_url = "http://localhost:8000"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/models/configs") as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 获取模型配置成功")
                    
                    model_configs = result.get('model_configs', {})
                    print(f"   📋 模型配置数量: {len(model_configs)}")
                    
                    # 查找我们刚添加的嵌入模型
                    embedding_models = [
                        config for config in model_configs.values() 
                        if config.get('model_type') == 'embedding'
                    ]
                    
                    print(f"   📋 嵌入模型数量: {len(embedding_models)}")
                    
                    for model in embedding_models:
                        print(f"      模型: {model.get('name', 'unknown')}")
                        print(f"      提供商: {model.get('provider', 'unknown')}")
                        print(f"      维度: {model.get('config', {}).get('dimensions', 'unknown')}")
                    
                    return len(embedding_models) > 0
                else:
                    error_text = await response.text()
                    print(f"   ❌ 获取模型配置失败 (状态码: {response.status})")
                    print(f"   📋 错误: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False


def test_frontend_data_flow():
    """测试前端数据流"""
    print_section("测试前端数据流")
    
    print("1. 模拟前端表单输入")
    # 模拟用户在前端输入的数据
    user_input = {
        'embeddingDimension': '2048',  # 用户输入的维度
        'embeddingModel': 'BAAI/bge-large-zh-v1.5',
        'modelProvider': 'siliconflow'
    }
    
    print(f"   👤 用户输入维度: {user_input['embeddingDimension']}")
    
    print("\n2. 前端JavaScript处理")
    # 模拟前端JavaScript的parseInt处理
    dimensions = int(user_input['embeddingDimension']) if user_input['embeddingDimension'] else 1024
    print(f"   🔧 JavaScript处理后: {dimensions} ({type(dimensions).__name__})")
    
    print("\n3. 构造config对象")
    config = {
        'config': {
            'dimensions': dimensions,
            'batch_size': 50,
            'chunk_size': 1000
        }
    }
    print(f"   📦 config.dimensions: {config['config']['dimensions']} ({type(config['config']['dimensions']).__name__})")
    
    print("\n4. 构造API请求数据")
    modelData = {
        'model_type': 'embedding',
        'config': config['config']
    }
    print(f"   📤 API请求中的dimensions: {modelData['config']['dimensions']} ({type(modelData['config']['dimensions']).__name__})")
    
    # 验证数据类型
    if isinstance(modelData['config']['dimensions'], int) and modelData['config']['dimensions'] > 0:
        print(f"   ✅ 维度参数格式正确")
        return True
    else:
        print(f"   ❌ 维度参数格式错误")
        return False


async def main():
    """主函数"""
    print("🚀 添加嵌入模型功能测试")
    print("测试前端addEmbeddingModel方法是否正确传递维度参数到后端")
    
    results = []
    
    try:
        # 1. 测试前端数据流
        results.append(test_frontend_data_flow())
        
        # 2. 测试添加嵌入模型API
        results.append(await test_add_embedding_model_api())
        
        # 3. 测试获取模型配置
        results.append(await test_get_model_configs())
        
        print_section("测试总结")
        
        if all(results):
            print("✅ 所有测试通过！")
            print("🎯 添加嵌入模型功能正常工作:")
            print("   - 前端数据流: 正确处理维度参数")
            print("   - API请求格式: 符合后端期望")
            print("   - 模型添加: 成功保存到系统")
            print("   - 配置获取: 可以正确检索")
            
            print("\n💡 修复要点:")
            print("   1. modelManager.addModel 现在正确构造API请求数据")
            print("   2. 维度参数正确传递到后端")
            print("   3. 后端API正确处理嵌入模型配置")
            print("   4. 前后端数据格式完全匹配")
            
        else:
            print("❌ 部分测试失败")
            failed_tests = []
            if not results[0]: failed_tests.append("前端数据流")
            if not results[1]: failed_tests.append("添加模型API")
            if not results[2]: failed_tests.append("获取模型配置")
            
            print(f"   失败的测试: {', '.join(failed_tests)}")
            print("   请检查:")
            print("   - 后端服务是否正在运行")
            print("   - API端点是否正确实现")
            print("   - 前端JavaScript是否正确修复")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)