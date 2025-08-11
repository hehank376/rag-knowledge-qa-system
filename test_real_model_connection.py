#!/usr/bin/env python3
"""
测试真实模型连接
"""
import requests
import json
import os
import sys

def test_real_connections():
    base_url = "http://localhost:8000"
    
    print("🧪 测试真实模型连接...")
    print("⚠️  请确保已设置相应的API密钥环境变量")
    print("OPENAI_API_KEY存在吗:", "OPENAI_API_KEY" in os.environ)
    print("SILICONFLOW_API_KEY存在吗:", "SILICONFLOWFLOW_API_KEY" in os.environ)
    # 获取API密钥
    openai_key = os.getenv("OPENAI_API_KEY")
    siliconflow_key = os.getenv("SILICONFLOW_API_KEY")
    
    #print('==========' siliconflow_key)
    
    if not openai_key and not siliconflow_key:
        print("❌ 未找到API密钥环境变量")
        print("请设置以下环境变量之一:")
        print("  - OPENAI_API_KEY")
        print("  - SILICONFLOW_API_KEY")
        return
    
    # 测试SiliconFlow LLM连接
    if siliconflow_key:
        print("\n1. 测试SiliconFlow LLM连接...")
        try:
            llm_config = {
                "provider": "siliconflow",
                "model": "Qwen/Qwen2-7B-Instruct",
                "api_key": siliconflow_key,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            response = requests.post(f"{base_url}/config/test/llm", json=llm_config)
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✓ SiliconFlow LLM连接测试成功")
                else:
                    print("✗ SiliconFlow LLM连接测试失败")
                print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"✗ SiliconFlow LLM连接测试失败: {response.text}")
        except Exception as e:
            print(f"✗ SiliconFlow LLM连接测试异常: {e}")
    
    # 测试SiliconFlow嵌入模型连接
    if siliconflow_key:
        print("\n2. 测试SiliconFlow嵌入模型连接...")
        try:
            embedding_config = {
                "provider": "siliconflow",
                "model": "BAAI/bge-large-zh-v1.5",
                "api_key": siliconflow_key,
                "chunk_size": 1000,
                "chunk_overlap": 200
            }
            response = requests.post(f"{base_url}/config/test/embedding", json=embedding_config)
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✓ SiliconFlow嵌入模型连接测试成功")
                else:
                    print("✗ SiliconFlow嵌入模型连接测试失败")
                print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"✗ SiliconFlow嵌入模型连接测试失败: {response.text}")
        except Exception as e:
            print(f"✗ SiliconFlow嵌入模型连接测试异常: {e}")
    
    # 测试OpenAI LLM连接
    if openai_key:
        print("\n3. 测试OpenAI LLM连接...")
        try:
            llm_config = {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "api_key": openai_key,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            response = requests.post(f"{base_url}/config/test/llm", json=llm_config)
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✓ OpenAI LLM连接测试成功")
                else:
                    print("✗ OpenAI LLM连接测试失败")
                print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"✗ OpenAI LLM连接测试失败: {response.text}")
        except Exception as e:
            print(f"✗ OpenAI LLM连接测试异常: {e}")
    
    # 测试OpenAI嵌入模型连接
    if openai_key:
        print("\n4. 测试OpenAI嵌入模型连接...")
        try:
            embedding_config = {
                "provider": "openai",
                "model": "text-embedding-ada-002",
                "api_key": openai_key,
                "chunk_size": 1000,
                "chunk_overlap": 200
            }
            response = requests.post(f"{base_url}/config/test/embedding", json=embedding_config)
            print(f"状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("✓ OpenAI嵌入模型连接测试成功")
                else:
                    print("✗ OpenAI嵌入模型连接测试失败")
                print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"✗ OpenAI嵌入模型连接测试失败: {response.text}")
        except Exception as e:
            print(f"✗ OpenAI嵌入模型连接测试异常: {e}")
    
    # 测试无API密钥的情况
    print("\n5. 测试无API密钥的情况...")
    try:
        llm_config = {
            "provider": "siliconflow",
            "model": "Qwen/Qwen2-7B-Instruct",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        response = requests.post(f"{base_url}/config/test/llm", json=llm_config)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"测试失败: {response.text}")
    except Exception as e:
        print(f"测试异常: {e}")
    
    print("\n🎉 真实模型连接测试完成!")
    print("\n💡 使用说明:")
    print("1. 设置环境变量:")
    print("   export SILICONFLOW_API_KEY='your-siliconflow-key'")
    print("   export OPENAI_API_KEY='your-openai-key'")
    print("2. 重新运行测试以验证真实连接")

if __name__ == "__main__":
    test_real_connections()