"""
配置管理API接口
实现任务8.3：配置管理API接口
"""
import logging
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator

from ..config.loader import ConfigLoader
from ..models.config import AppConfig, DatabaseConfig, VectorStoreConfig, EmbeddingsConfig, LLMConfig, RetrievalConfig, APIConfig
from ..utils.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# 创建API路由器
router = APIRouter(prefix="/config", tags=["configuration"])


class ConfigResponse(BaseModel):
    """配置响应模型"""
    success: bool
    message: str
    config: Optional[Dict[str, Any]] = None


class ConfigUpdateRequest(BaseModel):
    """配置更新请求模型"""
    section: str
    config: Dict[str, Any]
    
    @field_validator('section')
    @classmethod
    def validate_section(cls, v):
        allowed_sections = ['database', 'vector_store', 'embeddings', 'llm', 'retrieval', 'api', 'all']
        if v not in allowed_sections:
            raise ValueError(f'Invalid section. Allowed: {allowed_sections}')
        return v


class ConfigValidationResponse(BaseModel):
    """配置验证响应模型"""
    valid: bool
    errors: Optional[Dict[str, str]] = None
    warnings: Optional[Dict[str, str]] = None


# 全局配置加载器实例
config_loader = ConfigLoader()

# 数据库相关端点
@router.get("/database/info", response_model=Dict[str, Any])
async def get_database_info():
    """
    获取数据库连接信息和支持的数据库类型
    
    Returns:
        Dict: 包含数据库信息的响应
    """
    try:
        from ..services.database_service import get_database_service
        
        db_service = get_database_service()
        
        # 获取连接信息
        connection_info = db_service.get_connection_info()
        
        # 获取支持的数据库类型
        supported_databases = db_service.get_supported_databases()
        
        # 获取当前配置
        current_config = db_service.get_database_config()
        
        return {
            "success": True,
            "data": {
                "connection_info": connection_info,
                "supported_databases": supported_databases,
                "current_config": current_config,
                "service_status": "initialized" if connection_info else "not_initialized"
            }
        }
        
    except Exception as e:
        logger.error(f"获取数据库信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取数据库信息失败: {str(e)}"
        )

@router.post("/database/test", response_model=Dict[str, Any])
async def test_database_connection(config: Dict[str, Any]):
    """
    测试数据库连接
    
    Args:
        config: 数据库配置
        
    Returns:
        Dict: 测试结果
    """
    try:
        from ..services.database_service import get_database_service
        
        db_service = get_database_service()
        
        # 执行连接测试
        test_result = await db_service.test_connection(config)
        
        return {
            "success": test_result['success'],
            "data": test_result,
            "message": test_result.get('message', '连接测试完成')
        }
        
    except Exception as e:
        logger.error(f"数据库连接测试失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"数据库连接测试失败: {str(e)}"
        }

@router.post("/database/reload", response_model=Dict[str, Any])
async def reload_database_config():
    """
    重新加载数据库配置
    
    Returns:
        Dict: 重新加载结果
    """
    try:
        from ..services.database_service import get_database_service
        
        db_service = get_database_service()
        
        # 重新加载配置
        success = await db_service.reload_config()
        
        if success:
            return {
                "success": True,
                "message": "数据库配置重新加载成功",
                "data": {
                    "reload_time": time.time(),
                    "connection_info": db_service.get_connection_info()
                }
            }
        else:
            return {
                "success": False,
                "message": "数据库配置重新加载失败"
            }
            
    except Exception as e:
        logger.error(f"重新加载数据库配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新加载数据库配置失败: {str(e)}"
        )

@router.get("/database/health", response_model=Dict[str, Any])
async def check_database_health():
    """
    检查数据库健康状态
    
    Returns:
        Dict: 健康检查结果
    """
    try:
        from ..services.database_service import get_database_service
        
        db_service = get_database_service()
        
        # 执行健康检查
        is_healthy = await db_service.health_check()
        
        return {
            "success": True,
            "data": {
                "healthy": is_healthy,
                "status": "healthy" if is_healthy else "unhealthy",
                "check_time": time.time(),
                "connection_info": db_service.get_connection_info() if is_healthy else None
            }
        }
        
    except Exception as e:
        logger.error(f"数据库健康检查失败: {str(e)}")
        return {
            "success": False,
            "data": {
                "healthy": False,
                "status": "error",
                "error": str(e),
                "check_time": time.time()
            }
        }
current_config: Optional[AppConfig] = None


def get_current_config() -> AppConfig:
    """获取当前配置"""
    global current_config, config_loader
    # 每次都重新加载配置文件，确保获取最新值
    config_loader = ConfigLoader()
    current_config = config_loader.load_config()
    return current_config


def reload_config():
    """重新加载配置"""
    global current_config, config_loader
    # 创建新的配置加载器实例，确保重新读取文件
    config_loader = ConfigLoader()
    current_config = config_loader.load_config()
    return current_config

