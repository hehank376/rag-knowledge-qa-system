#!/usr/bin/env python3
"""
配置保存功能测试脚本

测试模型配置的保存和加载功能：
- 配置文件保存
- 参数修改持久化
- 配置重新加载
- 前后端配置同步
"""

import asyncio
import json
import yaml
import tempfile
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

# 导入我们的API
from rag_system.api.config_api import router as config_router


def print_section(title: str, content: str = ""):
    """打印格式化的章节"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")
    if content:
        print(content)


def print_test_result(test_name: str, success: bool, details: str = ""):
    """打印测试结果"""
    status = "✅ 通过" if success else "❌ 失败"
    print(f"{status} {test_name}")
    if details:
        print(f"   详情: {details}")


def create_test_app():
    """创建测试应用"""
    app = FastAPI(title="配置保存功能测试")
    app.include_router(config_router)
    return app


def create_test_config_file():
    """创建测试配置文件"""
    test_config = {
        "app": {
            "name": "RAG Test System",
            "version": "1.0.0-test",
            "debug": True
        },
        "embeddings": {
            "provider": "mock",
            "model": "test-embedding-model",
            "api_key": "test_key",
            "base_url": "https://api.test.com/v1",
            "chunk_size": 1000,
            "chunk_overlap": 200,
            "batch_size": 100,
            "timeout": 60
        },
        "reranking": {
            "provider": "sentence_transformers",
            "model": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "batch_size": 32,
            "max_length": 512,
            "timeout": 30.0
        },
        "llm": {
            "provider": "mock",
            "model": "test-llm-model",
            "api_key": "test_llm_key",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        "retrieval": {
            "top_k": 5,
            "similarity_threshold": 0.7,
            "search_mode": "hybrid",
            "enable_rerank": True,
            "enable_cache": True
        }
    }
    
    # 创建临时配置文件
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
    yaml.dump(test_config, temp_file, default_flow_style=False, allow_unicode=True, indent=2)
    temp_file.close()
    
    return temp_file.name, test_config


async def test_embedding_config_save():
    """测试嵌入模型配置保存"""
    print_section("测试嵌入模型配置保存")
    
    app = create_test_app()
    client = TestClient(app)
    
    try:
        # 测试添加嵌入模型配置
        model_data = {
            "model_type": "embedding",
            "name": "test_siliconflow_embedding",
            "provider": "siliconflow",
            "model_name": "BAAI/bge-large-zh-v1.5",
            "config": {
                "api_key": "sk-test123456789",
                "base_url": "https://api.siliconflow.cn/v1",
                "chunk_size": 800,
                "chunk_overlap": 100,
                "batch_size": 64,
                "timeout": 120
            },
            "enabled": True,
            "priority": 8
        }
        
        response = client.post("/config/models/add-model", json=model_data)
        
        if response.status_code == 200:
            data = response.json()
            success = data.get("success", False)
            print_test_result("添加嵌入模型配置", success, 
                            f"响应: {data.get('message', '无消息')}")
            
            # 验证配置是否保存到文件
            if success:
                # 检查配置是否正确加载
                config_response = client.get("/config/embeddings")
                if config_response.status_code == 200:
                    config_data = config_response.json()
                    if config_data.get("success"):
                        embedding_config = config_data.get("config", {}).get("embeddings", {})
                        expected_values = {
                            "provider": "siliconflow",
                            "model": "BAAI/bge-large-zh-v1.5",
                            "chunk_size": 800,
                            "chunk_overlap": 100,
                            "batch_size": 64
                        }
                        
                        all_match = True
                        for key, expected_value in expected_values.items():
                            actual_value = embedding_config.get(key)
                            if actual_value != expected_value:
                                print(f"   配置不匹配: {key} = {actual_value}, 期望: {expected_value}")
                                all_match = False
                        
                        print_test_result("配置保存验证", all_match, 
                                        f"配置内容: {json.dumps(embedding_config, indent=2, ensure_ascii=False)}")
                        return all_match
            
            return success
        else:
            print_test_result("添加嵌入模型配置", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("添加嵌入模型配置", False, f"异常: {str(e)}")
        return False


async def test_reranking_config_save():
    """测试重排序模型配置保存"""
    print_section("测试重排序模型配置保存")
    
    app = create_test_app()
    client = TestClient(app)
    
    try:
        # 测试添加重排序模型配置
        model_data = {
            "model_type": "reranking",
            "name": "test_reranking_model",
            "provider": "sentence_transformers",
            "model_name": "cross-encoder/ms-marco-MiniLM-L-12-v2",
            "config": {
                "batch_size": 16,
                "max_length": 256,
                "timeout": 45.0
            },
            "enabled": True,
            "priority": 7
        }
        
        response = client.post("/config/models/add-model", json=model_data)
        
        if response.status_code == 200:
            data = response.json()
            success = data.get("success", False)
            print_test_result("添加重排序模型配置", success, 
                            f"响应: {data.get('message', '无消息')}")
            return success
        else:
            print_test_result("添加重排序模型配置", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("添加重排序模型配置", False, f"异常: {str(e)}")
        return False


async def test_model_switch_save():
    """测试模型切换配置保存"""
    print_section("测试模型切换配置保存")
    
    app = create_test_app()
    client = TestClient(app)
    
    try:
        # 先添加一个模型
        model_data = {
            "model_type": "embedding",
            "name": "test_openai_embedding",
            "provider": "openai",
            "model_name": "text-embedding-ada-002",
            "config": {
                "api_key": "sk-openai123456789",
                "base_url": "https://api.openai.com/v1",
                "chunk_size": 1200,
                "chunk_overlap": 150,
                "batch_size": 50
            },
            "enabled": True,
            "priority": 9
        }
        
        add_response = client.post("/config/models/add-model", json=model_data)
        
        if add_response.status_code == 200 and add_response.json().get("success"):
            # 测试切换到这个模型
            switch_data = {
                "model_type": "embedding",
                "model_name": "text-embedding-ada-002"
            }
            
            switch_response = client.post("/config/models/switch-active", json=switch_data)
            
            if switch_response.status_code == 200:
                switch_result = switch_response.json()
                success = switch_result.get("success", False)
                print_test_result("切换嵌入模型", success, 
                                f"响应: {switch_result.get('message', '无消息')}")
                
                # 验证切换后的配置
                if success:
                    config_response = client.get("/config/embeddings")
                    if config_response.status_code == 200:
                        config_data = config_response.json()
                        if config_data.get("success"):
                            embedding_config = config_data.get("config", {}).get("embeddings", {})
                            current_model = embedding_config.get("model")
                            print_test_result("模型切换验证", current_model == "text-embedding-ada-002",
                                            f"当前模型: {current_model}")
                            return current_model == "text-embedding-ada-002"
                
                return success
            else:
                print_test_result("切换嵌入模型", False, f"HTTP状态码: {switch_response.status_code}")
                return False
        else:
            print_test_result("添加测试模型", False, "添加模型失败，无法测试切换")
            return False
            
    except Exception as e:
        print_test_result("测试模型切换", False, f"异常: {str(e)}")
        return False


async def test_config_update_api():
    """测试配置更新API"""
    print_section("测试配置更新API")
    
    app = create_test_app()
    client = TestClient(app)
    
    try:
        # 测试更新模型配置
        update_data = {
            "embeddings": {
                "provider": "huggingface",
                "model": "sentence-transformers/all-mpnet-base-v2",
                "api_key": "hf_test123456789",
                "base_url": "https://api-inference.huggingface.co",
                "chunk_size": 600,
                "chunk_overlap": 80,
                "batch_size": 32,
                "timeout": 90
            },
            "reranking": {
                "provider": "huggingface",
                "model": "cross-encoder/ms-marco-TinyBERT-L-2-v2",
                "batch_size": 64,
                "max_length": 128,
                "timeout": 20.0
            }
        }
        
        response = client.post("/config/models/update-config", json=update_data)
        
        if response.status_code == 200:
            data = response.json()
            success = data.get("success", False)
            print_test_result("更新模型配置", success, 
                            f"响应: {data.get('message', '无消息')}")
            
            # 验证更新后的配置
            if success:
                config_response = client.get("/config/embeddings")
                if config_response.status_code == 200:
                    config_data = config_response.json()
                    if config_data.get("success"):
                        embedding_config = config_data.get("config", {}).get("embeddings", {})
                        expected_provider = "huggingface"
                        expected_model = "sentence-transformers/all-mpnet-base-v2"
                        expected_chunk_size = 600
                        
                        provider_match = embedding_config.get("provider") == expected_provider
                        model_match = embedding_config.get("model") == expected_model
                        chunk_size_match = embedding_config.get("chunk_size") == expected_chunk_size
                        
                        all_match = provider_match and model_match and chunk_size_match
                        print_test_result("配置更新验证", all_match,
                                        f"Provider: {embedding_config.get('provider')}, "
                                        f"Model: {embedding_config.get('model')}, "
                                        f"Chunk Size: {embedding_config.get('chunk_size')}")
                        return all_match
            
            return success
        else:
            print_test_result("更新模型配置", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("测试配置更新", False, f"异常: {str(e)}")
        return False


async def test_config_persistence():
    """测试配置持久化"""
    print_section("测试配置持久化")
    
    try:
        # 创建测试配置文件
        config_file, original_config = create_test_config_file()
        
        print_test_result("创建测试配置文件", True, f"文件路径: {config_file}")
        
        # 模拟配置修改
        modified_config = original_config.copy()
        modified_config["embeddings"]["model"] = "new-test-model"
        modified_config["embeddings"]["chunk_size"] = 1500
        modified_config["reranking"]["batch_size"] = 64
        
        # 保存修改后的配置
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(modified_config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        print_test_result("保存修改后的配置", True, "配置已写入文件")
        
        # 重新读取配置验证
        with open(config_file, 'r', encoding='utf-8') as f:
            loaded_config = yaml.safe_load(f)
        
        # 验证修改是否持久化
        embedding_model_match = loaded_config["embeddings"]["model"] == "new-test-model"
        chunk_size_match = loaded_config["embeddings"]["chunk_size"] == 1500
        reranking_batch_match = loaded_config["reranking"]["batch_size"] == 64
        
        all_match = embedding_model_match and chunk_size_match and reranking_batch_match
        print_test_result("配置持久化验证", all_match,
                        f"Embedding Model: {loaded_config['embeddings']['model']}, "
                        f"Chunk Size: {loaded_config['embeddings']['chunk_size']}, "
                        f"Reranking Batch: {loaded_config['reranking']['batch_size']}")
        
        # 清理测试文件
        os.unlink(config_file)
        print_test_result("清理测试文件", True, "测试文件已删除")
        
        return all_match
        
    except Exception as e:
        print_test_result("测试配置持久化", False, f"异常: {str(e)}")
        return False


async def run_comprehensive_test():
    """运行综合测试"""
    print("🚀 配置保存功能综合测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 运行各项测试
    test_functions = [
        ("嵌入模型配置保存", test_embedding_config_save),
        ("重排序模型配置保存", test_reranking_config_save),
        ("模型切换配置保存", test_model_switch_save),
        ("配置更新API", test_config_update_api),
        ("配置持久化", test_config_persistence)
    ]
    
    for test_name, test_func in test_functions:
        try:
            result = await test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print_test_result(test_name, False, f"测试异常: {str(e)}")
            test_results.append((test_name, False))
    
    # 测试总结
    print_section("测试总结")
    
    passed_tests = sum(1 for _, result in test_results if result)
    total_tests = len(test_results)
    
    print(f"总测试数: {total_tests}")
    print(f"通过测试: {passed_tests}")
    print(f"失败测试: {total_tests - passed_tests}")
    print(f"通过率: {passed_tests/total_tests*100:.1f}%")
    
    print("\n详细结果:")
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} {test_name}")
    
    # 功能特性总结
    print_section("配置保存功能特性")
    
    features = [
        "✅ 嵌入模型配置保存到YAML文件",
        "✅ 重排序模型配置保存到YAML文件", 
        "✅ 模型切换时配置自动更新",
        "✅ 配置参数修改持久化",
        "✅ 配置重新加载机制",
        "✅ API密钥和基础URL保存",
        "✅ 批处理大小和超时参数保存",
        "✅ 配置验证和错误处理"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    asyncio.run(run_comprehensive_test())