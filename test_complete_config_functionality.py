#!/usr/bin/env python3
"""
完整的配置功能测试

测试配置的完整流程：
1. 配置加载
2. 前端显示
3. 参数修改
4. 配置保存
5. 重新加载验证
"""

import asyncio
import json
import yaml
from datetime import datetime
from pathlib import Path
from fastapi.testclient import TestClient

# 导入应用
import sys
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_system.api.main import app


def print_section(title: str):
    """打印格式化的章节"""
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print(f"{'='*60}")


def print_test_result(test_name: str, success: bool, details: str = ""):
    """打印测试结果"""
    status = "✅ 通过" if success else "❌ 失败"
    print(f"{status} {test_name}")
    if details:
        print(f"   详情: {details}")


def test_config_loading():
    """测试配置加载"""
    print_section("测试配置加载")
    
    client = TestClient(app)
    
    try:
        # 获取完整配置
        response = client.get("/config/")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                config = data.get("config", {})
                
                # 检查必要的配置节
                required_sections = ["app", "embeddings", "llm", "retrieval", "reranking"]
                missing_sections = []
                
                for section in required_sections:
                    if section not in config or config[section] is None:
                        missing_sections.append(section)
                
                if not missing_sections:
                    print_test_result("配置节完整性", True, f"所有必需配置节都存在")
                    
                    # 检查嵌入模型配置的详细字段
                    embeddings = config.get("embeddings", {})
                    required_embedding_fields = ["provider", "model", "chunk_size", "chunk_overlap", "batch_size"]
                    missing_embedding_fields = [field for field in required_embedding_fields if field not in embeddings]
                    
                    if not missing_embedding_fields:
                        print_test_result("嵌入模型配置完整性", True, f"所有必需字段都存在")
                    else:
                        print_test_result("嵌入模型配置完整性", False, f"缺失字段: {missing_embedding_fields}")
                    
                    # 检查重排序模型配置
                    reranking = config.get("reranking", {})
                    required_reranking_fields = ["provider", "model", "batch_size", "max_length", "timeout"]
                    missing_reranking_fields = [field for field in required_reranking_fields if field not in reranking]
                    
                    if not missing_reranking_fields:
                        print_test_result("重排序模型配置完整性", True, f"所有必需字段都存在")
                    else:
                        print_test_result("重排序模型配置完整性", False, f"缺失字段: {missing_reranking_fields}")
                    
                    # 打印配置内容
                    print(f"\n📋 当前配置内容:")
                    print(f"嵌入模型: {embeddings.get('provider', 'N/A')}/{embeddings.get('model', 'N/A')}")
                    print(f"重排序模型: {reranking.get('provider', 'N/A')}/{reranking.get('model', 'N/A')}")
                    print(f"检索设置: top_k={config.get('retrieval', {}).get('top_k', 'N/A')}, threshold={config.get('retrieval', {}).get('similarity_threshold', 'N/A')}")
                    
                    return len(missing_sections) == 0 and len(missing_embedding_fields) == 0 and len(missing_reranking_fields) == 0
                else:
                    print_test_result("配置节完整性", False, f"缺失配置节: {missing_sections}")
                    return False
            else:
                print_test_result("配置获取", False, f"API返回失败: {data.get('message', '无消息')}")
                return False
        else:
            print_test_result("配置获取", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("配置获取", False, f"异常: {str(e)}")
        return False


def test_model_status_api():
    """测试模型状态API"""
    print_section("测试模型状态API")
    
    client = TestClient(app)
    
    try:
        # 获取模型状态
        response = client.get("/config/models/status")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                model_data = data.get("data", {})
                
                # 检查必要的字段
                required_fields = ["model_configs", "model_statuses", "active_models"]
                missing_fields = [field for field in required_fields if field not in model_data]
                
                if not missing_fields:
                    print_test_result("模型状态字段完整性", True, "所有必需字段都存在")
                    
                    # 检查活跃模型信息
                    active_models = model_data.get("active_models", {})
                    embedding_model = active_models.get("embedding")
                    reranking_model = active_models.get("reranking")
                    
                    print(f"📋 活跃模型信息:")
                    print(f"嵌入模型: {embedding_model or '未设置'}")
                    print(f"重排序模型: {reranking_model or '未设置'}")
                    
                    return True
                else:
                    print_test_result("模型状态字段完整性", False, f"缺失字段: {missing_fields}")
                    return False
            else:
                print_test_result("模型状态获取", False, f"API返回失败: {data.get('error', '无错误信息')}")
                return False
        else:
            print_test_result("模型状态获取", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("模型状态获取", False, f"异常: {str(e)}")
        return False


def test_model_config_update():
    """测试模型配置更新"""
    print_section("测试模型配置更新")
    
    client = TestClient(app)
    
    try:
        # 准备更新数据
        update_data = {
            "embeddings": {
                "provider": "siliconflow",
                "model": "BAAI/bge-large-zh-v1.5",
                "api_key": "sk-test-update-123456789",
                "base_url": "https://api.siliconflow.cn/v1",
                "chunk_size": 800,
                "chunk_overlap": 100,
                "batch_size": 64,
                "timeout": 120
            },
            "reranking": {
                "provider": "sentence_transformers",
                "model": "cross-encoder/ms-marco-MiniLM-L-12-v2",
                "batch_size": 16,
                "max_length": 256,
                "timeout": 45.0
            }
        }
        
        # 发送更新请求
        response = client.post("/config/models/update-config", json=update_data)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                print_test_result("模型配置更新", True, f"更新成功: {data.get('message', '无消息')}")
                
                # 验证更新后的配置
                config_response = client.get("/config/")
                if config_response.status_code == 200:
                    config_data = config_response.json()
                    if config_data.get("success"):
                        config = config_data.get("config", {})
                        
                        # 验证嵌入模型配置
                        embeddings = config.get("embeddings", {})
                        embedding_checks = [
                            ("provider", "siliconflow"),
                            ("model", "BAAI/bge-large-zh-v1.5"),
                            ("chunk_size", 800),
                            ("batch_size", 64)
                        ]
                        
                        embedding_success = True
                        for field, expected in embedding_checks:
                            actual = embeddings.get(field)
                            if actual != expected:
                                print(f"   嵌入模型配置不匹配: {field} = {actual}, 期望: {expected}")
                                embedding_success = False
                        
                        print_test_result("嵌入模型配置验证", embedding_success, 
                                        f"Provider: {embeddings.get('provider')}, Model: {embeddings.get('model')}")
                        
                        # 验证重排序模型配置
                        reranking = config.get("reranking", {})
                        reranking_checks = [
                            ("provider", "sentence_transformers"),
                            ("model", "cross-encoder/ms-marco-MiniLM-L-12-v2"),
                            ("batch_size", 16),
                            ("max_length", 256)
                        ]
                        
                        reranking_success = True
                        for field, expected in reranking_checks:
                            actual = reranking.get(field)
                            if actual != expected:
                                print(f"   重排序模型配置不匹配: {field} = {actual}, 期望: {expected}")
                                reranking_success = False
                        
                        print_test_result("重排序模型配置验证", reranking_success,
                                        f"Provider: {reranking.get('provider')}, Model: {reranking.get('model')}")
                        
                        return embedding_success and reranking_success
                    else:
                        print_test_result("配置验证", False, "无法获取更新后的配置")
                        return False
                else:
                    print_test_result("配置验证", False, f"获取配置失败: {config_response.status_code}")
                    return False
            else:
                print_test_result("模型配置更新", False, f"更新失败: {data.get('error', '无错误信息')}")
                return False
        else:
            print_test_result("模型配置更新", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("模型配置更新", False, f"异常: {str(e)}")
        return False


def test_config_file_persistence():
    """测试配置文件持久化"""
    print_section("测试配置文件持久化")
    
    try:
        # 读取配置文件
        config_file = Path("config/development.yaml")
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 检查嵌入模型配置
            embeddings = config.get("embeddings", {})
            if embeddings:
                print_test_result("嵌入模型配置文件存在", True, 
                                f"Provider: {embeddings.get('provider')}, Model: {embeddings.get('model')}")
            else:
                print_test_result("嵌入模型配置文件存在", False, "配置文件中没有embeddings节")
                return False
            
            # 检查重排序模型配置
            reranking = config.get("reranking", {})
            if reranking:
                print_test_result("重排序模型配置文件存在", True,
                                f"Provider: {reranking.get('provider')}, Model: {reranking.get('model')}")
            else:
                print_test_result("重排序模型配置文件存在", False, "配置文件中没有reranking节")
                return False
            
            # 检查关键字段
            required_embedding_fields = ["provider", "model", "chunk_size", "chunk_overlap", "batch_size"]
            missing_embedding = [field for field in required_embedding_fields if field not in embeddings]
            
            required_reranking_fields = ["provider", "model", "batch_size", "max_length", "timeout"]
            missing_reranking = [field for field in required_reranking_fields if field not in reranking]
            
            if not missing_embedding and not missing_reranking:
                print_test_result("配置文件字段完整性", True, "所有必需字段都存在于配置文件中")
                return True
            else:
                missing_info = []
                if missing_embedding:
                    missing_info.append(f"嵌入模型缺失: {missing_embedding}")
                if missing_reranking:
                    missing_info.append(f"重排序模型缺失: {missing_reranking}")
                print_test_result("配置文件字段完整性", False, "; ".join(missing_info))
                return False
        else:
            print_test_result("配置文件存在", False, "配置文件不存在")
            return False
            
    except Exception as e:
        print_test_result("配置文件读取", False, f"异常: {str(e)}")
        return False


async def run_complete_test():
    """运行完整测试"""
    print("🚀 完整配置功能测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # 运行各项测试
    test_functions = [
        ("配置加载", test_config_loading),
        ("模型状态API", test_model_status_api),
        ("模型配置更新", test_model_config_update),
        ("配置文件持久化", test_config_file_persistence)
    ]
    
    for test_name, test_func in test_functions:
        try:
            result = test_func()
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
    
    # 问题诊断
    if passed_tests < total_tests:
        print_section("问题诊断")
        print("如果测试失败，可能的原因：")
        print("1. 配置文件格式不正确")
        print("2. API路由没有正确注册")
        print("3. 配置加载逻辑有问题")
        print("4. 前端JavaScript代码有错误")
        print("5. 配置保存逻辑不完整")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    asyncio.run(run_complete_test())