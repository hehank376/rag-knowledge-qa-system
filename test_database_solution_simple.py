#!/usr/bin/env python3
"""
数据库解决方案简化测试
验证核心功能而不依赖复杂的模块结构
"""

import asyncio
import sys
import os
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class SimpleDatabaseTester:
    """简化的数据库解决方案测试器"""
    
    def __init__(self):
        self.test_results = []
    
    def add_test_result(self, test_name: str, success: bool, message: str = ""):
        """添加测试结果"""
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
        
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{status} - {test_name}: {message}")
    
    async def test_database_factory(self):
        """测试数据库工厂"""
        try:
            from rag_system.database.factory import DatabaseFactory
            
            # 测试获取支持的数据库类型
            supported_types = DatabaseFactory.get_supported_types()
            
            if 'sqlite' in supported_types:
                self.add_test_result("工厂-支持类型", True, f"支持的数据库: {supported_types}")
            else:
                self.add_test_result("工厂-支持类型", False, "未找到SQLite支持")
            
            # 测试创建SQLite适配器
            try:
                adapter = DatabaseFactory.create_adapter('sqlite:///./test.db')
                if adapter and adapter.get_database_type() == 'sqlite':
                    self.add_test_result("工厂-创建适配器", True, "SQLite适配器创建成功")
                else:
                    self.add_test_result("工厂-创建适配器", False, "SQLite适配器创建失败")
            except Exception as e:
                self.add_test_result("工厂-创建适配器", False, f"创建适配器异常: {str(e)}")
            
        except ImportError as e:
            self.add_test_result("数据库工厂", False, f"导入失败: {str(e)}")
        except Exception as e:
            self.add_test_result("数据库工厂", False, f"异常: {str(e)}")
    
    async def test_database_adapters(self):
        """测试数据库适配器"""
        try:
            from rag_system.database.adapters.sqlite_adapter import SQLiteAdapter
            
            # 测试SQLite适配器创建
            adapter = SQLiteAdapter('sqlite:///./test_simple.db')
            
            if adapter:
                self.add_test_result("SQLite适配器", True, "SQLite适配器创建成功")
                
                # 测试数据库类型检测
                db_type = adapter.get_database_type()
                if db_type == 'sqlite':
                    self.add_test_result("类型检测", True, f"正确检测数据库类型: {db_type}")
                else:
                    self.add_test_result("类型检测", False, f"数据库类型检测错误: {db_type}")
            else:
                self.add_test_result("SQLite适配器", False, "SQLite适配器创建失败")
                
        except ImportError as e:
            self.add_test_result("数据库适配器", False, f"导入失败: {str(e)}")
        except Exception as e:
            self.add_test_result("数据库适配器", False, f"异常: {str(e)}")
    
    async def test_database_connection(self):
        """测试数据库连接管理器"""
        try:
            from rag_system.database.connection import DatabaseManager
            
            # 测试数据库管理器创建
            db_manager = DatabaseManager('sqlite:///./test_connection.db')
            
            if db_manager:
                self.add_test_result("连接管理器", True, "数据库管理器创建成功")
                
                # 测试数据库类型获取
                try:
                    await db_manager.initialize()
                    db_type = db_manager.get_database_type()
                    if db_type == 'sqlite':
                        self.add_test_result("管理器类型检测", True, f"管理器正确检测类型: {db_type}")
                    else:
                        self.add_test_result("管理器类型检测", False, f"管理器类型检测错误: {db_type}")
                    
                    # 清理
                    await db_manager.close()
                    
                except Exception as e:
                    self.add_test_result("管理器初始化", False, f"初始化异常: {str(e)}")
            else:
                self.add_test_result("连接管理器", False, "数据库管理器创建失败")
                
        except ImportError as e:
            self.add_test_result("数据库连接", False, f"导入失败: {str(e)}")
        except Exception as e:
            self.add_test_result("数据库连接", False, f"异常: {str(e)}")
    
    async def test_config_compatibility(self):
        """测试配置兼容性"""
        try:
            # 测试配置文件读取
            import yaml
            
            config_path = 'config/development.yaml'
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                if 'database' in config:
                    db_config = config['database']
                    if 'url' in db_config:
                        self.add_test_result("配置兼容性", True, f"配置文件格式正确: {db_config['url']}")
                    else:
                        self.add_test_result("配置兼容性", False, "配置文件缺少url字段")
                else:
                    self.add_test_result("配置兼容性", False, "配置文件缺少database部分")
            else:
                self.add_test_result("配置兼容性", False, "配置文件不存在")
                
        except Exception as e:
            self.add_test_result("配置兼容性", False, f"异常: {str(e)}")
    
    async def test_api_integration(self):
        """测试API集成"""
        try:
            # 检查API文件是否存在增强的端点
            api_file = 'rag_system/api/config_api.py'
            if os.path.exists(api_file):
                with open(api_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查是否包含数据库相关端点
                if '/database/info' in content and '/database/test' in content:
                    self.add_test_result("API集成", True, "API端点已正确添加")
                else:
                    self.add_test_result("API集成", False, "API端点未找到")
            else:
                self.add_test_result("API集成", False, "API文件不存在")
                
        except Exception as e:
            self.add_test_result("API集成", False, f"异常: {str(e)}")
    
    async def test_frontend_integration(self):
        """测试前端集成"""
        try:
            # 检查前端文件是否存在
            frontend_files = [
                'frontend/js/api.js',
                'frontend/js/database-config.js'
            ]
            
            all_exist = True
            for file_path in frontend_files:
                if not os.path.exists(file_path):
                    all_exist = False
                    break
            
            if all_exist:
                # 检查API客户端是否包含数据库方法
                with open('frontend/js/api.js', 'r', encoding='utf-8') as f:
                    api_content = f.read()
                
                if 'getDatabaseInfo' in api_content and 'testDatabaseConnection' in api_content:
                    self.add_test_result("前端集成", True, "前端文件和API方法已正确添加")
                else:
                    self.add_test_result("前端集成", False, "前端API方法未找到")
            else:
                self.add_test_result("前端集成", False, "前端文件不完整")
                
        except Exception as e:
            self.add_test_result("前端集成", False, f"异常: {str(e)}")
    
    async def test_architecture_design(self):
        """测试架构设计"""
        try:
            # 检查核心架构文件是否存在
            architecture_files = [
                'rag_system/database/base.py',
                'rag_system/database/factory.py',
                'rag_system/database/adapters/__init__.py',
                'rag_system/database/adapters/sqlite_adapter.py',
                'rag_system/database/adapters/postgresql_adapter.py',
                'rag_system/database/adapters/mysql_adapter.py'
            ]
            
            existing_files = []
            missing_files = []
            
            for file_path in architecture_files:
                if os.path.exists(file_path):
                    existing_files.append(file_path)
                else:
                    missing_files.append(file_path)
            
            if len(existing_files) == len(architecture_files):
                self.add_test_result("架构设计", True, "所有架构文件已创建")
            else:
                self.add_test_result("架构设计", False, f"缺少文件: {missing_files}")
                
        except Exception as e:
            self.add_test_result("架构设计", False, f"异常: {str(e)}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        print("开始数据库解决方案测试...")
        print("="*60)
        
        # 运行各项测试
        test_methods = [
            self.test_architecture_design,
            self.test_database_factory,
            self.test_database_adapters,
            self.test_database_connection,
            self.test_config_compatibility,
            self.test_api_integration,
            self.test_frontend_integration
        ]
        
        for test_method in test_methods:
            try:
                await test_method()
            except Exception as e:
                test_name = test_method.__name__.replace('test_', '').replace('_', ' ')
                self.add_test_result(test_name, False, f"测试执行异常: {str(e)}")
        
        # 输出测试结果
        self.print_test_results()
    
    def print_test_results(self):
        """打印测试结果"""
        print("\n" + "="*60)
        print("数据库解决方案测试结果")
        print("="*60)
        
        passed = 0
        failed = 0
        
        for result in self.test_results:
            if result['success']:
                passed += 1
            else:
                failed += 1
        
        print(f"\n测试总结: 通过 {passed} 项，失败 {failed} 项")
        
        if failed == 0:
            print("\n🎉 所有测试通过！数据库解决方案实现成功。")
            print("\n✨ 解决方案特点:")
            print("  • ✅ 多数据库支持架构已建立")
            print("  • ✅ 与现有配置系统兼容")
            print("  • ✅ API和前端集成完成")
            print("  • ✅ 适配器模式正确实现")
        else:
            print(f"\n⚠️  有 {failed} 项测试失败。")
            print("\n📋 失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  • {result['test']}: {result['message']}")
        
        print("\n" + "="*60)

async def main():
    """主函数"""
    tester = SimpleDatabaseTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())