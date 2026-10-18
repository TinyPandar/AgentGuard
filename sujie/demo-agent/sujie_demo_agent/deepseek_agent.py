"""DeepSeek adapter using the same guarded tool-calling transport as Bailian."""

import os
import re
from dataclasses import dataclass, field

from .bailian_agent import BailianChatModel

DEFAULT_MODEL = "deepseek-flash"


@dataclass(repr=False, frozen=True)
class DeepSeekCredentials:
    api_key: str = field(repr=False)
    base_url: str = field(default="https://api.deepseek.com", init=False)

    def __post_init__(self):
        if (
            not self.api_key.startswith("sk-")
            or len(self.api_key) < 20
            or not self.api_key.isascii()
            or any(character.isspace() for character in self.api_key)
        ):
            raise ValueError("INVALID_DEEPSEEK_KEY")

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("DEEPSEEK_API_KEY", ""))


class DeepSeekChatModel(BailianChatModel):
    provider_code = "DEEPSEEK"

    def __init__(
        self,
        credentials: DeepSeekCredentials,
        *,
        model=DEFAULT_MODEL,
        max_tokens=1024,
        timeout=60.0,
    ):
        super().__init__(credentials, model=model, max_tokens=max_tokens, timeout=timeout)

    def valid_model(self, model: str) -> bool:
        return bool(re.fullmatch(r"deepseek-[A-Za-z0-9.-]{1,80}", model))

    def extra_payload(self) -> dict:
        # The existing Host retains content/tool_calls, not reasoning_content.
        # Non-thinking mode keeps multi-turn tool calls compatible with that contract.
        return {"thinking": {"type": "disabled"}}
