import pyaudio
import tempfile
from pydub import AudioSegment
from textual import log


class AudioHandler:
    """Handles low-level audio capture and export functionality."""

    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.stream = None

        # Audio format constants
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.CHUNK = 1024

    def get_audio_devices(self) -> list[tuple[str, str]]:
        """
        Return a list of available audio devices as (code, display_name) tuples.
        The display name includes the device name and its code.
        """
        device_count = self.audio.get_device_count()
        devices = [
            (str(i), f"{self.audio.get_device_info_by_index(i)['name']} ({i})")
            for i in range(device_count)
        ]
        return devices


    def select_audio_device(self) -> int:
        """Prompt the user to select an audio device."""
        devices = [
            (i, self.audio.get_device_info_by_index(i)["name"])
            for i in range(self.audio.get_device_count())
        ]
        print("Available audio devices:")
        for idx, name in devices:
            print(f"{idx}: {name}")

        selected_index = int(input("Select device index: "))
        return selected_index

    def open_stream(self, device_index: int) -> None:
        """Open a PyAudio stream for recording."""
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
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def export_frames_to_flac(self, frames: list[bytes]) -> str:
        """
        Combine audio frames into a pydub AudioSegment and
        export to a temporary FLAC file. Returns the file path.
        """
        audio_data = b"".join(frames)
        audio_segment = AudioSegment(
            data=audio_data,
            sample_width=self.audio.get_sample_size(self.FORMAT),
            frame_rate=self.RATE,
            channels=self.CHANNELS,
        )

        # Write to a temporary file
        temp_flac = tempfile.NamedTemporaryFile(delete=False, suffix=".flac")
        audio_segment.export(temp_flac.name, format="flac")
        return temp_flac.name