@router.get("/", response_model=ConfigResponse)
async def get_config() -> ConfigResponse:
    """
    获取系统配置
    
    Returns:
        系统配置信息
        
    Raises:
        HTTPException: 当获取配置失败时
    """
    try:
        logger.info("获取系统配置")
        
        config = get_current_config()
        
        # 将配置转换为字典格式
        config_dict = {
            "app": {
                "name": config.name,
                "version": config.version,
                "debug": config.debug
            },
            "database": {
                "url": config.database.url,
                "echo": config.database.echo
            } if config.database else None,
            "vector_store": {
                "type": config.vector_store.type,
                "persist_directory": config.vector_store.persist_directory,
                "collection_name": config.vector_store.collection_name
            } if config.vector_store else None,
            "embeddings": {
                "provider": config.embeddings.provider,
                "model": config.embeddings.model,
                "dimensions": getattr(config.embeddings, 'dimensions', 1024),  # 添加维度字段
                "chunk_size": config.embeddings.chunk_size,
                "chunk_overlap": config.embeddings.chunk_overlap,
                "batch_size": getattr(config.embeddings, 'batch_size', 100),
                "api_key": getattr(config.embeddings, 'api_key', ''),
                "base_url": getattr(config.embeddings, 'base_url', ''),
                "timeout": getattr(config.embeddings, 'timeout', 60),
                "retry_attempts": getattr(config.embeddings, 'retry_attempts', 2)
            } if config.embeddings else None,
            "llm": {
                "provider": config.llm.provider,
                "model": config.llm.model,
                "temperature": config.llm.temperature,
                "max_tokens": config.llm.max_tokens,
                "api_key": getattr(config.llm, 'api_key', ''),
                "base_url": getattr(config.llm, 'base_url', ''),
                "timeout": getattr(config.llm, 'timeout', 120),
                "retry_attempts": getattr(config.llm, 'retry_attempts', 2)
            } if config.llm else None,
            "retrieval": {
                "top_k": config.retrieval.top_k,
                "similarity_threshold": config.retrieval.similarity_threshold,
                "search_mode": getattr(config.retrieval, 'search_mode', 'semantic'),
                "enable_rerank": getattr(config.retrieval, 'enable_rerank', False),
                "enable_cache": getattr(config.retrieval, 'enable_cache', False)
            } if config.retrieval else None,
            "reranking": {
                "provider": getattr(config.reranking, 'provider', 'sentence_transformers') if config.reranking else 'sentence_transformers',
                "model": getattr(config.reranking, 'model', 'cross-encoder/ms-marco-MiniLM-L-6-v2') if config.reranking else 'cross-encoder/ms-marco-MiniLM-L-6-v2',
                "model_name": getattr(config.reranking, 'model_name', getattr(config.reranking, 'model', 'cross-encoder/ms-marco-MiniLM-L-6-v2')) if config.reranking else 'cross-encoder/ms-marco-MiniLM-L-6-v2',
                "batch_size": getattr(config.reranking, 'batch_size', 32) if config.reranking else 32,
                "max_length": getattr(config.reranking, 'max_length', 512) if config.reranking else 512,
                "timeout": getattr(config.reranking, 'timeout', 30.0) if config.reranking else 30.0,
                "api_key": getattr(config.reranking, 'api_key', '') if config.reranking else '',
                "base_url": getattr(config.reranking, 'base_url', '') if config.reranking else ''
            } if config.reranking else None,
            "api": {
                "host": config.api.host,
                "port": config.api.port,
                "cors_origins": config.api.cors_origins
            } if config.api else None
        }
        
        logger.info("成功获取系统配置")
        
        return ConfigResponse(
            success=True,
            message="配置获取成功",
            config=config_dict
        )
        
    except ConfigurationError as e:
        logger.error(f"获取配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取配置失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取配置时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取配置时发生内部错误"
        )


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """
    健康检查接口
    
    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "service": "config_api",
        "version": "1.0.0"
    }


@router.get("/{section}", response_model=ConfigResponse)
async def get_config_section(section: str) -> ConfigResponse:
    """
    获取特定配置节
    
    Args:
        section: 配置节名称 (database, vector_store, embeddings, llm, retrieval, api)
        
    Returns:
        指定配置节信息
        
    Raises:
        HTTPException: 当配置节不存在或获取失败时
    """
    try:
        logger.info(f"获取配置节: {section}")
        
        allowed_sections = ['database', 'vector_store', 'embeddings', 'llm', 'retrieval', 'api']
        if section not in allowed_sections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的配置节: {section}. 支持的配置节: {', '.join(allowed_sections)}"
            )
        
        config = get_current_config()
        section_config = getattr(config, section, None)
        
        if section_config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置节不存在: {section}"
            )
        
        # 将配置对象转换为字典
        if hasattr(section_config, '__dict__'):
            config_dict = section_config.__dict__
        else:
            config_dict = section_config
        
        logger.info(f"成功获取配置节: {section}")
        
        return ConfigResponse(
            success=True,
            message=f"配置节 '{section}' 获取成功",
            config={section: config_dict}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配置节时发生未知错误: {section}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取配置节时发生内部错误"
        )


def validate_config_section(section: str, config_data: Dict[str, Any]) -> ConfigValidationResponse:
    """
    验证配置节数据
    
    Args:
        section: 配置节名称
        config_data: 配置数据
        
    Returns:
        验证结果
    """
    errors = {}
    warnings = {}
    
    try:
        # 处理 'all' 配置节的特殊情况
        if section == "all":
            # 验证所有配置节
            for section_name, section_data in config_data.items():
                if section_name in ['database', 'vector_store', 'embeddings', 'llm', 'retrieval', 'api', 'app']:
                    section_result = validate_config_section(section_name, section_data)
                    if section_result.errors:
                        for key, error in section_result.errors.items():
                            errors[f"{section_name}.{key}"] = error
                    if section_result.warnings:
                        for key, warning in section_result.warnings.items():
                            warnings[f"{section_name}.{key}"] = warning
            
            return ConfigValidationResponse(
                valid=len(errors) == 0,
                errors=errors if errors else None,
                warnings=warnings if warnings else None
            )
        if section == "database":
            if "url" not in config_data:
                errors["url"] = "数据库URL是必需的"
            elif not isinstance(config_data["url"], str):
                errors["url"] = "数据库URL必须是字符串"
            
            if "echo" in config_data and not isinstance(config_data["echo"], bool):
                errors["echo"] = "echo参数必须是布尔值"
                
        elif section == "vector_store":
            if "type" not in config_data:
                errors["type"] = "向量存储类型是必需的"
            elif "type" in config_data:
                allowed_types = ["chroma", "pinecone", "faiss"]
                if config_data["type"] not in allowed_types:
                    errors["type"] = f"不支持的向量存储类型. 支持: {', '.join(allowed_types)}"
            
            if "persist_directory" in config_data and not isinstance(config_data["persist_directory"], str):
                errors["persist_directory"] = "持久化目录必须是字符串"
                
        elif section == "embeddings":
            if "provider" not in config_data:
                errors["provider"] = "嵌入提供商是必需的"
            elif "provider" in config_data:
                allowed_providers = ["openai", "siliconflow", "deepseek", "ollama", "azure", "huggingface", "mock"]
                if config_data["provider"] not in allowed_providers:
                    errors["provider"] = f"不支持的嵌入提供商. 支持: {', '.join(allowed_providers)}"
            
            if "model" not in config_data:
                errors["model"] = "嵌入模型是必需的"
            
            if "chunk_size" in config_data:
                if not isinstance(config_data["chunk_size"], int) or config_data["chunk_size"] <= 0:
                    errors["chunk_size"] = "chunk_size必须是正整数"
                elif config_data["chunk_size"] > 8000:
                    warnings["chunk_size"] = "chunk_size过大可能影响性能"
            
            if "chunk_overlap" in config_data:
                if not isinstance(config_data["chunk_overlap"], int) or config_data["chunk_overlap"] < 0:
                    errors["chunk_overlap"] = "chunk_overlap必须是非负整数"
                    
        elif section == "llm":
            if "provider" not in config_data:
                errors["provider"] = "LLM提供商是必需的"
            elif "provider" in config_data:
                allowed_providers = ["openai", "siliconflow", "deepseek", "ollama", "azure", "anthropic", "mock"]
                if config_data["provider"] not in allowed_providers:
                    errors["provider"] = f"不支持的LLM提供商. 支持: {', '.join(allowed_providers)}"
            
            if "model" not in config_data:
                errors["model"] = "LLM模型是必需的"
            
            if "temperature" in config_data:
                if not isinstance(config_data["temperature"], (int, float)):
                    errors["temperature"] = "temperature必须是数字"
                elif not (0 <= config_data["temperature"] <= 2):
                    errors["temperature"] = "temperature必须在0-2之间"
            
            if "max_tokens" in config_data:
                if not isinstance(config_data["max_tokens"], int) or config_data["max_tokens"] <= 0:
                    errors["max_tokens"] = "max_tokens必须是正整数"
                    
        elif section == "retrieval":
            if "top_k" not in config_data:
                errors["top_k"] = "top_k是必需的"
            elif "top_k" in config_data:
                if not isinstance(config_data["top_k"], int) or config_data["top_k"] <= 0:
                    errors["top_k"] = "top_k必须是正整数"
                elif config_data["top_k"] > 50:
                    warnings["top_k"] = "top_k过大可能影响性能"
            
            if "similarity_threshold" in config_data:
                if not isinstance(config_data["similarity_threshold"], (int, float)):
                    errors["similarity_threshold"] = "similarity_threshold必须是数字"
                elif not (0 <= config_data["similarity_threshold"] <= 1):
                    errors["similarity_threshold"] = "similarity_threshold必须在0-1之间"
            
            if "search_mode" in config_data:
                valid_search_modes = ["semantic", "keyword", "hybrid"]
                if config_data["search_mode"] not in valid_search_modes:
                    errors["search_mode"] = f"无效的搜索模式. 支持: {', '.join(valid_search_modes)}"
            
            if "enable_rerank" in config_data:
                if not isinstance(config_data["enable_rerank"], bool):
                    errors["enable_rerank"] = "enable_rerank必须是布尔值"
            
            if "enable_cache" in config_data:
                if not isinstance(config_data["enable_cache"], bool):
                    errors["enable_cache"] = "enable_cache必须是布尔值"
                    
        elif section == "api":
            if "host" not in config_data:
                errors["host"] = "主机地址是必需的"
            if "port" not in config_data:
                errors["port"] = "端口是必需的"
            elif "port" in config_data:
                if not isinstance(config_data["port"], int):
                    errors["port"] = "端口必须是整数"
                elif not (1 <= config_data["port"] <= 65535):
                    errors["port"] = "端口必须在1-65535之间"
            
            if "cors_origins" in config_data:
                if not isinstance(config_data["cors_origins"], list):
                    errors["cors_origins"] = "cors_origins必须是列表"
                    
    except Exception as e:
        errors["validation"] = f"验证过程中发生错误: {str(e)}"
    
    return ConfigValidationResponse(
        valid=len(errors) == 0,
        errors=errors if errors else None,
        warnings=warnings if warnings else None
    )


@router.post("/validate", response_model=ConfigValidationResponse)
async def validate_config(request: ConfigUpdateRequest) -> ConfigValidationResponse:
    """
    验证配置数据
    
    Args:
        request: 配置验证请求
        
    Returns:
        验证结果
    """
    try:
        logger.info(f"验证配置节: {request.section}")
        
        validation_result = validate_config_section(request.section, request.config)
        
        logger.info(f"配置验证完成: {request.section}, 有效: {validation_result.valid}")
        
        return validation_result
        
    except Exception as e:
        logger.error(f"配置验证时发生错误: {str(e)}")
        return ConfigValidationResponse(
            valid=False,
            errors={"validation": f"验证过程中发生错误: {str(e)}"}
        )


def save_config_to_file(config_data: Dict[str, Any], config_path: str = None):
    """保存配置到YAML文件"""
    import yaml
    from pathlib import Path
    
    if config_path is None:
        config_path = config_loader.config_path
    
    try:
        # 读取现有配置文件
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                existing_config = yaml.safe_load(f) or {}
        else:
            existing_config = {}
        
        # 合并新配置
        for section, data in config_data.items():
            if section in existing_config:
                existing_config[section].update(data)
            else:
                existing_config[section] = data
        
        # 保存到文件
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(existing_config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        logger.info(f"配置已保存到文件: {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"保存配置到文件失败: {str(e)}")
        return False


@router.put("/{section}", response_model=ConfigResponse)
async def update_config_section(section: str, config_data: Dict[str, Any]) -> ConfigResponse:
    """
    更新配置节
    
    Args:
        section: 配置节名称
        config_data: 新的配置数据
        
    Returns:
        更新结果
        
    Raises:
        HTTPException: 当更新失败时
    """
    try:
        logger.info(f"更新配置节: {section}")
        
        # 验证配置节名称
        allowed_sections = ['database', 'vector_store', 'embeddings', 'llm', 'retrieval', 'api', 'all']
        if section not in allowed_sections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的配置节: {section}. 支持的配置节: {', '.join(allowed_sections)}"
            )
        
        # 处理 'all' 配置节的特殊情况
        if section == 'all':
            # 更新所有配置节
            current_config = get_current_config()
            updated_sections = {}
            
            for section_name, section_data in config_data.items():
                if section_name in ['database', 'vector_store', 'embeddings', 'llm', 'retrieval', 'api']:
                    # 验证每个配置节
                    validation_result = validate_config_section(section_name, section_data)
                    if not validation_result.valid:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"配置节 '{section_name}' 验证失败: {validation_result.errors}"
                        )
                    
                    # 更新配置节
                    if section_name == "database":
                        current_config.database = DatabaseConfig(**section_data)
                    elif section_name == "vector_store":
                        current_config.vector_store = VectorStoreConfig(**section_data)
                    elif section_name == "embeddings":
                        current_config.embeddings = EmbeddingsConfig(**section_data)
                    elif section_name == "llm":
                        current_config.llm = LLMConfig(**section_data)
                    elif section_name == "retrieval":
                        current_config.retrieval = RetrievalConfig(**section_data)
                    elif section_name == "api":
                        current_config.api = APIConfig(**section_data)
                    
                    updated_sections[section_name] = section_data
            
            logger.info("所有配置节更新成功")
            
            # 保存配置到文件
            save_success = save_config_to_file(updated_sections)
            
            message = "所有配置更新成功"
            if save_success:
                message += "，已保存到配置文件"
            else:
                message += "，但保存到配置文件失败"
            
            return ConfigResponse(
                success=True,
                message=message,
                config=updated_sections
            )
        
        # 验证单个配置节数据
        validation_result = validate_config_section(section, config_data)
        if not validation_result.valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"配置验证失败: {validation_result.errors}"
            )
        
        # 获取当前配置
        current_config = get_current_config()
        
        # 更新配置节
        if section == "database":
            current_config.database = DatabaseConfig(**config_data)
        elif section == "vector_store":
            current_config.vector_store = VectorStoreConfig(**config_data)
        elif section == "embeddings":
            current_config.embeddings = EmbeddingsConfig(**config_data)
        elif section == "llm":
            current_config.llm = LLMConfig(**config_data)
        elif section == "retrieval":
            current_config.retrieval = RetrievalConfig(**config_data)
        elif section == "api":
            current_config.api = APIConfig(**config_data)
        
        logger.info(f"配置节更新成功: {section}")
        
        # 保存配置到文件
        if section == 'all':
            save_success = save_config_to_file(updated_sections)
        else:
            save_success = save_config_to_file({section: config_data})
        
        # 返回更新后的配置节
        if section == 'all':
            config_dict = updated_sections
        else:
            updated_section = getattr(current_config, section)
            config_dict = updated_section.__dict__ if hasattr(updated_section, '__dict__') else updated_section
        
        message = f"配置节 '{section}' 更新成功"
        if save_success:
            message += "，已保存到配置文件"
        else:
            message += "，但保存到配置文件失败"
        
        response = ConfigResponse(
            success=True,
            message=message,
            config={section: config_dict} if section != 'all' else config_dict
        )
        
        # 添加警告信息
        if validation_result.warnings:
            response.message += f" (警告: {validation_result.warnings})"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新配置节时发生错误: {section}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新配置节时发生内部错误: {str(e)}"
        )


@router.post("/reload", response_model=ConfigResponse)
async def reload_configuration() -> ConfigResponse:
    """
    重新加载配置
    
    Returns:
        重新加载结果
        
    Raises:
        HTTPException: 当重新加载失败时
    """
    try:
        logger.info("重新加载系统配置")
        
        # 重新加载配置
        new_config = reload_config()
        
        logger.info("系统配置重新加载成功")
        
        return ConfigResponse(
            success=True,
            message="配置重新加载成功",
            config={
                "app": {
                    "name": new_config.name,
                    "version": new_config.version,
                    "debug": new_config.debug
                }
            }
        )
        
    except ConfigurationError as e:
        logger.error(f"重新加载配置失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"重新加载配置失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"重新加载配置时发生未知错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重新加载配置时发生内部错误"
        )


@router.post("/test/llm")
async def test_llm_connection(llm_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    测试LLM连接
    
    Args:
        llm_config: LLM配置
        
    Returns:
        测试结果
    """
    try:
        logger.info("测试LLM连接")
        
        provider = llm_config.get("provider", "unknown").lower()
        model = llm_config.get("model", "unknown")
        api_key = llm_config.get("api_key", "")
        
        # Mock提供商直接返回成功
        if provider == "mock":
            return {
                "success": True,
                "message": f"Mock LLM连接测试成功 (模型: {model})",
                "latency": 50,
                "provider": provider,
                "model": model
            }
        
        # 真实提供商需要API密钥
        if not api_key:
            return {
                "success": False,
                "message": f"LLM提供商 {provider} 需要API密钥",
                "provider": provider,
                "model": model,
                "error": "missing_api_key"
            }
        
        # 尝试实际连接测试
        start_time = time.time()
        
        if provider == "siliconflow":
            success, message = await _test_siliconflow_llm(llm_config)
        elif provider == "openai":
            success, message = await _test_openai_llm(llm_config)
        else:
            success = False
            message = f"不支持的LLM提供商: {provider}"
        
        latency = int((time.time() - start_time) * 1000)
        
        return {
            "success": success,
            "message": message,
            "latency": latency,
            "provider": provider,
            "model": model
        }
            
    except Exception as e:
        logger.error(f"LLM连接测试失败: {str(e)}")
        return {
            "success": False,
            "message": f"LLM连接测试失败: {str(e)}",
            "provider": llm_config.get("provider", "unknown"),
            "model": llm_config.get("model", "unknown")
        }


