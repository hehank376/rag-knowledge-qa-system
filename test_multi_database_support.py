#!/usr/bin/env python3
"""
多数据库支持测试
"""

import asyncio
import sys
import os
from typing import Dict, Any, List

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rag_system.database.connection import init_database, close_database, get_supported_databases
from rag_system.database.factory import DatabaseFactory
from rag_system.utils.logger import get_logger

logger = get_logger(__name__)

class MultiDatabaseTester:
    """多数据库支持测试器"""
    
    def __init__(self):
        self.test_results = []
        self.test_databases = [
            {
                'name': 'SQLite',
                'url': 'sqlite:///./test_multi_db.db',
                'config': {'timeout': 30.0}
            },
            # 注意：以下数据库需要实际的服务器才能测试
            # {
            #     'name': 'PostgreSQL',
            #     'url': 'postgresql://user:password@localhost:5432/testdb',
            #     'config': {'min_size': 1, 'max_size': 5}
            # },
            # {
            #     'name': 'MySQL',
            #     'url': 'mysql://user:password@localhost:3306/testdb',
            #     'config': {'minsize': 1, 'maxsize': 5}
            # }
        ]
    
    def add_test_result(self, test_name: str, success: bool, message: str = ""):
        """添加测试结果"""
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
        
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{status} - {test_name}: {message}")
    
    async def test_database_factory(self):
        """测试数据库工厂"""
        try:
            # 测试获取支持的数据库类型
            supported_types = DatabaseFactory.get_supported_types()
            
            if 'sqlite' in supported_types:
                self.add_test_result("工厂-支持类型", True, f"支持的数据库: {supported_types}")
            else:
                self.add_test_result("工厂-支持类型", False, "未找到SQLite支持")
            
            # 测试创建SQLite适配器
            adapter = DatabaseFactory.create_adapter('sqlite:///./test.db')
            if adapter and adapter.get_database_type() == 'sqlite':
                self.add_test_result("工厂-创建适配器", True, "SQLite适配器创建成功")
            else:
                self.add_test_result("工厂-创建适配器", False, "SQLite适配器创建失败")
            
            # 测试不支持的数据库类型
            try:
                DatabaseFactory.create_adapter('unsupported://test')
                self.add_test_result("工厂-错误处理", False, "应该抛出异常但没有")
            except ValueError:
                self.add_test_result("工厂-错误处理", True, "正确处理不支持的数据库类型")
                
        except Exception as e:
            self.add_test_result("数据库工厂", False, f"异常: {str(e)}")
    
    async def test_database_connection(self, db_config: Dict[str, Any]):
        """测试数据库连接"""
        db_name = db_config['name']
        
        try:
            # 初始化数据库
            db_manager = await init_database(db_config['url'], db_config['config'])
            
            if db_manager:
                self.add_test_result(f"{db_name}-连接", True, "数据库连接成功")
                
                # 测试健康检查
                is_healthy = await db_manager.health_check()
                if is_healthy:
                    self.add_test_result(f"{db_name}-健康检查", True, "数据库健康检查通过")
                else:
                    self.add_test_result(f"{db_name}-健康检查", False, "数据库健康检查失败")
                
                # 测试获取数据库类型
                db_type = db_manager.get_database_type()
                expected_type = db_config['url'].split('://')[0].lower()
                if expected_type == 'postgres':
                    expected_type = 'postgresql'
                
                if db_type == expected_type:
                    self.add_test_result(f"{db_name}-类型检测", True, f"数据库类型: {db_type}")
                else:
                    self.add_test_result(f"{db_name}-类型检测", False, f"期望: {expected_type}, 实际: {db_type}")
                
                # 测试表操作
                await self.test_table_operations(db_manager, db_name)
                
                # 测试CRUD操作
                await self.test_crud_operations(db_manager, db_name)
                
                # 关闭连接
                await close_database()
                self.add_test_result(f"{db_name}-关闭连接", True, "数据库连接关闭成功")
                
            else:
                self.add_test_result(f"{db_name}-连接", False, "数据库连接失败")
                
        except Exception as e:
            self.add_test_result(f"{db_name}-连接", False, f"异常: {str(e)}")
    
    async def test_table_operations(self, db_manager, db_name: str):
        """测试表操作"""
        try:
            # 测试检查表是否存在
            users_exists = await db_manager.table_exists('users')
            if users_exists:
                self.add_test_result(f"{db_name}-表检查", True, "users表存在")
            else:
                self.add_test_result(f"{db_name}-表检查", False, "users表不存在")
            
            sessions_exists = await db_manager.table_exists('user_sessions')
            if sessions_exists:
                self.add_test_result(f"{db_name}-会话表", True, "user_sessions表存在")
            else:
                self.add_test_result(f"{db_name}-会话表", False, "user_sessions表不存在")
                
        except Exception as e:
            self.add_test_result(f"{db_name}-表操作", False, f"异常: {str(e)}")
    
    async def test_crud_operations(self, db_manager, db_name: str):
        """测试CRUD操作"""
        try:
            # 清理测试数据
            await db_manager.execute_update("DELETE FROM users WHERE username = ?", ('testuser',))
            
            # 测试插入
            insert_query = """
                INSERT INTO users (id, username, email, password_hash, full_name, role) 
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = ('test-id-123', 'testuser', 'test@example.com', 'hashed_password', '测试用户', 'user')
            
            rows_affected = await db_manager.execute_update(insert_query, params)
            if rows_affected > 0:
                self.add_test_result(f"{db_name}-插入", True, f"插入了 {rows_affected} 行")
            else:
                self.add_test_result(f"{db_name}-插入", False, "插入失败")
            
            # 测试查询
            select_query = "SELECT * FROM users WHERE username = ?"
            results = await db_manager.execute_query(select_query, ('testuser',))
            
            if results and len(results) > 0:
                user = results[0]
                if user['username'] == 'testuser' and user['email'] == 'test@example.com':
                    self.add_test_result(f"{db_name}-查询", True, f"查询到用户: {user['username']}")
                else:
                    self.add_test_result(f"{db_name}-查询", False, "查询结果不正确")
            else:
                self.add_test_result(f"{db_name}-查询", False, "查询无结果")
            
            # 测试更新
            update_query = "UPDATE users SET full_name = ? WHERE username = ?"
            rows_affected = await db_manager.execute_update(update_query, ('更新的用户', 'testuser'))
            
            if rows_affected > 0:
                self.add_test_result(f"{db_name}-更新", True, f"更新了 {rows_affected} 行")
            else:
                self.add_test_result(f"{db_name}-更新", False, "更新失败")
            
            # 验证更新
            results = await db_manager.execute_query(select_query, ('testuser',))
            if results and results[0]['full_name'] == '更新的用户':
                self.add_test_result(f"{db_name}-更新验证", True, "更新验证成功")
            else:
                self.add_test_result(f"{db_name}-更新验证", False, "更新验证失败")
            
            # 测试删除
            delete_query = "DELETE FROM users WHERE username = ?"
            rows_affected = await db_manager.execute_update(delete_query, ('testuser',))
            
            if rows_affected > 0:
                self.add_test_result(f"{db_name}-删除", True, f"删除了 {rows_affected} 行")
            else:
                self.add_test_result(f"{db_name}-删除", False, "删除失败")
                
        except Exception as e:
            self.add_test_result(f"{db_name}-CRUD", False, f"异常: {str(e)}")
    
    async def test_transaction_support(self, db_config: Dict[str, Any]):
        """测试事务支持"""
        db_name = db_config['name']
        
        try:
            db_manager = await init_database(db_config['url'], db_config['config'])
            
            # 测试事务回滚
            async with db_manager.begin_transaction() as conn:
                try:
                    # 插入测试数据
                    await db_manager.execute_update(
                        "INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)",
                        ('tx-test-1', 'txuser1', 'tx1@test.com', 'hash1')
                    )
                    
                    # 故意触发错误（重复插入相同ID）
                    await db_manager.execute_update(
                        "INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)",
                        ('tx-test-1', 'txuser2', 'tx2@test.com', 'hash2')
                    )
                    
                except Exception:
                    # 事务应该自动回滚
                    pass
            
            # 检查数据是否被回滚
            results = await db_manager.execute_query(
                "SELECT * FROM users WHERE id = ?", ('tx-test-1',)
            )
            
            if not results:
                self.add_test_result(f"{db_name}-事务回滚", True, "事务回滚成功")
            else:
                self.add_test_result(f"{db_name}-事务回滚", False, "事务回滚失败")
            
            await close_database()
            
        except Exception as e:
            self.add_test_result(f"{db_name}-事务", False, f"异常: {str(e)}")
    
    async def test_batch_operations(self, db_config: Dict[str, Any]):
        """测试批量操作"""
        db_name = db_config['name']
        
        try:
            db_manager = await init_database(db_config['url'], db_config['config'])
            
            # 清理测试数据
            await db_manager.execute_update("DELETE FROM users WHERE username LIKE 'batch%'")
            
            # 准备批量数据
            batch_data = [
                ('batch-1', 'batch1', 'batch1@test.com', 'hash1'),
                ('batch-2', 'batch2', 'batch2@test.com', 'hash2'),
                ('batch-3', 'batch3', 'batch3@test.com', 'hash3')
            ]
            
            # 执行批量插入
            insert_query = "INSERT INTO users (id, username, email, password_hash) VALUES (?, ?, ?, ?)"
            rows_affected = await db_manager.execute_many(insert_query, batch_data)
            
            if rows_affected >= len(batch_data):
                self.add_test_result(f"{db_name}-批量插入", True, f"批量插入了 {rows_affected} 行")
            else:
                self.add_test_result(f"{db_name}-批量插入", False, f"期望插入 {len(batch_data)} 行，实际 {rows_affected} 行")
            
            # 验证批量插入结果
            results = await db_manager.execute_query("SELECT * FROM users WHERE username LIKE 'batch%'")
            
            if len(results) == len(batch_data):
                self.add_test_result(f"{db_name}-批量验证", True, f"批量插入验证成功，共 {len(results)} 条记录")
            else:
                self.add_test_result(f"{db_name}-批量验证", False, f"期望 {len(batch_data)} 条，实际 {len(results)} 条")
            
            # 清理测试数据
            await db_manager.execute_update("DELETE FROM users WHERE username LIKE 'batch%'")
            
            await close_database()
            
        except Exception as e:
            self.add_test_result(f"{db_name}-批量操作", False, f"异常: {str(e)}")
    
    async def test_database_extensibility(self):
        """测试数据库扩展性"""
        try:
            # 测试注册自定义适配器
            from rag_system.database.base import DatabaseAdapter
            
            class MockAdapter(DatabaseAdapter):
                def get_database_type(self):
                    return "mock"
                
                def format_placeholder(self, index):
                    return "?"
                
                async def initialize(self):
                    pass
                
                async def close(self):
                    pass
                
                async def get_connection(self):
                    pass
                
                async def execute_query(self, query, params=None):
                    return []
                
                async def execute_update(self, query, params=None):
                    return 0
                
                async def execute_many(self, query, params_list):
                    return 0
                
                async def begin_transaction(self):
                    pass
                
                async def create_tables(self, schema):
                    pass
                
                async def table_exists(self, table_name):
                    return True
                
                async def create_index(self, table_name, index_name, columns):
                    pass
            
            # 注册自定义适配器
            DatabaseFactory.register_adapter('mock', MockAdapter)
            
            # 测试是否支持新类型
            if DatabaseFactory.is_supported('mock'):
                self.add_test_result("扩展性-注册适配器", True, "成功注册自定义适配器")
            else:
                self.add_test_result("扩展性-注册适配器", False, "注册自定义适配器失败")
            
            # 测试创建自定义适配器
            mock_adapter = DatabaseFactory.create_adapter('mock://test')
            if mock_adapter.get_database_type() == 'mock':
                self.add_test_result("扩展性-创建适配器", True, "成功创建自定义适配器")
            else:
                self.add_test_result("扩展性-创建适配器", False, "创建自定义适配器失败")
                
        except Exception as e:
            self.add_test_result("数据库扩展性", False, f"异常: {str(e)}")
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("开始多数据库支持测试...")
        
        # 测试数据库工厂
        await self.test_database_factory()
        
        # 测试数据库扩展性
        await self.test_database_extensibility()
        
        # 测试各种数据库连接
        for db_config in self.test_databases:
            await self.test_database_connection(db_config)
            await self.test_transaction_support(db_config)
            await self.test_batch_operations(db_config)
        
        # 输出测试结果
        self.print_test_results()
    
    def print_test_results(self):
        """打印测试结果"""
        print("\n" + "="*80)
        print("多数据库支持测试结果")
        print("="*80)
        
        passed = 0
        failed = 0
        
        for result in self.test_results:
            status = "✅ 通过" if result['success'] else "❌ 失败"
            print(f"{status} {result['test']}: {result['message']}")
            
            if result['success']:
                passed += 1
            else:
                failed += 1
        
        print("\n" + "-"*80)
        print(f"测试总结: 通过 {passed} 项，失败 {failed} 项")
        
        if failed == 0:
            print("🎉 所有测试通过！多数据库支持功能正常。")
        else:
            print(f"⚠️  有 {failed} 项测试失败，请检查相关功能。")
        
        print("\n支持的数据库类型:")
        for db_type in get_supported_databases():
            print(f"  - {db_type}")
        
        print("="*80)

async def main():
    """主函数"""
    tester = MultiDatabaseTester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())