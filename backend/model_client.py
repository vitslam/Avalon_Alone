import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, AsyncGenerator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class BaseModelClient(ABC):
    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """
        发送聊天完成请求到模型（非流式）

        Args:
            messages: 消息列表，每个消息包含role和content
            **kwargs: 其他可选参数

        Returns:
            模型响应文本
        """
        pass

    @abstractmethod
    async def stream_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """
        发送聊天完成请求到模型（流式）

        Args:
            messages: 消息列表，每个消息包含role和content
            **kwargs: 其他可选参数

        Yields:
            模型响应的文本块
        """
        pass


class OpenAIModelClient(BaseModelClient):
    def __init__(self, api_key: str = None, base_url: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model
        self.client = None
        self._initialize()

    def _initialize(self):
        """初始化OpenAI客户端"""
        if not self.api_key:
            raise ValueError("未提供OpenAI API密钥")

        try:
            from openai import AsyncOpenAI
            import httpx

            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=httpx.Timeout(30)
            )
            print(f"✅ OpenAI客户端初始化成功，模型: {self.model}")
        except ImportError:
            raise ImportError("未找到openai包，请安装: pip install openai")
        except Exception as e:
            raise RuntimeError(f"OpenAI客户端初始化失败: {e}")

    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """发送聊天完成请求到OpenAI模型（非流式）"""
        if not self.client:
            self._initialize()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI请求失败: {e}")
            return None

    async def stream_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """发送聊天完成请求到OpenAI模型（流式）"""
        if not self.client:
            self._initialize()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print(f"OpenAI流式请求失败: {e}")


class ZhipuAIModelClient(BaseModelClient):
    def __init__(self, api_key: str = None, model: str = "glm-4.5"):
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self.model = model
        self.client = None
        self._initialize()

    def _initialize(self):
        """初始化智谱AI客户端"""
        if not self.api_key:
            raise ValueError("未提供智谱AI API密钥")

        try:
            from zhipuai import ZhipuAI

            self.client = ZhipuAI(api_key=self.api_key)
            print(f"✅ 智谱AI客户端初始化成功，模型: {self.model}")
        except ImportError:
            raise ImportError("未找到zhipuai包，请安装: pip install zhipuai")
        except Exception as e:
            raise RuntimeError(f"智谱AI客户端初始化失败: {e}")

    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """发送聊天完成请求到智谱AI模型（非流式）"""
        if not self.client:
            self._initialize()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"智谱AI请求失败: {e}")
            return None

    async def stream_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """发送聊天完成请求到智谱AI模型（流式）"""
        if not self.client:
            self._initialize()

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print(f"智谱AI流式请求失败: {e}")


class ModelClientFactory:
    @staticmethod
    def create_client(provider: str, **kwargs) -> BaseModelClient:
        """
        创建模型客户端实例

        Args:
            provider: 模型提供商，如'openai'、'zhipu'
            **kwargs: 其他配置参数

        Returns:
            模型客户端实例
        """
        provider = provider.lower()

        if provider == "openai":
            return OpenAIModelClient(**kwargs)
        elif provider == "zhipu":
            return ZhipuAIModelClient(**kwargs)
        else:
            raise ValueError(f"不支持的模型提供商: {provider}")


async def main():
    # 示例1: 使用智谱AI模型（非流式）
    try:
        zhipu_client = ModelClientFactory.create_client(
            "zhipu",
            model="glm-4.5"
        )

        messages = [
            {"role": "system", "content": "你是一个 helpful 的助手。"},
            {"role": "user", "content": "请介绍一下阿瓦隆游戏。"}
        ]

        response = await zhipu_client.chat_completion(messages)
        print(f"\n智谱AI 非流式响应: {response}")
    except Exception as e:
        print(f"智谱AI 非流式示例失败: {e}")

    # 示例2: 使用智谱AI模型（流式）
    try:
        zhipu_client = ModelClientFactory.create_client(
            "zhipu",
            model="glm-4.5"
        )

        messages = [
            {"role": "system", "content": "你是一个 helpful 的助手。"},
            {"role": "user", "content": "请介绍一下阿瓦隆游戏。"}
        ]

        print("\n智谱AI 流式响应:")
        async for chunk in zhipu_client.stream_chat_completion(messages):
            print(chunk, end="", flush=True)
        print()  # 换行
    except Exception as e:
        print(f"智谱AI 流式示例失败: {e}")


if __name__ == "__main__":
    asyncio.run(main())