#!/usr/bin/env python3
"""
统一嵌入配置管理器
确保所有服务使用相同的嵌入模型配置
"""

import os
from typing import Dict, Any

class UnifiedEmbeddingConfig:
    """统一嵌入配置管理器"""
    
    @staticmethod
    def get_embedding_config() -> Dict[str, Any]:
        """获取统一的嵌入配置"""
        api_key = os.getenv('SILICONFLOW_API_KEY')
        
        if api_key:
            return {
                'provider': 'siliconflow',
                'model': 'BAAI/bge-large-zh-v1.5',
                'api_key': api_key,
                'dimensions': 1024,
                'batch_size': 100,
                'timeout': 60,
                'retry_attempts': 3
            }
        else:
            # 回退到mock配置
            return {
                'provider': 'mock',
                'model': 'mock-embedding',
                'api_key': None,
                'dimensions': 768,
                'batch_size': 100,
                'timeout': 30,
                'retry_attempts': 3
            }
    
    @staticmethod
    def get_vector_dimension() -> int:
        """获取向量维度"""
        config = UnifiedEmbeddingConfig.get_embedding_config()
        return config['dimensions']
    
    @staticmethod
    def is_real_model() -> bool:
        """检查是否使用真实模型"""
        return os.getenv('SILICONFLOW_API_KEY') is not None
