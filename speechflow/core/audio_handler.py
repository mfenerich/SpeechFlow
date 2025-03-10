import os
import threading

import pyaudio
from pydub import AudioSegment

from .constants import SAMPLE_RATE, FORMAT, CHANNELS, CHUNK_LENGTH_S

class AudioHandler:
    """Handles low-level audio capture and export functionality."""

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        chunk_length_s: float = CHUNK_LENGTH_S,
        fmt=FORMAT,
        channels: int = CHANNELS,
    ):
        self.audio = pyaudio.PyAudio()
        self.stream = None

        # Audio format constants
        self.FORMAT = fmt
        self.CHANNELS = channels
        self.RATE = sample_rate
        self.CHUNK = int(self.RATE * chunk_length_s)
        self.lock = threading.Lock()

    def get_audio_devices(self) -> list[tuple[str, str]]:
        """Return a list of available audio devices as (code, display_name) tuples."""
        device_count = self.audio.get_device_count()
        # If no devices, return empty list. Handled by main app.
        return [
            (str(i), f"{self.audio.get_device_info_by_index(i)['name']} ({i})")
            for i in range(device_count)
        ]

    def open_stream(self, device_index: int) -> None:
        """Open a PyAudio stream for recording."""
        device_info = self.audio.get_device_info_by_index(device_index)
        if device_info["maxInputChannels"] < self.CHANNELS:
            raise ValueError(f"Device does not support {self.CHANNELS} channels.")

        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            input_device_index=device_index,
        )

    def read_chunk(self) -> bytes:
        """Read a chunk of audio data."""
        if self.stream is None:
            raise RuntimeError("Audio stream is not open.")
        return self.stream.read(self.CHUNK, exception_on_overflow=False)

    def close_stream(self) -> None:
        """Close the PyAudio stream."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def export_frames_to_flac(self, frames: list[bytes], output_dir: str = "./") -> str:
        """Combine frames and export them as a FLAC file."""
        if not frames:
            raise ValueError("No frames to export.")

        audio_data = b"".join(frames)
        audio_segment = AudioSegment(
            data=audio_data,
            sample_width=pyaudio.PyAudio().get_sample_size(self.FORMAT),
            frame_rate=self.RATE,
            channels=self.CHANNELS,
        )
        file_path = os.path.join(output_dir, "recorded_audio.flac")
        audio_segment.export(file_path, format="flac")
        return file_path
