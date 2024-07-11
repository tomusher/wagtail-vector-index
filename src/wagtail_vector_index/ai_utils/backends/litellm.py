import inspect
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Generator, NotRequired, Self

import litellm
import litellm.types.utils
from django.core.exceptions import ImproperlyConfigured

from ..types import (
    AIResponse,
    AIResponseStreamingPart,
    AIStreamingResponse,
    ChatMessage,
)
from .base import (
    BaseChatBackend,
    BaseChatConfig,
    BaseChatConfigSettingsDict,
    BaseConfigSettingsDict,
    BaseEmbeddingBackend,
    BaseEmbeddingConfig,
    BaseEmbeddingConfigSettingsDict,
)


class BaseLiteLLMSettingsDict(BaseConfigSettingsDict):
    DEFAULT_PARAMETERS: NotRequired[Mapping[str, Any] | None]


class LiteLLMBackendSettingsDict(BaseLiteLLMSettingsDict, BaseChatConfigSettingsDict):
    pass


class LiteLLMEmbeddingSettingsDict(
    BaseLiteLLMSettingsDict, BaseEmbeddingConfigSettingsDict
):
    pass


def build_ai_response(response):
    """Convert a LiteLLM response to the appropriate AIResponse class"""

    # Normally, LiteLLM returns a CustomStreamWrapper for streaming calls,
    # but in some cases such as when passing a mock_response, it returns a generator.
    # They can both be treated as equivalent for our purposes.
    if type(response) == litellm.CustomStreamWrapper or inspect.isgenerator(response):
        return LiteLLMStreamingAIResponse(response)

    return AIResponse(
        choices=[choice["message"]["content"] for choice in response.choices]
    )


class LiteLLMStreamingAIResponse(AIStreamingResponse):
    """A wrapper around a litellm.CustomStreamWrapper to make it compatible with the AIStreamingResponse interface."""

    def __init__(self, stream_wrapper: litellm.CustomStreamWrapper | Generator) -> None:
        self.stream_wrapper = stream_wrapper

    def __iter__(self):
        return self

    def __aiter__(self):
        return self

    def _build_chunk(self, response) -> AIResponseStreamingPart:
        index = response.choices[0].index
        choice = response.choices[0]
        assert isinstance(choice, litellm.utils.StreamingChoices)  # type: ignore
        content = choice.delta.content
        if not content:
            raise StopIteration
        assert isinstance(content, str)

        return {
            "index": index,
            "content": content,
        }

    def __next__(self) -> AIResponseStreamingPart:
        next_response = next(self.stream_wrapper)
        return self._build_chunk(next_response)

    async def __anext__(self):
        next_response = await self.stream_wrapper.__anext__()
        try:
            return self._build_chunk(next_response)
        except StopIteration as e:
            raise StopAsyncIteration from e


@dataclass(kw_only=True)
class LiteLLMBackendConfigMixin:
    default_parameters: Mapping[str, Any]

    @classmethod
    def from_settings(cls, config: BaseLiteLLMSettingsDict, **kwargs: Any) -> Self:
        default_parameters = config.get("DEFAULT_PARAMETERS")
        if default_parameters is None:
            default_parameters = {}
        kwargs.setdefault("default_parameters", default_parameters)

        return super().from_settings(config, **kwargs)  # type: ignore

    @classmethod
    def _get_token_limit(cls, *, model_id: str) -> int:
        """Backend-specific method for retrieving the token limit for the provided model."""
        model_info = litellm.get_model_info(model=model_id)  # type: ignore
        if (
            not model_info
            or "max_input_tokens" not in model_info
            or not model_info["max_input_tokens"]
        ):
            raise ImproperlyConfigured(
                f"LiteLLM doesn't know about model {model_id}. Set `TOKEN_LIMIT` to specify the maximum tokens accepted by this model as input."
            )
        return model_info["max_input_tokens"]


@dataclass(kw_only=True)
class LiteLLMChatBackendConfig(
    LiteLLMBackendConfigMixin, BaseChatConfig[LiteLLMBackendSettingsDict]
):
    pass


@dataclass(kw_only=True)
class LiteLLMEmbeddingBackendConfig(
    LiteLLMBackendConfigMixin, BaseEmbeddingConfig[LiteLLMEmbeddingSettingsDict]
):
    @classmethod
    def _get_embedding_output_dimensions(cls, *, model_id: str) -> int:
        model_info = litellm.get_model_info(model=model_id)  # type: ignore
        if (
            not model_info
            or "output_vector_size" not in model_info
            or not model_info["output_vector_size"]
        ):
            raise ImproperlyConfigured(
                f"LiteLLM doesn't know about model {model_id}. Set `EMBEDDING_OUTPUT_DIMENSIONS` to specify the size of the embeddings generated by this model."
            )
        return model_info["output_vector_size"]


class LiteLLMChatBackend(BaseChatBackend[LiteLLMChatBackendConfig]):
    config: LiteLLMChatBackendConfig
    config_cls = LiteLLMChatBackendConfig

    def chat(
        self, *, messages: Sequence[ChatMessage], stream: bool = False, **kwargs
    ) -> AIResponse | AIStreamingResponse:
        parameters = {**self.config.default_parameters, **kwargs}
        response = litellm.completion(
            model=self.config.model_id,
            messages=list(messages),
            stream=stream,
            **parameters,
        )
        return build_ai_response(response)

    async def achat(
        self, *, messages: Sequence[ChatMessage], stream: bool = False, **kwargs
    ) -> AIResponse | AIStreamingResponse:
        parameters = {**self.config.default_parameters, **kwargs}
        response = await litellm.acompletion(
            model=self.config.model_id,
            messages=list(messages),
            stream=stream,
            **parameters,
        )
        return build_ai_response(response)


class LiteLLMEmbeddingBackend(BaseEmbeddingBackend[LiteLLMEmbeddingBackendConfig]):
    config: LiteLLMEmbeddingBackendConfig
    config_cls = LiteLLMEmbeddingBackendConfig

    def embed(self, inputs: Iterable[str], **kwargs) -> Iterator[list[float]]:
        response = litellm.embedding(model=self.config.model_id, input=inputs, **kwargs)
        # LiteLLM *should* return an EmbeddingResponse
        assert isinstance(response, litellm.types.utils.EmbeddingResponse)
        yield from [data["embedding"] for data in response["data"]]

    async def aembed(self, inputs: Iterable[str], **kwargs) -> Iterator[list[float]]:
        response = await litellm.aembedding(
            model=self.config.model_id, input=inputs, **kwargs
        )

        return iter([data["embedding"] for data in response["data"]])
