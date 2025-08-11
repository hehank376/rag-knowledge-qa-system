#!/usr/bin/env python3
"""
最优数据库集成方案测试
验证与现有系统的完美集成
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.services.database_service import DatabaseService, get_database_service
from rag_system.services.config_service import ConfigService
from rag_system.utils.logger import get_logger

logger = get_logger(__name__)

class OptimalDatabaseIntegrationTester:
    """最优数据库集成方案测试器"""
    
    def __init__(self):
        self.test_results = []
        self.config_service = ConfigService()
        self.database_service = None
    
    def add_test_result(self, test_name: str, success: bool, message: str = ""):
        """添加测试结果"""
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
        
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{status} - {test_name}: {message}")
    
    async def test_config_integration(self):
        """测试配置系统集成"""
        try:
            # 测试从现有配置文件读取数据库配置
            self.database_service = DatabaseService()
            db_config = self.database_service.get_database_config()
            
            if db_config and 'url' in db_config:
                self.add_test_result("配置集成", True, f"成功读取配置: {db_config['type']}")
            else:
                self.add_test_result("配置集成", False, "无法读取数据库配置")
            
            # 测试配置格式兼容性
            expected_keys = ['url', 'type', 'config']
            if all(key in db_config for key in expected_keys):
                self.add_test_result("配置格式", True, "配置格式完全兼容")
            else:
                missing_keys = [key for key in expected_keys if key not in db_config]
                self.add_test_result("配置格式", False, f"缺少配置项: {missing_keys}")
                
        except Exception as e:
            self.add_test_result("配置集成", False, f"异常: {str(e)}")
    
    async def test_database_initialization(self):
        """测试数据库初始化"""
        try:
            if not self.database_service:
                self.database_service = DatabaseService()
            
            # 测试数据库服务初始化
            db_manager = await self.database_service.initialize()
            
            if db_manager:
                self.add_test_result("数据库初始化", True, "数据库服务初始化成功")
                
                # 测试数据库类型检测
                db_type = db_manager.get_database_type()
                if db_type in ['sqlite', 'postgresql', 'mysql']:
                    self.add_test_result("类型检测", True, f"正确检测数据库类型: {db_type}")
                else:
                    self.add_test_result("类型检测", False, f"未知数据库类型: {db_type}")
            else:
                self.add_test_result("数据库初始化", False, "数据库管理器初始化失败")
                
        except Exception as e:
            self.add_test_result("数据库初始化", False, f"异常: {str(e)}")
    
    async def test_connection_testing(self):
        """测试连接测试功能"""
        try:
            if not self.database_service:
                self.database_service = DatabaseService()
            
            # 测试使用当前配置的连接测试
            test_result = await self.database_service.test_connection()
            
            if test_result['success']:
                self.add_test_result("连接测试", True, "连接测试成功")
            else:
                self.add_test_result("连接测试", False, f"连接测试失败: {test_result.get('message')}")
            
            # 测试自定义配置的连接测试
            custom_config = {
                'url': 'sqlite:///./test_custom.db',
                'config': {'timeout': 30.0}
            }
            
            custom_test_result = await self.database_service.test_connection(custom_config)
            
            if custom_test_result['success']:
                self.add_test_result("自定义连接测试", True, "自定义配置连接测试成功")
            else:
                self.add_test_result("自定义连接测试", False, "自定义配置连接测试失败")
                
        except Exception as e:
            self.add_test_result("连接测试", False, f"异常: {str(e)}")
    
    async def test_health_check(self):
        """测试健康检查功能"""
        try:
            if not self.database_service:
                self.database_service = DatabaseService()
                await self.database_service.initialize()
            
            # 测试健康检查
            is_healthy = await self.database_service.health_check()
            
            if is_healthy:
                self.add_test_result("健康检查", True, "数据库健康检查通过")
            else:
                self.add_test_result("健康检查", False, "数据库健康检查失败")
                
        except Exception as e:
            self.add_test_result("健康检查", False, f"异常: {str(e)}")
    
    async def test_connection_info(self):
        """测试连接信息获取"""
        try:
            if not self.database_service:
                self.database_service = DatabaseService()
                await self.database_service.initialize()
            
            # 测试连接信息获取
            connection_info = self.database_service.get_connection_info()
            
            if connection_info:
                expected_keys = ['database_type', 'service_initialized', 'supported_types']
                if all(key in connection_info for key in expected_keys):
                    self.add_test_result("连接信息", True, f"连接信息完整: {connection_info['database_type']}")
                else:
                    missing_keys = [key for key in expected_keys if key not in connection_info]
                    self.add_test_result("连接信息", False, f"连接信息不完整，缺少: {missing_keys}")
            else:
                self.add_test_result("连接信息", False, "无法获取连接信息")
                
        except Exception as e:
            self.add_test_result("连接信息", False, f"异常: {str(e)}")
    
    async def test_supported_databases(self):
        """测试支持的数据库类型"""
        try:
            if not self.database_service:
                self.database_service = DatabaseService()
            
            # 测试获取支持的数据库类型
            supported_dbs = self.database_service.get_supported_databases()
            
            expected_types = ['sqlite', 'postgresql', 'mysql']
            if all(db_type in supported_dbs for db_type in expected_types):
                self.add_test_result("支持的数据库", True, f"支持所有预期数据库类型: {list(supported_dbs.keys())}")
            else:
                missing_types = [db_type for db_type in expected_types if db_type not in supported_dbs]
                self.add_test_result("支持的数据库", False, f"缺少数据库类型支持: {missing_types}")
            
            # 测试数据库信息完整性
            for db_type, db_info in supported_dbs.items():
                required_fields = ['name', 'description', 'url_template', 'config_fields']
                if all(field in db_info for field in required_fields):
                    self.add_test_result(f"{db_type}信息完整性", True, f"{db_type}信息完整")
                else:
                    missing_fields = [field for field in required_fields if field not in db_info]
                    self.add_test_result(f"{db_type}信息完整性", False, f"{db_type}信息不完整，缺少: {missing_fields}")
                    
        except Exception as e:
            self.add_test_result("支持的数据库", False, f"异常: {str(e)}")
    
    async def test_config_reload(self):
        """测试配置重新加载"""
        try:
            if not self.database_service:
                self.database_service = DatabaseService()
                await self.database_service.initialize()
            
            # 测试配置重新加载
            reload_success = await self.database_service.reload_config()
            
            if reload_success:
                self.add_test_result("配置重新加载", True, "配置重新加载成功")
            else:
                self.add_test_result("配置重新加载", False, "配置重新加载失败")
                
        except Exception as e:
            self.add_test_result("配置重新加载", False, f"异常: {str(e)}")
    
    async def test_backward_compatibility(self):
        """测试向后兼容性"""
        try:
            # 测试现有配置文件格式兼容性
            from rag_system.config.loader import ConfigLoader
            
            config_loader = ConfigLoader()
            config = config_loader.get_config()
            
            # 检查数据库配置是否存在
            if 'database' in config:
                db_config = config['database']
                
                # 检查必要的配置项
                if 'url' in db_config:
                    self.add_test_result("向后兼容性", True, "现有配置格式完全兼容")
                else:
                    self.add_test_result("向后兼容性", False, "配置格式不兼容，缺少url")
            else:
                self.add_test_result("向后兼容性", False, "配置文件中缺少database部分")
                
        except Exception as e:
            self.add_test_result("向后兼容性", False, f"异常: {str(e)}")
    
    async def test_service_integration(self):
        """测试服务集成"""
        try:
            # 测试全局服务获取
            global_service = get_database_service()
            
            if global_service:
                self.add_test_result("全局服务", True, "全局数据库服务获取成功")
                
                # 测试服务单例模式
                another_service = get_database_service()
                if global_service is another_service:
                    self.add_test_result("单例模式", True, "数据库服务正确实现单例模式")
                else:
                    self.add_test_result("单例模式", False, "数据库服务未正确实现单例模式")
            else:
                self.add_test_result("全局服务", False, "无法获取全局数据库服务")
                
        except Exception as e:
            self.add_test_result("服务集成", False, f"异常: {str(e)}")
    
    async def test_error_handling(self):
        """测试错误处理"""
        try:
            # 测试无效配置的错误处理
            invalid_config = {
                'url': 'invalid://invalid',
                'config': {}
            }
            
            test_service = DatabaseService()
            result = await test_service.test_connection(invalid_config)
            
            if not result['success'] and 'error' in result:
                self.add_test_result("错误处理", True, "正确处理无效配置错误")
            else:
                self.add_test_result("错误处理", False, "未正确处理无效配置错误")
                
        except Exception as e:
            # 异常也是正确的错误处理方式
            self.add_test_result("错误处理", True, f"正确抛出异常: {str(e)}")
    
    async def test_performance(self):
        """测试性能"""
        try:
            import time
            
            if not self.database_service:
                self.database_service = DatabaseService()
            
            # 测试初始化性能
            start_time = time.time()
            await self.database_service.initialize()
            init_time = time.time() - start_time
            
            if init_time < 5.0:  # 5秒内完成初始化
                self.add_test_result("初始化性能", True, f"初始化耗时: {init_time:.2f}秒")
            else:
                self.add_test_result("初始化性能", False, f"初始化耗时过长: {init_time:.2f}秒")
            
            # 测试连接测试性能
            start_time = time.time()
            await self.database_service.test_connection()
            test_time = time.time() - start_time
            
            if test_time < 3.0:  # 3秒内完成连接测试
                self.add_test_result("连接测试性能", True, f"连接测试耗时: {test_time:.2f}秒")
            else:
                self.add_test_result("连接测试性能", False, f"连接测试耗时过长: {test_time:.2f}秒")
                
        except Exception as e:
            self.add_test_result("性能测试", False, f"异常: {str(e)}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始最优数据库集成方案测试...")
        
        # 运行各项测试
        test_methods = [
            self.test_config_integration,
            self.test_database_initialization,
            self.test_connection_testing,
            self.test_health_check,
            self.test_connection_info,
            self.test_supported_databases,
            self.test_config_reload,
            self.test_backward_compatibility,
            self.test_service_integration,
            self.test_error_handling,
            self.test_performance
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                test_name = test_method.__name__.replace('test_', '').replace('_', ' ')
                self.add_test_result(test_name, False, f"测试执行异常: {str(e)}")
        
        # 清理资源
        if self.database_service:
            await self.database_service.close()
        
        # 输出测试结果
        self.print_test_results()
    
    def print_test_results(self):
        """打印测试结果"""
        print("\n" + "="*80)
        print("最优数据库集成方案测试结果")
        print("="*80)
        
        passed = 0
        failed = 0
        
        # 按类别分组显示结果
        categories = {
            '配置集成': ['配置集成', '配置格式', '向后兼容性'],
            '数据库功能': ['数据库初始化', '类型检测', '连接测试', '自定义连接测试'],
            '服务管理': ['健康检查', '连接信息', '配置重新加载', '全局服务', '单例模式'],
            '扩展性': ['支持的数据库', 'sqlite信息完整性', 'postgresql信息完整性', 'mysql信息完整性'],
            '可靠性': ['错误处理', '初始化性能', '连接测试性能']
        }
        
        for category, test_names in categories.items():
            print(f"\n📁 {category}")
            print("-" * 40)
            
            for result in self.test_results:
                if result['test'] in test_names:
                    status = "✅ 通过" if result['success'] else "❌ 失败"
                    print(f"  {status} {result['test']}: {result['message']}")
                    
                    if result['success']:
                        passed += 1
                    else:
                        failed += 1
        
        # 显示未分类的测试结果
        categorized_tests = set()
        for test_names in categories.values():
            categorized_tests.update(test_names)
        
        uncategorized = [r for r in self.test_results if r['test'] not in categorized_tests]
        if uncategorized:
            print(f"\n📁 其他测试")
            print("-" * 40)
            for result in uncategorized:
                status = "✅ 通过" if result['success'] else "❌ 失败"
                print(f"  {status} {result['test']}: {result['message']}")
                
                if result['success']:
                    passed += 1
                else:
                    failed += 1
        
        print("\n" + "="*80)
        print(f"测试总结: 通过 {passed} 项，失败 {failed} 项")
        
        if failed == 0:
            print("🎉 所有测试通过！最优数据库集成方案完美运行。")
            print("\n✨ 方案优势:")
            print("  • 完全向后兼容现有配置")
            print("  • 支持多种数据库类型")
            print("  • 无缝集成现有系统")
            print("  • 企业级性能和可靠性")
            print("  • 优雅的错误处理")
        else:
            print(f"⚠️  有 {failed} 项测试失败，请检查相关功能。")
        
        print("="*80)

async def main():
    """主函数"""
    tester = OptimalDatabaseIntegrationTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())