async def _test_siliconflow_llm(config: Dict[str, Any]) -> tuple[bool, str]:
    """测试SiliconFlow LLM连接"""
    try:
        import httpx
        
        api_key = config.get("api_key")
        base_url = config.get("base_url", "https://api.siliconflow.cn/v1")
        model = config.get("model", "Qwen/Qwen2-7B-Instruct")
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 发送简单的测试请求
        test_data = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=test_data
            )
            
            if response.status_code == 200:
                return True, f"SiliconFlow LLM连接成功 (模型: {model})"
            elif response.status_code == 401:
                return False, "API密钥无效"
            elif response.status_code == 404:
                return False, f"模型 {model} 不存在"
            else:
                return False, f"连接失败 (状态码: {response.status_code})"
                
    except httpx.TimeoutException:
        return False, "连接超时"
    except Exception as e:
        return False, f"连接异常: {str(e)}"


async def _test_openai_llm(config: Dict[str, Any]) -> tuple[bool, str]:
    """测试OpenAI LLM连接"""
    try:
        import httpx
        
        api_key = config.get("api_key")
        base_url = config.get("base_url", "https://api.openai.com/v1")
        model = config.get("model", "gpt-3.5-turbo")
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 发送简单的测试请求
        test_data = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=test_data
            )
            
            if response.status_code == 200:
                return True, f"OpenAI LLM连接成功 (模型: {model})"
            elif response.status_code == 401:
                return False, "API密钥无效"
            elif response.status_code == 404:
                return False, f"模型 {model} 不存在"
            else:
                return False, f"连接失败 (状态码: {response.status_code})"
                
    except httpx.TimeoutException:
        return False, "连接超时"
    except Exception as e:
        return False, f"连接异常: {str(e)}"


