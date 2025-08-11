"""
Mock LLM实现，用于测试
"""
import logging
from typing import List, Dict, Any
import asyncio

from .base import BaseLLM, LLMConfig, LLMResponse

logger = logging.getLogger(__name__)


class MockLLM(BaseLLM):
    """Mock LLM实现"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.call_count = 0
        self.responses = []
    
    async def generate(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs
    ) -> LLMResponse:
        """生成回复"""
        self.call_count += 1
        
        # 模拟API调用延迟
        await asyncio.sleep(0.1)
        
        # 获取最后一条用户消息
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        # 生成模拟回复
        response_content = self._generate_mock_response(user_message)
        
        response = LLMResponse(
            content=response_content,
            usage={
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(user_message.split()) + len(response_content.split())
            },
            model=self.config.model,
            finish_reason="stop"
        )
        
        # 记录响应用于测试验证
        self.responses.append(response)
        
        logger.debug(f"Mock LLM生成回复: {response_content[:100]}...")
        return response
    
    async def generate_text(
        self, 
        prompt: str, 
        **kwargs
    ) -> str:
        """生成文本（简化接口）"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.generate(messages, **kwargs)
        return response.content
    
    def _generate_mock_response(self, user_message: str) -> str:
        """生成模拟回复"""
        user_message_lower = user_message.lower()
        
        # 根据问题类型生成不同的模拟回复
        if "什么是" in user_message_lower or "what is" in user_message_lower:
            return f"根据提供的文档内容，{user_message}是一个重要的概念。基于检索到的相关信息，我可以为您提供以下解释：这是一个模拟的答案，用于演示系统的问答功能。"
        
        elif "如何" in user_message_lower or "how to" in user_message_lower:
            return f"关于{user_message}，根据文档中的信息，建议您按照以下步骤进行：1. 首先了解基本概念；2. 然后进行实际操作；3. 最后验证结果。这是基于检索内容生成的指导性回答。"
        
        elif "为什么" in user_message_lower or "why" in user_message_lower:
            return f"关于{user_message}这个问题，根据相关文档的分析，主要原因包括：技术因素、业务需求和用户体验等多个方面。这是基于检索到的上下文信息提供的解释。"
        
        elif "没有找到" in user_message_lower or "no relevant" in user_message_lower:
            return "抱歉，我在当前的知识库中没有找到与您的问题相关的信息。建议您：1. 检查问题的表述是否准确；2. 尝试使用不同的关键词；3. 或者上传更多相关的文档来丰富知识库。"
        
        else:
            return f"基于检索到的相关文档内容，关于您的问题「{user_message}」，我可以提供以下信息：这是一个综合性的回答，结合了多个文档源的内容。如果您需要更具体的信息，请提供更详细的问题描述。"
    
    def set_custom_response(self, response: str):
        """设置自定义响应（用于测试）"""
        self._custom_response = response
    
    def get_call_history(self) -> List[Dict[str, Any]]:
        """获取调用历史（用于测试验证）"""
        return [
            {
                "call_number": i + 1,
                "response": resp.content,
                "usage": resp.usage
            }
            for i, resp in enumerate(self.responses)
        ]
    
    def reset(self):
        """重置状态（用于测试）"""
        self.call_count = 0
        self.responses = []
        self._custom_response = None
    
    def generate_with_context(self, question: str, context: str, **kwargs) -> Dict[str, Any]:
        """基于上下文生成回答（同步版本，用于兼容）"""
        # 模拟基于上下文的回答生成
        answer = f"基于提供的上下文信息，关于「{question}」的回答是：{self._generate_mock_response(question)}"
        
        return {
            'answer': answer,
            'model': self.config.model,
            'provider': 'mock',
            'confidence': 0.8
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            'provider': 'mock',
            'model': self.config.model,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
            'call_count': self.call_count
        }
    
    def health_check(self) -> bool:
        """健康检查"""
        # Mock LLM总是健康的
        return True