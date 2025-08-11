"""
向后兼容性支持
"""
import logging
import warnings
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import yaml
import json

from ..llm.base import LLMConfig
from ..embeddings.base import EmbeddingConfig
from .model_exceptions import ModelConfigError, ErrorCode

logger = logging.getLogger(__name__)


class CompatibilityManager:
    """兼容性管理器"""
    
    def __init__(self):
        self.deprecated_warnings: List[str] = []
        self.migration_log: List[str] = []
    
    def convert_legacy_llm_config(self, legacy_config: Dict[str, Any]) -> LLMConfig:
        """转换旧版LLM配置"""
        try:
            # 记录转换过程
            self.migration_log.append(f"转换旧版LLM配置: {legacy_config.get('provider', 'unknown')}")
            
            # 处理旧版字段映射
            converted_config = self._map_legacy_llm_fields(legacy_config)
            
            # 验证并创建新配置
            return LLMConfig(**converted_config)
            
        except Exception as e:
            logger.error(f"转换旧版LLM配置失败: {str(e)}")
            raise ModelConfigError(
                f"无法转换旧版LLM配置: {str(e)}",
                error_code=ErrorCode.CONFIG_INVALID
            )
    
    def convert_legacy_embedding_config(self, legacy_config: Dict[str, Any]) -> EmbeddingConfig:
        """转换旧版嵌入配置"""
        try:
            # 记录转换过程
            self.migration_log.append(f"转换旧版嵌入配置: {legacy_config.get('provider', 'unknown')}")
            
            # 处理旧版字段映射
            converted_config = self._map_legacy_embedding_fields(legacy_config)
            
            # 验证并创建新配置
            return EmbeddingConfig(**converted_config)
            
        except Exception as e:
            logger.error(f"转换旧版嵌入配置失败: {str(e)}")
            raise ModelConfigError(
                f"无法转换旧版嵌入配置: {str(e)}",
                error_code=ErrorCode.CONFIG_INVALID
            )
    
    def _map_legacy_llm_fields(self, legacy_config: Dict[str, Any]) -> Dict[str, Any]:
        """映射旧版LLM字段"""
        converted = {}
        
        # 基础字段映射
        field_mappings = {
            # 新字段名: [旧字段名列表]
            'provider': ['provider', 'llm_provider', 'model_provider'],
            'model': ['model', 'llm_model', 'model_name'],
            'api_key': ['api_key', 'llm_api_key', 'openai_api_key'],
            'base_url': ['base_url', 'api_base', 'llm_api_base', 'openai_api_base'],
            'temperature': ['temperature', 'llm_temperature'],
            'max_tokens': ['max_tokens', 'llm_max_tokens', 'max_length'],
            'timeout': ['timeout', 'llm_timeout', 'request_timeout'],
            'retry_attempts': ['retry_attempts', 'max_retries', 'retries']
        }
        
        # 应用字段映射
        for new_field, old_fields in field_mappings.items():
            for old_field in old_fields:
                if old_field in legacy_config:
                    converted[new_field] = legacy_config[old_field]
                    if old_field != new_field:
                        self._add_deprecation_warning(
                            f"配置字段 '{old_field}' 已弃用，请使用 '{new_field}'"
                        )
                    break
        
        # 处理特殊情况
        converted = self._handle_special_llm_cases(legacy_config, converted)
        
        # 设置默认值
        converted = self._set_llm_defaults(converted)
        
        return converted
    
    def _map_legacy_embedding_fields(self, legacy_config: Dict[str, Any]) -> Dict[str, Any]:
        """映射旧版嵌入字段"""
        converted = {}
        
        # 基础字段映射
        field_mappings = {
            'provider': ['provider', 'embedding_provider', 'embeddings_provider'],
            'model': ['model', 'embedding_model', 'embeddings_model'],
            'api_key': ['api_key', 'embedding_api_key', 'embeddings_api_key', 'openai_api_key'],
            'base_url': ['base_url', 'api_base', 'embedding_api_base', 'embeddings_api_base'],
            'dimensions': ['dimensions', 'dimension', 'embedding_dimensions', 'vector_size'],
            'batch_size': ['batch_size', 'embedding_batch_size', 'batch_limit'],
            'max_tokens': ['max_tokens', 'embedding_max_tokens', 'max_length'],
            'timeout': ['timeout', 'embedding_timeout', 'request_timeout'],
            'retry_attempts': ['retry_attempts', 'max_retries', 'retries']
        }
        
        # 应用字段映射
        for new_field, old_fields in field_mappings.items():
            for old_field in old_fields:
                if old_field in legacy_config:
                    converted[new_field] = legacy_config[old_field]
                    if old_field != new_field:
                        self._add_deprecation_warning(
                            f"配置字段 '{old_field}' 已弃用，请使用 '{new_field}'"
                        )
                    break
        
        # 处理特殊情况
        converted = self._handle_special_embedding_cases(legacy_config, converted)
        
        # 设置默认值
        converted = self._set_embedding_defaults(converted)
        
        return converted
    
    def _handle_special_llm_cases(self, legacy_config: Dict[str, Any], converted: Dict[str, Any]) -> Dict[str, Any]:
        """处理LLM特殊情况"""
        # 处理OpenAI特殊配置
        if not converted.get('provider') and legacy_config.get('openai_api_key'):
            converted['provider'] = 'openai'
            self._add_deprecation_warning("检测到OpenAI API密钥，自动设置provider为'openai'")
        
        # 处理旧版模型名称
        if converted.get('model'):
            converted['model'] = self._normalize_model_name(converted['model'], converted.get('provider', 'openai'))
        
        # 处理旧版URL格式
        if converted.get('base_url'):
            converted['base_url'] = self._normalize_base_url(converted['base_url'])
        
        # 处理旧版布尔值
        for field in ['stream']:
            if field in legacy_config:
                converted[field] = self._normalize_boolean(legacy_config[field])
        
        return converted
    
    def _handle_special_embedding_cases(self, legacy_config: Dict[str, Any], converted: Dict[str, Any]) -> Dict[str, Any]:
        """处理嵌入模型特殊情况"""
        # 处理OpenAI特殊配置
        if not converted.get('provider') and legacy_config.get('openai_api_key'):
            converted['provider'] = 'openai'
            self._add_deprecation_warning("检测到OpenAI API密钥，自动设置provider为'openai'")
        
        # 处理旧版模型名称
        if converted.get('model'):
            converted['model'] = self._normalize_embedding_model_name(
                converted['model'], 
                converted.get('provider', 'openai')
            )
        
        # 处理旧版维度设置
        if not converted.get('dimensions') and converted.get('model'):
            converted['dimensions'] = self._infer_embedding_dimensions(
                converted['model'], 
                converted.get('provider', 'openai')
            )
        
        return converted
    
    def _normalize_model_name(self, model_name: str, provider: str) -> str:
        """标准化模型名称"""
        # OpenAI模型名称映射
        openai_mappings = {
            'gpt-3.5': 'gpt-3.5-turbo',
            'gpt-4': 'gpt-4',
            'gpt-35-turbo': 'gpt-3.5-turbo',
            'text-davinci-003': 'gpt-3.5-turbo-instruct'
        }
        
        if provider == 'openai' and model_name in openai_mappings:
            old_name = model_name
            new_name = openai_mappings[model_name]
            self._add_deprecation_warning(f"模型名称 '{old_name}' 已弃用，自动转换为 '{new_name}'")
            return new_name
        
        return model_name
    
    def _normalize_embedding_model_name(self, model_name: str, provider: str) -> str:
        """标准化嵌入模型名称"""
        # OpenAI嵌入模型名称映射
        openai_mappings = {
            'text-embedding-ada-002': 'text-embedding-ada-002',
            'text-embedding-3-small': 'text-embedding-3-small',
            'text-embedding-3-large': 'text-embedding-3-large',
            'ada-002': 'text-embedding-ada-002'
        }
        
        if provider == 'openai' and model_name in openai_mappings:
            return openai_mappings[model_name]
        
        return model_name
    
    def _infer_embedding_dimensions(self, model_name: str, provider: str) -> Optional[int]:
        """推断嵌入模型维度"""
        # OpenAI模型维度映射
        openai_dimensions = {
            'text-embedding-ada-002': 1536,
            'text-embedding-3-small': 1536,
            'text-embedding-3-large': 3072
        }
        
        if provider == 'openai' and model_name in openai_dimensions:
            return openai_dimensions[model_name]
        
        # SiliconFlow模型维度映射
        siliconflow_dimensions = {
            'BAAI/bge-large-zh-v1.5': 1024,
            'BAAI/bge-base-zh-v1.5': 768
        }
        
        if provider == 'siliconflow' and model_name in siliconflow_dimensions:
            return siliconflow_dimensions[model_name]
        
        return None
    
    def _normalize_base_url(self, base_url: str) -> str:
        """标准化基础URL"""
        # 移除末尾的斜杠
        base_url = base_url.rstrip('/')
        
        # 处理常见的URL变体
        url_mappings = {
            'https://api.openai.com/v1': 'https://api.openai.com/v1',
            'https://api.openai.com': 'https://api.openai.com/v1'
        }
        
        if base_url in url_mappings:
            return url_mappings[base_url]
        
        return base_url
    
    def _normalize_boolean(self, value: Any) -> bool:
        """标准化布尔值"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(value, (int, float)):
            return bool(value)
        else:
            return False
    
    def _set_llm_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """设置LLM默认值"""
        defaults = {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'temperature': 0.7,
            'max_tokens': 1000,
            'timeout': 60,
            'retry_attempts': 3
        }
        
        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value
        
        return config
    
    def _set_embedding_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """设置嵌入模型默认值"""
        defaults = {
            'provider': 'openai',
            'model': 'text-embedding-ada-002',
            'batch_size': 100,
            'max_tokens': 8192,
            'timeout': 60,
            'retry_attempts': 3
        }
        
        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value
        
        return config
    
    def _add_deprecation_warning(self, message: str):
        """添加弃用警告"""
        if message not in self.deprecated_warnings:
            self.deprecated_warnings.append(message)
            warnings.warn(message, DeprecationWarning, stacklevel=3)
            logger.warning(f"弃用警告: {message}")
    
    def convert_legacy_config_file(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """转换旧版配置文件"""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        try:
            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    legacy_config = yaml.safe_load(f)
                elif config_path.suffix.lower() == '.json':
                    legacy_config = json.load(f)
                else:
                    raise ValueError(f"不支持的配置文件格式: {config_path.suffix}")
            
            # 转换配置
            converted_config = self._convert_full_config(legacy_config)
            
            # 记录转换日志
            self.migration_log.append(f"成功转换配置文件: {config_path}")
            
            return converted_config
            
        except Exception as e:
            logger.error(f"转换配置文件失败: {config_path} - {str(e)}")
            raise ModelConfigError(
                f"无法转换配置文件 {config_path}: {str(e)}",
                error_code=ErrorCode.CONFIG_INVALID
            )
    
    def _convert_full_config(self, legacy_config: Dict[str, Any]) -> Dict[str, Any]:
        """转换完整配置"""
        converted = {}
        
        # 转换应用配置
        if 'app' in legacy_config:
            converted['app'] = legacy_config['app']
        
        # 转换数据库配置
        if 'database' in legacy_config:
            converted['database'] = legacy_config['database']
        
        # 转换向量存储配置
        if 'vector_store' in legacy_config or 'vector_db' in legacy_config:
            vector_config = legacy_config.get('vector_store', legacy_config.get('vector_db', {}))
            converted['vector_store'] = self._convert_vector_store_config(vector_config)
        
        # 转换LLM配置
        if 'llm' in legacy_config:
            converted['llm'] = self.convert_legacy_llm_config(legacy_config['llm']).to_dict()
        
        # 转换嵌入配置
        embedding_config = legacy_config.get('embeddings', legacy_config.get('embedding', {}))
        if embedding_config:
            converted['embeddings'] = self.convert_legacy_embedding_config(embedding_config).to_dict()
        
        # 转换检索配置
        if 'retrieval' in legacy_config:
            converted['retrieval'] = legacy_config['retrieval']
        
        # 转换API配置
        if 'api' in legacy_config:
            converted['api'] = legacy_config['api']
        
        # 处理API密钥
        if 'api_keys' in legacy_config:
            converted['api_keys'] = legacy_config['api_keys']
        
        return converted
    
    def _convert_vector_store_config(self, vector_config: Dict[str, Any]) -> Dict[str, Any]:
        """转换向量存储配置"""
        converted = {}
        
        # 字段映射
        field_mappings = {
            'type': ['type', 'store_type', 'vector_store_type'],
            'persist_directory': ['persist_directory', 'persist_dir', 'path', 'vector_store_path'],
            'collection_name': ['collection_name', 'collection', 'index_name']
        }
        
        for new_field, old_fields in field_mappings.items():
            for old_field in old_fields:
                if old_field in vector_config:
                    converted[new_field] = vector_config[old_field]
                    if old_field != new_field:
                        self._add_deprecation_warning(
                            f"向量存储配置字段 '{old_field}' 已弃用，请使用 '{new_field}'"
                        )
                    break
        
        # 设置默认值
        if 'type' not in converted:
            converted['type'] = 'chroma'
        if 'persist_directory' not in converted:
            converted['persist_directory'] = './chroma_db'
        if 'collection_name' not in converted:
            converted['collection_name'] = 'knowledge_base'
        
        return converted
    
    def save_converted_config(self, converted_config: Dict[str, Any], output_path: Union[str, Path]):
        """保存转换后的配置"""
        output_path = Path(output_path)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(converted_config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self.migration_log.append(f"保存转换后的配置到: {output_path}")
            logger.info(f"配置转换完成，保存到: {output_path}")
            
        except Exception as e:
            logger.error(f"保存转换后的配置失败: {output_path} - {str(e)}")
            raise ModelConfigError(
                f"无法保存转换后的配置到 {output_path}: {str(e)}",
                error_code=ErrorCode.CONFIG_INVALID
            )
    
    def get_migration_report(self) -> Dict[str, Any]:
        """获取迁移报告"""
        return {
            'migration_log': self.migration_log.copy(),
            'deprecated_warnings': self.deprecated_warnings.copy(),
            'total_warnings': len(self.deprecated_warnings),
            'migration_steps': len(self.migration_log)
        }
    
    def clear_logs(self):
        """清理日志"""
        self.migration_log.clear()
        self.deprecated_warnings.clear()


# 全局兼容性管理器实例
_global_compatibility_manager: Optional[CompatibilityManager] = None


def get_compatibility_manager() -> CompatibilityManager:
    """获取全局兼容性管理器"""
    global _global_compatibility_manager
    if _global_compatibility_manager is None:
        _global_compatibility_manager = CompatibilityManager()
    return _global_compatibility_manager


def ensure_backward_compatibility(config: Dict[str, Any]) -> Dict[str, Any]:
    """确保向后兼容性"""
    manager = get_compatibility_manager()
    return manager._convert_full_config(config)


def convert_legacy_llm_config(legacy_config: Dict[str, Any]) -> LLMConfig:
    """转换旧版LLM配置（便捷函数）"""
    manager = get_compatibility_manager()
    return manager.convert_legacy_llm_config(legacy_config)


def convert_legacy_embedding_config(legacy_config: Dict[str, Any]) -> EmbeddingConfig:
    """转换旧版嵌入配置（便捷函数）"""
    manager = get_compatibility_manager()
    return manager.convert_legacy_embedding_config(legacy_config)


# API兼容性装饰器
def deprecated_api(message: str, version: str = "2.0"):
    """API弃用装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            warnings.warn(
                f"{func.__name__} 已弃用: {message} (将在版本 {version} 中移除)",
                DeprecationWarning,
                stacklevel=2
            )
            return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = f"[已弃用] {func.__doc__ or ''}\n\n弃用原因: {message}"
        return wrapper
    
    return decorator


# 兼容性检查函数
def check_config_compatibility(config: Dict[str, Any]) -> List[str]:
    """检查配置兼容性"""
    issues = []
    
    # 检查LLM配置
    if 'llm' not in config:
        issues.append("缺少必需的配置节: llm")
    else:
        llm_config = config['llm']
        if 'provider' not in llm_config:
            issues.append("LLM配置缺少provider字段")
        if 'model' not in llm_config:
            issues.append("LLM配置缺少model字段")
    
    # 检查嵌入配置（支持新旧字段名）
    embedding_config = config.get('embeddings', config.get('embedding', {}))
    if not embedding_config:
        issues.append("缺少必需的配置节: embeddings")
    else:
        if 'provider' not in embedding_config:
            issues.append("嵌入配置缺少provider字段")
        if 'model' not in embedding_config:
            issues.append("嵌入配置缺少model字段")
    
    return issues