import os
from typing import List, Optional, AsyncIterator

from speechflow.core.audio_handler import AudioHandler
from thinkhub.chat import get_chat_service
from thinkhub.transcription import get_transcription_service


class AudioProcessor:
    """Handles audio recording, processing and transcription."""
    
    def __init__(self, audio_handler: AudioHandler):
        """Initialize the audio processor.
        
        Args:
            audio_handler: The audio handler to use for capturing audio.
        """
        self.audio_handler = audio_handler
        self.transcription_service = get_transcription_service(os.getenv("TRANSCRIPTION_SERVICE"))
        self.chat_service = get_chat_service(os.getenv("CHAT_SERVICE"))
        self.frames: List[bytes] = []
        self.device_index: Optional[int] = None
        
    async def initialize(self) -> None:
        """Initialize transcription service."""
        await self.transcription_service.initialize_client()
        
    async def close(self) -> None:
        """Ensure graceful shutdown of services."""
        await self.transcription_service.close()
        
    def set_device(self, device_index: int) -> None:
        """Set the audio input device.
        
        Args:
            device_index: Index of the audio device to use.
        """
        self.device_index = device_index
        
    def start_recording(self) -> None:
        """Prepare for recording by clearing frames."""
        self.frames = []
        
    def capture_audio_chunk(self) -> bool:
        """Capture a single chunk of audio data.
        
        Returns:
            bool: True if chunk was captured successfully, False otherwise.
        """
        try:
            data = self.audio_handler.read_chunk()
            if not data:
                return False
            self.frames.append(data)
            return True
        except Exception:
            return False
            
    def open_audio_stream(self) -> bool:
        """Open the audio stream for recording.
        
        Returns:
            bool: True if opened successfully, False otherwise.
        """
        try:
            if self.device_index is None:
                return False
            self.audio_handler.open_stream(self.device_index)
            return True
        except Exception:
            return False
            
    def close_audio_stream(self) -> None:
        """Close the audio stream."""
        self.audio_handler.close_stream()
        
    def get_frame_count(self) -> int:
        """Get the number of frames captured."""
        return len(self.frames)
        
    async def process_audio(self) -> AsyncIterator[str]:
        """Process recorded audio and yield chat responses.
        
        Yields:
            str: Incremental chat responses.
        """
        if not self.frames:
            yield "No audio recorded to process."
            return
            
        try:
            # Export audio frames to a file
            file_path = self.audio_handler.export_frames_to_flac(self.frames)
            
            # Transcribe the audio
            transcription = await self.transcription_service.transcribe(file_path)
            
            # Generate chat responses from transcription
            full_text = ""
            async for partial_text in self.chat_service.stream_chat_response(transcription):
                full_text += partial_text
                yield full_text
                
        except Exception as e:
            yield f"Error: {str(e)}"