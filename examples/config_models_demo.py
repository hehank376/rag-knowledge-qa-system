#!/usr/bin/env python3
"""
配置模型演示脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import yaml
from pydantic import ValidationError

from rag_system.llm.base import LLMConfig
from rag_system.embeddings.base import EmbeddingConfig


def demo_llm_config():
    """演示LLM配置模型"""
    print("=== LLM配置模型演示 ===\n")
    
    # 1. 基本创建
    print("1. 基本配置创建")
    config = LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="sk-test123",
        temperature=0.8,
        max_tokens=2000
    )
    print(f"   提供商: {config.provider}")
    print(f"   模型: {config.model}")
    print(f"   温度: {config.temperature}")
    print(f"   最大令牌: {config.max_tokens}")
    print()
    
    # 2. 默认配置
    print("2. 获取默认配置")
    
    # OpenAI默认配置
    openai_config = LLMConfig.get_default_config("openai", "gpt-4")
    print(f"   OpenAI默认配置:")
    print(f"   - 温度: {openai_config.temperature}")
    print(f"   - 最大令牌: {openai_config.max_tokens}")
    print(f"   - 超时: {openai_config.timeout}")
    
    # SiliconFlow默认配置
    sf_config = LLMConfig.get_default_config("siliconflow", "qwen-turbo")
    print(f"   SiliconFlow默认配置:")
    print(f"   - 基础URL: {sf_config.base_url}")
    print(f"   - 温度: {sf_config.temperature}")
    
    # Mock默认配置
    mock_config = LLMConfig.get_default_config("mock", "test-model")
    print(f"   Mock默认配置:")
    print(f"   - 超时: {mock_config.timeout}")
    print(f"   - 重试次数: {mock_config.retry_attempts}")
    print()
    
    # 3. 序列化和反序列化
    print("3. 序列化和反序列化")
    
    # 转换为字典
    config_dict = config.to_dict()
    print(f"   字典格式: {json.dumps(config_dict, indent=2, ensure_ascii=False)}")
    
    # 转换为JSON
    json_str = config.to_json()
    print(f"   JSON长度: {len(json_str)} 字符")
    
    # 转换为YAML
    yaml_str = config.to_yaml()
    print(f"   YAML格式:")
    print("   " + yaml_str.replace("\n", "\n   "))
    
    # 从字典创建
    new_config = LLMConfig.from_dict(config_dict)
    print(f"   从字典重建: {new_config.provider}/{new_config.model}")
    
    # 从JSON创建
    json_config = LLMConfig.from_json(json_str)
    print(f"   从JSON重建: {json_config.provider}/{json_config.model}")
    
    # 从YAML创建
    yaml_config = LLMConfig.from_yaml(yaml_str)
    print(f"   从YAML重建: {yaml_config.provider}/{yaml_config.model}")
    print()
    
    # 4. 配置验证
    print("4. 配置验证")
    
    try:
        # 无效提供商
        invalid_config = LLMConfig(provider="invalid", model="test")
        print("   ❌ 应该验证失败但没有")
    except ValidationError as e:
        print(f"   ✅ 无效提供商验证失败: {e.errors()[0]['msg']}")
    
    try:
        # 缺少API密钥
        no_key_config = LLMConfig(provider="openai", model="gpt-4")
        print("   ❌ 应该验证失败但没有")
    except ValidationError as e:
        print(f"   ✅ 缺少API密钥验证失败: {e.errors()[0]['msg']}")
    
    try:
        # 温度超出范围
        high_temp_config = LLMConfig(
            provider="mock", 
            model="test", 
            temperature=3.0
        )
        print("   ❌ 应该验证失败但没有")
    except ValidationError as e:
        print(f"   ✅ 温度超出范围验证失败: {e.errors()[0]['msg']}")
    print()
    
    # 5. 配置合并
    print("5. 配置合并")
    base_config = LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="sk-base",
        temperature=0.7
    )
    
    override_config = LLMConfig(
        provider="openai",
        model="gpt-4",
        api_key="sk-override",
        temperature=0.9,
        max_tokens=3000
    )
    
    merged_config = base_config.merge_with(override_config)
    print(f"   基础温度: {base_config.temperature}")
    print(f"   覆盖温度: {override_config.temperature}")
    print(f"   合并后温度: {merged_config.temperature}")
    print(f"   合并后令牌: {merged_config.max_tokens}")
    print()
    
    # 6. 兼容性检查
    print("6. 兼容性检查")
    
    # 高温度警告
    high_temp_config = LLMConfig(
        provider="mock",
        model="test",
        temperature=1.8
    )
    warnings = high_temp_config.validate_compatibility()
    print(f"   高温度配置警告: {len(warnings)} 个")
    for warning in warnings:
        print(f"   - {warning}")
    
    # 短超时警告
    short_timeout_config = LLMConfig(
        provider="mock",
        model="test",
        timeout=15
    )
    warnings = short_timeout_config.validate_compatibility()
    print(f"   短超时配置警告: {len(warnings)} 个")
    for warning in warnings:
        print(f"   - {warning}")
    print()


def demo_embedding_config():
    """演示嵌入配置模型"""
    print("=== 嵌入配置模型演示 ===\n")
    
    # 1. 基本创建
    print("1. 基本配置创建")
    config = EmbeddingConfig(
        provider="openai",
        model="text-embedding-ada-002",
        api_key="sk-test123",
        batch_size=50,
        dimensions=1536
    )
    print(f"   提供商: {config.provider}")
    print(f"   模型: {config.model}")
    print(f"   批处理大小: {config.batch_size}")
    print(f"   向量维度: {config.dimensions}")
    print()
    
    # 2. 默认配置
    print("2. 获取默认配置")
    
    # OpenAI默认配置
    openai_config = EmbeddingConfig.get_default_config("openai", "text-embedding-ada-002")
    print(f"   OpenAI默认配置:")
    print(f"   - 批处理大小: {openai_config.batch_size}")
    print(f"   - 最大令牌: {openai_config.max_tokens}")
    print(f"   - 向量维度: {openai_config.dimensions}")
    
    # Mock默认配置
    mock_config = EmbeddingConfig.get_default_config("mock", "test-embedding")
    print(f"   Mock默认配置:")
    print(f"   - 向量维度: {mock_config.dimensions}")
    print(f"   - 超时: {mock_config.timeout}")
    print()
    
    # 3. 字段标准化
    print("3. 字段标准化")
    
    # 使用dimension字段（兼容性）
    compat_config = EmbeddingConfig(
        provider="mock",
        model="test",
        dimension=512  # 使用旧字段名
    )
    print(f"   使用dimension字段: {compat_config.dimension}")
    print(f"   自动设置dimensions: {compat_config.dimensions}")
    
    # URL字段标准化
    url_config = EmbeddingConfig(
        provider="mock",
        model="test",
        api_base="https://api.example.com"  # 使用旧字段名
    )
    print(f"   使用api_base字段: {url_config.api_base}")
    print(f"   自动设置base_url: {url_config.base_url}")
    print()
    
    # 4. 提供商特定配置
    print("4. 提供商特定配置")
    
    # OpenAI自动设置维度
    ada_config = EmbeddingConfig(
        provider="openai",
        model="text-embedding-ada-002",
        api_key="sk-test"
    )
    print(f"   Ada-002自动维度: {ada_config.dimensions}")
    
    # SiliconFlow自动设置URL
    sf_config = EmbeddingConfig(
        provider="siliconflow",
        model="test-embedding",
        api_key="sk-test"
    )
    print(f"   SiliconFlow自动URL: {sf_config.base_url}")
    print()
    
    # 5. 序列化演示
    print("5. 序列化演示")
    yaml_output = config.to_yaml()
    print("   YAML格式:")
    print("   " + yaml_output.replace("\n", "\n   "))
    
    # 6. 兼容性检查
    print("6. 兼容性检查")
    
    # 大批处理大小警告
    large_batch_config = EmbeddingConfig(
        provider="mock",
        model="test",
        batch_size=600
    )
    warnings = large_batch_config.validate_compatibility()
    print(f"   大批处理配置警告: {len(warnings)} 个")
    for warning in warnings:
        print(f"   - {warning}")
    
    # 高维度警告
    high_dim_config = EmbeddingConfig(
        provider="mock",
        model="test",
        dimensions=5000
    )
    warnings = high_dim_config.validate_compatibility()
    print(f"   高维度配置警告: {len(warnings)} 个")
    for warning in warnings:
        print(f"   - {warning}")
    print()


def demo_advanced_features():
    """演示高级功能"""
    print("=== 高级功能演示 ===\n")
    
    # 1. 额外参数
    print("1. 额外参数支持")
    llm_config = LLMConfig(
        provider="mock",
        model="test",
        extra_params={
            "custom_setting": "value",
            "special_mode": True,
            "advanced_options": {
                "option1": "a",
                "option2": "b"
            }
        }
    )
    print(f"   额外参数: {json.dumps(llm_config.extra_params, indent=2)}")
    print()
    
    # 2. 配置文件示例
    print("2. 配置文件示例")
    
    # 创建示例配置
    sample_configs = {
        "llm_configs": [
            {
                "name": "primary_llm",
                "provider": "openai",
                "model": "gpt-4",
                "api_key": "${OPENAI_API_KEY}",
                "temperature": 0.7,
                "max_tokens": 2000
            },
            {
                "name": "backup_llm",
                "provider": "siliconflow",
                "model": "qwen-turbo",
                "api_key": "${SILICONFLOW_API_KEY}",
                "temperature": 0.8,
                "max_tokens": 1500
            }
        ],
        "embedding_configs": [
            {
                "name": "primary_embedding",
                "provider": "openai",
                "model": "text-embedding-ada-002",
                "api_key": "${OPENAI_API_KEY}",
                "batch_size": 100
            }
        ]
    }
    
    # 保存为YAML文件
    with open("sample_model_config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(sample_configs, f, default_flow_style=False, allow_unicode=True)
    
    print("   已生成示例配置文件: sample_model_config.yaml")
    
    # 显示文件内容
    with open("sample_model_config.yaml", "r", encoding="utf-8") as f:
        content = f.read()
    print("   文件内容:")
    print("   " + content.replace("\n", "\n   "))
    
    # 3. 从配置文件加载
    print("3. 从配置文件加载配置")
    
    with open("sample_model_config.yaml", "r", encoding="utf-8") as f:
        loaded_configs = yaml.safe_load(f)
    
    # 创建LLM配置实例
    for llm_data in loaded_configs["llm_configs"]:
        name = llm_data.pop("name")  # 移除name字段，因为LLMConfig不需要
        try:
            # 模拟环境变量替换
            if llm_data["api_key"].startswith("${"):
                llm_data["api_key"] = "mock-api-key-for-demo"
            
            config = LLMConfig.from_dict(llm_data)
            print(f"   加载LLM配置 '{name}': {config.provider}/{config.model}")
        except Exception as e:
            print(f"   ❌ 加载LLM配置 '{name}' 失败: {str(e)}")
    
    # 创建嵌入配置实例
    for emb_data in loaded_configs["embedding_configs"]:
        name = emb_data.pop("name")
        try:
            if emb_data["api_key"].startswith("${"):
                emb_data["api_key"] = "mock-api-key-for-demo"
            
            config = EmbeddingConfig.from_dict(emb_data)
            print(f"   加载嵌入配置 '{name}': {config.provider}/{config.model}")
        except Exception as e:
            print(f"   ❌ 加载嵌入配置 '{name}' 失败: {str(e)}")
    print()


def demo_error_handling():
    """演示错误处理"""
    print("=== 错误处理演示 ===\n")
    
    error_cases = [
        {
            "name": "无效提供商",
            "config": {"provider": "invalid_provider", "model": "test"}
        },
        {
            "name": "空模型名称",
            "config": {"provider": "mock", "model": ""}
        },
        {
            "name": "温度超出范围",
            "config": {"provider": "mock", "model": "test", "temperature": 5.0}
        },
        {
            "name": "负数令牌",
            "config": {"provider": "mock", "model": "test", "max_tokens": -100}
        },
        {
            "name": "禁止的额外字段",
            "config": {"provider": "mock", "model": "test", "unknown_field": "value"}
        }
    ]
    
    for case in error_cases:
        try:
            config = LLMConfig(**case["config"])
            print(f"   ❌ {case['name']}: 应该失败但成功了")
        except ValidationError as e:
            error_msg = e.errors()[0]["msg"]
            print(f"   ✅ {case['name']}: {error_msg}")
        except Exception as e:
            print(f"   ⚠️  {case['name']}: 意外错误 - {str(e)}")
    
    print("\n=== 演示完成 ===")


if __name__ == "__main__":
    demo_llm_config()
    demo_embedding_config()
    demo_advanced_features()
    demo_error_handling()