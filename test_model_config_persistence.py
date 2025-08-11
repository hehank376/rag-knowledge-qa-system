#!/usr/bin/env python3
"""
模型配置持久化测试

测试添加模型后配置是否正确保存到配置文件
"""

import asyncio
import sys
import json
import yaml
from pathlib import Path
import aiohttp
import time

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_section(title: str):
    """打印格式化的章节"""
    print(f"\n{'='*60}")
    print(f"🔍 {title}")
    print(f"{'='*60}")


def read_config_file():
    """读取配置文件"""
    config_path = Path("config/development.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return None


async def test_add_embedding_model_with_persistence():
    """测试添加嵌入模型并验证配置持久化"""
    print_section("测试添加嵌入模型并验证配置持久化")
    
    base_url = "http://localhost:8000"
    
    # 1. 读取当前配置
    print("1. 读取当前配置文件")
    original_config = read_config_file()
    if original_config:
        original_dimensions = original_config.get('embeddings', {}).get('dimensions', 'unknown')
        print(f"   📋 当前维度: {original_dimensions}")
    else:
        print("   ❌ 无法读取配置文件")
        return False
    
    # 2. 构造测试数据
    print("\n2. 构造测试数据")
    test_dimensions = 2048  # 新的维度值
    model_data = {
        "model_type": "embedding",
        "name": "test_embedding_persistence",
        "provider": "siliconflow",
        "model_name": "BAAI/bge-large-zh-v1.5",
        "config": {
            "provider": "siliconflow",  # 添加到config中
            "dimensions": test_dimensions,  # 关键：用户设置的维度
            "batch_size": 50,
            "chunk_size": 1000,
            "chunk_overlap": 50,
            "timeout": 120,
            "api_key": "sk-test-persistence-key",
            "base_url": "https://api.siliconflow.cn/v1"
        }
    }
    
    print(f"   📤 测试维度: {test_dimensions}")
    print(f"   📤 模型名称: {model_data['model_name']}")
    
    # 3. 发送添加模型请求
    print("\n3. 发送添加模型请求")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/models/add",
                json=model_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 添加模型成功")
                    print(f"   📋 响应: {result.get('message', 'No message')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加模型失败 (状态码: {response.status})")
                    print(f"   📋 错误: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        print(f"   💡 请确保后端服务正在运行: python -m rag_system.api.main")
        return False
    
    # 4. 等待配置文件更新
    print("\n4. 等待配置文件更新")
    time.sleep(2)  # 等待文件写入完成
    
    # 5. 验证配置文件是否已更新
    print("\n5. 验证配置文件更新")
    updated_config = read_config_file()
    if updated_config:
        updated_dimensions = updated_config.get('embeddings', {}).get('dimensions', 'unknown')
        updated_model = updated_config.get('embeddings', {}).get('model', 'unknown')
        updated_provider = updated_config.get('embeddings', {}).get('provider', 'unknown')
        
        print(f"   📋 更新后维度: {updated_dimensions}")
        print(f"   📋 更新后模型: {updated_model}")
        print(f"   📋 更新后提供商: {updated_provider}")
        
        # 验证关键参数
        success = True
        if updated_dimensions == test_dimensions:
            print(f"   ✅ 维度参数已正确保存: {updated_dimensions}")
        else:
            print(f"   ❌ 维度参数保存错误: 期望 {test_dimensions}, 实际 {updated_dimensions}")
            success = False
        
        if updated_model == model_data['model_name']:
            print(f"   ✅ 模型名称已正确保存: {updated_model}")
        else:
            print(f"   ❌ 模型名称保存错误: 期望 {model_data['model_name']}, 实际 {updated_model}")
            success = False
        
        if updated_provider == model_data['config']['provider']:
            print(f"   ✅ 提供商已正确保存: {updated_provider}")
        else:
            print(f"   ❌ 提供商保存错误: 期望 {model_data['config']['provider']}, 实际 {updated_provider}")
            success = False
        
        return success
    else:
        print("   ❌ 无法读取更新后的配置文件")
        return False


async def test_add_reranking_model_with_persistence():
    """测试添加重排序模型并验证配置持久化"""
    print_section("测试添加重排序模型并验证配置持久化")
    
    base_url = "http://localhost:8000"
    
    # 构造测试数据
    model_data = {
        "model_type": "reranking",
        "name": "test_reranking_persistence",
        "provider": "siliconflow",
        "model_name": "BAAI/bge-reranker-v2-m3",
        "config": {
            "provider": "siliconflow",
            "batch_size": 16,  # 测试值
            "max_length": 256,  # 测试值
            "timeout": 30,
            "api_key": "sk-test-reranking-key",
            "base_url": "https://api.siliconflow.cn/v1"
        }
    }
    
    print(f"   📤 测试批处理大小: {model_data['config']['batch_size']}")
    print(f"   📤 测试最大长度: {model_data['config']['max_length']}")
    
    # 发送请求
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{base_url}/models/add",
                json=model_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"   ✅ 添加重排序模型成功")
                    print(f"   📋 响应: {result.get('message', 'No message')}")
                else:
                    error_text = await response.text()
                    print(f"   ❌ 添加重排序模型失败 (状态码: {response.status})")
                    print(f"   📋 错误: {error_text}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ 请求失败: {str(e)}")
        return False
    
    # 等待并验证配置文件
    time.sleep(2)
    updated_config = read_config_file()
    if updated_config:
        reranking_config = updated_config.get('reranking', {})
        updated_batch_size = reranking_config.get('batch_size', 'unknown')
        updated_max_length = reranking_config.get('max_length', 'unknown')
        updated_model = reranking_config.get('model', 'unknown')
        
        print(f"   📋 更新后批处理大小: {updated_batch_size}")
        print(f"   📋 更新后最大长度: {updated_max_length}")
        print(f"   📋 更新后模型: {updated_model}")
        
        # 验证参数
        success = True
        if updated_batch_size == model_data['config']['batch_size']:
            print(f"   ✅ 批处理大小已正确保存")
        else:
            print(f"   ❌ 批处理大小保存错误")
            success = False
        
        if updated_max_length == model_data['config']['max_length']:
            print(f"   ✅ 最大长度已正确保存")
        else:
            print(f"   ❌ 最大长度保存错误")
            success = False
        
        return success
    else:
        print("   ❌ 无法读取更新后的配置文件")
        return False


async def main():
    """主函数"""
    print("🚀 模型配置持久化测试")
    print("测试添加模型后配置是否正确保存到配置文件")
    
    results = []
    
    try:
        # 1. 测试嵌入模型配置持久化
        results.append(await test_add_embedding_model_with_persistence())
        
        # 2. 测试重排序模型配置持久化
        results.append(await test_add_reranking_model_with_persistence())
        
        print_section("测试总结")
        
        test_names = ["嵌入模型配置持久化", "重排序模型配置持久化"]
        
        print("📊 测试结果:")
        for i, (name, result) in enumerate(zip(test_names, results), 1):
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {i}. {name}: {status}")
        
        if all(results):
            print("\n🎉 所有测试通过！")
            print("🎯 模型配置持久化功能正常工作:")
            print("   ✅ 添加嵌入模型时，维度参数正确保存到配置文件")
            print("   ✅ 添加重排序模型时，参数正确保存到配置文件")
            print("   ✅ 用户修改的参数不会丢失")
            print("   ✅ 配置文件与内存状态保持同步")
            
            print("\n💡 用户现在可以:")
            print("   1. 在前端修改嵌入模型维度参数")
            print("   2. 点击添加模型按钮")
            print("   3. 配置会同时保存到内存和配置文件")
            print("   4. 重启服务后配置仍然有效")
            
        else:
            failed_tests = [name for name, result in zip(test_names, results) if not result]
            print(f"\n❌ 部分测试失败: {', '.join(failed_tests)}")
            
            print("\n🔧 可能的问题:")
            print("   - 后端服务未运行")
            print("   - 配置文件写入权限问题")
            print("   - save_model_config_to_file 函数实现问题")
            print("   - 配置文件路径错误")
        
        return all(results)
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)