import os
from typing import AsyncGenerator
from openai import AsyncOpenAI

class ChatGPTService:
    def __init__(self, model: str="gpt-4o"):
        """
        Initializes your ChatGPTService with a hypothetical AsyncOpenAI client.
        Adjust to match whatever async library you are using.
        """

        api_key = os.getenv("CHATGPT_API_KEY")
        
        # Hypothetical usage of an async OpenAI client:
        self.openai = AsyncOpenAI(api_key=api_key)
        
        self.model = model

    async def stream_chat_response(self, transcription: str, system_prompt: str="You are a helpful assistant.") -> AsyncGenerator[str, None]:
        """
        Streams the ChatGPT response given a transcription string.
        Yields partial responses (tokens) as they arrive.
        """
        if not transcription.strip():
            return  # Empty or whitespace-only, so stop immediately.

        try:
            response_aiter = await self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": transcription},
                ],
                stream=True,
            )

            async for chunk in response_aiter:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

        except Exception as e:
            # Handle or log exceptions appropriately
            yield f"[Error streaming response: {e}]"

