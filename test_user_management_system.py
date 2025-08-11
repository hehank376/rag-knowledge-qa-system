#!/usr/bin/env python3
"""
用户管理系统测试
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.models.user import (
    UserCreate, UserUpdate, UserLogin, UserRole, UserStatus, PasswordChange
)
from rag_system.services.user_service import UserService
from rag_system.middleware.auth_middleware import AuthMiddleware, init_auth_middleware
from rag_system.database.connection import init_database
from rag_system.utils.logger import get_logger

logger = get_logger(__name__)

class UserManagementTester:
    """用户管理系统测试器"""
    
    def __init__(self):
        self.user_service = None
        self.auth_middleware = None
        self.test_results = []
    
    async def initialize(self):
        """初始化测试环境"""
        try:
            # 初始化数据库
            await init_database("sqlite:///./test_users.db")
            
            # 初始化用户服务
            config = {
                'jwt_secret': 'test-secret-key-12345',
                'jwt_algorithm': 'HS256',
                'jwt_expiration_hours': 24,
                'session_expiration_hours': 168,
                'max_login_attempts': 5,
                'lockout_duration_minutes': 30
            }
            self.user_service = UserService(config)
            await self.user_service.initialize()
            
            # 初始化认证中间件
            self.auth_middleware = init_auth_middleware(self.user_service)
            
            logger.info("用户管理系统测试环境初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"测试环境初始化失败: {str(e)}")
            return False
    
    def add_test_result(self, test_name: str, success: bool, message: str = ""):
        """添加测试结果"""
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now()
        })
        
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{status} - {test_name}: {message}")
    
    async def test_user_creation(self):
        """测试用户创建"""
        try:
            # 测试创建普通用户
            user_data = UserCreate(
                username="testuser",
                email="test@example.com",
                password="password123",
                full_name="测试用户"
            )
            
            user = await self.user_service.create_user(user_data)
            
            if user and user.username == "testuser":
                self.add_test_result("用户创建", True, f"成功创建用户: {user.username}")
            else:
                self.add_test_result("用户创建", False, "用户创建失败")
                
        except Exception as e:
            self.add_test_result("用户创建", False, f"异常: {str(e)}")
    
    async def test_user_authentication(self):
        """测试用户认证"""
        try:
            # 测试正确的登录凭据
            login_data = UserLogin(username="admin", password="admin123")
            
            token_response = await self.user_service.authenticate_user(login_data)
            
            if token_response and token_response.access_token:
                self.add_test_result("用户认证", True, "登录成功，获得访问令牌")
                
                # 测试令牌验证
                user = await self.user_service.get_current_user(token_response.access_token)
                if user and user.username == "admin":
                    self.add_test_result("令牌验证", True, "令牌验证成功")
                else:
                    self.add_test_result("令牌验证", False, "令牌验证失败")
            else:
                self.add_test_result("用户认证", False, "登录失败")\n                \n        except Exception as e:\n            self.add_test_result("用户认证", False, f"异常: {str(e)}")\n    \n    async def test_password_security(self):\n        """测试密码安全性"""\n        try:\n            # 测试密码哈希\n            password = "testpassword123"\n            hashed = self.user_service._hash_password(password)\n            \n            if hashed and hashed != password:\n                self.add_test_result("密码哈希", True, "密码正确哈希")\n                \n                # 测试密码验证\n                if self.user_service._verify_password(password, hashed):\n                    self.add_test_result("密码验证", True, "密码验证正确")\n                else:\n                    self.add_test_result("密码验证", False, "密码验证失败")\n                    \n                # 测试错误密码\n                if not self.user_service._verify_password("wrongpassword", hashed):\n                    self.add_test_result("错误密码拒绝", True, "正确拒绝错误密码")\n                else:\n                    self.add_test_result("错误密码拒绝", False, "未能拒绝错误密码")\n            else:\n                self.add_test_result("密码哈希", False, "密码哈希失败")\n                \n        except Exception as e:\n            self.add_test_result("密码安全性", False, f"异常: {str(e)}")\n    \n    async def test_jwt_token_functionality(self):\n        """测试JWT令牌功能"""\n        try:\n            from rag_system.models.user import User\n            \n            # 创建测试用户\n            test_user = User(\n                id="test-user-id",\n                username="testjwt",\n                email="jwt@test.com",\n                password_hash="dummy",\n                role=UserRole.USER\n            )\n            \n            # 生成JWT令牌\n            token = self.user_service._generate_jwt_token(test_user)\n            \n            if token:\n                self.add_test_result("JWT生成", True, "JWT令牌生成成功")\n                \n                # 验证JWT令牌\n                payload = self.user_service._verify_jwt_token(token)\n                \n                if payload and payload.get('username') == 'testjwt':\n                    self.add_test_result("JWT验证", True, "JWT令牌验证成功")\n                else:\n                    self.add_test_result("JWT验证", False, "JWT令牌验证失败")\n            else:\n                self.add_test_result("JWT生成", False, "JWT令牌生成失败")\n                \n        except Exception as e:\n            self.add_test_result("JWT功能", False, f"异常: {str(e)}")\n    \n    async def test_user_roles_and_permissions(self):\n        """测试用户角色和权限"""\n        try:\n            from rag_system.models.user import User\n            \n            # 测试不同角色的权限\n            roles_permissions = [\n                (UserRole.ADMIN, ['read', 'write', 'delete', 'admin'], True),\n                (UserRole.USER, ['read', 'write'], True),\n                (UserRole.VIEWER, ['read'], True),\n                (UserRole.GUEST, ['read'], True)\n            ]\n            \n            for role, permissions, should_have in roles_permissions:\n                user = User(\n                    id=f"test-{role.value}",\n                    username=f"test{role.value}",\n                    email=f"{role.value}@test.com",\n                    password_hash="dummy",\n                    role=role\n                )\n                \n                # 测试权限检查
                has_read = user.has_permission('read')
                has_write = user.has_permission('write')
                
                if role == UserRole.ADMIN:
                    # 管理员应该有所有权限
                    if has_read and has_write:
                        self.add_test_result(f"{role.value}权限", True, "管理员权限正确")
                    else:
                        self.add_test_result(f"{role.value}权限", False, "管理员权限不正确")
                elif role == UserRole.VIEWER:
                    # 查看者只有读权限
                    if has_read and not has_write:
                        self.add_test_result(f"{role.value}权限", True, "查看者权限正确")
                    else:
                        self.add_test_result(f"{role.value}权限", False, "查看者权限不正确")
                else:
                    # 普通用户有读写权限
                    if has_read:
                        self.add_test_result(f"{role.value}权限", True, f"{role.value}权限正确")
                    else:
                        self.add_test_result(f"{role.value}权限", False, f"{role.value}权限不正确")\n                        \n        except Exception as e:\n            self.add_test_result("角色权限", False, f"异常: {str(e)}")\n    \n    async def test_session_management(self):\n        """测试会话管理"""\n        try:\n            # 测试会话创建和验证\n            from rag_system.models.user import UserSession\n            \n            session = UserSession(\n                user_id="test-user",\n                expires_at=datetime.utcnow() + timedelta(hours=1)\n            )\n            \n            if session.is_valid():\n                self.add_test_result("会话创建", True, "会话创建成功且有效")\n            else:\n                self.add_test_result("会话创建", False, "会话创建失败或无效")\n            \n            # 测试过期会话\n            expired_session = UserSession(\n                user_id="test-user",\n                expires_at=datetime.utcnow() - timedelta(hours=1)\n            )\n            \n            if expired_session.is_expired():\n                self.add_test_result("会话过期检测", True, "正确检测到过期会话")\n            else:\n                self.add_test_result("会话过期检测", False, "未能检测到过期会话")\n                \n        except Exception as e:\n            self.add_test_result("会话管理", False, f"异常: {str(e)}")\n    \n    async def test_authentication_middleware(self):\n        """测试认证中间件"""\n        try:\n            # 测试中间件启用/禁用\n            self.auth_middleware.set_enabled(False)\n            \n            if not self.auth_middleware.enabled:\n                self.add_test_result("中间件禁用", True, "认证中间件成功禁用")\n            else:\n                self.add_test_result("中间件禁用", False, "认证中间件禁用失败")\n            \n            # 重新启用\n            self.auth_middleware.set_enabled(True)\n            \n            if self.auth_middleware.enabled:\n                self.add_test_result("中间件启用", True, "认证中间件成功启用")\n            else:\n                self.add_test_result("中间件启用", False, "认证中间件启用失败")\n                \n        except Exception as e:\n            self.add_test_result("认证中间件", False, f"异常: {str(e)}")\n    \n    async def test_user_statistics(self):\n        """测试用户统计"""\n        try:\n            stats = await self.user_service.get_user_stats()\n            \n            if isinstance(stats, dict) and 'total_users' in stats:\n                self.add_test_result("用户统计", True, f"获取统计信息成功: {stats}")\n            else:\n                self.add_test_result("用户统计", False, "获取统计信息失败")\n                \n        except Exception as e:\n            self.add_test_result("用户统计", False, f"异常: {str(e)}")\n    \n    async def test_security_features(self):\n        """测试安全功能"""\n        try:\n            # 测试登录尝试限制\n            username = "testlimit"\n            \n            # 模拟多次失败登录\n            for i in range(3):\n                self.user_service._record_login_attempt(username, False)\n            \n            # 检查是否被锁定（需要达到最大尝试次数）\n            is_locked_before_limit = self.user_service._is_account_locked(username)\n            \n            # 继续失败尝试直到达到限制\n            for i in range(3):\n                self.user_service._record_login_attempt(username, False)\n            \n            is_locked_after_limit = self.user_service._is_account_locked(username)\n            \n            if not is_locked_before_limit and is_locked_after_limit:\n                self.add_test_result("登录限制", True, "登录尝试限制功能正常")\n            else:\n                self.add_test_result("登录限制", False, "登录尝试限制功能异常")\n            \n            # 测试成功登录清除失败记录\n            self.user_service._record_login_attempt(username, True)\n            is_locked_after_success = self.user_service._is_account_locked(username)\n            \n            if not is_locked_after_success:\n                self.add_test_result("登录重置", True, "成功登录后正确重置失败记录")\n            else:\n                self.add_test_result("登录重置", False, "成功登录后未能重置失败记录")\n                \n        except Exception as e:\n            self.add_test_result("安全功能", False, f"异常: {str(e)}")\n    \n    async def run_all_tests(self):\n        """运行所有测试"""\n        logger.info("开始用户管理系统测试...")\n        \n        # 初始化测试环境\n        if not await self.initialize():\n            logger.error("测试环境初始化失败，终止测试")\n            return\n        \n        # 运行各项测试\n        test_methods = [\n            self.test_user_creation,\n            self.test_user_authentication,\n            self.test_password_security,\n            self.test_jwt_token_functionality,\n            self.test_user_roles_and_permissions,\n            self.test_session_management,\n            self.test_authentication_middleware,\n            self.test_user_statistics,\n            self.test_security_features\n        ]\n        \n        for test_method in test_methods:\n            try:\n                await test_method()\n            except Exception as e:\n                test_name = test_method.__name__.replace('test_', '').replace('_', ' ')\n                self.add_test_result(test_name, False, f"测试执行异常: {str(e)}")\n        \n        # 输出测试结果\n        self.print_test_results()\n    \n    def print_test_results(self):\n        """打印测试结果"""\n        print("\\n" + "="*80)\n        print("用户管理系统测试结果")\n        print("="*80)\n        \n        passed = 0\n        failed = 0\n        \n        for result in self.test_results:\n            status = "✅ 通过" if result['success'] else "❌ 失败"\n            print(f"{status} {result['test']}: {result['message']}")\n            \n            if result['success']:\n                passed += 1\n            else:\n                failed += 1\n        \n        print("\\n" + "-"*80)\n        print(f"测试总结: 通过 {passed} 项，失败 {failed} 项")\n        \n        if failed == 0:\n            print("🎉 所有测试通过！用户管理系统功能正常。")\n        else:\n            print(f"⚠️  有 {failed} 项测试失败，请检查相关功能。")\n        \n        print("="*80)\n\nasync def main():\n    """主函数"""\n    tester = UserManagementTester()\n    await tester.run_all_tests()\n\nif __name__ == "__main__":\n    asyncio.run(main())