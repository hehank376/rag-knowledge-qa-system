"""
大语言模型基础接口
"""
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from datetime import datetime
import json
import yaml


class LLMConfig(BaseModel):
    """LLM配置模型"""
    provider: str = Field(..., description="LLM提供商", pattern="^[a-zA-Z][a-zA-Z0-9_-]*$")
    model: str = Field(..., description="模型名称", min_length=1)
    api_key: Optional[str] = Field(None, description="API密钥")
    api_base: Optional[str] = Field(None, description="API基础URL")
    base_url: Optional[str] = Field(None, description="基础URL（兼容字段）")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="温度参数")
    max_tokens: int = Field(1000, gt=0, le=100000, description="最大令牌数")
    timeout: int = Field(60, gt=0, le=3600, description="超时时间（秒）")
    retry_attempts: int = Field(3, ge=0, le=10, description="重试次数")
    
    # 高级配置
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Top-p采样参数")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="频率惩罚")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="存在惩罚")
    stop: Optional[Union[str, List[str]]] = Field(None, description="停止序列")
    
    # 平台特定配置
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="额外参数")
    
    model_config = ConfigDict(
        extra="forbid",  # 禁止额外字段
        validate_assignment=True,  # 赋值时验证
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "provider": "openai",
                "model": "gpt-4",
                "api_key": "sk-...",
                "temperature": 0.7,
                "max_tokens": 1000,
                "timeout": 60,
                "retry_attempts": 3
            }
        }
    )
    
    @field_validator('provider')
    @classmethod
    def validate_provider(cls, v):
        """验证提供商名称"""
        supported_providers = {
            'openai', 'siliconflow', 'modelscope', 'deepseek', 
            'ollama', 'mock', 'anthropic', 'azure', 'huggingface'
        }
        if v.lower() not in supported_providers:
            raise ValueError(f"不支持的提供商: {v}. 支持的提供商: {', '.join(supported_providers)}")
        return v.lower()
    
    @field_validator('model')
    @classmethod
    def validate_model(cls, v):
        """验证模型名称"""
        if not v or v.isspace():
            raise ValueError("模型名称不能为空")
        return v.strip()
    
    @model_validator(mode='after')
    def validate_api_key(self):
        """验证API密钥"""
        provider = self.provider.lower()
        if provider not in ['mock', 'ollama'] and not self.api_key:
            raise ValueError(f"提供商 {provider} 需要API密钥")
        return self
    
    @model_validator(mode='after')
    def validate_url_fields(self):
        """验证URL字段"""
        # 统一使用base_url字段
        if self.api_base and not self.base_url:
            self.base_url = self.api_base
        elif self.base_url and not self.api_base:
            self.api_base = self.base_url
        
        return self
    
    @model_validator(mode='after')
    def validate_provider_specific(self):
        """验证提供商特定配置"""
        provider = self.provider.lower()
        model = self.model
        
        # OpenAI特定验证
        if provider == 'openai':
            valid_models = {
                'gpt-4', 'gpt-4-turbo', 'gpt-3.5-turbo', 
                'gpt-4-32k', 'gpt-3.5-turbo-16k'
            }
            if model not in valid_models and not model.startswith(('gpt-4', 'gpt-3.5')):
                # 允许新模型，只发出警告
                pass
        
        # SiliconFlow特定验证
        elif provider == 'siliconflow':
            if not self.base_url:
                self.base_url = 'https://api.siliconflow.cn/v1'
        
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(exclude_none=True)
    
    def to_json(self, **kwargs) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json(exclude_none=True, **kwargs)
    
    def to_yaml(self) -> str:
        """转换为YAML字符串"""
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """从字典创建配置"""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'LLMConfig':
        """从JSON字符串创建配置"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'LLMConfig':
        """从YAML字符串创建配置"""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)
    
    @classmethod
    def get_default_config(cls, provider: str, model: str) -> 'LLMConfig':
        """获取默认配置"""
        defaults = {
            'openai': {
                'api_key': 'your-api-key-here',
                'temperature': 0.7,
                'max_tokens': 1000,
                'timeout': 60,
                'retry_attempts': 3
            },
            'siliconflow': {
                'api_key': 'your-api-key-here',
                'base_url': 'https://api.siliconflow.cn/v1',
                'temperature': 0.7,
                'max_tokens': 1000,
                'timeout': 60,
                'retry_attempts': 3
            },
            'mock': {
                'temperature': 0.7,
                'max_tokens': 1000,
                'timeout': 10,
                'retry_attempts': 1
            }
        }
        
        config_data = {
            'provider': provider,
            'model': model,
            **defaults.get(provider.lower(), defaults['openai'])
        }
        
        return cls(**config_data)
    
    def merge_with(self, other: 'LLMConfig') -> 'LLMConfig':
        """与另一个配置合并"""
        merged_data = self.to_dict()
        other_data = other.to_dict()
        
        # 合并extra_params
        if 'extra_params' in other_data:
            merged_data['extra_params'] = {
                **merged_data.get('extra_params', {}),
                **other_data['extra_params']
            }
            del other_data['extra_params']
        
        merged_data.update(other_data)
        return self.__class__(**merged_data)
    
    def validate_compatibility(self) -> List[str]:
        """验证配置兼容性，返回警告列表"""
        warnings = []
        
        # 检查温度设置
        if self.temperature > 1.5:
            warnings.append(f"温度设置较高 ({self.temperature})，可能导致输出不稳定")
        
        # 检查令牌数设置
        if self.max_tokens > 4000 and self.provider == 'openai' and 'gpt-3.5' in self.model:
            warnings.append("GPT-3.5模型的最大令牌数建议不超过4000")
        
        # 检查超时设置
        if self.timeout < 30:
            warnings.append(f"超时时间较短 ({self.timeout}秒)，可能导致请求失败")
        
        return warnings


class LLMResponse(BaseModel):
    """LLM响应模型"""
    content: str
    usage: Dict[str, Any] = {}
    model: str = ""
    finish_reason: str = ""
    provider: str = ""
    confidence: float = 0.0


class BaseLLM(ABC):
    """大语言模型基础类"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialized = False
    
    @abstractmethod
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> LLMResponse:
        """生成回复"""
        pass
    
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        **kwargs
    ) -> str:
        """生成文本（简化接口）"""
        pass
    
    @abstractmethod
    def generate_with_context(self, question: str, context: str, **kwargs) -> Dict[str, Any]:
        """基于上下文生成回答（同步版本，用于兼容）"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass
    
    async def initialize(self) -> None:
        """初始化LLM"""
        self._initialized = True
    
    async def cleanup(self) -> None:
        """清理资源"""
        self._initialized = False
    
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def _estimate_confidence(self, answer: str, context: str) -> float:
        """估算回答的置信度（基础实现）"""
        if not answer or len(answer.strip()) < 10:
            return 0.1
        elif "不知道" in answer or "无法" in answer or "don't know" in answer.lower():
            return 0.3
        elif len(answer) > 50:
            return 0.7
        else:
            return 0.5