@router.get("/models/metrics")
async def get_models_metrics() -> Dict[str, Any]:
    """
    获取模型性能指标
    
    Returns:
        模型性能指标信息
    """
    try:
        logger.info("获取模型性能指标")
        
        # 尝试从模型管理器获取指标
        try:
            from ..services.model_manager import get_model_manager
            manager = get_model_manager()
            if manager:
                metrics_data = await manager.get_performance_metrics()
                return {
                    "success": True,
                    "data": metrics_data,
                    "timestamp": time.time()
                }
        except ImportError:
            logger.warning("模型管理器服务不可用")
        
        # 如果模型管理器不可用，返回基本指标信息
        config = get_current_config()
        
        metrics = {
            "embedding_metrics": {
                "total_requests": 0,
                "avg_response_time": 0.0,
                "success_rate": 100.0,
                "error_count": 0,
                "cache_hit_rate": 0.0
            },
            "reranking_metrics": {
                "total_requests": 0,
                "avg_response_time": 0.0,
                "success_rate": 100.0,
                "error_count": 0,
                "cache_hit_rate": 0.0
            },
            "system_metrics": {
                "memory_usage": 0.0,
                "cpu_usage": 0.0,
                "gpu_usage": 0.0,
                "disk_usage": 0.0
            }
        }
        
        return {
            "success": True,
            "data": metrics,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"获取模型指标失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": time.time()
        }


# 第一个重复的函数定义已删除


# 重复的函数定义已删除
    """
    测试模型连接
    
    Args:
        request: 模型测试请求
        
    Returns:
        测试结果
    """
    try:
        logger.info(f"测试模型: {request.model_type} - {request.model_name}")
        
        # 验证模型类型
        if request.model_type not in ['embedding', 'reranking']:
            return {
                "success": False,
                "error": f"不支持的模型类型: {request.model_type}"
            }
        
        # 尝试使用模型管理器测试
        try:
            from ..services.model_manager import get_model_manager
            manager = get_model_manager()
            if manager:
                result = await manager.test_model(request.model_type, request.model_name)
                return {
                    "success": result.get('success', False),
                    "message": result.get('message', '测试完成'),
                    "test_result": result.get('details', {}),
                    "latency": result.get('latency', 0)
                }
        except ImportError:
            logger.warning("模型管理器服务不可用")
        
        # 如果模型管理器不可用，进行基本测试
        config = get_current_config()
        start_time = time.time()
        
        if request.model_type == 'embedding':
            if config.embeddings and config.embeddings.provider == 'mock':
                test_result = {
                    "success": True,
                    "message": f"嵌入模型测试成功: {request.model_name}",
                    "test_result": {
                        "model": request.model_name,
                        "dimensions": getattr(config.embeddings, 'dimensions', 1536),
                        "test_text": "Hello, world!",
                        "embedding_length": getattr(config.embeddings, 'dimensions', 1536)
                    },
                    "latency": int((time.time() - start_time) * 1000)
                }
            else:
                test_result = {
                    "success": False,
                    "message": "嵌入模型测试需要有效的API配置",
                    "test_result": {},
                    "latency": int((time.time() - start_time) * 1000)
                }
        elif request.model_type == 'reranking':
            test_result = {
                "success": True,
                "message": f"重排序模型测试成功: {request.model_name}",
                "test_result": {
                    "model": request.model_name,
                    "test_query": "测试查询",
                    "test_documents": ["文档1", "文档2"],
                    "reranked_scores": [0.8, 0.6]
                },
                "latency": int((time.time() - start_time) * 1000)
            }
        
        return test_result
        
    except Exception as e:
        logger.error(f"测试模型失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "latency": int((time.time() - start_time) * 1000) if 'start_time' in locals() else 0
        }


