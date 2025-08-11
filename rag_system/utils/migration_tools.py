"""
配置和数据迁移工具
"""
import os
import shutil
import logging
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from .compatibility import CompatibilityManager
from .model_exceptions import ModelConfigError, ErrorCode

logger = logging.getLogger(__name__)


@dataclass
class MigrationStep:
    """迁移步骤"""
    step_id: str
    description: str
    source_path: Optional[str] = None
    target_path: Optional[str] = None
    backup_path: Optional[str] = None
    completed: bool = False
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MigrationPlan:
    """迁移计划"""
    plan_id: str
    description: str
    steps: List[MigrationStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed, rolled_back


@dataclass
class VectorCompatibilityReport:
    """向量兼容性报告"""
    source_dimension: int
    target_dimension: int
    compatible: bool
    conversion_needed: bool
    estimated_time: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ConfigMigrationTool:
    """配置迁移工具"""
    
    def __init__(self, backup_dir: str = "./migration_backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.compatibility_manager = CompatibilityManager()
        self.migration_history: List[MigrationPlan] = []
    
    def create_migration_plan(self, source_config_path: str, target_config_path: str, 
                            description: str = "") -> MigrationPlan:
        """创建迁移计划"""
        plan_id = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        plan = MigrationPlan(
            plan_id=plan_id,
            description=description or f"迁移配置从 {source_config_path} 到 {target_config_path}"
        )
        
        # 添加迁移步骤
        steps = [
            MigrationStep(
                step_id=f"{plan_id}_backup",
                description="备份原始配置文件",
                source_path=source_config_path,
                backup_path=str(self.backup_dir / f"{plan_id}_backup.yaml")
            ),
            MigrationStep(
                step_id=f"{plan_id}_validate",
                description="验证源配置文件",
                source_path=source_config_path
            ),
            MigrationStep(
                step_id=f"{plan_id}_convert",
                description="转换配置格式",
                source_path=source_config_path,
                target_path=target_config_path
            ),
            MigrationStep(
                step_id=f"{plan_id}_verify",
                description="验证转换后的配置",
                target_path=target_config_path
            )
        ]
        
        plan.steps = steps
        self.migration_history.append(plan)
        return plan
    
    def execute_migration_plan(self, plan: MigrationPlan) -> bool:
        """执行迁移计划"""
        logger.info(f"开始执行迁移计划: {plan.plan_id}")
        plan.status = "running"
        
        try:
            for step in plan.steps:
                logger.info(f"执行迁移步骤: {step.description}")
                
                if step.step_id.endswith("_backup"):
                    self._execute_backup_step(step)
                elif step.step_id.endswith("_validate"):
                    self._execute_validate_step(step)
                elif step.step_id.endswith("_convert"):
                    self._execute_convert_step(step)
                elif step.step_id.endswith("_verify"):
                    self._execute_verify_step(step)
                
                step.completed = True
                step.timestamp = datetime.now()
                logger.info(f"迁移步骤完成: {step.description}")
            
            plan.status = "completed"
            plan.completed_at = datetime.now()
            logger.info(f"迁移计划执行完成: {plan.plan_id}")
            return True
            
        except Exception as e:
            error_msg = f"迁移计划执行失败: {str(e)}"
            logger.error(error_msg)
            plan.status = "failed"
            
            # 记录失败的步骤
            for step in plan.steps:
                if not step.completed:
                    step.error_message = error_msg
                    break
            
            return False
    
    def _execute_backup_step(self, step: MigrationStep):
        """执行备份步骤"""
        if not step.source_path or not step.backup_path:
            raise ModelConfigError("备份步骤缺少源路径或备份路径", ErrorCode.CONFIG_INVALID)
        
        source_path = Path(step.source_path)
        backup_path = Path(step.backup_path)
        
        if not source_path.exists():
            raise ModelConfigError(f"源配置文件不存在: {source_path}", ErrorCode.CONFIG_NOT_FOUND)
        
        # 创建备份
        shutil.copy2(source_path, backup_path)
        logger.info(f"配置文件已备份到: {backup_path}")
    
    def _execute_validate_step(self, step: MigrationStep):
        """执行验证步骤"""
        if not step.source_path:
            raise ModelConfigError("验证步骤缺少源路径", ErrorCode.CONFIG_INVALID)
        
        source_path = Path(step.source_path)
        
        # 验证文件存在
        if not source_path.exists():
            raise ModelConfigError(f"源配置文件不存在: {source_path}", ErrorCode.CONFIG_NOT_FOUND)
        
        # 验证文件格式
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                if source_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.safe_load(f)
                elif source_path.suffix.lower() == '.json':
                    json.load(f)
                else:
                    raise ModelConfigError(f"不支持的配置文件格式: {source_path.suffix}", ErrorCode.CONFIG_INVALID)
        except Exception as e:
            raise ModelConfigError(f"配置文件格式无效: {str(e)}", ErrorCode.CONFIG_INVALID)
        
        logger.info(f"源配置文件验证通过: {source_path}")
    
    def _execute_convert_step(self, step: MigrationStep):
        """执行转换步骤"""
        if not step.source_path or not step.target_path:
            raise ModelConfigError("转换步骤缺少源路径或目标路径", ErrorCode.CONFIG_INVALID)
        
        source_path = Path(step.source_path)
        target_path = Path(step.target_path)
        
        # 转换配置
        converted_config = self.compatibility_manager.convert_legacy_config_file(str(source_path))
        
        # 保存转换后的配置
        self.compatibility_manager.save_converted_config(converted_config, str(target_path))
        
        logger.info(f"配置已转换并保存到: {target_path}")
    
    def _execute_verify_step(self, step: MigrationStep):
        """执行验证步骤"""
        if not step.target_path:
            raise ModelConfigError("验证步骤缺少目标路径", ErrorCode.CONFIG_INVALID)
        
        target_path = Path(step.target_path)
        
        # 验证转换后的配置文件
        if not target_path.exists():
            raise ModelConfigError(f"转换后的配置文件不存在: {target_path}", ErrorCode.CONFIG_NOT_FOUND)
        
        # 加载并验证配置
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 检查配置兼容性
            from .compatibility import check_config_compatibility
            issues = check_config_compatibility(config)
            
            if issues:
                raise ModelConfigError(f"转换后的配置存在问题: {'; '.join(issues)}", ErrorCode.CONFIG_INVALID)
            
        except Exception as e:
            raise ModelConfigError(f"转换后的配置验证失败: {str(e)}", ErrorCode.CONFIG_INVALID)
        
        logger.info(f"转换后的配置验证通过: {target_path}")
    
    def rollback_migration(self, plan: MigrationPlan) -> bool:
        """回滚迁移"""
        logger.info(f"开始回滚迁移计划: {plan.plan_id}")
        
        try:
            # 找到备份步骤
            backup_step = None
            convert_step = None
            
            for step in plan.steps:
                if step.step_id.endswith("_backup"):
                    backup_step = step
                elif step.step_id.endswith("_convert"):
                    convert_step = step
            
            if not backup_step or not backup_step.backup_path:
                raise ModelConfigError("找不到备份文件，无法回滚", ErrorCode.CONFIG_NOT_FOUND)
            
            if not convert_step or not convert_step.target_path:
                raise ModelConfigError("找不到目标文件路径，无法回滚", ErrorCode.CONFIG_INVALID)
            
            backup_path = Path(backup_step.backup_path)
            target_path = Path(convert_step.target_path)
            
            # 检查备份文件是否存在
            if not backup_path.exists():
                raise ModelConfigError(f"备份文件不存在: {backup_path}", ErrorCode.CONFIG_NOT_FOUND)
            
            # 恢复备份
            if target_path.exists():
                target_path.unlink()  # 删除转换后的文件
            
            shutil.copy2(backup_path, target_path)
            
            plan.status = "rolled_back"
            logger.info(f"迁移计划回滚完成: {plan.plan_id}")
            return True
            
        except Exception as e:
            error_msg = f"迁移回滚失败: {str(e)}"
            logger.error(error_msg)
            return False
    
    def get_migration_history(self) -> List[MigrationPlan]:
        """获取迁移历史"""
        return self.migration_history.copy()
    
    def save_migration_history(self, file_path: str):
        """保存迁移历史"""
        history_data = []
        for plan in self.migration_history:
            plan_data = {
                "plan_id": plan.plan_id,
                "description": plan.description,
                "status": plan.status,
                "created_at": plan.created_at.isoformat(),
                "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
                "steps": []
            }
            
            for step in plan.steps:
                step_data = {
                    "step_id": step.step_id,
                    "description": step.description,
                    "source_path": step.source_path,
                    "target_path": step.target_path,
                    "backup_path": step.backup_path,
                    "completed": step.completed,
                    "error_message": step.error_message,
                    "timestamp": step.timestamp.isoformat()
                }
                plan_data["steps"].append(step_data)
            
            history_data.append(plan_data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"迁移历史已保存到: {file_path}")


class VectorDataMigrationTool:
    """向量数据迁移工具"""
    
    def __init__(self):
        self.compatibility_reports: List[VectorCompatibilityReport] = []
    
    def check_vector_compatibility(self, source_dimension: int, target_dimension: int) -> VectorCompatibilityReport:
        """检查向量兼容性"""
        report = VectorCompatibilityReport(
            source_dimension=source_dimension,
            target_dimension=target_dimension,
            compatible=source_dimension == target_dimension,
            conversion_needed=source_dimension != target_dimension
        )
        
        if not report.compatible:
            if source_dimension > target_dimension:
                report.warnings.append(f"目标维度({target_dimension})小于源维度({source_dimension})，可能导致信息丢失")
                report.warnings.append("建议使用降维技术(如PCA)进行转换")
            else:
                report.warnings.append(f"目标维度({target_dimension})大于源维度({source_dimension})，需要填充零值")
                report.warnings.append("填充的零值可能影响向量相似度计算")
        
        # 估算转换时间（基于经验公式）
        if report.conversion_needed:
            # 假设每1000个向量需要1秒处理时间
            report.estimated_time = max(source_dimension, target_dimension) / 1000.0
        
        self.compatibility_reports.append(report)
        return report
    
    def convert_vector_dimensions(self, vectors: List[List[float]], 
                                target_dimension: int) -> List[List[float]]:
        """转换向量维度"""
        if not vectors:
            return vectors
        
        source_dimension = len(vectors[0])
        
        if source_dimension == target_dimension:
            return vectors  # 无需转换
        
        converted_vectors = []
        
        for vector in vectors:
            if len(vector) != source_dimension:
                raise ModelConfigError(
                    f"向量维度不一致: 期望{source_dimension}，实际{len(vector)}",
                    ErrorCode.DATA_INVALID
                )
            
            if source_dimension > target_dimension:
                # 降维：截取前target_dimension个元素
                converted_vector = vector[:target_dimension]
            else:
                # 升维：填充零值
                converted_vector = vector + [0.0] * (target_dimension - source_dimension)
            
            converted_vectors.append(converted_vector)
        
        logger.info(f"向量维度转换完成: {source_dimension} -> {target_dimension}, 共{len(vectors)}个向量")
        return converted_vectors
    
    def validate_vector_data(self, vectors: List[List[float]], 
                           expected_dimension: int) -> Tuple[bool, List[str]]:
        """验证向量数据"""
        errors = []
        
        if not vectors:
            errors.append("向量数据为空")
            return False, errors
        
        for i, vector in enumerate(vectors):
            if not isinstance(vector, list):
                errors.append(f"向量{i}不是列表类型")
                continue
            
            if len(vector) != expected_dimension:
                errors.append(f"向量{i}维度错误: 期望{expected_dimension}，实际{len(vector)}")
            
            for j, value in enumerate(vector):
                if not isinstance(value, (int, float)):
                    errors.append(f"向量{i}的第{j}个元素不是数值类型")
                elif not (-1e10 <= value <= 1e10):  # 检查数值范围
                    errors.append(f"向量{i}的第{j}个元素数值异常: {value}")
        
        return len(errors) == 0, errors
    
    def get_compatibility_reports(self) -> List[VectorCompatibilityReport]:
        """获取兼容性报告"""
        return self.compatibility_reports.copy()


class MigrationManager:
    """迁移管理器"""
    
    def __init__(self, backup_dir: str = "./migration_backups"):
        self.config_tool = ConfigMigrationTool(backup_dir)
        self.vector_tool = VectorDataMigrationTool()
        self.backup_dir = Path(backup_dir)
    
    def migrate_system(self, source_config: str, target_config: str, 
                      vector_data_path: Optional[str] = None) -> bool:
        """完整系统迁移"""
        logger.info("开始完整系统迁移")
        
        try:
            # 1. 配置迁移
            config_plan = self.config_tool.create_migration_plan(
                source_config, target_config, "完整系统配置迁移"
            )
            
            if not self.config_tool.execute_migration_plan(config_plan):
                logger.error("配置迁移失败")
                return False
            
            # 2. 向量数据迁移（如果提供）
            if vector_data_path:
                logger.info("开始向量数据迁移")
                # 这里可以添加向量数据迁移逻辑
                # 实际实现需要根据具体的向量存储格式来定制
                pass
            
            logger.info("完整系统迁移完成")
            return True
            
        except Exception as e:
            logger.error(f"系统迁移失败: {str(e)}")
            
            # 尝试回滚配置迁移
            if 'config_plan' in locals():
                logger.info("尝试回滚配置迁移")
                self.config_tool.rollback_migration(config_plan)
            
            return False
    
    def create_migration_report(self) -> Dict[str, Any]:
        """创建迁移报告"""
        config_history = self.config_tool.get_migration_history()
        vector_reports = self.vector_tool.get_compatibility_reports()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "config_migrations": {
                "total_count": len(config_history),
                "successful_count": len([p for p in config_history if p.status == "completed"]),
                "failed_count": len([p for p in config_history if p.status == "failed"]),
                "rolled_back_count": len([p for p in config_history if p.status == "rolled_back"]),
                "plans": [{
                    "plan_id": plan.plan_id,
                    "description": plan.description,
                    "status": plan.status,
                    "created_at": plan.created_at.isoformat(),
                    "completed_at": plan.completed_at.isoformat() if plan.completed_at else None
                } for plan in config_history]
            },
            "vector_compatibility": {
                "total_checks": len(vector_reports),
                "compatible_count": len([r for r in vector_reports if r.compatible]),
                "conversion_needed_count": len([r for r in vector_reports if r.conversion_needed]),
                "reports": [{
                    "source_dimension": report.source_dimension,
                    "target_dimension": report.target_dimension,
                    "compatible": report.compatible,
                    "conversion_needed": report.conversion_needed,
                    "estimated_time": report.estimated_time,
                    "warnings_count": len(report.warnings),
                    "errors_count": len(report.errors)
                } for report in vector_reports]
            }
        }
        
        return report
    
    def save_migration_report(self, file_path: str):
        """保存迁移报告"""
        report = self.create_migration_report()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"迁移报告已保存到: {file_path}")
    
    def cleanup_backups(self, days_to_keep: int = 30):
        """清理旧备份文件"""
        if not self.backup_dir.exists():
            return
        
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
        cleaned_count = 0
        
        for backup_file in self.backup_dir.glob("*.yaml"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                cleaned_count += 1
        
        logger.info(f"清理了{cleaned_count}个过期备份文件")


# 全局迁移管理器实例
_global_migration_manager: Optional[MigrationManager] = None


def get_migration_manager() -> MigrationManager:
    """获取全局迁移管理器"""
    global _global_migration_manager
    if _global_migration_manager is None:
        _global_migration_manager = MigrationManager()
    return _global_migration_manager


def migrate_config_file(source_path: str, target_path: str) -> bool:
    """迁移配置文件（便捷函数）"""
    manager = get_migration_manager()
    plan = manager.config_tool.create_migration_plan(source_path, target_path)
    return manager.config_tool.execute_migration_plan(plan)


def check_vector_compatibility(source_dim: int, target_dim: int) -> VectorCompatibilityReport:
    """检查向量兼容性（便捷函数）"""
    manager = get_migration_manager()
    return manager.vector_tool.check_vector_compatibility(source_dim, target_dim)