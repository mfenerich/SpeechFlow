import os
from typing import AsyncGenerator
from openai import AsyncOpenAI
import tiktoken

from speechflow.services.chat.base import ChatServiceInterface

class OpenAIChatService(ChatServiceInterface):
    def __init__(self, model: str = "gpt-4o"):
        """
        Initializes your ChatGPTService with a hypothetical AsyncOpenAI client.
        Adjust to match whatever async library you are using.
        """
        api_key = os.getenv("CHATGPT_API_KEY")

        if not api_key:
            raise ValueError("CHATGPT_API_KEY environment variable not set")

        self.openai = AsyncOpenAI(api_key=api_key)
        self.model = model

        # Initialize the message context
        self.messages: list[dict[str, str]] = []

        # Token management
        self.model_encoding = tiktoken.encoding_for_model(model)
        self.MAX_TOKENS = 4096

    def _check_and_manage_token_limit(self):
        """
        Ensures that the total tokens in the messages context does not exceed the model's maximum token limit.
        Removes the oldest user messages as needed, keeping the system prompt intact.
        """
        total_tokens = sum(len(self.model_encoding.encode(m["content"])) for m in self.messages)

        while total_tokens > self.MAX_TOKENS:
            # Remove the second message to preserve the system prompt
            removed_message = self.messages.pop(1)
            total_tokens -= len(self.model_encoding.encode(removed_message["content"]))

    async def stream_chat_response(self, transcription: str, system_prompt: str = "You are a helpful assistant.") -> AsyncGenerator[str, None]:
        """
        Streams the ChatGPT response given a transcription string.
        Yields partial responses (tokens) as they arrive.
        """
        if not transcription.strip():
            return  # Empty or whitespace-only input, so stop immediately.

        # Add system prompt if this is the first interaction
        if not self.messages:
            self.messages.append({"role": "system", "content": system_prompt})

        # Add user input to messages
        self.messages.append({"role": "user", "content": transcription})

        # Manage token limits
        self._check_and_manage_token_limit()

        try:
            response_aiter = await self.openai.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=True,
            )

            full_response_chunks = []  # To collect chunks for constructing full_response
            async for chunk in response_aiter:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    content = delta.content
                    full_response_chunks.append(content)
                    yield content  # Stream the chunk

            # Construct the full response from collected chunks
            full_response = "".join(full_response_chunks)
            self.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            # Handle or log exceptions appropriately
            yield f"[Error streaming response: {e}]"
