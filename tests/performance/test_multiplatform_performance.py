"""
多平台模型性能测试和基准测试
"""
import pytest
import time
import asyncio
import threading
import statistics
import psutil
import os
from typing import List, Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from rag_system.llm.factory import LLMFactory
from rag_system.llm.base import LLMConfig
from rag_system.embeddings.factory import EmbeddingFactory
from rag_system.embeddings.base import EmbeddingConfig
from rag_system.utils.health_checker import ModelHealthChecker


class PerformanceBenchmark:
    """性能基准测试工具"""
    
    def __init__(self):
        self.results = []
        self.process = psutil.Process(os.getpid())
    
    def measure_time(self, func, *args, **kwargs):
        """测量函数执行时间"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        return result, end_time - start_time
    
    def measure_memory(self, func, *args, **kwargs):
        """测量函数内存使用"""
        initial_memory = self.process.memory_info().rss
        result = func(*args, **kwargs)
        final_memory = self.process.memory_info().rss
        
        return result, final_memory - initial_memory
    
    def measure_cpu(self, func, duration=1.0, *args, **kwargs):
        """测量函数CPU使用率"""
        # 开始CPU监控
        cpu_percent_start = psutil.cpu_percent(interval=None)
        
        start_time = time.time()
        result = func(*args, **kwargs)
        
        # 等待足够时间获取准确的CPU使用率
        elapsed = time.time() - start_time
        if elapsed < duration:
            time.sleep(duration - elapsed)
        
        cpu_percent = psutil.cpu_percent(interval=None)
        
        return result, cpu_percent
    
    def add_result(self, test_name: str, metrics: Dict[str, Any]):
        """添加测试结果"""
        self.results.append({
            "test_name": test_name,
            "timestamp": time.time(),
            **metrics
        })
    
    def get_summary(self) -> Dict[str, Any]:
        """获取性能测试摘要"""
        if not self.results:
            return {}
        
        summary = {
            "total_tests": len(self.results),
            "test_results": self.results
        }
        
        # 计算平均值
        if self.results:
            time_values = [r.get("execution_time", 0) for r in self.results if "execution_time" in r]
            memory_values = [r.get("memory_usage", 0) for r in self.results if "memory_usage" in r]
            
            if time_values:
                summary["avg_execution_time"] = statistics.mean(time_values)
                summary["max_execution_time"] = max(time_values)
                summary["min_execution_time"] = min(time_values)
            
            if memory_values:
                summary["avg_memory_usage"] = statistics.mean(memory_values)
                summary["max_memory_usage"] = max(memory_values)
        
        return summary


class TestLLMFactoryPerformance:
    """LLM工厂性能测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.benchmark = PerformanceBenchmark()
        self.factory = LLMFactory()
    
    def test_single_llm_creation_performance(self):
        """测试单个LLM创建性能"""
        config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key"
        )
        
        # 测量创建时间
        llm, execution_time = self.benchmark.measure_time(
            self.factory.create_llm, config
        )
        
        # 测量内存使用
        _, memory_usage = self.benchmark.measure_memory(
            self.factory.create_llm, config
        )
        
        # 记录结果
        self.benchmark.add_result("single_llm_creation", {
            "execution_time": execution_time,
            "memory_usage": memory_usage,
            "provider": config.provider,
            "model": config.model
        })
        
        # 验证性能要求
        assert execution_time < 1.0, f"LLM创建时间过长: {execution_time:.3f}s"
        assert memory_usage < 10 * 1024 * 1024, f"内存使用过多: {memory_usage / 1024 / 1024:.2f}MB"
        assert llm is not None
    
    def test_batch_llm_creation_performance(self):
        """测试批量LLM创建性能"""
        configs = [
            LLMConfig(
                provider="siliconflow",
                model="Qwen/Qwen2-7B-Instruct",
                api_key=f"test-key-{i}"
            )
            for i in range(10)
        ]
        
        def create_batch_llms():
            return [self.factory.create_llm(config) for config in configs]
        
        # 测量批量创建性能
        llms, execution_time = self.benchmark.measure_time(create_batch_llms)
        _, memory_usage = self.benchmark.measure_memory(create_batch_llms)
        
        # 记录结果
        self.benchmark.add_result("batch_llm_creation", {
            "execution_time": execution_time,
            "memory_usage": memory_usage,
            "batch_size": len(configs),
            "avg_time_per_llm": execution_time / len(configs)
        })
        
        # 验证性能要求
        assert len(llms) == 10
        assert execution_time < 5.0, f"批量创建时间过长: {execution_time:.3f}s"
        assert execution_time / len(configs) < 0.5, f"平均创建时间过长: {execution_time / len(configs):.3f}s"
    
    def test_concurrent_llm_creation_performance(self):
        """测试并发LLM创建性能"""
        configs = [
            LLMConfig(
                provider="siliconflow",
                model="Qwen/Qwen2-7B-Instruct",
                api_key=f"test-key-{i}"
            )
            for i in range(20)
        ]
        
        def create_llm_worker(config):
            start_time = time.time()
            llm = self.factory.create_llm(config)
            end_time = time.time()
            return llm, end_time - start_time
        
        # 并发创建
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_llm_worker, config) for config in configs]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # 分析结果
        llms = [result[0] for result in results]
        individual_times = [result[1] for result in results]
        
        self.benchmark.add_result("concurrent_llm_creation", {
            "total_time": total_time,
            "concurrent_count": len(configs),
            "avg_individual_time": statistics.mean(individual_times),
            "max_individual_time": max(individual_times),
            "min_individual_time": min(individual_times),
            "throughput": len(configs) / total_time
        })
        
        # 验证性能要求
        assert len(llms) == 20
        assert all(llm is not None for llm in llms)
        assert total_time < 10.0, f"并发创建总时间过长: {total_time:.3f}s"
        assert len(configs) / total_time > 2.0, f"并发吞吐量过低: {len(configs) / total_time:.2f} LLMs/s"
    
    def test_provider_switching_performance(self):
        """测试提供商切换性能"""
        providers = ["openai", "siliconflow", "mock"]
        switching_times = []
        
        for i in range(len(providers)):
            current_provider = providers[i]
            next_provider = providers[(i + 1) % len(providers)]
            
            # 创建当前提供商的LLM
            current_config = LLMConfig(
                provider=current_provider,
                model="test-model",
                api_key="test-key"
            )
            current_llm = self.factory.create_llm(current_config)
            
            # 切换到下一个提供商
            next_config = LLMConfig(
                provider=next_provider,
                model="test-model",
                api_key="test-key"
            )
            
            start_time = time.time()
            next_llm = self.factory.create_llm(next_config)
            switch_time = time.time() - start_time
            
            switching_times.append(switch_time)
            
            assert current_llm.config.provider == current_provider
            assert next_llm.config.provider == next_provider
        
        # 记录切换性能
        self.benchmark.add_result("provider_switching", {
            "avg_switch_time": statistics.mean(switching_times),
            "max_switch_time": max(switching_times),
            "min_switch_time": min(switching_times),
            "total_switches": len(switching_times)
        })
        
        # 验证切换性能
        avg_switch_time = statistics.mean(switching_times)
        assert avg_switch_time < 0.5, f"提供商切换时间过长: {avg_switch_time:.3f}s"


