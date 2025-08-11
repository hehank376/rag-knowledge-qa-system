"""
健康监控服务
"""
import logging
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from ..utils.health_checker import ModelHealthChecker, ModelHealthCheckConfig, ModelHealthStatus
from ..llm.base import LLMConfig
from ..embeddings.base import EmbeddingConfig
from ..models.health import HealthStatus
from ..utils.exceptions import HealthCheckError

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """告警信息"""
    id: str
    level: AlertLevel
    title: str
    message: str
    component: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class HealthMonitoringService:
    """健康监控服务"""
    
    def __init__(
        self, 
        health_checker: ModelHealthChecker,
        llm_configs: List[LLMConfig],
        embedding_configs: List[EmbeddingConfig],
        alert_handlers: Optional[List[Callable[[Alert], None]]] = None
    ):
        self.health_checker = health_checker
        self.llm_configs = llm_configs
        self.embedding_configs = embedding_configs
        self.alert_handlers = alert_handlers or []
        
        # 告警管理
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.max_history_size = 1000
        
        # 监控状态
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        # 监控配置
        self.monitoring_interval = 60  # 监控间隔（秒）
        self.alert_cooldown = 300  # 告警冷却时间（秒）
        self.last_alert_time: Dict[str, datetime] = {}
    
    async def start_monitoring(self):
        """启动健康监控"""
        if self._running:
            logger.warning("健康监控已在运行")
            return
        
        self._running = True
        logger.info("启动健康监控服务")
        
        # 启动健康检查器的定期检查
        await self.health_checker.start_periodic_check(
            self.llm_configs, 
            self.embedding_configs
        )
        
        # 启动监控任务
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def stop_monitoring(self):
        """停止健康监控"""
        if not self._running:
            return
        
        self._running = False
        logger.info("停止健康监控服务")
        
        # 停止健康检查器
        await self.health_checker.stop_periodic_check()
        
        # 停止监控任务
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
    
    async def _monitoring_loop(self):
        """监控循环"""
        while self._running:
            try:
                await self._check_and_alert()
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"监控循环异常: {str(e)}")
                await asyncio.sleep(60)  # 出错时等待1分钟
    
    async def _check_and_alert(self):
        """检查健康状态并生成告警"""
        try:
            # 获取当前健康状态
            report = self.health_checker.generate_health_report()
            
            # 检查整体状态
            await self._check_overall_health(report)
            
            # 检查各个模型状态
            await self._check_model_health(report)
            
            # 检查提供商状态
            await self._check_provider_health(report)
            
            # 清理已解决的告警
            self._cleanup_resolved_alerts()
            
        except Exception as e:
            logger.error(f"健康检查和告警生成失败: {str(e)}")
    
    async def _check_overall_health(self, report: Dict[str, Any]):
        """检查整体健康状态"""
        overall_status = report["overall_status"]
        alert_id = "system_overall_health"
        
        if overall_status == "unhealthy":
            await self._create_alert(
                alert_id=alert_id,
                level=AlertLevel.CRITICAL,
                title="系统整体健康状态异常",
                message=f"系统中有 {report['unhealthy_models']} 个模型不健康",
                component="system",
                metadata={"unhealthy_count": report["unhealthy_models"]}
            )
        elif overall_status == "degraded":
            await self._create_alert(
                alert_id=alert_id,
                level=AlertLevel.WARNING,
                title="系统健康状态降级",
                message=f"系统中有 {report['unhealthy_models']} 个模型不健康",
                component="system",
                metadata={"unhealthy_count": report["unhealthy_models"]}
            )
        else:
            # 系统健康，解决相关告警
            await self._resolve_alert(alert_id)
    
    async def _check_model_health(self, report: Dict[str, Any]):
        """检查各个模型健康状态"""
        for model_key, model_info in report["models"].items():
            alert_id = f"model_{model_key}"
            
            if not model_info["is_healthy"]:
                level = AlertLevel.ERROR
                if model_info["consecutive_failures"] >= 5:
                    level = AlertLevel.CRITICAL
                
                await self._create_alert(
                    alert_id=alert_id,
                    level=level,
                    title=f"模型 {model_info['model_name']} 不健康",
                    message=f"模型 {model_info['provider']}/{model_info['model_name']} ({model_info['model_type']}) 连续失败 {model_info['consecutive_failures']} 次",
                    component=f"{model_info['provider']}/{model_info['model_name']}",
                    metadata={
                        "provider": model_info["provider"],
                        "model_name": model_info["model_name"],
                        "model_type": model_info["model_type"],
                        "consecutive_failures": model_info["consecutive_failures"],
                        "success_rate": model_info["success_rate"],
                        "error_message": model_info["error_message"]
                    }
                )
            elif model_info["success_rate"] < 0.8 and model_info["total_checks"] > 10:
                # 成功率低告警
                await self._create_alert(
                    alert_id=f"{alert_id}_low_success_rate",
                    level=AlertLevel.WARNING,
                    title=f"模型 {model_info['model_name']} 成功率较低",
                    message=f"模型 {model_info['provider']}/{model_info['model_name']} 成功率为 {model_info['success_rate']:.2%}",
                    component=f"{model_info['provider']}/{model_info['model_name']}",
                    metadata={
                        "provider": model_info["provider"],
                        "model_name": model_info["model_name"],
                        "success_rate": model_info["success_rate"],
                        "total_checks": model_info["total_checks"]
                    }
                )
            else:
                # 模型健康，解决相关告警
                await self._resolve_alert(alert_id)
                await self._resolve_alert(f"{alert_id}_low_success_rate")
    
    async def _check_provider_health(self, report: Dict[str, Any]):
        """检查提供商健康状态"""
        for provider, provider_info in report["providers"].items():
            alert_id = f"provider_{provider}"
            
            if provider_info["unhealthy"] > 0:
                unhealthy_ratio = provider_info["unhealthy"] / provider_info["total"]
                
                if unhealthy_ratio >= 0.5:  # 50%以上模型不健康
                    await self._create_alert(
                        alert_id=alert_id,
                        level=AlertLevel.ERROR,
                        title=f"提供商 {provider} 大量模型不健康",
                        message=f"提供商 {provider} 有 {provider_info['unhealthy']}/{provider_info['total']} 个模型不健康",
                        component=f"provider_{provider}",
                        metadata={
                            "provider": provider,
                            "total_models": provider_info["total"],
                            "unhealthy_models": provider_info["unhealthy"],
                            "unhealthy_ratio": unhealthy_ratio
                        }
                    )
                elif unhealthy_ratio > 0:
                    await self._create_alert(
                        alert_id=alert_id,
                        level=AlertLevel.WARNING,
                        title=f"提供商 {provider} 部分模型不健康",
                        message=f"提供商 {provider} 有 {provider_info['unhealthy']}/{provider_info['total']} 个模型不健康",
                        component=f"provider_{provider}",
                        metadata={
                            "provider": provider,
                            "total_models": provider_info["total"],
                            "unhealthy_models": provider_info["unhealthy"],
                            "unhealthy_ratio": unhealthy_ratio
                        }
                    )
            else:
                # 提供商健康，解决相关告警
                await self._resolve_alert(alert_id)
    
    async def _create_alert(
        self, 
        alert_id: str, 
        level: AlertLevel, 
        title: str, 
        message: str, 
        component: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """创建告警"""
        # 检查冷却时间
        if alert_id in self.last_alert_time:
            time_since_last = datetime.now() - self.last_alert_time[alert_id]
            if time_since_last.total_seconds() < self.alert_cooldown:
                return  # 在冷却时间内，不重复告警
        
        # 检查是否已存在相同告警
        if alert_id in self.active_alerts and not self.active_alerts[alert_id].resolved:
            return  # 告警已存在且未解决
        
        # 创建新告警
        alert = Alert(
            id=alert_id,
            level=level,
            title=title,
            message=message,
            component=component,
            timestamp=datetime.now(),
            metadata=metadata
        )
        
        # 添加到活跃告警
        self.active_alerts[alert_id] = alert
        self.last_alert_time[alert_id] = alert.timestamp
        
        # 记录日志
        log_level = logging.ERROR if level in [AlertLevel.ERROR, AlertLevel.CRITICAL] else logging.WARNING
        logger.log(log_level, f"[{level.value.upper()}] {title}: {message}")
        
        # 调用告警处理器
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"告警处理器执行失败: {str(e)}")
    
    async def _resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self.active_alerts and not self.active_alerts[alert_id].resolved:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            
            logger.info(f"告警已解决: {alert.title}")
    
    def _cleanup_resolved_alerts(self):
        """清理已解决的告警"""
        # 将已解决的告警移到历史记录
        resolved_alerts = [
            alert for alert in self.active_alerts.values() 
            if alert.resolved and alert.resolved_at and 
            (datetime.now() - alert.resolved_at).total_seconds() > 3600  # 1小时后清理
        ]
        
        for alert in resolved_alerts:
            self.alert_history.append(alert)
            del self.active_alerts[alert.id]
        
        # 限制历史记录大小
        if len(self.alert_history) > self.max_history_size:
            self.alert_history = self.alert_history[-self.max_history_size:]
    
    def get_active_alerts(self) -> List[Alert]:
        """获取活跃告警"""
        return [alert for alert in self.active_alerts.values() if not alert.resolved]
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """获取告警历史"""
        return self.alert_history[-limit:]
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """添加告警处理器"""
        self.alert_handlers.append(handler)
    
    def remove_alert_handler(self, handler: Callable[[Alert], None]):
        """移除告警处理器"""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)


# 默认告警处理器
def console_alert_handler(alert: Alert):
    """控制台告警处理器"""
    print(f"[{alert.timestamp}] [{alert.level.value.upper()}] {alert.title}: {alert.message}")


def file_alert_handler(alert: Alert, log_file: str = "alerts.log"):
    """文件告警处理器"""
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{alert.timestamp}] [{alert.level.value.upper()}] {alert.component}: {alert.title} - {alert.message}\n")
    except Exception as e:
        logger.error(f"写入告警日志失败: {str(e)}")


def email_alert_handler(alert: Alert, email_config: Dict[str, Any]):
    """邮件告警处理器（示例）"""
    # 这里可以集成邮件发送功能
    logger.info(f"邮件告警: {alert.title} - {alert.message}")


def webhook_alert_handler(alert: Alert, webhook_url: str):
    """Webhook告警处理器（示例）"""
    # 这里可以集成Webhook通知
    logger.info(f"Webhook告警: {alert.title} - {alert.message}")