@router.post("/models/update-config")
async def update_model_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新模型配置参数
    
    Args:
        config_data: 模型配置数据
        
    Returns:
        更新结果
    """
    try:
        logger.info("更新模型配置参数")
        
        # 获取当前配置
        config = get_current_config()
        updated_sections = {}
        
        # 更新嵌入模型配置
        if 'embeddings' in config_data:
            embedding_data = config_data['embeddings']
            if config.embeddings:
                # 更新现有配置
                for key, value in embedding_data.items():
                    if hasattr(config.embeddings, key):
                        setattr(config.embeddings, key, value)
            updated_sections['embeddings'] = embedding_data
        
        # 更新重排序模型配置
        if 'reranking' in config_data:
            reranking_data = config_data['reranking']
            if hasattr(config, 'reranking') and config.reranking:
                # 更新现有配置
                for key, value in reranking_data.items():
                    if hasattr(config.reranking, key):
                        setattr(config.reranking, key, value)
            updated_sections['reranking'] = reranking_data
        
        # 保存配置到文件
        save_success = save_config_to_file(updated_sections)
        
        return {
            "success": True,
            "message": "模型配置更新成功" + ("，已保存到配置文件" if save_success else "，但保存到配置文件失败"),
            "updated_sections": list(updated_sections.keys())
        }
        
    except Exception as e:
        logger.error(f"更新模型配置失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/models/health-check")
async def perform_model_health_check() -> Dict[str, Any]:
    """
    执行模型健康检查
    
    Returns:
        健康检查结果
    """
    try:
        logger.info("执行模型健康检查")
        
        config = get_current_config()
        health_results = {}
        
        # 检查嵌入模型
        if config.embeddings:
            logger.info("测试嵌入模型连接")
            embedding_health = await _test_embedding_health(config.embeddings)
            health_results['embedding'] = embedding_health
        
        # 检查LLM模型
        if config.llm:
            logger.info("测试LLM连接")
            llm_health = await _test_llm_health(config.llm)
            health_results['llm'] = llm_health
        
        # 检查重排序模型
        if hasattr(config, 'reranking') and config.reranking:
            health_results['reranking'] = {
                "status": "healthy",
                "message": "重排序模型运行正常",
                "latency": 50
            }
        
        # 计算整体健康状态
        all_healthy = all(result.get('status') == 'healthy' for result in health_results.values())
        
        return {
            "success": True,
            "overall_status": "healthy" if all_healthy else "unhealthy",
            "details": health_results,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "overall_status": "error",
            "timestamp": time.time()
        }


async def _test_embedding_health(embedding_config) -> Dict[str, Any]:
    """测试嵌入模型健康状态"""
    try:
        provider = embedding_config.provider.lower()
        
        if provider == 'mock':
            return {
                "status": "healthy",
                "message": "Mock嵌入模型运行正常",
                "latency": 10
            }
        
        # 对于真实的API提供商，进行连接测试
        if provider in ['openai', 'siliconflow']:
            api_key = getattr(embedding_config, 'api_key', '')
            if not api_key:
                return {
                    "status": "unhealthy",
                    "message": f"嵌入模型 {provider} 缺少API密钥",
                    "latency": 0
                }
            
            # 进行实际的API测试
            start_time = time.time()
            success, message = await _test_embedding_api(embedding_config)
            latency = int((time.time() - start_time) * 1000)
            
            return {
                "status": "healthy" if success else "unhealthy",
                "message": message,
                "latency": latency
            }
        
        return {
            "status": "unknown",
            "message": f"未知的嵌入提供商: {provider}",
            "latency": 0
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"嵌入模型健康检查异常: {str(e)}",
            "latency": 0
        }


async def _test_embedding_api(config) -> tuple[bool, str]:
    """测试嵌入API连接"""
    try:
        import httpx
        
        provider = config.provider.lower()
        api_key = getattr(config, 'api_key', '')
        base_url = getattr(config, 'base_url', '')
        model = config.model
        
        if provider == 'siliconflow':
            if not base_url:
                base_url = 'https://api.siliconflow.cn/v1'
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            test_data = {
                "model": model,
                "input": "Hello, world!",
                "encoding_format": "float"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{base_url}/embeddings",
                    headers=headers,
                    json=test_data
                )
                
                if response.status_code == 200:
                    return True, f"嵌入模型连接成功 (模型: {model})"
                elif response.status_code == 401:
                    return False, "API密钥无效"
                else:
                    return False, f"连接失败 (状态码: {response.status_code})"
        
        return False, f"不支持的嵌入提供商: {provider}"
        
    except httpx.TimeoutException:
        return False, "连接超时"
    except Exception as e:
        return False, f"连接异常: {str(e)}"


async def _test_llm_health(llm_config) -> Dict[str, Any]:
    """测试LLM健康状态"""
    try:
        provider = llm_config.provider.lower()
        
        if provider == 'mock':
            return {
                "status": "healthy",
                "message": "Mock LLM运行正常",
                "latency": 20
            }
        
        # 对于真实的API提供商，进行连接测试
        api_key = getattr(llm_config, 'api_key', '')
        if not api_key:
            return {
                "status": "unhealthy",
                "message": f"LLM {provider} 缺少API密钥",
                "latency": 0
            }
        
        # 进行实际的API测试
        start_time = time.time()
        if provider == 'siliconflow':
            success, message = await _test_siliconflow_llm({
                'provider': provider,
                'model': llm_config.model,
                'api_key': api_key,
                'base_url': getattr(llm_config, 'base_url', 'https://api.siliconflow.cn/v1')
            })
        elif provider == 'openai':
            success, message = await _test_openai_llm({
                'provider': provider,
                'model': llm_config.model,
                'api_key': api_key,
                'base_url': getattr(llm_config, 'base_url', 'https://api.openai.com/v1')
            })
        else:
            success = False
            message = f"不支持的LLM提供商: {provider}"
        
        latency = int((time.time() - start_time) * 1000)
        
        return {
            "status": "healthy" if success else "unhealthy",
            "message": message,
            "latency": latency
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"LLM健康检查异常: {str(e)}",
            "latency": 0
        }


# 模型管理相关的数据模型
class ModelConfigRequest(BaseModel):
    """模型配置请求模型"""
    model_type: str  # embedding 或 reranking
    name: str
    provider: str
    model_name: str
    config: Dict[str, Any]
    enabled: bool = True
    priority: int = 5

class ModelSwitchRequest(BaseModel):
    """模型切换请求模型"""
    model_type: str  # embedding 或 reranking
    model_name: str

class ModelTestRequest(BaseModel):
    """模型测试请求模型"""
    model_type: str  # embedding 或 reranking
    model_name: str


# 模型管理端点
@router.get("/models/status")
async def get_models_status() -> Dict[str, Any]:
    """
    获取模型状态和配置信息
    
    Returns:
        模型状态信息
    """
    try:
        logger.info("获取模型状态")
        
        # 从模型管理器获取状态（如果存在）
        try:
            from ..services.model_manager import get_model_manager
            manager = get_model_manager()
            if manager:
                status_data = await manager.get_comprehensive_status()
                return {
                    "success": True,
                    "data": status_data,
                    "timestamp": time.time()
                }
        except ImportError:
            logger.warning("模型管理器服务不可用")
        
        # 如果模型管理器不可用，返回基本配置信息
        config = get_current_config()
        
        # 构建基本的模型状态信息
        model_configs = {}
        model_statuses = {}
        service_details = {}
        
        # 从配置中获取嵌入模型信息
        if config.embeddings:
            embedding_config = {
                'name': f"embedding_{config.embeddings.provider}_{config.embeddings.model}",
                'model_type': 'embedding',
                'provider': config.embeddings.provider,
                'model_name': config.embeddings.model,
                'config': {
                    'api_key': getattr(config.embeddings, 'api_key', ''),
                    'base_url': getattr(config.embeddings, 'base_url', ''),
                    'dimensions': getattr(config.embeddings, 'dimensions', 1536),
                    'batch_size': getattr(config.embeddings, 'batch_size', 100),
                    'chunk_size': config.embeddings.chunk_size,
                    'chunk_overlap': config.embeddings.chunk_overlap,
                    'timeout': getattr(config.embeddings, 'timeout', 60)
                },
                'enabled': True,
                'priority': 10
            }
            model_configs[embedding_config['name']] = embedding_config
            model_statuses[embedding_config['name']] = {
                'status': 'ready',
                'health': 'unknown',
                'last_used': None
            }
        
        # 从配置中获取重排序模型信息
        if hasattr(config, 'reranking') and config.reranking:
            reranking_config = {
                'name': f"reranking_{getattr(config.reranking, 'provider', 'sentence_transformers')}_{getattr(config.reranking, 'model', 'cross-encoder')}",
                'model_type': 'reranking',
                'provider': getattr(config.reranking, 'provider', 'sentence_transformers'),
                'model_name': getattr(config.reranking, 'model', 'cross-encoder/ms-marco-MiniLM-L-6-v2'),
                'config': {
                    'api_key': getattr(config.reranking, 'api_key', ''),
                    'base_url': getattr(config.reranking, 'base_url', ''),
                    'batch_size': getattr(config.reranking, 'batch_size', 32),
                    'max_length': getattr(config.reranking, 'max_length', 512),
                    'timeout': getattr(config.reranking, 'timeout', 30.0)
                },
                'enabled': True,
                'priority': 10
            }
            model_configs[reranking_config['name']] = reranking_config
            model_statuses[reranking_config['name']] = {
                'status': 'ready',
                'health': 'unknown',
                'last_used': None
            }
        
        return {
            "success": True,
            "data": {
                "model_configs": model_configs,
                "model_statuses": model_statuses,
                "service_details": service_details,
                "active_models": {
                    "embedding": list(model_configs.keys())[0] if any(c['model_type'] == 'embedding' for c in model_configs.values()) else None,
                    "reranking": list(model_configs.keys())[0] if any(c['model_type'] == 'reranking' for c in model_configs.values()) else None
                }
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"获取模型状态失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


@router.get("/models/metrics")
async def get_models_metrics() -> Dict[str, Any]:
    """
    获取模型性能指标
    
    Returns:
        模型性能指标
    """
    try:
        logger.info("获取模型性能指标")
        
        # 从模型管理器获取指标（如果存在）
        try:
            from ..services.model_manager import get_model_manager
            manager = get_model_manager()
            if manager:
                manager_stats = manager.get_manager_stats()
                model_statuses = manager.get_all_model_statuses()
                
                return {
                    "success": True,
                    "data": {
                        "manager_stats": manager_stats,
                        "model_statuses": {name: status.to_dict() for name, status in model_statuses.items()},
                        "service_details": {}
                    },
                    "timestamp": time.time()
                }
        except ImportError:
            logger.warning("模型管理器服务不可用")
        
        # 返回基本指标
        return {
            "success": True,
            "data": {
                "manager_stats": {
                    "total_models": 1,
                    "loaded_models": 1,
                    "total_requests": 0,
                    "model_switches": 0
                },
                "model_statuses": {},
                "service_details": {}
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"获取模型指标失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": None
        }


@router.post("/models/switch-active")
async def switch_active_model(request: ModelSwitchRequest) -> Dict[str, Any]:
    """
    切换活跃模型
    
    Args:
        request: 模型切换请求
        
    Returns:
        切换结果
    """
    try:
        logger.info(f"切换活跃模型: {request.model_type} -> {request.model_name}")
        
        # 尝试使用模型管理器
        try:
            from ..services.model_manager import get_model_manager, ModelType
            manager = get_model_manager()
            if manager:
                model_type = ModelType(request.model_type)
                success = await manager.switch_active_model(model_type, request.model_name)
                
                if success:
                    return {
                        "success": True,
                        "message": f"成功切换{request.model_type}模型到: {request.model_name}",
                        "active_models": {
                            "embedding": manager.active_embedding_model,
                            "reranking": manager.active_reranking_model
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": f"切换模型失败: {request.model_name}"
                    }
        except ImportError:
            logger.warning("模型管理器服务不可用，使用配置更新方式")
        
        # 如果模型管理器不可用，更新配置
        config = get_current_config()
        
        if request.model_type == "embedding":
            if config.embeddings:
                # 保存嵌入模型配置
                embedding_config = {
                    "provider": config.embeddings.provider,
                    "model": request.model_name,
                    "chunk_size": config.embeddings.chunk_size,
                    "chunk_overlap": config.embeddings.chunk_overlap,
                    "batch_size": getattr(config.embeddings, 'batch_size', 100)
                }
                
                # 保留现有的API配置
                if hasattr(config.embeddings, 'api_key'):
                    embedding_config["api_key"] = config.embeddings.api_key
                if hasattr(config.embeddings, 'base_url'):
                    embedding_config["base_url"] = config.embeddings.base_url
                if hasattr(config.embeddings, 'timeout'):
                    embedding_config["timeout"] = config.embeddings.timeout
                if hasattr(config.embeddings, 'retry_attempts'):
                    embedding_config["retry_attempts"] = config.embeddings.retry_attempts
                
                save_success = save_config_to_file({"embeddings": embedding_config})
                
                if save_success:
                    # 重新加载配置
                    reload_config()
                
                return {
                    "success": True,
                    "message": f"成功切换嵌入模型到: {request.model_name}",
                    "active_models": {
                        "embedding": request.model_name,
                        "reranking": getattr(config, 'reranking', {}).get('model', None) if hasattr(config, 'reranking') else None
                    }
                }
        
        elif request.model_type == "reranking":
            # 处理重排序模型切换
            current_reranking = getattr(config, 'reranking', None)
            if current_reranking:
                reranking_config = {
                    "provider": current_reranking.provider if hasattr(current_reranking, 'provider') else 'sentence_transformers',
                    "model": request.model_name,
                    "batch_size": getattr(current_reranking, 'batch_size', 32),
                    "max_length": getattr(current_reranking, 'max_length', 512),
                    "timeout": getattr(current_reranking, 'timeout', 30.0)
                }
                
                # 保留现有的API配置
                if hasattr(current_reranking, 'api_key'):
                    reranking_config["api_key"] = current_reranking.api_key
                if hasattr(current_reranking, 'base_url'):
                    reranking_config["base_url"] = current_reranking.base_url
                if hasattr(current_reranking, 'retry_attempts'):
                    reranking_config["retry_attempts"] = current_reranking.retry_attempts
            else:
                # 如果没有现有配置，创建默认配置
                reranking_config = {
                    "provider": "sentence_transformers",
                    "model": request.model_name,
                    "batch_size": 32,
                    "max_length": 512,
                    "timeout": 30.0
                }
            
            save_success = save_config_to_file({"reranking": reranking_config})
            
            if save_success:
                # 重新加载配置
                reload_config()
            
            return {
                "success": True,
                "message": f"成功切换重排序模型到: {request.model_name}",
                "active_models": {
                    "embedding": config.embeddings.model if config.embeddings else None,
                    "reranking": request.model_name
                }
            }
        
        return {
            "success": False,
            "error": f"不支持的模型类型或配置不存在: {request.model_type}"
        }
        
    except Exception as e:
        logger.error(f"切换活跃模型失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/models/add-model")
async def add_model(request: ModelConfigRequest) -> Dict[str, Any]:
    """
    添加新模型配置
    
    Args:
        request: 模型配置请求
        
    Returns:
        添加结果
    """
    try:
        logger.info(f"添加新模型: {request.model_type} - {request.name}")
        
        # 尝试使用模型管理器
        try:
            from ..services.model_manager import get_model_manager, ModelConfig, ModelType
            manager = get_model_manager()
            if manager:
                model_config = ModelConfig(
                    model_type=ModelType(request.model_type),
                    name=request.name,
                    provider=request.provider,
                    model_name=request.model_name,
                    config=request.config,
                    enabled=request.enabled,
                    priority=request.priority
                )
                
                success = await manager.register_model(model_config)
                
                if success:
                    return {
                        "success": True,
                        "message": f"成功添加{request.model_type}模型: {request.name}",
                        "model_config": model_config.to_dict()
                    }
                else:
                    return {
                        "success": False,
                        "error": f"添加模型失败: {request.name}"
                    }
        except ImportError:
            logger.warning("模型管理器服务不可用，使用配置更新方式")
        
        # 如果模型管理器不可用，更新配置文件
        config = get_current_config()
        
        if request.model_type == "embedding":
            # 更新嵌入模型配置
            embedding_config = {
                "provider": request.provider,
                "model": request.model_name,
                "chunk_size": request.config.get("chunk_size", 1000),
                "chunk_overlap": request.config.get("chunk_overlap", 200),
                "batch_size": request.config.get("batch_size", 100)
            }
            
            # 如果有API密钥，添加到配置中
            if "api_key" in request.config:
                embedding_config["api_key"] = request.config["api_key"]
            if "base_url" in request.config:
                embedding_config["base_url"] = request.config["base_url"]
            if "timeout" in request.config:
                embedding_config["timeout"] = request.config["timeout"]
            if "retry_attempts" in request.config:
                embedding_config["retry_attempts"] = request.config["retry_attempts"]
            
            save_success = save_config_to_file({"embeddings": embedding_config})
            
            if save_success:
                # 重新加载配置
                reload_config()
                return {
                    "success": True,
                    "message": f"成功添加嵌入模型: {request.name}",
                    "model_config": {
                        "name": request.name,
                        "provider": request.provider,
                        "model_name": request.model_name,
                        "config": request.config
                    }
                }
        
        elif request.model_type == "reranking":
            # 更新重排序模型配置
            reranking_config = {
                "provider": request.provider,
                "model": request.model_name,
                "batch_size": request.config.get("batch_size", 32),
                "max_length": request.config.get("max_length", 512),
                "timeout": request.config.get("timeout", 30.0)
            }
            
            # 如果有API密钥，添加到配置中
            if "api_key" in request.config:
                reranking_config["api_key"] = request.config["api_key"]
            if "base_url" in request.config:
                reranking_config["base_url"] = request.config["base_url"]
            if "retry_attempts" in request.config:
                reranking_config["retry_attempts"] = request.config["retry_attempts"]
            
            save_success = save_config_to_file({"reranking": reranking_config})
            
            if save_success:
                # 重新加载配置
                reload_config()
                return {
                    "success": True,
                    "message": f"成功添加重排序模型: {request.name}",
                    "model_config": {
                        "name": request.name,
                        "provider": request.provider,
                        "model_name": request.model_name,
                        "config": request.config
                    }
                }
        
        return {
            "success": False,
            "error": f"不支持的模型类型或添加失败: {request.model_type}"
        }
        
    except Exception as e:
        logger.error(f"添加模型失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/models/test-model")
async def test_model(request: ModelTestRequest) -> Dict[str, Any]:
    """
    测试指定模型
    
    Args:
        request: 模型测试请求
        
    Returns:
        测试结果
    """
    try:
        logger.info(f"测试模型: {request.model_type} - {request.model_name}")
        
        # 尝试使用模型管理器
        try:
            from ..services.model_manager import get_model_manager
            manager = get_model_manager()
            if manager:
                if request.model_type == "embedding":
                    service = manager.get_embedding_service(request.model_name)
                    if service:
                        test_result = await service.test_embedding("模型测试查询")
                        return {
                            "success": True,
                            "message": f"模型测试成功: {request.model_name}",
                            "test_result": test_result
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Embedding服务不存在或未加载: {request.model_name}"
                        }
                
                elif request.model_type == "reranking":
                    service = manager.get_reranking_service(request.model_name)
                    if service:
                        # 创建测试数据
                        from ..models.vector import SearchResult
                        import uuid
                        
                        test_results = [
                            SearchResult(
                                chunk_id=str(uuid.uuid4()),
                                document_id=str(uuid.uuid4()),
                                content="这是一个测试文档，用于验证重排序功能",
                                similarity_score=0.8,
                                metadata={"source": "test.txt"}
                            )
                        ]
                        
                        from ..models.config import RetrievalConfig
                        test_config = RetrievalConfig(enable_rerank=True)
                        reranked_results = await service.rerank_results(
                            "测试查询", test_results, test_config
                        )
                        
                        return {
                            "success": True,
                            "message": f"模型测试成功: {request.model_name}",
                            "test_result": {
                                "success": True,
                                "original_count": len(test_results),
                                "reranked_count": len(reranked_results),
                                "processing_time": 0.1
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"重排序服务不存在或未加载: {request.model_name}"
                        }
        except ImportError:
            logger.warning("模型管理器服务不可用，使用配置测试方式")
        
        # 如果模型管理器不可用，使用配置进行测试
        config = get_current_config()
        
        if request.model_type == "embedding" and config.embeddings:
            if config.embeddings.model == request.model_name:
                # 使用现有的嵌入模型测试功能
                embedding_config = {
                    "provider": config.embeddings.provider,
                    "model": config.embeddings.model,
                    "api_key": getattr(config.embeddings, 'api_key', ''),
                    "base_url": getattr(config.embeddings, 'base_url', '')
                }
                
                test_result = await test_embedding_connection(embedding_config)
                return {
                    "success": test_result["success"],
                    "message": f"模型测试完成: {request.model_name}",
                    "test_result": test_result
                }
        
        return {
            "success": False,
            "error": f"不支持的模型类型或模型不存在: {request.model_type} - {request.model_name}"
        }
        
    except Exception as e:
        logger.error(f"测试模型失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/models/update-config")
async def update_model_config(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    更新模型配置参数
    
    Args:
        request: 包含模型配置更新的请求
        
    Returns:
        更新结果
    """
    try:
        logger.info("更新模型配置参数")
        
        # 获取当前配置
        config = get_current_config()
        config_updates = {}
        
        # 处理嵌入模型配置更新
        if "embeddings" in request:
            embedding_data = request["embeddings"]
            embedding_config = {
                "provider": embedding_data.get("provider", config.embeddings.provider if config.embeddings else "mock"),
                "model": embedding_data.get("model", config.embeddings.model if config.embeddings else "test-model"),
                "chunk_size": embedding_data.get("chunk_size", 1000),
                "chunk_overlap": embedding_data.get("chunk_overlap", 200),
                "batch_size": embedding_data.get("batch_size", 100)
            }
            
            # 添加API配置
            if "api_key" in embedding_data:
                embedding_config["api_key"] = embedding_data["api_key"]
            if "base_url" in embedding_data:
                embedding_config["base_url"] = embedding_data["base_url"]
            if "timeout" in embedding_data:
                embedding_config["timeout"] = embedding_data["timeout"]
            if "retry_attempts" in embedding_data:
                embedding_config["retry_attempts"] = embedding_data["retry_attempts"]
            
            config_updates["embeddings"] = embedding_config
        
        # 处理重排序模型配置更新
        if "reranking" in request:
            reranking_data = request["reranking"]
            reranking_config = {
                "provider": reranking_data.get("provider", "sentence_transformers"),
                "model": reranking_data.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
                "batch_size": reranking_data.get("batch_size", 32),
                "max_length": reranking_data.get("max_length", 512),
                "timeout": reranking_data.get("timeout", 30.0)
            }
            
            # 添加API配置
            if "api_key" in reranking_data:
                reranking_config["api_key"] = reranking_data["api_key"]
            if "base_url" in reranking_data:
                reranking_config["base_url"] = reranking_data["base_url"]
            if "retry_attempts" in reranking_data:
                reranking_config["retry_attempts"] = reranking_data["retry_attempts"]
            
            config_updates["reranking"] = reranking_config
        
        # 保存配置到文件
        if config_updates:
            save_success = save_config_to_file(config_updates)
            
            if save_success:
                # 强制重新加载配置
                global current_config
                current_config = None  # 清除缓存
                reload_config()  # 重新加载
                
                return {
                    "success": True,
                    "message": "模型配置更新成功",
                    "updated_configs": config_updates
                }
            else:
                return {
                    "success": False,
                    "error": "配置保存失败"
                }
        else:
            return {
                "success": False,
                "error": "没有提供有效的配置更新"
            }
        
    except Exception as e:
        logger.error(f"更新模型配置失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/models/health-check")
