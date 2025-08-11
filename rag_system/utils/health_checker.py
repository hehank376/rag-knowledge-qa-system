"""
健康检查器
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..models.health import HealthStatus, ComponentHealth
from ..utils.exceptions import HealthCheckError
from ..llm.factory import LLMFactory
from ..embeddings.factory import EmbeddingFactory
from ..llm.base import BaseLLM, LLMConfig
from ..embeddings.base import BaseEmbedding, EmbeddingConfig

logger = logging.getLogger(__name__)


@dataclass
class ModelHealthStatus:
    """模型健康状态"""
    provider: str
    model_name: str
    model_type: str  # 'llm' or 'embedding'
    is_healthy: bool
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    last_check: Optional[datetime] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    success_rate: float = 0.0
    
    def update_success(self, response_time: float):
        """更新成功状态"""
        self.is_healthy = True
        self.response_time = response_time
        self.error_message = None
        self.last_check = datetime.now()
        self.consecutive_failures = 0
        self.total_checks += 1
        self.success_rate = ((self.success_rate * (self.total_checks - 1)) + 1.0) / self.total_checks
    
    def update_failure(self, error_message: str):
        """更新失败状态"""
        self.is_healthy = False
        self.response_time = None
        self.error_message = error_message
        self.last_check = datetime.now()
        self.consecutive_failures += 1
        self.total_checks += 1
        self.success_rate = (self.success_rate * (self.total_checks - 1)) / self.total_checks


@dataclass
class ModelHealthCheckConfig:
    """模型健康检查配置"""
    check_interval: int = 300  # 检查间隔（秒）
    timeout: int = 30  # 超时时间（秒）
    max_consecutive_failures: int = 3  # 最大连续失败次数
    test_prompt: str = "Hello, this is a health check test."
    test_text: str = "This is a test document for embedding health check."
    enable_startup_check: bool = True
    enable_periodic_check: bool = True
    failure_threshold: float = 0.8  # 成功率阈值


class ModelHealthChecker:
    """模型健康检查器"""
    
    def __init__(self, config: Optional[ModelHealthCheckConfig] = None):
        self.config = config or ModelHealthCheckConfig()
        self.model_status: Dict[str, ModelHealthStatus] = {}
        self.last_check = None
        self._check_task = None
        self._running = False
    
    def _get_model_key(self, provider: str, model_name: str, model_type: str) -> str:
        """生成模型唯一标识"""
        return f"{provider}:{model_type}:{model_name}"

    async def check_llm_health(self, llm_config: LLMConfig) -> ModelHealthStatus:
        """检查LLM健康状态"""
        model_key = self._get_model_key(llm_config.provider, llm_config.model, 'llm')
        
        # 获取或创建模型状态
        if model_key not in self.model_status:
            self.model_status[model_key] = ModelHealthStatus(
                provider=llm_config.provider,
                model_name=llm_config.model,
                model_type='llm',
                is_healthy=False
            )
        
        status = self.model_status[model_key]
        start_time = datetime.now()
        
        try:
            # 创建LLM实例
            llm = LLMFactory.create_llm(llm_config)
            
            # 执行健康检查
            response = await llm.generate(self.config.test_prompt)
            
            # 验证响应
            if not response or len(response.strip()) == 0:
                raise Exception("LLM返回空响应")
            
            response_time = (datetime.now() - start_time).total_seconds()
            status.update_success(response_time)
            
            logger.info(f"LLM健康检查成功: {llm_config.provider}/{llm_config.model}")
            
        except Exception as e:
            error_msg = f"LLM健康检查失败: {str(e)}"
            status.update_failure(error_msg)
            logger.error(f"{llm_config.provider}/{llm_config.model}: {error_msg}")
        
        return status
    
    async def check_embedding_health(self, embedding_config: EmbeddingConfig) -> ModelHealthStatus:
        """检查嵌入模型健康状态"""
        model_key = self._get_model_key(
            embedding_config.provider, 
            embedding_config.model, 
            'embedding'
        )
        
        # 获取或创建模型状态
        if model_key not in self.model_status:
            self.model_status[model_key] = ModelHealthStatus(
                provider=embedding_config.provider,
                model_name=embedding_config.model,
                model_type='embedding',
                is_healthy=False
            )
        
        status = self.model_status[model_key]
        start_time = datetime.now()
        
        try:
            # 创建嵌入模型实例
            embedding = EmbeddingFactory.create_embedding(embedding_config)
            
            # 执行健康检查
            vectors = await embedding.embed_text(self.config.test_text)
            
            # 验证响应
            if not vectors or len(vectors) == 0:
                raise Exception("嵌入模型返回空向量")
            
            if not isinstance(vectors, list) or not all(isinstance(v, (int, float)) for v in vectors):
                raise Exception("嵌入模型返回无效向量格式")
            
            response_time = (datetime.now() - start_time).total_seconds()
            status.update_success(response_time)
            
            logger.info(f"嵌入模型健康检查成功: {embedding_config.provider}/{embedding_config.model}")
            
        except Exception as e:
            error_msg = f"嵌入模型健康检查失败: {str(e)}"
            status.update_failure(error_msg)
            logger.error(f"{embedding_config.provider}/{embedding_config.model}: {error_msg}")
        
        return status

    async def check_all_models(self, llm_configs: List[LLMConfig], 
                              embedding_configs: List[EmbeddingConfig]) -> Dict[str, ModelHealthStatus]:
        """检查所有模型"""
        results = {}
        
        # 检查所有LLM
        for llm_config in llm_configs:
            try:
                status = await asyncio.wait_for(
                    self.check_llm_health(llm_config),
                    timeout=self.config.timeout
                )
                model_key = self._get_model_key(llm_config.provider, llm_config.model, 'llm')
                results[model_key] = status
            except asyncio.TimeoutError:
                model_key = self._get_model_key(llm_config.provider, llm_config.model, 'llm')
                if model_key in self.model_status:
                    self.model_status[model_key].update_failure("健康检查超时")
                    results[model_key] = self.model_status[model_key]
            except Exception as e:
                logger.error(f"LLM健康检查异常: {llm_config.provider}/{llm_config.model}: {str(e)}")
        
        # 检查所有嵌入模型
        for embedding_config in embedding_configs:
            try:
                status = await asyncio.wait_for(
                    self.check_embedding_health(embedding_config),
                    timeout=self.config.timeout
                )
                model_key = self._get_model_key(
                    embedding_config.provider, 
                    embedding_config.model, 
                    'embedding'
                )
                results[model_key] = status
            except asyncio.TimeoutError:
                model_key = self._get_model_key(
                    embedding_config.provider, 
                    embedding_config.model, 
                    'embedding'
                )
                if model_key in self.model_status:
                    self.model_status[model_key].update_failure("健康检查超时")
                    results[model_key] = self.model_status[model_key]
            except Exception as e:
                logger.error(f"嵌入模型健康检查异常: {embedding_config.provider}/{embedding_config.model}: {str(e)}")
        
        self.last_check = datetime.now()
        return results
    
    async def start_periodic_check(self, llm_configs: List[LLMConfig], 
                                  embedding_configs: List[EmbeddingConfig]):
        """启动定期健康检查"""
        if not self.config.enable_periodic_check:
            logger.info("定期健康检查已禁用")
            return
        
        if self._running:
            logger.warning("定期健康检查已在运行")
            return
        
        self._running = True
        logger.info(f"启动定期健康检查，间隔: {self.config.check_interval}秒")
        
        async def check_loop():
            while self._running:
                try:
                    await self.check_all_models(llm_configs, embedding_configs)
                    await asyncio.sleep(self.config.check_interval)
                except Exception as e:
                    logger.error(f"定期健康检查异常: {str(e)}")
                    await asyncio.sleep(60)  # 出错时等待1分钟再重试
        
        self._check_task = asyncio.create_task(check_loop())
    
    async def stop_periodic_check(self):
        """停止定期健康检查"""
        if not self._running:
            return
        
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("定期健康检查已停止")

    def get_model_status(self, provider: str, model_name: str, model_type: str) -> Optional[ModelHealthStatus]:
        """获取特定模型的健康状态"""
        model_key = self._get_model_key(provider, model_name, model_type)
        return self.model_status.get(model_key)
    
    def get_provider_status(self, provider: str) -> Dict[str, ModelHealthStatus]:
        """获取特定提供商的所有模型状态"""
        return {
            key: status for key, status in self.model_status.items()
            if status.provider == provider
        }
    
    def get_unhealthy_models(self) -> Dict[str, ModelHealthStatus]:
        """获取所有不健康的模型"""
        return {
            key: status for key, status in self.model_status.items()
            if not status.is_healthy
        }
    
    def get_models_with_high_failure_rate(self) -> Dict[str, ModelHealthStatus]:
        """获取失败率高的模型"""
        return {
            key: status for key, status in self.model_status.items()
            if status.success_rate < self.config.failure_threshold and status.total_checks > 0
        }
    
    def get_overall_health_status(self) -> HealthStatus:
        """获取整体健康状态"""
        if not self.model_status:
            return HealthStatus.UNKNOWN
        
        healthy_count = sum(1 for status in self.model_status.values() if status.is_healthy)
        total_count = len(self.model_status)
        
        if healthy_count == total_count:
            return HealthStatus.HEALTHY
        elif healthy_count == 0:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.DEGRADED
    
    def generate_health_report(self) -> Dict[str, Any]:
        """生成健康检查报告"""
        report = {
            "overall_status": self.get_overall_health_status().value,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "total_models": len(self.model_status),
            "healthy_models": sum(1 for s in self.model_status.values() if s.is_healthy),
            "unhealthy_models": sum(1 for s in self.model_status.values() if not s.is_healthy),
            "models": {},
            "providers": {},
            "alerts": []
        }
        
        # 按提供商分组统计
        provider_stats = {}
        for status in self.model_status.values():
            if status.provider not in provider_stats:
                provider_stats[status.provider] = {
                    "total": 0,
                    "healthy": 0,
                    "unhealthy": 0,
                    "avg_response_time": 0,
                    "models": []
                }
            
            stats = provider_stats[status.provider]
            stats["total"] += 1
            if status.is_healthy:
                stats["healthy"] += 1
            else:
                stats["unhealthy"] += 1
            
            if status.response_time:
                current_avg = stats["avg_response_time"]
                stats["avg_response_time"] = (current_avg * (stats["total"] - 1) + status.response_time) / stats["total"]
            
            stats["models"].append({
                "name": status.model_name,
                "type": status.model_type,
                "healthy": status.is_healthy,
                "response_time": status.response_time,
                "success_rate": status.success_rate,
                "consecutive_failures": status.consecutive_failures,
                "last_check": status.last_check.isoformat() if status.last_check else None,
                "error": status.error_message
            })
        
        report["providers"] = provider_stats
        
        # 生成详细的模型状态
        for key, status in self.model_status.items():
            report["models"][key] = {
                "provider": status.provider,
                "model_name": status.model_name,
                "model_type": status.model_type,
                "is_healthy": status.is_healthy,
                "response_time": status.response_time,
                "success_rate": status.success_rate,
                "consecutive_failures": status.consecutive_failures,
                "total_checks": status.total_checks,
                "last_check": status.last_check.isoformat() if status.last_check else None,
                "error_message": status.error_message
            }
        
        # 生成告警
        for key, status in self.model_status.items():
            if not status.is_healthy:
                report["alerts"].append({
                    "level": "error",
                    "message": f"模型 {status.provider}/{status.model_name} ({status.model_type}) 不健康",
                    "details": status.error_message,
                    "consecutive_failures": status.consecutive_failures
                })
            elif status.consecutive_failures >= self.config.max_consecutive_failures // 2:
                report["alerts"].append({
                    "level": "warning",
                    "message": f"模型 {status.provider}/{status.model_name} ({status.model_type}) 连续失败次数较多",
                    "consecutive_failures": status.consecutive_failures
                })
            elif status.success_rate < self.config.failure_threshold and status.total_checks > 10:
                report["alerts"].append({
                    "level": "warning",
                    "message": f"模型 {status.provider}/{status.model_name} ({status.model_type}) 成功率较低",
                    "success_rate": status.success_rate
                })
        
        return report

    async def startup_health_check(self, llm_configs: List[LLMConfig], 
                                  embedding_configs: List[EmbeddingConfig]) -> bool:
        """启动时健康检查"""
        if not self.config.enable_startup_check:
            logger.info("启动时健康检查已禁用")
            return True
        
        logger.info("开始启动时健康检查...")
        
        try:
            results = await self.check_all_models(llm_configs, embedding_configs)
            
            healthy_count = sum(1 for status in results.values() if status.is_healthy)
            total_count = len(results)
            
            logger.info(f"启动时健康检查完成: {healthy_count}/{total_count} 个模型健康")
            
            # 记录不健康的模型
            unhealthy_models = [key for key, status in results.items() if not status.is_healthy]
            if unhealthy_models:
                logger.warning(f"以下模型不健康: {', '.join(unhealthy_models)}")
            
            # 如果有模型可用，认为启动成功
            return healthy_count > 0
            
        except Exception as e:
            logger.error(f"启动时健康检查失败: {str(e)}")
            return False
    
    def cleanup(self):
        """清理资源"""
        if self._check_task and not self._check_task.done():
            self._check_task.cancel()
        self._running = False
        logger.info("模型健康检查器已清理")


# 保持向后兼容的原始HealthChecker类
class HealthChecker:
    """原始健康检查器（向后兼容）"""
    
    def __init__(self):
        self.components = {}
        self.last_check = None
    
    def register_component(self, name: str, check_func):
        """注册组件检查函数"""
        self.components[name] = check_func
        logger.info(f"注册健康检查组件: {name}")
    
    async def check_component(self, name: str, check_func) -> ComponentHealth:
        """检查单个组件"""
        start_time = datetime.now()
        
        try:
            # 执行检查函数
            result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
            
            response_time = (datetime.now() - start_time).total_seconds()
            
            return ComponentHealth(
                name=name,
                status=HealthStatus.HEALTHY,
                response_time=response_time,
                details=result or {}
            )
            
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"组件 {name} 健康检查失败: {str(e)}")
            
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                error=str(e)
            )
    
    async def check_all_components(self) -> Dict[str, ComponentHealth]:
        """检查所有组件"""
        results = {}
        
        for name, check_func in self.components.items():
            results[name] = await self.check_component(name, check_func)
        
        self.last_check = datetime.now()
        return results
    
    def get_overall_status(self, results: Dict[str, ComponentHealth]) -> HealthStatus:
        """获取整体健康状态"""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in results.values()]
        
        if all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.DEGRADED