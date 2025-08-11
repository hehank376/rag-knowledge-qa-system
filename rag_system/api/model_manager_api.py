"""
模型管理API

提供模型配置、加载、切换、监控等功能的API接口。
支持嵌入模型和重排序模型的统一管理。
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..services.model_manager import ModelManager, ModelConfig, ModelType
from ..utils.exceptions import ConfigurationError, ProcessingError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])


async def save_model_config_to_file(model_type: str, model_name: str, config: Dict[str, Any]) -> bool:
    """保存模型配置到配置文件"""
    try:
        # 导入配置保存函数
        from .config_api import save_config_to_file
        from ..config.loader import ConfigLoader
        
        config_loader = ConfigLoader()
        
        # 根据模型类型确定配置节
        if model_type == "embedding":
            section_name = "embeddings"
            # 构造嵌入模型配置
            embedding_config = {
                'provider': config.get('provider', 'siliconflow'),
                'model': model_name,
                'dimensions': config.get('dimensions', 1024),  # 关键：保存用户设置的维度
                'batch_size': config.get('batch_size', 50),
                'chunk_size': config.get('chunk_size', 1000),
                'chunk_overlap': config.get('chunk_overlap', 50),
                'timeout': config.get('timeout', 120),
                'api_key': config.get('api_key', ''),
                'base_url': config.get('base_url', '')
            }
            config_data = {section_name: embedding_config}
            
        elif model_type == "reranking":
            section_name = "reranking"
            # 构造重排序模型配置
            reranking_config = {
                'provider': config.get('provider', 'siliconflow'),
                'model': model_name,
                'model_name': model_name,  # 兼容性
                'batch_size': config.get('batch_size', 32),
                'max_length': config.get('max_length', 512),
                'timeout': config.get('timeout', 60),
                'api_key': config.get('api_key', ''),
                'base_url': config.get('base_url', '')
            }
            config_data = {section_name: reranking_config}
        else:
            logger.error(f"不支持的模型类型: {model_type}")
            return False
        
        # 保存到配置文件
        success = save_config_to_file(config_data, config_loader.config_path)
        
        if success:
            # 重新加载配置缓存，确保API返回最新值
            from .config_api import reload_config
            reload_config()
            
            logger.info(f"模型配置已保存到配置文件并重新加载: {model_type} - {model_name}")
            return True
        else:
            logger.error(f"保存模型配置到文件失败: {model_type} - {model_name}")
            return False
            
    except Exception as e:
        logger.error(f"保存模型配置到文件时出错: {str(e)}")
        return False


# 全局模型管理器实例
_model_manager_instance: Optional[ModelManager] = None

# 依赖注入：获取模型管理器实例
async def get_model_manager() -> ModelManager:
    """获取模型管理器实例（单例模式）"""
    global _model_manager_instance
    
    if _model_manager_instance is None:
        from ..config.loader import ConfigLoader
        
        config_loader = ConfigLoader()
        app_config = config_loader.load_config()
        
        # 构造模型管理器配置
        config = {
            'embeddings': {
                'provider': app_config.embeddings.provider,
                'model': app_config.embeddings.model,
                'dimensions': app_config.embeddings.dimensions,
                'batch_size': app_config.embeddings.batch_size,
                'api_key': app_config.embeddings.api_key,
                'base_url': app_config.embeddings.base_url
            },
            'reranking': {
                'provider': getattr(app_config.reranking, 'provider', 'mock') if app_config.reranking else 'mock',
                'model': getattr(app_config.reranking, 'model', 'mock-reranking') if app_config.reranking else 'mock-reranking',
                'batch_size': getattr(app_config.reranking, 'batch_size', 32) if app_config.reranking else 32,
                'max_length': getattr(app_config.reranking, 'max_length', 512) if app_config.reranking else 512,
                'api_key': getattr(app_config.reranking, 'api_key', '') if app_config.reranking else '',
                'base_url': getattr(app_config.reranking, 'base_url', '') if app_config.reranking else ''
            }
        }
        
        # 创建并初始化模型管理器
        _model_manager_instance = ModelManager(config)
        await _model_manager_instance.initialize()
        logger.info("模型管理器单例实例已创建并初始化")
    
    return _model_manager_instance


class AddModelRequest(BaseModel):
    """添加模型请求"""
    model_type: str = Field(..., description="模型类型 (embedding/reranking)")
    name: str = Field(..., description="模型名称")
    provider: str = Field(..., description="提供商")
    model_name: str = Field(..., description="具体模型名称")
    config: Dict[str, Any] = Field(default_factory=dict, description="模型配置")


class TestModelRequest(BaseModel):
    """测试模型请求"""
    model_type: str = Field(..., description="模型类型 (embedding/reranking)")
    model_name: str = Field(..., description="模型名称")


class SwitchModelRequest(BaseModel):
    """切换模型请求"""
    model_type: str = Field(..., description="模型类型 (embedding/reranking)")
    model_name: str = Field(..., description="模型名称")


@router.post("/add")
async def add_model(
    request: AddModelRequest,
    manager: ModelManager = Depends(get_model_manager)
):
    """添加新模型配置"""
    try:
        
        # 创建模型配置
        model_config = ModelConfig(
            model_type=ModelType(request.model_type),
            name=request.name,
            provider=request.provider,
            model_name=request.model_name,
            config=request.config
        )
        
        # 注册模型到内存
        success = await manager.register_model(model_config)
        if success:
            # 同时更新配置文件
            await save_model_config_to_file(request.model_type, request.model_name, request.config)
            
            # 尝试加载模型
            load_success = await manager.load_model(request.name)
            return {
                "success": True,
                "message": f"模型 {request.name} 添加成功并已保存到配置文件",
                "loaded": load_success
            }
        else:
            raise HTTPException(status_code=400, detail="模型添加失败")
            
    except Exception as e:
        logger.error(f"添加模型失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"添加模型失败: {str(e)}")


@router.post("/test")
async def test_model(
    request: TestModelRequest,
    manager: ModelManager = Depends(get_model_manager)
):
    """测试模型连接"""
    try:
        
        # 测试模型
        result = await manager.test_model(request.model_type, request.model_name)
        return result
        
    except Exception as e:
        logger.error(f"测试模型失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"测试模型失败: {str(e)}")


@router.get("/configs")
async def get_model_configs(
    manager: ModelManager = Depends(get_model_manager)
):
    """获取所有模型配置"""
    try:
        
        # 获取综合状态信息
        status = await manager.get_comprehensive_status()
        return {
            "success": True,
            "model_configs": status.get("model_configs", {}),
            "active_models": status.get("active_models", {}),
            "model_statuses": status.get("model_statuses", {})
        }
        
    except Exception as e:
        logger.error(f"获取模型配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取模型配置失败: {str(e)}")


@router.post("/switch")
async def switch_active_model(
    request: SwitchModelRequest,
    manager: ModelManager = Depends(get_model_manager)
):
    """切换活跃模型"""
    try:
        
        # 切换模型
        success = await manager.switch_active_model(ModelType(request.model_type), request.model_name)
        if success:
            return {
                "success": True,
                "message": f"成功切换到模型: {request.model_name}"
            }
        else:
            raise HTTPException(status_code=400, detail="模型切换失败")
            
    except Exception as e:
        logger.error(f"切换模型失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"切换模型失败: {str(e)}")