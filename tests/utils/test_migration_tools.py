"""
配置和数据迁移工具测试
"""
import pytest
import tempfile
import json
import yaml
import os
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime

from rag_system.utils.migration_tools import (
    MigrationStep, MigrationPlan, VectorCompatibilityReport,
    ConfigMigrationTool, VectorDataMigrationTool, MigrationManager,
    get_migration_manager, migrate_config_file, check_vector_compatibility
)
from rag_system.utils.model_exceptions import ModelConfigError


class TestMigrationStep:
    """迁移步骤测试"""
    
    def test_migration_step_creation(self):
        """测试迁移步骤创建"""
        step = MigrationStep(
            step_id="test_step",
            description="测试步骤",
            source_path="/source/config.yaml",
            target_path="/target/config.yaml"
        )
        
        assert step.step_id == "test_step"
        assert step.description == "测试步骤"
        assert step.source_path == "/source/config.yaml"
        assert step.target_path == "/target/config.yaml"
        assert step.completed is False
        assert step.error_message is None
        assert isinstance(step.timestamp, datetime)


class TestMigrationPlan:
    """迁移计划测试"""
    
    def test_migration_plan_creation(self):
        """测试迁移计划创建"""
        plan = MigrationPlan(
            plan_id="test_plan",
            description="测试迁移计划"
        )
        
        assert plan.plan_id == "test_plan"
        assert plan.description == "测试迁移计划"
        assert len(plan.steps) == 0
        assert isinstance(plan.created_at, datetime)
        assert plan.completed_at is None
        assert plan.status == "pending"


class TestVectorCompatibilityReport:
    """向量兼容性报告测试"""
    
    def test_vector_compatibility_report_creation(self):
        """测试向量兼容性报告创建"""
        report = VectorCompatibilityReport(
            source_dimension=1536,
            target_dimension=1024,
            compatible=False,
            conversion_needed=True
        )
        
        assert report.source_dimension == 1536
        assert report.target_dimension == 1024
        assert report.compatible is False
        assert report.conversion_needed is True
        assert report.estimated_time is None
        assert len(report.warnings) == 0
        assert len(report.errors) == 0


