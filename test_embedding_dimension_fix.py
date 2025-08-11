#!/usr/bin/env python3
"""
嵌入维度参数保存测试

测试前端修改嵌入维度参数后是否能正确保存到配置文件
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


def read_config_file():
    """读取当前配置文件"""
    config_path = Path("config/development.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


async def test_embedding_dimension_update():
    """测试嵌入维度参数更新"""
    print_section("测试嵌入维度参数更新")
    
    base_url = "http://localhost:8000"
    
    # 1. 读取当前配置
    print("1. 读取当前配置文件")
    current_config = read_config_file()
    if current_config:
        current_dimensions = current_config.get('embeddings', {}).get('dimensions', 'unknown')
        print(f"   📋 当前维度: {current_dimensions}")
    else:
        print("   ❌ 无法读取配置文件")
        return False
    
    # 2. 模拟前端发送的配置更新请求
    print("\n2. 模拟前端配置更新请求")
    new_dimensions = 2048  # 新的维度值
    
    # 模拟前端collectFormData()函数收集的数据
    settings_data = {
        "app": {
            "name": "RAG Knowledge QA System (Dev)",
            "debug": True
        },
        "llm": {
            "provider": "siliconflow",
            "model": "Qwen/Qwen3-8B",
            "api_key": "test-key-save-fix",
            "base_url": "",
            "temperature": 0.8,
            "max_tokens": 1024
        },
        "embeddings": {
            "provider": "siliconflow",
            "model": "BAAI/bge-large-zh-v1.5",
            "api_key": "sk-test-update-123456789",
            "base_url": "https://api.siliconflow.cn/v1",
            "dimensions": new_dimensions,  # 这是我们要测试的新维度值
            "batch_size": 50,
            "chunk_size": 1000,
            "chunk_overlap": 50,
            "timeout": 120
        },
        "reranking": {
            "provider": "siliconflow",
            "model": "BAAI/bge-reranker-v2-m3",
            "api_key": "sk-test-update-123456789",
            "base_url": "https://api.siliconflow.cn/v1",
            "batch_size": 30,
            "max_length": 512,
            "timeout": 60
        },
        "retrieval": {
            "top_k": 15,
            "similarity_threshold": 0.25,
            "search_mode": "semantic",
            "enable_rerank": False,
            "enable_cache": False
        },
        "vector_store": {
            "type": "chroma",
            "persist_directory": "./chroma_db",
            "collection_name": "documents"
        },
        "database": {
            "url": "sqlite:///./database/rag_system.db",
            "echo": True
        },
        "advanced": {
            "max_concurrent_requests": 50,
            "request_timeout": 30,
            "cache_size": 100,
            "log_level": "DEBUG",
            "enable_metrics": True,
            "enable_debug_mode": True
        }
    }
    
    print(f"   📤 准备发送新维度值: {new_dimensions}")
    
    # 3. 发送配置更新请求
    print("\n3. 发送配置更新请求")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{base_url}/config/all",
                json=settings_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 配置更新成功")
                    print(f"   📋 响应: {result.get('message', 'No message')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 配置更新失败 (状态码: {response.status})")
                    print(f"   📋 错误: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        print(f"   💡 请确保后端服务正在运行: python -m rag_system.api.main")
        return False
    
    # 4. 验证配置文件是否已更新
    print("\n4. 验证配置文件更新")
    import time
    time.sleep(1)  # 等待文件写入完成
    
    updated_config = read_config_file()
    if updated_config:
        updated_dimensions = updated_config.get('embeddings', {}).get('dimensions', 'unknown')
        print(f"   📋 更新后维度: {updated_dimensions}")
        
        if updated_dimensions == new_dimensions:
            print(f"   ✅ 维度参数已成功更新到配置文件")
            return True
        else:
            print(f"   ❌ 维度参数未正确更新")
            print(f"   📋 期望值: {new_dimensions}")
            print(f"   📋 实际值: {updated_dimensions}")
            return False
    else:
        print("   ❌ 无法读取更新后的配置文件")
        return False


async def test_api_validation():
    """测试API验证功能"""
    print_section("测试API验证功能")
    
    base_url = "http://localhost:8000"
    
    # 测试配置验证端点
    print("1. 测试配置验证端点")
    test_config = {
        "section": "embeddings",
        "config": {
            "provider": "siliconflow",
            "model": "BAAI/bge-large-zh-v1.5",
            "dimensions": 2048,  # 测试新维度值
            "batch_size": 50
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/config/validate",
                json=test_config,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 配置验证成功")
                    print(f"   📋 验证结果: valid={result.get('valid', False)}")
                    if result.get('errors'):
                        print(f"   ⚠️  验证错误: {result['errors']}")
                    return result.get('valid', False)
                else:
                    error_text = await response.text()
                    print(f"   ❌ 配置验证失败 (状态码: {response.status})")
                    print(f"   📋 错误: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 验证请求失败: {str(e)}")
        return False


def test_frontend_form_data():
    """测试前端表单数据收集"""
    print_section("测试前端表单数据收集")
    
    # 模拟前端JavaScript中的数据收集逻辑
    print("1. 模拟前端数据收集")
    
    # 模拟DOM元素值
    mock_form_values = {
        'embeddingDimension': '2048',  # 这是用户在前端输入的新值
        'embeddingModel': 'BAAI/bge-large-zh-v1.5',
        'modelProvider': 'siliconflow',
        'modelApiKey': 'sk-test-update-123456789',
        'modelBaseUrl': 'https://api.siliconflow.cn/v1',
        'embeddingBatchSize': '50',
        'chunkSize': '1000',
        'chunkOverlap': '50',
        'embeddingTimeout': '120'
    }
    
    # 模拟前端collectFormData()中的嵌入配置部分
    embeddings_config = {
        'provider': mock_form_values['modelProvider'],
        'model': mock_form_values['embeddingModel'],
        'api_key': mock_form_values['modelApiKey'],
        'base_url': mock_form_values['modelBaseUrl'],
        'dimensions': int(mock_form_values['embeddingDimension']),  # 关键：维度参数
        'batch_size': int(mock_form_values['embeddingBatchSize']),
        'chunk_size': int(mock_form_values['chunkSize']),
        'chunk_overlap': int(mock_form_values['chunkOverlap']),
        'timeout': float(mock_form_values['embeddingTimeout'])
    }
    
    print(f"   📋 模拟前端收集的嵌入配置:")
    for key, value in embeddings_config.items():
        print(f"      {key}: {value} ({type(value).__name__})")
    
    # 验证维度参数类型和值
    dimensions = embeddings_config['dimensions']
    if isinstance(dimensions, int) and dimensions > 0:
        print(f"   ✅ 维度参数格式正确: {dimensions} (int)")
        return True
    else:
        print(f"   ❌ 维度参数格式错误: {dimensions} ({type(dimensions).__name__})")
        return False


async def main():
    """主函数"""
    print("🚀 嵌入维度参数保存测试")
    print("测试前端修改嵌入维度参数后是否能正确保存到配置文件")
    
    results = []
    
    try:
        # 1. 测试前端表单数据收集
        results.append(test_frontend_form_data())
        
        # 2. 测试API验证功能
        results.append(await test_api_validation())
        
        # 3. 测试完整的配置更新流程
        results.append(await test_embedding_dimension_update())
        
        print_section("测试总结")
        
        if all(results):
            print("✅ 所有测试通过！")
            print("🎯 嵌入维度参数保存功能正常工作:")
            print("   - 前端数据收集: 正确处理维度参数")
            print("   - API验证: 正确验证配置格式")
            print("   - 配置保存: 成功保存到配置文件")
            
            print("\n💡 使用说明:")
            print("   1. 在前端设置页面修改嵌入维度值")
            print("   2. 点击保存设置按钮")
            print("   3. 配置会自动保存到 config/development.yaml")
            print("   4. 重启服务后新配置生效")
            
        else:
            print("❌ 部分测试失败")
            print("请检查以下可能的问题:")
            print("   - 后端服务是否正在运行")
            print("   - 配置文件是否有写入权限")
            print("   - API端点是否正确实现")
            print("   - 前端JavaScript是否正确收集数据")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)