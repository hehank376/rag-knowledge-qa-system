"""
OpenAI LLM实现
"""
import logging
from typing import List, Dict, Any, Optional
import asyncio

from .base import BaseLLM, LLMConfig, LLMResponse
from ..utils.exceptions import ProcessingError
from ..utils.model_exceptions import ModelConnectionError, ModelResponseError, ModelAuthenticationError

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    """OpenAI LLM实现"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
    
    async def initialize(self) -> None:
        """初始化OpenAI客户端"""
        try:
            # 动态导入OpenAI库
            try:
                import openai
                self.openai = openai
            except ImportError:
                raise ProcessingError("请安装openai库: pip install openai")
            
            # 创建异步客户端
            self.client = openai.AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.api_base,
                timeout=self.config.timeout
            )
            
            logger.info(f"OpenAI LLM初始化成功，模型: {self.config.model}")
            
        except Exception as e:
            logger.error(f"OpenAI LLM初始化失败: {str(e)}")
            raise ProcessingError(f"OpenAI LLM初始化失败: {str(e)}")
    
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> LLMResponse:
        """生成回复"""
        if not self.client:
            raise ProcessingError("OpenAI客户端未初始化")
        
        try:
            # 合并配置参数
            params = {
                "model": self.config.model,
                "messages": messages,
                "temperature": kwargs.get("temperature", self.config.temperature),
                "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            }
            
            logger.debug(f"调用OpenAI API: {params['model']}")
            
            # 调用OpenAI API
            response = await self.client.chat.completions.create(**params)
            
            # 解析响应
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            logger.debug(f"OpenAI API调用成功，生成 {usage['completion_tokens']} 个token")
            
            return LLMResponse(
                content=content,
                usage=usage,
                model=response.model,
                finish_reason=response.choices[0].finish_reason
            )
            
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {str(e)}")
            raise ProcessingError(f"OpenAI API调用失败: {str(e)}")
    
    async def generate_text(
        self, 
        prompt: str, 
        **kwargs
    ) -> str:
        """生成文本（简化接口）"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.generate(messages, **kwargs)
        return response.content
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self.client:
            await self.client.close()
            self.client = None
        self._initialized = False
        logger.info("OpenAI LLM资源清理完成")
    
    def generate_with_context(self, question: str, context: str, **kwargs) -> Dict[str, Any]:
        """基于上下文生成回答（同步版本，用于兼容）"""
        prompt = f"""基于以下上下文信息，回答用户的问题。如果上下文中没有相关信息，请说明无法从提供的信息中找到答案。

上下文信息：
{context}

用户问题：{question}

请提供准确、有帮助的回答："""
        
        try:
            # 这里需要同步调用，实际实现中可能需要使用asyncio.run
            import asyncio
            answer = asyncio.run(self.generate_text(prompt, **kwargs))
            return {
                'answer': answer,
                'model': self.config.model,
                'provider': 'openai',
                'confidence': self._estimate_confidence(answer, context)
            }
        except Exception as e:
            logger.error(f"Context-based generation error: {str(e)}")
            return {
                'answer': f"抱歉，生成回答时出现错误：{str(e)}",
                'model': self.config.model,
                'provider': 'openai',
                'confidence': 0.0
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'provider': 'openai',
            'model': self.config.model,
            'api_base': self.config.api_base,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature
        }
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            import asyncio
            test_response = asyncio.run(self.generate_text("Hello", max_tokens=10))
            return len(test_response) > 0
        except:
            return False