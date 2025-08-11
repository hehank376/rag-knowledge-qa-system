"""
SiliconFlow LLM Implementation
硅基流动大语言模型实现
"""
import logging
import asyncio
import time
from typing import Dict, List, Optional, Any
import httpx

from .base import BaseLLM, LLMConfig, LLMResponse
from ..utils.exceptions import ProcessingError
from ..utils.model_exceptions import (
    ModelConnectionError, ModelResponseError, ModelAuthenticationError,
    ModelRateLimitError, ModelTimeoutError
)

logger = logging.getLogger(__name__)


class SiliconFlowLLM(BaseLLM):
    """硅基流动LLM实现"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.api_key = config.api_key or ""
        self.base_url = config.base_url or config.api_base or "https://api.siliconflow.cn/v1"
        self.model = config.model or "Qwen/Qwen2-7B-Instruct"
        self.max_tokens = config.max_tokens
        self.temperature = config.temperature
        self.timeout = config.timeout
        self.retry_attempts = config.retry_attempts
        self._client: Optional[httpx.AsyncClient] = None
        
        if not self.api_key:
            raise ValueError("SiliconFlow API key is required")
    
    async def initialize(self) -> None:
        """初始化SiliconFlow客户端"""
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'RAG-System/1.0'
            }
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout
            )
            
            # 测试连接
            if not self.api_key.startswith("test-"):
                await self._test_connection()
            
            await super().initialize()
            logger.info(f"SiliconFlow LLM初始化成功，模型: {self.model}")
            
        except Exception as e:
            logger.error(f"SiliconFlow LLM初始化失败: {str(e)}")
            if self._client:
                await self._client.aclose()
                self._client = None
            raise ProcessingError(f"SiliconFlow LLM初始化失败: {str(e)}")
    
    async def _test_connection(self) -> None:
        """测试API连接"""
        try:
            test_messages = [{"role": "user", "content": "Hello"}]
            await self._create_completion(test_messages, max_tokens=5)
            logger.debug("SiliconFlow API连接测试成功")
        except Exception as e:
            raise ModelConnectionError(f"SiliconFlow API连接测试失败: {str(e)}", "siliconflow", self.model)
    
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> LLMResponse:
        """生成回复"""
        if not self._initialized:
            raise ProcessingError("SiliconFlow LLM未初始化")
        
        try:
            start_time = time.time()
            
            # 调用API
            response_data = await self._create_completion(messages, **kwargs)
            
            processing_time = time.time() - start_time
            
            # 解析响应
            content = response_data['choices'][0]['message']['content']
            usage = response_data.get('usage', {})
            
            logger.debug(f"SiliconFlow API调用成功，处理时间: {processing_time:.2f}s")
            
            return LLMResponse(
                content=content,
                usage=usage,
                model=response_data.get('model', self.model),
                finish_reason=response_data['choices'][0].get('finish_reason', ''),
                provider='siliconflow',
                confidence=self._estimate_confidence(content, "")
            )
            
        except Exception as e:
            logger.error(f"SiliconFlow API调用失败: {str(e)}")
            raise ProcessingError(f"SiliconFlow API调用失败: {str(e)}")
    
    async def generate_text(
        self, 
        prompt: str, 
        **kwargs
    ) -> str:
        """生成文本（简化接口）"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.generate(messages, **kwargs)
        return response.content
    
    async def _create_completion(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> Dict[str, Any]:
        """调用SiliconFlow API创建完成"""
        if not self._client:
            raise ProcessingError("HTTP客户端未初始化")
        
        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            'temperature': kwargs.get('temperature', self.temperature),
            'stream': False
        }
        
        # 添加其他可选参数
        if 'top_p' in kwargs:
            payload['top_p'] = kwargs['top_p']
        if 'frequency_penalty' in kwargs:
            payload['frequency_penalty'] = kwargs['frequency_penalty']
        if 'presence_penalty' in kwargs:
            payload['presence_penalty'] = kwargs['presence_penalty']
        
        for attempt in range(self.retry_attempts):
            try:
                response = await self._client.post('/chat/completions', json=payload)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    raise ModelAuthenticationError(
                        f"API认证失败: {response.text}", 
                        "siliconflow", 
                        self.model
                    )
                elif response.status_code == 429:
                    raise ModelRateLimitError(
                        f"API限流: {response.text}", 
                        "siliconflow", 
                        self.model
                    )
                else:
                    raise ModelResponseError(
                        f"API请求失败: {response.status_code} - {response.text}",
                        "siliconflow",
                        self.model
                    )
                    
            except httpx.TimeoutException:
                if attempt == self.retry_attempts - 1:
                    raise ModelTimeoutError(
                        f"API请求超时: {self.timeout}s",
                        "siliconflow",
                        self.model
                    )
                
                wait_time = 2 ** attempt
                logger.warning(f"API请求超时，等待 {wait_time}s 后重试")
                await asyncio.sleep(wait_time)
                
            except ModelRateLimitError:
                if attempt == self.retry_attempts - 1:
                    raise
                
                wait_time = 2 ** attempt
                logger.warning(f"API限流，等待 {wait_time}s 后重试")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    raise
                
                wait_time = 2 ** attempt
                logger.warning(f"API调用失败，等待 {wait_time}s 后重试: {str(e)}")
                await asyncio.sleep(wait_time)
        
        raise ProcessingError("API调用重试次数已用完")
    
    def generate_with_context(self, question: str, context: str, **kwargs) -> Dict[str, Any]:
        """基于上下文生成回答"""
        prompt = f"""基于以下上下文信息，回答用户的问题。如果上下文中没有相关信息，请说明无法从提供的信息中找到答案。

上下文信息：
{context}

用户问题：{question}

请提供准确、有帮助的回答："""
        
        try:
            answer = asyncio.run(self.generate_text(prompt, **kwargs))
            return {
                'answer': answer,
                'model': self.model,
                'provider': 'siliconflow',
                'confidence': self._estimate_confidence(answer, context)
            }
        except Exception as e:
            logger.error(f"Context-based generation error: {str(e)}")
            return {
                'answer': f"抱歉，生成回答时出现错误：{str(e)}",
                'model': self.model,
                'provider': 'siliconflow',
                'confidence': 0.0
            }
    
    def _estimate_confidence(self, answer: str, context: str) -> float:
        """估算回答的置信度"""
        if "无法" in answer or "不知道" in answer or "没有" in answer:
            return 0.3
        elif "根据上下文" in answer or "基于提供的信息" in answer:
            return 0.9
        elif len(answer) > 50 and context:
            # 检查答案中的词是否在上下文中出现
            answer_words = set(answer.split()[:10])  # 取前10个词
            context_words = set(context.split())
            if answer_words & context_words:  # 有交集
                return 0.8
            else:
                return 0.7
        elif len(answer) > 30:
            return 0.7
        else:
            return 0.6
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'provider': 'siliconflow',
            'model': self.model,
            'base_url': self.base_url,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'timeout': self.timeout
        }
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            test_response = asyncio.run(self.generate_text("Hello", max_tokens=10))
            return len(test_response) > 0
        except:
            return False
    
    async def cleanup(self) -> None:
        """清理资源"""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        await super().cleanup()
        logger.info("SiliconFlow LLM资源清理完成")
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            'Qwen/Qwen2-7B-Instruct',
            'Qwen/Qwen2-72B-Instruct',
            'Qwen/Qwen2.5-7B-Instruct',
            'Qwen/Qwen2.5-72B-Instruct',
            'deepseek-ai/DeepSeek-V3',
            'meta-llama/Llama-3.1-8B-Instruct',
            'meta-llama/Llama-3.1-70B-Instruct',
            'microsoft/DialoGPT-medium'
        ]