import os
from google.cloud import speech_v1

class TranscriptionService:
    def __init__(self, bucket_name="speechmarcel"):
        self.client = None
        self.bucket_name = bucket_name
        self.rate = 24000

    async def initialize_client(self):
        """Initialize SpeechAsyncClient within the correct event loop."""
        self.client = speech_v1.SpeechAsyncClient()

    async def transcribe(self, file_path: str) -> str:
        """Asynchronously transcribe audio."""
        if self.client is None:
            await self.initialize_client()

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found.")

        try:
            # Read audio file
            with open(file_path, "rb") as f:
                audio_content = f.read()

            audio = speech_v1.RecognitionAudio(content=audio_content)
            config = speech_v1.RecognitionConfig(
                encoding=speech_v1.RecognitionConfig.AudioEncoding.FLAC,
                sample_rate_hertz=self.rate,
                language_code="en-US",
            )

            # Perform async recognition
            response = await self.client.recognize(config=config, audio=audio)

            # Process response
            transcription = "".join(
                result.alternatives[0].transcript for result in response.results
            )
            return transcription or "No transcription available."

        except Exception as e:
            return f"Transcription failed due to an error: {e}"

    async def close(self):
        """Close the gRPC client."""
        if self.client:
            await self.client.close()
