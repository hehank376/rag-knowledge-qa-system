#!/usr/bin/env python3
"""
配置保存功能修复测试

验证语言模型参数修改保存到配置文件的功能
"""

import sys
import json
import time
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
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


def read_config_file():
    """读取配置文件内容"""
    config_file = Path("config/development.yaml")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            return f.read()
    return None


def test_llm_config_save():
    """测试LLM配置保存"""
    print_section("测试LLM配置保存功能")
    
    client = TestClient(app)
    
    # 读取保存前的配置
    config_before = read_config_file()
    
    # 准备测试数据
    test_config = {
        "llm": {
            "provider": "siliconflow",
            "model": "Qwen/Qwen2.5-7B-Instruct",
            "api_key": "test-key-modified-" + str(int(time.time())),
            "base_url": "https://api.siliconflow.cn/v1",
            "temperature": 0.9,
            "max_tokens": 2000,
            "timeout": 150,
            "retry_attempts": 3
        }
    }
    
    try:
        # 发送更新请求
        response = client.put("/config/all", json=test_config)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print_test_result("API调用成功", True, f"消息: {data.get('message')}")
                
                # 等待文件写入完成
                time.sleep(1)
                
                # 读取保存后的配置
                config_after = read_config_file()
                
                if config_after and config_after != config_before:
                    print_test_result("配置文件已更新", True, "文件内容发生变化")
                    
                    # 检查具体的LLM配置是否保存
                    if test_config["llm"]["api_key"] in config_after:
                        print_test_result("LLM API密钥已保存", True, f"找到: {test_config['llm']['api_key']}")
                    else:
                        print_test_result("LLM API密钥已保存", False, "未在配置文件中找到新的API密钥")
                    
                    if str(test_config["llm"]["temperature"]) in config_after:
                        print_test_result("LLM温度参数已保存", True, f"找到: {test_config['llm']['temperature']}")
                    else:
                        print_test_result("LLM温度参数已保存", False, "未在配置文件中找到新的温度参数")
                    
                    if str(test_config["llm"]["max_tokens"]) in config_after:
                        print_test_result("LLM最大令牌数已保存", True, f"找到: {test_config['llm']['max_tokens']}")
                    else:
                        print_test_result("LLM最大令牌数已保存", False, "未在配置文件中找到新的最大令牌数")
                    
                    return True
                else:
                    print_test_result("配置文件已更新", False, "文件内容未发生变化")
                    return False
            else:
                print_test_result("API调用成功", False, f"错误: {data.get('error', '未知错误')}")
                return False
        else:
            print_test_result("API调用成功", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("API调用成功", False, f"异常: {str(e)}")
        return False


def test_all_config_save():
    """测试完整配置保存"""
    print_section("测试完整配置保存功能")
    
    client = TestClient(app)
    
    # 读取保存前的配置
    config_before = read_config_file()
    
    # 准备测试数据
    timestamp = str(int(time.time()))
    test_config = {
        "app": {
            "name": f"RAG System Test {timestamp}",
            "debug": True
        },
        "llm": {
            "provider": "siliconflow",
            "model": "Qwen/Qwen2.5-14B-Instruct",
            "api_key": f"test-all-config-{timestamp}",
            "base_url": "https://api.siliconflow.cn/v1",
            "temperature": 0.85,
            "max_tokens": 1800,
            "timeout": 120,
            "retry_attempts": 2
        },
        "embeddings": {
            "provider": "siliconflow",
            "model": "BAAI/bge-large-zh-v1.5",
            "api_key": f"test-embedding-{timestamp}",
            "base_url": "https://api.siliconflow.cn/v1",
            "dimensions": 1024,
            "batch_size": 50,
            "chunk_size": 800,
            "chunk_overlap": 100,
            "timeout": 60
        },
        "retrieval": {
            "top_k": 8,
            "similarity_threshold": 0.75,
            "search_mode": "hybrid",
            "enable_rerank": True,
            "enable_cache": True
        }
    }
    
    try:
        # 发送更新请求
        response = client.put("/config/all", json=test_config)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print_test_result("完整配置API调用", True, f"消息: {data.get('message')}")
                
                # 等待文件写入完成
                time.sleep(1)
                
                # 读取保存后的配置
                config_after = read_config_file()
                
                if config_after and config_after != config_before:
                    print_test_result("配置文件已更新", True, "文件内容发生变化")
                    
                    # 检查各个配置节是否保存
                    checks = [
                        (test_config["app"]["name"], "应用名称"),
                        (test_config["llm"]["api_key"], "LLM API密钥"),
                        (str(test_config["llm"]["temperature"]), "LLM温度"),
                        (test_config["embeddings"]["api_key"], "嵌入模型API密钥"),
                        (str(test_config["retrieval"]["top_k"]), "检索top_k"),
                        (str(test_config["retrieval"]["similarity_threshold"]), "相似度阈值")
                    ]
                    
                    all_saved = True
                    for value, name in checks:
                        if value in config_after:
                            print_test_result(f"{name}已保存", True, f"找到: {value}")
                        else:
                            print_test_result(f"{name}已保存", False, f"未找到: {value}")
                            all_saved = False
                    
                    return all_saved
                else:
                    print_test_result("配置文件已更新", False, "文件内容未发生变化")
                    return False
            else:
                print_test_result("完整配置API调用", False, f"错误: {data.get('error', '未知错误')}")
                return False
        else:
            print_test_result("完整配置API调用", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("完整配置API调用", False, f"异常: {str(e)}")
        return False


def test_config_reload():
    """测试配置重新加载"""
    print_section("测试配置重新加载功能")
    
    client = TestClient(app)
    
    try:
        response = client.post("/config/reload")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print_test_result("配置重新加载", True, f"消息: {data.get('message')}")
                return True
            else:
                print_test_result("配置重新加载", False, f"错误: {data.get('error', '未知错误')}")
                return False
        else:
            print_test_result("配置重新加载", False, f"HTTP状态码: {response.status_code}")
            return False
            
    except Exception as e:
        print_test_result("配置重新加载", False, f"异常: {str(e)}")
        return False


def show_config_file_content():
    """显示配置文件内容（部分）"""
    print_section("当前配置文件内容（LLM部分）")
    
    config_content = read_config_file()
    if config_content:
        # 提取LLM配置部分
        lines = config_content.split('\n')
        llm_section = []
        in_llm_section = False
        
        for line in lines:
            if line.startswith('llm:'):
                in_llm_section = True
                llm_section.append(line)
            elif in_llm_section:
                if line.startswith('  ') or line.strip() == '':
                    llm_section.append(line)
                else:
                    break
        
        if llm_section:
            print("LLM配置内容:")
            for line in llm_section:
                print(f"  {line}")
        else:
            print("未找到LLM配置节")
    else:
        print("无法读取配置文件")


def main():
    """主函数"""
    print("🚀 配置保存功能修复测试")
    print("验证语言模型参数修改保存到配置文件的功能")
    
    # 显示当前配置
    show_config_file_content()
    
    # 运行测试
    tests = [
        ("LLM配置保存", test_llm_config_save),
        ("完整配置保存", test_all_config_save),
        ("配置重新加载", test_config_reload)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_test_result(test_name, False, f"测试异常: {str(e)}")
            results.append((test_name, False))
    
    # 显示更新后的配置
    show_config_file_content()
    
    # 统计结果
    print_section("测试结果统计")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"总测试数: {total}")
    print(f"通过测试: {passed}")
    print(f"失败测试: {total - passed}")
    print(f"通过率: {(passed / total * 100):.1f}%")
    
    print("\n详细结果:")
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} {test_name}")
    
    if passed == total:
        print(f"\n🎉 所有测试通过！配置保存功能正常工作。")
    else:
        print(f"\n⚠️ 有 {total - passed} 个测试失败，需要进一步检查。")
    
    print("\n💡 修复说明:")
    print("  • 修复了'all'配置节更新时不保存到文件的问题")
    print("  • 在update_config_section函数中添加了文件保存逻辑")
    print("  • 现在所有配置更改都会正确保存到development.yaml文件")


if __name__ == "__main__":
    main()