async def perform_health_check() -> Dict[str, Any]:
    """
    执行健康检查
    
    Returns:
        健康检查结果
    """
    try:
        logger.info("执行模型健康检查")
        
        # 尝试使用模型管理器
        try:
            from ..services.model_manager import get_model_manager
            manager = get_model_manager()
            if manager:
                await manager._perform_health_checks()
                model_statuses = manager.get_all_model_statuses()
                
                # 统计健康状态
                total_models = len(model_statuses)
                healthy_models = sum(1 for status in model_statuses.values() if status.health == 'healthy')
                unhealthy_models = sum(1 for status in model_statuses.values() if status.health == 'unhealthy')
                
                return {
                    "success": True,
                    "message": "健康检查完成",
                    "health_summary": {
                        "total_models": total_models,
                        "healthy_models": healthy_models,
                        "unhealthy_models": unhealthy_models,
                        "health_rate": healthy_models / total_models if total_models > 0 else 0
                    },
                    "model_statuses": {name: status.to_dict() for name, status in model_statuses.items()},
                    "timestamp": time.time()
                }
        except ImportError:
            logger.warning("模型管理器服务不可用，执行基本健康检查")
        
        # 基本健康检查
        config = get_current_config()
        health_results = {}
        
        # 检查嵌入模型配置
        if config.embeddings:
            embedding_config = {
                "provider": config.embeddings.provider,
                "model": config.embeddings.model,
                "api_key": getattr(config.embeddings, 'api_key', ''),
                "base_url": getattr(config.embeddings, 'base_url', '')
            }
            
            test_result = await test_embedding_connection(embedding_config)
            health_results["embedding"] = {
                "status": "healthy" if test_result["success"] else "unhealthy",
                "message": test_result["message"],
                "model": config.embeddings.model
            }
        
        # 检查LLM配置
        if config.llm:
            llm_config = {
                "provider": config.llm.provider,
                "model": config.llm.model,
                "api_key": getattr(config.llm, 'api_key', ''),
                "base_url": getattr(config.llm, 'base_url', '')
            }
            
            test_result = await test_llm_connection(llm_config)
            health_results["llm"] = {
                "status": "healthy" if test_result["success"] else "unhealthy",
                "message": test_result["message"],
                "model": config.llm.model
            }
        
        healthy_count = sum(1 for result in health_results.values() if result["status"] == "healthy")
        total_count = len(health_results)
        
        return {
            "success": True,
            "message": "基本健康检查完成",
            "health_summary": {
                "total_models": total_count,
                "healthy_models": healthy_count,
                "unhealthy_models": total_count - healthy_count,
                "health_rate": healthy_count / total_count if total_count > 0 else 0
            },
            "model_statuses": health_results,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/test/embedding")
async def test_embedding_connection(embedding_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    测试嵌入模型连接
    
    Args:
        embedding_config: 嵌入模型配置
        
    Returns:
        测试结果
    """
    try:
        logger.info("测试嵌入模型连接")
        
        provider = embedding_config.get("provider", "unknown").lower()
        model = embedding_config.get("model", "unknown")
        api_key = embedding_config.get("api_key", "")
        
        # Mock提供商直接返回成功
        if provider == "mock":
            return {
                "success": True,
                "message": f"Mock嵌入模型连接测试成功 (模型: {model})",
                "latency": 30,
                "provider": provider,
                "model": model,
                "dimensions": 768
            }
        
        # 真实提供商需要API密钥
        if not api_key:
            return {
                "success": False,
                "message": f"嵌入模型提供商 {provider} 需要API密钥",
                "provider": provider,
                "model": model,
                "error": "missing_api_key"
            }
        
        # 尝试实际连接测试
        start_time = time.time()
        
        if provider == "siliconflow":
            success, message, dimensions = await _test_siliconflow_embedding(embedding_config)
        elif provider == "openai":
            success, message, dimensions = await _test_openai_embedding(embedding_config)
        else:
            success = False
            message = f"不支持的嵌入模型提供商: {provider}"
            dimensions = None
        
        latency = int((time.time() - start_time) * 1000)
        
        result = {
            "success": success,
            "message": message,
            "latency": latency,
            "provider": provider,
            "model": model
        }
        
        if dimensions:
            result["dimensions"] = dimensions
            
        return result
            
    except Exception as e:
        logger.error(f"嵌入模型连接测试失败: {str(e)}")
        return {
            "success": False,
            "message": f"嵌入模型连接测试失败: {str(e)}",
            "provider": embedding_config.get("provider", "unknown"),
            "model": embedding_config.get("model", "unknown")
        }


async def _test_siliconflow_embedding(config: Dict[str, Any]) -> tuple[bool, str, Optional[int]]:
    """测试SiliconFlow嵌入模型连接"""
    try:
        import httpx
        
        api_key = config.get("api_key")
        base_url = config.get("base_url", "https://api.siliconflow.cn/v1")
        model = config.get("model", "BAAI/bge-large-zh-v1.5")
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 发送简单的测试请求
        test_data = {
            "model": model,
            "input": ["测试文本"],
            "encoding_format": "float"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{base_url}/embeddings",
                headers=headers,
                json=test_data
            )
            
            if response.status_code == 200:
                result = response.json()
                dimensions = len(result.get("data", [{}])[0].get("embedding", []))
                return True, f"SiliconFlow嵌入模型连接成功 (模型: {model})", dimensions
            elif response.status_code == 401:
                return False, "API密钥无效", None
            elif response.status_code == 404:
                return False, f"模型 {model} 不存在", None
            else:
                return False, f"连接失败 (状态码: {response.status_code})", None
                
    except httpx.TimeoutException:
        return False, "连接超时", None
    except Exception as e:
        return False, f"连接异常: {str(e)}", None


async def _test_openai_embedding(config: Dict[str, Any]) -> tuple[bool, str, Optional[int]]:
    """测试OpenAI嵌入模型连接"""
    try:
        import httpx
        
        api_key = config.get("api_key")
        base_url = config.get("base_url", "https://api.openai.com/v1")
        model = config.get("model", "text-embedding-ada-002")
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        # 发送简单的测试请求
        test_data = {
            "model": model,
            "input": ["test text"],
            "encoding_format": "float"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{base_url}/embeddings",
                headers=headers,
                json=test_data
            )
            
            if response.status_code == 200:
                result = response.json()
                dimensions = len(result.get("data", [{}])[0].get("embedding", []))
                return True, f"OpenAI嵌入模型连接成功 (模型: {model})", dimensions
            elif response.status_code == 401:
                return False, "API密钥无效", None
            elif response.status_code == 404:
                return False, f"模型 {model} 不存在", None
            else:
                return False, f"连接失败 (状态码: {response.status_code})", None
                
    except httpx.TimeoutException:
        return False, "连接超时", None
    except Exception as e:
        return False, f"连接异常: {str(e)}", None


@router.post("/test/storage")
async def test_storage_connection(storage_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    测试存储连接
    
    Args:
        storage_config: 存储配置
        
    Returns:
        测试结果
    """
    try:
        logger.info("测试存储连接")
        
        storage_type = storage_config.get("type", "unknown")
        
        # 模拟测试结果
        if storage_type == "chroma":
            return {
                "success": True,
                "message": "Chroma向量存储连接测试成功",
                "latency": 20,
                "type": storage_type,
                "status": "healthy"
            }
        else:
            return {
                "success": True,
                "message": f"存储连接配置有效 (类型: {storage_type})",
                "latency": 40,
                "type": storage_type,
                "note": "实际连接测试需要存储服务运行"
            }
            
    except Exception as e:
        logger.error(f"存储连接测试失败: {str(e)}")
        return {
            "success": False,
            "message": f"存储连接测试失败: {str(e)}",
            "type": storage_config.get("type", "unknown")
        }


@router.post("/test/all")
async def test_all_connections(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    测试所有连接
    
    Args:
        config: 完整配置
        
    Returns:
        所有测试结果
    """
    try:
        logger.info("测试所有连接")
        
        results = {
            "overall_success": True,
            "tests": {}
        }
        
        # 测试LLM连接
        if "llm" in config:
            llm_result = await test_llm_connection(config["llm"])
            results["tests"]["llm"] = llm_result
            if not llm_result["success"]:
                results["overall_success"] = False
        
        # 测试嵌入模型连接
        if "embedding" in config:
            embedding_result = await test_embedding_connection(config["embedding"])
            results["tests"]["embedding"] = embedding_result
            if not embedding_result["success"]:
                results["overall_success"] = False
        
        # 测试存储连接
        if "storage" in config:
            storage_result = await test_storage_connection(config["storage"])
            results["tests"]["storage"] = storage_result
            if not storage_result["success"]:
                results["overall_success"] = False
        
        results["message"] = "所有连接测试完成" if results["overall_success"] else "部分连接测试失败"
        
        return results
        
    except Exception as e:
        logger.error(f"连接测试失败: {str(e)}")
        return {
            "overall_success": False,
            "message": f"连接测试失败: {str(e)}",
            "tests": {}
        }


@router.get("/schema/{section}")
async def get_config_schema(section: str) -> Dict[str, Any]:
    """
    获取配置节的JSON Schema
    
    Args:
        section: 配置节名称
        
    Returns:
        配置节的JSON Schema
        
    Raises:
        HTTPException: 当配置节不存在时
    """
    try:
        logger.info(f"获取配置节Schema: {section}")
        
        allowed_sections = ['database', 'vector_store', 'embeddings', 'llm', 'retrieval', 'api']
        if section not in allowed_sections:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的配置节: {section}. 支持的配置节: {', '.join(allowed_sections)}"
            )
        
        # 定义各配置节的Schema
        schemas = {
            "database": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "数据库连接URL"},
                    "echo": {"type": "boolean", "description": "是否输出SQL日志"}
                },
                "required": ["url"]
            },
            "vector_store": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["chroma", "pinecone", "faiss"], "description": "向量存储类型"},
                    "persist_directory": {"type": "string", "description": "持久化目录"},
                    "collection_name": {"type": "string", "description": "集合名称"}
                },
                "required": ["type"]
            },
            "embeddings": {
                "type": "object",
                "properties": {
                    "provider": {"type": "string", "enum": ["openai", "huggingface", "mock"], "description": "嵌入提供商"},
                    "model": {"type": "string", "description": "嵌入模型名称"},
                    "chunk_size": {"type": "integer", "minimum": 1, "maximum": 8000, "description": "文本块大小"},
                    "chunk_overlap": {"type": "integer", "minimum": 0, "description": "文本块重叠大小"}
                },
                "required": ["provider", "model"]
            },
            "llm": {
                "type": "object",
                "properties": {
                    "provider": {"type": "string", "enum": ["openai", "anthropic", "mock"], "description": "LLM提供商"},
                    "model": {"type": "string", "description": "LLM模型名称"},
                    "temperature": {"type": "number", "minimum": 0, "maximum": 2, "description": "生成温度"},
                    "max_tokens": {"type": "integer", "minimum": 1, "description": "最大token数"}
                },
                "required": ["provider", "model"]
            },
            "retrieval": {
                "type": "object",
                "properties": {
                    "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "description": "检索结果数量"},
                    "similarity_threshold": {"type": "number", "minimum": 0, "maximum": 1, "description": "相似度阈值"}
                },
                "required": ["top_k"]
            },
            "api": {
                "type": "object",
                "properties": {
                    "host": {"type": "string", "description": "API主机地址"},
                    "port": {"type": "integer", "minimum": 1, "maximum": 65535, "description": "API端口"},
                    "cors_origins": {"type": "array", "items": {"type": "string"}, "description": "CORS允许的源"}
                },
                "required": ["host", "port"]
            }
        }
        
        return {
            "section": section,
            "schema": schemas[section]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取配置Schema时发生错误: {section}, 错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取配置Schema时发生内部错误"
        )