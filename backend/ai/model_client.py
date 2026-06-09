import os
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, AsyncGenerator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DEFAULT_REQUEST_TIMEOUT_SECONDS = int(os.getenv("AI_RESPONSE_TIMEOUT", "30"))
DEFAULT_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "0"))


def _create_async_openai_client(
    api_key: str,
    base_url: str,
    timeout_seconds: int,
    max_retries: int,
):
    from openai import AsyncOpenAI
    import httpx

    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=httpx.Timeout(timeout_seconds),
        max_retries=max_retries,
    )


@dataclass
class ModelCallResult:
    """模型 API 调用结果，成功时 content 有值，失败时 error 有详情。"""
    success: bool
    content: Optional[str] = None
    error: Optional[Dict[str, Any]] = None


def classify_api_error(
    exc: Exception,
    timeout_seconds: Optional[int] = None,
    max_retries: Optional[int] = None,
) -> Dict[str, Any]:
    """将异常归类为可写入玩家日志的错误信息。"""
    message = str(exc)
    lower_message = message.lower()
    exception_name = type(exc).__name__

    error_type = "api_error"
    if (
        "timed out" in lower_message
        or "timeout" in lower_message
        or "timeout" in exception_name.lower()
    ):
        error_type = "timeout"
    elif hasattr(exc, "status_code"):
        error_type = f"http_{exc.status_code}"

    error: Dict[str, Any] = {
        "type": error_type,
        "message": message,
        "exception": exception_name,
    }
    if timeout_seconds is not None:
        error["timeout_seconds"] = timeout_seconds
    if max_retries is not None:
        error["max_retries"] = max_retries
    if hasattr(exc, "status_code"):
        error["status_code"] = exc.status_code
    if hasattr(exc, "code"):
        error["code"] = exc.code
    return error


def _failed_result(
    exc: Exception,
    provider: str,
    timeout_seconds: int,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> ModelCallResult:
    print(f"{provider}请求失败: {exc}")
    return ModelCallResult(
        success=False,
        error=classify_api_error(
            exc,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        ),
    )


class BaseModelClient(ABC):
    request_timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES

    @abstractmethod
    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> ModelCallResult:
        """
        发送聊天完成请求到模型（非流式）

        Args:
            messages: 消息列表，每个消息包含role和content
            **kwargs: 其他可选参数

        Returns:
            包含响应文本或错误详情的 ModelCallResult
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
        self.request_timeout_seconds = DEFAULT_REQUEST_TIMEOUT_SECONDS
        self.max_retries = DEFAULT_MAX_RETRIES
        self._initialize()

    def _initialize(self):
        """初始化OpenAI客户端"""
        if not self.api_key:
            raise ValueError("未提供OpenAI API密钥")

        try:
            self.client = _create_async_openai_client(
                self.api_key,
                self.base_url,
                self.request_timeout_seconds,
                self.max_retries,
            )
            print(
                f"✅ OpenAI客户端初始化成功，模型: {self.model}，"
                f"超时 {self.request_timeout_seconds}s，重试 {self.max_retries} 次"
            )
        except ImportError:
            raise ImportError("未找到openai包，请安装: pip install openai")
        except Exception as e:
            raise RuntimeError(f"OpenAI客户端初始化失败: {e}")

    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> ModelCallResult:
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
            content = response.choices[0].message.content
            if content is None or not content.strip():
                return ModelCallResult(
                    success=False,
                    error={
                        "type": "empty_response",
                        "message": "模型返回空内容",
                    },
                )
            return ModelCallResult(success=True, content=content.strip())
        except Exception as e:
            return _failed_result(
                e, "OpenAI", self.request_timeout_seconds, self.max_retries
            )

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
    def __init__(self, api_key: str = None, model: str = "glm-4.7"):
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        self.model = model
        self.client = None
        self.request_timeout_seconds = DEFAULT_REQUEST_TIMEOUT_SECONDS
        self.max_retries = DEFAULT_MAX_RETRIES
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

    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> ModelCallResult:
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
            content = response.choices[0].message.content
            if content is None or not content.strip():
                return ModelCallResult(
                    success=False,
                    error={
                        "type": "empty_response",
                        "message": "模型返回空内容",
                    },
                )
            return ModelCallResult(success=True, content=content.strip())
        except Exception as e:
            return _failed_result(
                e, "智谱AI", self.request_timeout_seconds, self.max_retries
            )

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


class VolcEngineModelClient(BaseModelClient):
    """火山方舟（豆包）模型客户端，使用 OpenAI 兼容接口"""

    VOLCENGINE_BASE_URL = "https://ark.cn-beijing.volces.com/api/plan/v3"

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("API_KEY")
        self.base_url = base_url or os.getenv("VOLCENGINE_BASE_URL", self.VOLCENGINE_BASE_URL)
        self.model = model or os.getenv("MODEL", "doubao-seed-2.0-mini")
        self.client = None
        self.request_timeout_seconds = DEFAULT_REQUEST_TIMEOUT_SECONDS
        self.max_retries = DEFAULT_MAX_RETRIES
        self._initialize()

    def _initialize(self):
        """初始化火山方舟客户端"""
        if not self.api_key:
            raise ValueError("未提供火山方舟 API密钥（API_KEY）")

        try:
            self.client = _create_async_openai_client(
                self.api_key,
                self.base_url,
                self.request_timeout_seconds,
                self.max_retries,
            )
            print(
                f"✅ 火山方舟客户端初始化成功，模型: {self.model}，"
                f"超时 {self.request_timeout_seconds}s，重试 {self.max_retries} 次"
            )
        except ImportError:
            raise ImportError("未找到openai包，请安装: pip install openai")
        except Exception as e:
            raise RuntimeError(f"火山方舟客户端初始化失败: {e}")

    async def chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> ModelCallResult:
        """发送聊天完成请求到火山方舟模型（非流式）"""
        if not self.client:
            self._initialize()

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                **kwargs
            )
            content = response.choices[0].message.content
            if content is None or not content.strip():
                return ModelCallResult(
                    success=False,
                    error={
                        "type": "empty_response",
                        "message": "模型返回空内容",
                    },
                )
            return ModelCallResult(success=True, content=content.strip())
        except Exception as e:
            return _failed_result(
                e, "火山方舟", self.request_timeout_seconds, self.max_retries
            )

    async def stream_chat_completion(self, messages: List[Dict[str, str]], **kwargs) -> AsyncGenerator[str, None]:
        """发送聊天完成请求到火山方舟模型（流式）"""
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
            print(f"火山方舟流式请求失败: {e}")


class ModelClientFactory:
    @staticmethod
    def create_client(provider: str, **kwargs) -> BaseModelClient:
        """
        创建模型客户端实例

        Args:
            provider: 模型提供商，如'openai'、'zhipu'、'volcengine'
            **kwargs: 其他配置参数

        Returns:
            模型客户端实例
        """
        provider = provider.lower()

        if provider == "openai":
            return OpenAIModelClient(**kwargs)
        elif provider == "zhipu":
            return ZhipuAIModelClient(**kwargs)
        elif provider == "volcengine":
            return VolcEngineModelClient(**kwargs)
        else:
            raise ValueError(f"不支持的模型提供商: {provider}")
