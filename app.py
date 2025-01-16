import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
import importlib

from textual import on
from textual.app import App
from textual.widgets import Select
from textual.events import Key as TextualKeyEvent
from textual.reactive import reactive

# Import centralized constants
from speechflow.core.constants import CHUNK_LENGTH_S, SAMPLE_RATE, FORMAT, CHANNELS

from speechflow.core.audio_handler import AudioHandler
from speechflow.services.chat.base import ChatServiceInterface
from speechflow.services.transcription.base import TranscriptionServiceInterface
from speechflow.core.interface import (
    AudioTranscriptionInterface,
    AudioStatusIndicator,
    ActivityIndicator,
    ResultsBox,
)

load_dotenv()

def load_class_from_env(env_variable: str):
    """Dynamically load a class from an environment variable."""
    class_path = os.getenv(env_variable)
    if not class_path:
        raise ValueError(f"Environment variable {env_variable} is not set.")
    try:
        module_name, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not load class '{class_path}' from '{env_variable}': {e}")

# Dynamically load services
TranscriptionServiceClass = load_class_from_env("TRANSCRIPTION_SERVICE")
ChatServiceClass = load_class_from_env("CHAT_SERVICE")

class AudioTranscriptionApp(App):
    """Main application for audio capture and transcription."""

    is_recording = reactive(False)
    device_selected = reactive(False)  # Tracks if a device has been selected
    frames = reactive(list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use audio handler & transcription service with shared constants
        self.audio_handler = AudioHandler(
            sample_rate=SAMPLE_RATE,
            chunk_length_s=CHUNK_LENGTH_S,
            fmt=FORMAT,
            channels=CHANNELS,
        )
        self.transcription_service = TranscriptionServiceClass(sample_rate=SAMPLE_RATE)
        self.chat_service = ChatServiceClass(model=os.getenv("CHATGPT_MODEL", "gpt-4o"))
        self.device_index = None

    async def on_load(self) -> None:
        """Load application resources and initialize transcription client."""
        css_path = Path(__file__).parent / "speechflow/styles.css"
        self.stylesheet.read(str(css_path))
        await self.transcription_service.initialize_client()

    async def on_exit(self) -> None:
        """Ensure graceful shutdown."""
        await self.transcription_service.close()

    def compose(self):
        """Compose widgets for the application layout."""
        devices = self.audio_handler.get_audio_devices()
        if not devices:
            yield AudioStatusIndicator(
                id="status-indicator",
                text="No audio devices found",
            )
        else:
            yield Select.from_values(
                devices,
                id="audio-device-select",
                prompt="Select an audio device",
            )
            yield AudioTranscriptionInterface()

    async def on_mount(self) -> None:
        """Run tasks when the app is mounted."""
        self.set_status_idle()

    @on(Select.Changed, "#audio-device-select")
    def on_device_selected(self, event: Select.Changed) -> None:
        """Handle audio device selection."""
        selected_option = event.value  # e.g., (key, label)
        self.device_index = int(selected_option[0])  # Convert key -> int
        self.device_selected = True

        # Disable the Select widget to prevent re-selection
        select_widget = self.query_one("#audio-device-select", Select)
        select_widget.disabled = True

        self.update_status(
            f"⚪ Device selected ({self.device_index}). Press 'K' to start recording ('Q' to quit)"
        )

    async def on_key(self, event: TextualKeyEvent) -> None:
        """Handle global key events."""
        await self.handle_key_press(event.key.lower())

    async def handle_key_press(self, key: str) -> None:
        """Toggle recording or quit based on key press."""
        if key == "q":
            self.exit()
            return

        # Require a device to be selected before recording
        if not self.device_selected:
            self.update_status("⚪ Please select an audio device first.")
            return

        if key == "k":
            self.is_recording = not self.is_recording
            if self.is_recording:
                self.set_status_recording()
                # Start capturing audio in the background
                self.run_worker(self.capture_audio)
            else:
                self.set_status_idle(processing=True)
                await self.process_audio()

    async def capture_audio(self) -> None:
        """Capture audio data while recording is active."""
        try:
            self.audio_handler.open_stream(self.device_index)
            while self.is_recording:
                try:
                    data = self.audio_handler.read_chunk()
                    if not data:
                        self.update_activity("Captured empty audio chunk.")
                        break
                    self.frames.append(data)
                    self.update_status(f"🔴 Recording... {len(self.frames)} chunks captured.")
                    await asyncio.sleep(0)
                except Exception as chunk_error:
                    self.update_activity(f"Error capturing audio chunk: {chunk_error}")
                    break
        except Exception as e:
            self.update_activity(f"Error: {e}")
            self.update_status("⚪ Recording failed. Try again.")
        finally:
            self.audio_handler.close_stream()
            if not self.is_recording:
                # Only set to idle if we've stopped recording
                self.update_activity("Idle...")

    async def process_audio(self) -> None:
        """Process the recorded audio."""
        if not self.frames:
            self.update_activity("No audio recorded to process.")
            return

        try:
            file_path = self.audio_handler.export_frames_to_flac(self.frames)
            self.update_activity("Processing transcription...")
            result = await self.transcription_service.transcribe(file_path)
            results_widget = self.query_one("#results-log", ResultsBox)

            full_text = ""  # Initialize a buffer for the full text
            async for partial_text in self.chat_service.stream_chat_response(result):
                results_widget.clear()  # Clear the widget before updating
                full_text += partial_text
                results_widget.write_result(full_text)  # Update the widget with the entire content

            self.update_activity("Transcription complete.")
        except Exception as e:
            self.update_activity(f"Error: {str(e)}")

    def update_status(self, message: str) -> None:
        """Helper to update the status widget."""
        status_widget = self.query_one("#status-indicator", AudioStatusIndicator)
        status_widget.update_status(message)

    def update_activity(self, message: str) -> None:
        """Helper to update the activity widget."""
        activity_widget = self.query_one("#activity-indicator", ActivityIndicator)
        activity_widget.update_activity(message)

    def set_status_idle(self, processing: bool = False) -> None:
        """
        Sets the status to the 'idle' message.
        If 'processing' is True, indicates we're processing the just-recorded audio.
        """
        if processing:
            self.update_status("⚪ Press 'K' to start recording ('Q' to quit)")
            self.update_activity("Processing audio...")
        else:
            self.update_status("⚪ Press 'K' to start recording ('Q' to quit)")
            self.update_activity("Idle...")

    def set_status_recording(self) -> None:
        """Sets the status to a 'recording' message and clears the frames buffer."""
        self.frames = []
        self.update_status("🔴 Recording... (Press 'K' to stop)")
        self.update_activity("Recording")


if __name__ == "__main__":
    app = AudioTranscriptionApp()
    app.run()
