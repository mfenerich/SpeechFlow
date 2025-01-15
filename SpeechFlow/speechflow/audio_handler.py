import pyaudio
import numpy as np
from pydub import AudioSegment
import sounddevice as sd
import threading

CHUNK_LENGTH_S = 0.05  # 50ms
SAMPLE_RATE = 24000
FORMAT = pyaudio.paInt16
CHANNELS = 1

class AudioHandler:
    """Handles low-level audio capture and export functionality."""

    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None

        # Audio format constants
        self.FORMAT = FORMAT
        self.CHANNELS = CHANNELS
        self.RATE = SAMPLE_RATE
        self.CHUNK = int(SAMPLE_RATE * CHUNK_LENGTH_S)
        self.lock = threading.Lock()
        self.frames = []  # Collected audio frames

    def get_audio_devices(self) -> list[tuple[str, str]]:
        """Return a list of available audio devices as (code, display_name) tuples."""
        device_count = self.audio.get_device_count()
        devices = [
            (str(i), f"{self.audio.get_device_info_by_index(i)['name']} ({i})")
            for i in range(device_count)
        ]
        return devices

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
        file_path = f"{output_dir}/recorded_audio.flac"
        audio_segment.export(file_path, format="flac")
        return file_path