class TestConfigMigrationTool:
    """配置迁移工具测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.tool = ConfigMigrationTool(backup_dir=self.temp_dir)
    
    def test_create_migration_plan(self):
        """测试创建迁移计划"""
        source_path = "/source/config.yaml"
        target_path = "/target/config.yaml"
        
        plan = self.tool.create_migration_plan(source_path, target_path, "测试迁移")
        
        assert plan.description == "测试迁移"
        assert len(plan.steps) == 4
        assert plan.status == "pending"
        
        # 检查步骤类型
        step_types = [step.step_id.split('_')[-1] for step in plan.steps]
        assert "backup" in step_types
        assert "validate" in step_types
        assert "convert" in step_types
        assert "verify" in step_types
    
    def test_backup_step_execution(self):
        """测试备份步骤执行"""
        # 创建源配置文件
        source_config = {
            'llm': {
                'provider': 'openai',
                'model': 'gpt-4',
                'api_key': 'sk-test123'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(source_config, f)
            source_path = f.name
        
        try:
            backup_path = str(Path(self.temp_dir) / "backup.yaml")
            
            step = MigrationStep(
                step_id="test_backup",
                description="测试备份",
                source_path=source_path,
                backup_path=backup_path
            )
            
            self.tool._execute_backup_step(step)
            
            # 验证备份文件存在
            assert Path(backup_path).exists()
            
            # 验证备份内容正确
            with open(backup_path, 'r') as f:
                backup_config = yaml.safe_load(f)
            
            assert backup_config == source_config
            
        finally:
            Path(source_path).unlink()
    
    def test_validate_step_execution(self):
        """测试验证步骤执行"""
        # 创建有效的配置文件
        valid_config = {
            'llm': {
                'provider': 'openai',
                'model': 'gpt-4',
                'api_key': 'sk-test123'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(valid_config, f)
            source_path = f.name
        
        try:
            step = MigrationStep(
                step_id="test_validate",
                description="测试验证",
                source_path=source_path
            )
            
            # 应该不抛出异常
            self.tool._execute_validate_step(step)
            
        finally:
            Path(source_path).unlink()
    
    def test_validate_step_invalid_file(self):
        """测试验证无效文件"""
        # 创建无效的配置文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            invalid_path = f.name
        
        try:
            step = MigrationStep(
                step_id="test_validate",
                description="测试验证",
                source_path=invalid_path
            )
            
            with pytest.raises(ModelConfigError):
                self.tool._execute_validate_step(step)
                
        finally:
            Path(invalid_path).unlink()
    
    @patch('rag_system.utils.migration_tools.CompatibilityManager')
    def test_convert_step_execution(self, mock_compatibility_manager):
        """测试转换步骤执行"""
        # 模拟兼容性管理器
        mock_manager = Mock()
        mock_manager.convert_legacy_config_file.return_value = {
            'llm': {'provider': 'openai', 'model': 'gpt-4'}
        }
        mock_compatibility_manager.return_value = mock_manager
        
        # 创建源配置文件
        source_config = {
            'llm': {
                'llm_provider': 'openai',
                'llm_model': 'gpt-4'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(source_config, f)
            source_path = f.name
        
        target_path = str(Path(self.temp_dir) / "converted.yaml")
        
        try:
            step = MigrationStep(
                step_id="test_convert",
                description="测试转换",
                source_path=source_path,
                target_path=target_path
            )
            
            # 重新创建工具以使用模拟的兼容性管理器
            tool = ConfigMigrationTool(backup_dir=self.temp_dir)
            tool._execute_convert_step(step)
            
            # 验证转换方法被调用
            mock_manager.convert_legacy_config_file.assert_called_once_with(source_path)
            mock_manager.save_converted_config.assert_called_once()
            
        finally:
            Path(source_path).unlink()
    
    def test_verify_step_execution(self):
        """测试验证步骤执行"""
        # 创建有效的转换后配置文件
        converted_config = {
            'llm': {
                'provider': 'openai',
                'model': 'gpt-4',
                'api_key': 'sk-test123'
            },
            'embeddings': {
                'provider': 'openai',
                'model': 'text-embedding-ada-002',
                'api_key': 'sk-test123'
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(converted_config, f)
            target_path = f.name
        
        try:
            step = MigrationStep(
                step_id="test_verify",
                description="测试验证",
                target_path=target_path
            )
            
            # 应该不抛出异常
            self.tool._execute_verify_step(step)
            
        finally:
            Path(target_path).unlink()
    
    def test_rollback_migration(self):
        """测试迁移回滚"""
        # 创建迁移计划
        source_path = "/source/config.yaml"
        target_path = str(Path(self.temp_dir) / "target.yaml")
        backup_path = str(Path(self.temp_dir) / "backup.yaml")
        
        plan = MigrationPlan(
            plan_id="test_rollback",
            description="测试回滚"
        )
        
        # 添加备份和转换步骤
        backup_step = MigrationStep(
            step_id="test_rollback_backup",
            description="备份步骤",
            source_path=source_path,
            backup_path=backup_path
        )
        
        convert_step = MigrationStep(
            step_id="test_rollback_convert",
            description="转换步骤",
            source_path=source_path,
            target_path=target_path
        )
        
        plan.steps = [backup_step, convert_step]
        
        # 创建备份文件和目标文件
        backup_config = {'test': 'backup_content'}
        target_config = {'test': 'target_content'}
        
        with open(backup_path, 'w') as f:
            yaml.dump(backup_config, f)
        
        with open(target_path, 'w') as f:
            yaml.dump(target_config, f)
        
        # 执行回滚
        result = self.tool.rollback_migration(plan)
        
        assert result is True
        assert plan.status == "rolled_back"
        
        # 验证目标文件被恢复为备份内容
        with open(target_path, 'r') as f:
            restored_config = yaml.safe_load(f)
        
        assert restored_config == backup_config
    
    def test_migration_history(self):
        """测试迁移历史"""
        # 创建几个迁移计划
        plan1 = self.tool.create_migration_plan("/source1.yaml", "/target1.yaml")
        plan2 = self.tool.create_migration_plan("/source2.yaml", "/target2.yaml")
        
        history = self.tool.get_migration_history()
        
        assert len(history) == 2
        assert plan1 in history
        assert plan2 in history
    
    def test_save_migration_history(self):
        """测试保存迁移历史"""
        # 创建迁移计划
        plan = self.tool.create_migration_plan("/source.yaml", "/target.yaml", "测试历史保存")
        plan.status = "completed"
        plan.completed_at = datetime.now()
        
        history_file = str(Path(self.temp_dir) / "history.json")
        
        self.tool.save_migration_history(history_file)
        
        # 验证历史文件存在
        assert Path(history_file).exists()
        
        # 验证历史内容
        with open(history_file, 'r', encoding='utf-8') as f:
            history_data = json.load(f)
        
        assert len(history_data) == 1
        assert history_data[0]['plan_id'] == plan.plan_id
        assert history_data[0]['description'] == "测试历史保存"
        assert history_data[0]['status'] == "completed"


class TestVectorDataMigrationTool:
    """向量数据迁移工具测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.tool = VectorDataMigrationTool()
    
    def test_check_vector_compatibility_same_dimension(self):
        """测试相同维度的向量兼容性检查"""
        report = self.tool.check_vector_compatibility(1536, 1536)
        
        assert report.source_dimension == 1536
        assert report.target_dimension == 1536
        assert report.compatible is True
        assert report.conversion_needed is False
        assert len(report.warnings) == 0
        assert len(report.errors) == 0
    
    def test_check_vector_compatibility_different_dimension(self):
        """测试不同维度的向量兼容性检查"""
        # 降维情况
        report1 = self.tool.check_vector_compatibility(1536, 1024)
        
        assert report1.source_dimension == 1536
        assert report1.target_dimension == 1024
        assert report1.compatible is False
        assert report1.conversion_needed is True
        assert len(report1.warnings) > 0
        assert "信息丢失" in report1.warnings[0]
        
        # 升维情况
        report2 = self.tool.check_vector_compatibility(768, 1536)
        
        assert report2.source_dimension == 768
        assert report2.target_dimension == 1536
        assert report2.compatible is False
        assert report2.conversion_needed is True
        assert len(report2.warnings) > 0
        assert "填充零值" in report2.warnings[0]
    
    def test_convert_vector_dimensions_same_dimension(self):
        """测试相同维度的向量转换"""
        vectors = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        
        converted = self.tool.convert_vector_dimensions(vectors, 3)
        
        assert converted == vectors  # 应该不变
    
    def test_convert_vector_dimensions_downsize(self):
        """测试降维向量转换"""
        vectors = [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]]
        
        converted = self.tool.convert_vector_dimensions(vectors, 2)
        
        expected = [[1.0, 2.0], [5.0, 6.0]]
        assert converted == expected
    
    def test_convert_vector_dimensions_upsize(self):
        """测试升维向量转换"""
        vectors = [[1.0, 2.0], [3.0, 4.0]]
        
        converted = self.tool.convert_vector_dimensions(vectors, 4)
        
        expected = [[1.0, 2.0, 0.0, 0.0], [3.0, 4.0, 0.0, 0.0]]
        assert converted == expected
    
    def test_convert_vector_dimensions_inconsistent(self):
        """测试不一致维度的向量转换"""
        vectors = [[1.0, 2.0, 3.0], [4.0, 5.0]]  # 维度不一致
        
        with pytest.raises(ModelConfigError):
            self.tool.convert_vector_dimensions(vectors, 2)
    
    def test_validate_vector_data_valid(self):
        """测试有效向量数据验证"""
        vectors = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        
        is_valid, errors = self.tool.validate_vector_data(vectors, 3)
        
        assert is_valid is True
        assert len(errors) == 0
    
    def test_validate_vector_data_empty(self):
        """测试空向量数据验证"""
        vectors = []
        
        is_valid, errors = self.tool.validate_vector_data(vectors, 3)
        
        assert is_valid is False
        assert len(errors) == 1
        assert "向量数据为空" in errors[0]
    
    def test_validate_vector_data_wrong_dimension(self):
        """测试错误维度的向量数据验证"""
        vectors = [[1.0, 2.0], [3.0, 4.0]]  # 都是2维，但期望3维
        
        is_valid, errors = self.tool.validate_vector_data(vectors, 3)
        
        assert is_valid is False
        assert len(errors) == 2
        assert "维度错误" in errors[0]
        assert "维度错误" in errors[1]
    
    def test_validate_vector_data_invalid_type(self):
        """测试无效类型的向量数据验证"""
        vectors = [["not", "numbers"], [1.0, 2.0]]
        
        is_valid, errors = self.tool.validate_vector_data(vectors, 2)
        
        assert is_valid is False
        assert len(errors) == 2
        assert "不是数值类型" in errors[0]
        assert "不是数值类型" in errors[1]
    
    def test_validate_vector_data_extreme_values(self):
        """测试极值的向量数据验证"""
        vectors = [[1e20, -1e20], [1.0, 2.0]]  # 极大值
        
        is_valid, errors = self.tool.validate_vector_data(vectors, 2)
        
        assert is_valid is False
        assert len(errors) == 2
        assert "数值异常" in errors[0]
        assert "数值异常" in errors[1]
    
    def test_get_compatibility_reports(self):
        """测试获取兼容性报告"""
        # 执行几次兼容性检查
        self.tool.check_vector_compatibility(1536, 1024)
        self.tool.check_vector_compatibility(768, 1536)
        
        reports = self.tool.get_compatibility_reports()
        
        assert len(reports) == 2
        assert reports[0].source_dimension == 1536
        assert reports[1].source_dimension == 768


