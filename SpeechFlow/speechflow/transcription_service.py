from google.cloud import speech_v1
from google.cloud.speech_v1 import RecognitionConfig, RecognitionAudio
import os

class TranscriptionService:
    def __init__(self, bucket_name="speechmarcel"):
        self.client = speech_v1.SpeechAsyncClient()  # Use the async client
        self.bucket_name = bucket_name
        self.rate = 24000
        # os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./runtimeenv-c0a1661d4386.json"

    async def transcribe(self, file_path: str) -> str:
        """Asynchronously transcribe audio using Google Speech-to-Text."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File {file_path} not found.")

        try:
            # Read audio file
            with open(file_path, "rb") as f:
                audio_content = f.read()

            audio = RecognitionAudio(content=audio_content)
            config = RecognitionConfig(
                encoding=RecognitionConfig.AudioEncoding.FLAC,
                sample_rate_hertz=self.rate,
                language_code="en-US",
            )

            # Use the async `recognize` method
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
        await self.client.close()