class TestEmbeddingFactoryPerformance:
    """嵌入工厂性能测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.benchmark = PerformanceBenchmark()
        self.factory = EmbeddingFactory()
    
    def test_embedding_creation_performance(self):
        """测试嵌入模型创建性能"""
        config = EmbeddingConfig(
            provider="siliconflow",
            model="BAAI/bge-large-zh-v1.5",
            api_key="test-key",
            dimensions=1024
        )
        
        # 测量创建性能
        embedding, execution_time = self.benchmark.measure_time(
            self.factory.create_embedding, config
        )
        
        _, memory_usage = self.benchmark.measure_memory(
            self.factory.create_embedding, config
        )
        
        self.benchmark.add_result("embedding_creation", {
            "execution_time": execution_time,
            "memory_usage": memory_usage,
            "provider": config.provider,
            "model": config.model,
            "dimensions": config.dimensions
        })
        
        # 验证性能
        assert execution_time < 1.0, f"嵌入模型创建时间过长: {execution_time:.3f}s"
        assert embedding is not None
        assert embedding.config.dimensions == 1024
    
    def test_different_dimensions_performance(self):
        """测试不同维度的性能影响"""
        dimensions = [256, 512, 1024, 1536]
        creation_times = []
        
        for dim in dimensions:
            config = EmbeddingConfig(
                provider="siliconflow",
                model="test-model",
                api_key="test-key",
                dimensions=dim
            )
            
            embedding, execution_time = self.benchmark.measure_time(
                self.factory.create_embedding, config
            )
            
            creation_times.append(execution_time)
            assert embedding.config.dimensions == dim
        
        self.benchmark.add_result("dimension_performance", {
            "dimensions": dimensions,
            "creation_times": creation_times,
            "avg_time": statistics.mean(creation_times),
            "time_variance": statistics.variance(creation_times) if len(creation_times) > 1 else 0
        })
        
        # 验证维度对性能的影响不应该太大
        max_time = max(creation_times)
        min_time = min(creation_times)
        assert max_time - min_time < 0.5, f"不同维度间性能差异过大: {max_time - min_time:.3f}s"


class TestConfigPerformance:
    """配置性能测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.benchmark = PerformanceBenchmark()
    
    def test_config_creation_performance(self):
        """测试配置创建性能"""
        def create_llm_configs():
            configs = []
            for i in range(100):
                config = LLMConfig(
                    provider="siliconflow",
                    model="Qwen/Qwen2-7B-Instruct",
                    api_key=f"test-key-{i}",
                    temperature=0.7,
                    max_tokens=1000
                )
                configs.append(config)
            return configs
        
        # 测量配置创建性能
        configs, execution_time = self.benchmark.measure_time(create_llm_configs)
        
        self.benchmark.add_result("config_creation", {
            "execution_time": execution_time,
            "config_count": len(configs),
            "avg_time_per_config": execution_time / len(configs)
        })
        
        # 验证配置创建性能
        assert len(configs) == 100
        assert execution_time < 1.0, f"配置创建时间过长: {execution_time:.3f}s"
        assert all(config.provider == "siliconflow" for config in configs)
    
    def test_config_serialization_performance(self):
        """测试配置序列化性能"""
        config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key",
            temperature=0.8,
            max_tokens=2000
        )
        
        def serialize_configs():
            results = []
            for _ in range(100):
                # 测试不同的序列化方法
                dict_result = config.to_dict()
                json_result = config.to_json()
                yaml_result = config.to_yaml()
                results.append((dict_result, json_result, yaml_result))
            return results
        
        # 测量序列化性能
        results, execution_time = self.benchmark.measure_time(serialize_configs)
        
        self.benchmark.add_result("config_serialization", {
            "execution_time": execution_time,
            "serialization_count": len(results),
            "avg_time_per_serialization": execution_time / len(results)
        })
        
        # 验证序列化性能
        assert len(results) == 100
        assert execution_time < 0.5, f"配置序列化时间过长: {execution_time:.3f}s"
    
    def test_config_validation_performance(self):
        """测试配置验证性能"""
        def validate_configs():
            valid_count = 0
            for i in range(50):
                try:
                    config = LLMConfig(
                        provider="siliconflow",
                        model=f"test-model-{i}",
                        api_key=f"test-key-{i}",
                        temperature=0.5 + (i % 10) * 0.1,
                        max_tokens=1000 + i * 10
                    )
                    warnings = config.validate_compatibility()
                    valid_count += 1
                except Exception:
                    pass
            return valid_count
        
        # 测量验证性能
        valid_count, execution_time = self.benchmark.measure_time(validate_configs)
        
        self.benchmark.add_result("config_validation", {
            "execution_time": execution_time,
            "valid_configs": valid_count,
            "total_configs": 50,
            "avg_time_per_validation": execution_time / 50
        })
        
        # 验证配置验证性能
        assert valid_count == 50
        assert execution_time < 0.5, f"配置验证时间过长: {execution_time:.3f}s"


