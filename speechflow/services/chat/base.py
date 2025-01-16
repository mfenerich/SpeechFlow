from abc import ABC, abstractmethod
from typing import AsyncGenerator

class ChatServiceInterface(ABC):
    @abstractmethod
    async def stream_chat_response(self, transcription: str, system_prompt: str) -> AsyncGenerator[str, None]:
        """Stream responses from a chat service."""
        pass