class TestMigrationManager:
    """迁移管理器测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = MigrationManager(backup_dir=self.temp_dir)
    
    @patch('rag_system.utils.migration_tools.ConfigMigrationTool.execute_migration_plan')
    def test_migrate_system_config_only(self, mock_execute):
        """测试仅配置的系统迁移"""
        mock_execute.return_value = True
        
        result = self.manager.migrate_system("/source.yaml", "/target.yaml")
        
        assert result is True
        mock_execute.assert_called_once()
    
    @patch('rag_system.utils.migration_tools.ConfigMigrationTool.execute_migration_plan')
    def test_migrate_system_with_rollback(self, mock_execute):
        """测试带回滚的系统迁移"""
        mock_execute.return_value = False
        
        result = self.manager.migrate_system("/source.yaml", "/target.yaml")
        
        assert result is False
        mock_execute.assert_called_once()
    
    def test_create_migration_report(self):
        """测试创建迁移报告"""
        # 创建一些迁移历史
        plan = self.manager.config_tool.create_migration_plan("/source.yaml", "/target.yaml")
        plan.status = "completed"
        
        # 创建一些向量兼容性报告
        self.manager.vector_tool.check_vector_compatibility(1536, 1024)
        
        report = self.manager.create_migration_report()
        
        assert "timestamp" in report
        assert "config_migrations" in report
        assert "vector_compatibility" in report
        
        config_migrations = report["config_migrations"]
        assert config_migrations["total_count"] == 1
        assert config_migrations["successful_count"] == 1
        
        vector_compatibility = report["vector_compatibility"]
        assert vector_compatibility["total_checks"] == 1
        assert vector_compatibility["conversion_needed_count"] == 1
    
    def test_save_migration_report(self):
        """测试保存迁移报告"""
        report_file = str(Path(self.temp_dir) / "migration_report.json")
        
        self.manager.save_migration_report(report_file)
        
        # 验证报告文件存在
        assert Path(report_file).exists()
        
        # 验证报告内容
        with open(report_file, 'r', encoding='utf-8') as f:
            report_data = json.load(f)
        
        assert "timestamp" in report_data
        assert "config_migrations" in report_data
        assert "vector_compatibility" in report_data
    
    def test_cleanup_backups(self):
        """测试清理备份文件"""
        # 创建一些备份文件
        old_backup = Path(self.temp_dir) / "old_backup.yaml"
        new_backup = Path(self.temp_dir) / "new_backup.yaml"
        
        old_backup.touch()
        new_backup.touch()
        
        # 修改旧备份文件的时间戳
        import time
        old_time = time.time() - (40 * 24 * 3600)  # 40天前
        os.utime(old_backup, (old_time, old_time))
        
        self.manager.cleanup_backups(days_to_keep=30)
        
        # 验证旧备份被删除，新备份保留
        assert not old_backup.exists()
        assert new_backup.exists()


class TestGlobalFunctions:
    """全局函数测试"""
    
    def test_get_migration_manager(self):
        """测试获取全局迁移管理器"""
        manager1 = get_migration_manager()
        manager2 = get_migration_manager()
        
        # 应该是同一个实例
        assert manager1 is manager2
        assert isinstance(manager1, MigrationManager)
    
    @patch('rag_system.utils.migration_tools.get_migration_manager')
    def test_migrate_config_file(self, mock_get_manager):
        """测试迁移配置文件便捷函数"""
        mock_manager = Mock()
        mock_tool = Mock()
        mock_plan = Mock()
        
        mock_manager.config_tool = mock_tool
        mock_tool.create_migration_plan.return_value = mock_plan
        mock_tool.execute_migration_plan.return_value = True
        mock_get_manager.return_value = mock_manager
        
        result = migrate_config_file("/source.yaml", "/target.yaml")
        
        assert result is True
        mock_tool.create_migration_plan.assert_called_once_with("/source.yaml", "/target.yaml")
        mock_tool.execute_migration_plan.assert_called_once_with(mock_plan)
    
    @patch('rag_system.utils.migration_tools.get_migration_manager')
    def test_check_vector_compatibility(self, mock_get_manager):
        """测试检查向量兼容性便捷函数"""
        mock_manager = Mock()
        mock_tool = Mock()
        mock_report = VectorCompatibilityReport(1536, 1024, False, True)
        
        mock_manager.vector_tool = mock_tool
        mock_tool.check_vector_compatibility.return_value = mock_report
        mock_get_manager.return_value = mock_manager
        
        result = check_vector_compatibility(1536, 1024)
        
        assert result is mock_report
        mock_tool.check_vector_compatibility.assert_called_once_with(1536, 1024)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])