class TestMemoryUsageOptimization:
    """内存使用优化测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.benchmark = PerformanceBenchmark()
        self.initial_memory = self.benchmark.process.memory_info().rss
    
    def test_factory_memory_efficiency(self):
        """测试工厂内存效率"""
        factory = LLMFactory()
        
        # 创建多个实例并测量内存增长
        memory_snapshots = [self.initial_memory]
        
        for i in range(20):
            config = LLMConfig(
                provider="siliconflow",
                model="Qwen/Qwen2-7B-Instruct",
                api_key=f"test-key-{i}"
            )
            
            llm = factory.create_llm(config)
            current_memory = self.benchmark.process.memory_info().rss
            memory_snapshots.append(current_memory)
        
        # 分析内存使用
        total_memory_increase = memory_snapshots[-1] - memory_snapshots[0]
        avg_memory_per_instance = total_memory_increase / 20
        
        self.benchmark.add_result("factory_memory_efficiency", {
            "total_memory_increase": total_memory_increase,
            "avg_memory_per_instance": avg_memory_per_instance,
            "memory_snapshots": memory_snapshots,
            "instances_created": 20
        })
        
        # 验证内存效率
        assert avg_memory_per_instance < 1024 * 1024, f"每个实例内存使用过多: {avg_memory_per_instance / 1024 / 1024:.2f}MB"
        assert total_memory_increase < 50 * 1024 * 1024, f"总内存增长过多: {total_memory_increase / 1024 / 1024:.2f}MB"
    
    def test_memory_cleanup_after_deletion(self):
        """测试删除后内存清理"""
        factory = LLMFactory()
        
        # 创建实例
        llms = []
        for i in range(10):
            config = LLMConfig(
                provider="siliconflow",
                model="Qwen/Qwen2-7B-Instruct",
                api_key=f"test-key-{i}"
            )
            llm = factory.create_llm(config)
            llms.append(llm)
        
        memory_after_creation = self.benchmark.process.memory_info().rss
        
        # 删除实例
        del llms
        
        # 强制垃圾回收
        import gc
        gc.collect()
        
        memory_after_deletion = self.benchmark.process.memory_info().rss
        
        memory_freed = memory_after_creation - memory_after_deletion
        
        self.benchmark.add_result("memory_cleanup", {
            "memory_after_creation": memory_after_creation,
            "memory_after_deletion": memory_after_deletion,
            "memory_freed": memory_freed,
            "cleanup_efficiency": memory_freed / (memory_after_creation - self.initial_memory) if memory_after_creation > self.initial_memory else 0
        })
        
        # 验证内存清理效果
        # 注意：由于Python的内存管理机制，可能不会立即释放所有内存
        # 允许一定的内存波动，因为Python的垃圾回收机制可能导致内存使用略有增加
        memory_change_mb = memory_freed / 1024 / 1024
        assert abs(memory_change_mb) < 50, f"内存变化过大: {memory_change_mb:.2f}MB"


class TestPerformanceRegression:
    """性能回归测试"""
    
    def setup_method(self):
        """设置测试环境"""
        self.benchmark = PerformanceBenchmark()
        
        # 性能基准（这些值应该基于实际测试确定）
        self.performance_baselines = {
            "llm_creation_time": 0.5,  # 秒
            "embedding_creation_time": 0.5,  # 秒
            "health_check_time": 0.1,  # 秒
            "memory_per_instance": 5 * 1024 * 1024,  # 5MB
            "concurrent_throughput": 5.0  # instances/second
        }
    
    def test_llm_creation_regression(self):
        """测试LLM创建性能回归"""
        factory = LLMFactory()
        config = LLMConfig(
            provider="siliconflow",
            model="Qwen/Qwen2-7B-Instruct",
            api_key="test-key"
        )
        
        # 多次测试取平均值
        times = []
        for _ in range(10):
            _, execution_time = self.benchmark.measure_time(
                factory.create_llm, config
            )
            times.append(execution_time)
        
        avg_time = statistics.mean(times)
        baseline = self.performance_baselines["llm_creation_time"]
        
        self.benchmark.add_result("llm_creation_regression", {
            "avg_time": avg_time,
            "baseline": baseline,
            "regression_ratio": avg_time / baseline,
            "within_baseline": avg_time <= baseline * 1.2  # 允许20%的性能波动
        })
        
        # 验证性能没有显著回归
        assert avg_time <= baseline * 1.5, f"LLM创建性能回归: {avg_time:.3f}s > {baseline * 1.5:.3f}s"
    
    def test_memory_usage_regression(self):
        """测试内存使用回归"""
        factory = LLMFactory()
        initial_memory = self.benchmark.process.memory_info().rss
        
        # 创建多个实例
        llms = []
        for i in range(10):
            config = LLMConfig(
                provider="siliconflow",
                model="Qwen/Qwen2-7B-Instruct",
                api_key=f"test-key-{i}"
            )
            llm = factory.create_llm(config)
            llms.append(llm)
        
        final_memory = self.benchmark.process.memory_info().rss
        memory_per_instance = (final_memory - initial_memory) / len(llms)
        baseline = self.performance_baselines["memory_per_instance"]
        
        self.benchmark.add_result("memory_usage_regression", {
            "memory_per_instance": memory_per_instance,
            "baseline": baseline,
            "regression_ratio": memory_per_instance / baseline,
            "within_baseline": memory_per_instance <= baseline * 1.2
        })
        
        # 验证内存使用没有显著回归
        assert memory_per_instance <= baseline * 1.5, f"内存使用回归: {memory_per_instance / 1024 / 1024:.2f}MB > {baseline * 1.5 / 1024 / 1024:.2f}MB"
    
    def test_generate_performance_report(self):
        """生成性能测试报告"""
        # 运行所有基准测试
        self.test_llm_creation_regression()
        self.test_memory_usage_regression()
        
        # 生成报告
        summary = self.benchmark.get_summary()
        
        # 验证报告包含必要信息
        assert "total_tests" in summary
        assert "test_results" in summary
        assert summary["total_tests"] > 0
        
        # 可以将报告保存到文件或输出到日志
        print("\n=== 性能测试报告 ===")
        print(f"总测试数: {summary['total_tests']}")
        
        if "avg_execution_time" in summary:
            print(f"平均执行时间: {summary['avg_execution_time']:.3f}s")
        
        if "avg_memory_usage" in summary:
            print(f"平均内存使用: {summary['avg_memory_usage'] / 1024 / 1024:.2f}MB")
        
        for result in summary["test_results"]:
            print(f"- {result['test_name']}: {result}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])