#!/usr/bin/env python3
"""
用户管理API
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPAuthorizationCredentials

from ..models.user import (
    UserCreate, UserUpdate, UserLogin, UserResponse, 
    TokenResponse, PasswordChange
)
from ..services.user_service import UserService
from ..middleware.auth_middleware import (
    get_current_user, get_current_active_user, require_admin
)
from ..utils.exceptions import (
    AuthenticationError, AuthorizationError, ValidationError,
    NotFoundError, ConflictError
)
from ..utils.logging_config import get_simple_logger as get_logger

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/users", tags=["用户管理"])

# 全局用户服务实例
user_service: Optional[UserService] = None

def get_user_service() -> UserService:
    """获取用户服务实例"""
    global user_service
    if user_service is None:
        # 这里应该从配置中初始化用户服务
        # 暂时创建一个默认配置的实例
        config = {
            'jwt_secret': 'your-secret-key-here',
            'jwt_algorithm': 'HS256',
            'jwt_expiration_hours': 24,
            'session_expiration_hours': 168,
            'max_login_attempts': 5,
            'lockout_duration_minutes': 30
        }
        user_service = UserService(config)
    return user_service

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: UserCreate,
    service: UserService = Depends(get_user_service)
) -> UserResponse:
    """
    用户注册
    
    创建新用户账户。默认角色为普通用户。
    """
    try:
        user = await service.create_user(user_data)
        logger.info(f"新用户注册成功: {user.username}")
        return user
    except ConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"用户注册失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册服务暂时不可用"
        )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    login_data: UserLogin,
    service: UserService = Depends(get_user_service)
) -> TokenResponse:
    """
    用户登录
    
    验证用户凭据并返回访问令牌。
    """
    try:
        token_response = await service.authenticate_user(login_data)
        logger.info(f"用户登录成功: {login_data.username}")
        return token_response
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"用户登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录服务暂时不可用"
        )

@router.post("/logout")
async def logout_user(
    credentials: HTTPAuthorizationCredentials = Depends(get_current_user),
    service: UserService = Depends(get_user_service)
) -> Dict[str, str]:
    """
    用户登出
    
    使当前用户的访问令牌失效。
    """
    try:
        if credentials:
            await service.logout(credentials.credentials)
        return {"message": "登出成功"}
    except Exception as e:
        logger.error(f"用户登出失败: {str(e)}")
        return {"message": "登出完成"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_active_user)
) -> UserResponse:
    """
    获取当前用户信息
    
    返回当前认证用户的详细信息。
    """
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: UserResponse = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service)
) -> UserResponse:
    """
    更新当前用户信息
    
    允许用户更新自己的个人信息。
    """
    try:
        # 创建一个临时的User对象用于权限检查
        from ..models.user import User
        temp_user = User(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            password_hash="",  # 不需要真实密码哈希
            role=current_user.role,
            status=current_user.status
        )
        
        updated_user = await service.update_user(current_user.id, update_data, temp_user)
        logger.info(f"用户信息更新成功: {current_user.username}")
        return updated_user
    except (ValidationError, ConflictError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"更新用户信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新服务暂时不可用"
        )

@router.post("/me/change-password")
async def change_current_user_password(
    password_data: PasswordChange,
    current_user: UserResponse = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service)
) -> Dict[str, str]:
    """
    修改当前用户密码
    
    允许用户修改自己的密码。
    """
    try:
        # 创建一个临时的User对象用于权限检查
        from ..models.user import User
        temp_user = User(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            password_hash="",  # 不需要真实密码哈希
            role=current_user.role,
            status=current_user.status
        )
        
        success = await service.change_password(current_user.id, password_data, temp_user)
        if success:
            logger.info(f"用户密码修改成功: {current_user.username}")
            return {"message": "密码修改成功，请重新登录"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="密码修改失败"
            )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"修改密码失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码修改服务暂时不可用"
        )

# 管理员专用端点
@router.get("/", response_model=Dict[str, Any])
async def list_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: UserResponse = Depends(require_admin()),
    service: UserService = Depends(get_user_service)
) -> Dict[str, Any]:
    """
    获取用户列表
    
    管理员专用：分页获取所有用户列表。
    """
    try:
        # 创建一个临时的User对象用于权限检查
        from ..models.user import User
        temp_user = User(
            id=current_user.id,
            username=current_user.username,
            email=current_user.email,
            password_hash="",
            role=current_user.role,
            status=current_user.status
        )
        
        result = await service.list_users(temp_user, page, size)
        return result
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="用户列表服务暂时不可用"
        )

@router.get("/health/check")
async def health_check() -> Dict[str, str]:
    """
    用户服务健康检查
    
    检查用户管理服务的运行状态。
    """
    try:
        return {
            "status": "healthy",
            "service": "user_management",
            "timestamp": str(datetime.utcnow())
        }
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="用户服务不可用"
        )