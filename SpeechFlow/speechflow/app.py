from textual import on
from textual.widgets import Select
from textual.app import App
from textual.events import Key as TextualKeyEvent
from textual.reactive import reactive

from .transcription import transcribe_audio

from .audio_handler import AudioHandler

from .interface import AudioTranscriptionInterface, AudioStatusIndicator, ActivityIndicator, ResultsBox

from pathlib import Path


class AudioTranscriptionApp(App):

    is_recording = reactive(False)
    device_selected = reactive(False)  # Tracks if a device has been selected
    frames = reactive(list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio_handler = AudioHandler()
        self.device_index = None

    async def on_load(self) -> None:
        css_path = Path(__file__).parent / "styles.css"
        self.stylesheet.read(str(css_path))

    def compose(self):
        devices = self.audio_handler.get_audio_devices()
        if not devices:
            yield AudioStatusIndicator(id="status-indicator", text="No audio devices found")
        else:
            yield Select.from_values(devices, id="audio-device-select", prompt="Select an audio device")
            yield AudioTranscriptionInterface()

    async def on_mount(self) -> None:
        """Run tasks when the app is mounted."""
        self.update_status("⚪ Please select an audio device to proceed")
        self.update_activity("Idle...")

    @on(Select.Changed, "#audio-device-select")
    def on_device_selected(self, event: Select.Changed) -> None:
        """Handle audio device selection."""
        selected_option = event.value  # This is a tuple (key, label)
        self.device_index = int(selected_option[0])  # Extract the key (index) and convert to int

        # Mark the device as selected
        self.device_selected = True

        # Disable the Select widget
        select_widget = self.query_one("#audio-device-select", Select)
        select_widget.disabled = True

        # Update status
        self.update_status("⚪ Press 'K' to start recording ('Q' to quit)")

    async def on_key(self, event: TextualKeyEvent) -> None:
        await self.handle_key_press(event.key)

    async def handle_key_press(self, key: str) -> None:
        if not self.device_selected and key.lower() != "q":
            self.update_status("⚪ Please select an audio device first.")
            return

        if key.lower() == "q":
            self.exit()

        elif key.lower() == "k":
            self.is_recording = not self.is_recording
            if self.is_recording:
                self.frames = []
                self.update_status("🔴 Recording... (Press 'K' to stop)")
                self.update_activity("Recording")

                # Start capturing audio in the background
                # self.run_worker(self.capture_audio)
            else:
                self.update_status("⚪ Press 'K' to start recording ('Q' to quit)")
                self.update_activity("Processing audio...")
                await self.process_audio()

    async def process_audio(self) -> None:
        if not self.frames:
            self.update_activity("No audio recorded to process.")
            return

        self.update_activity("Preparing audio for transcription...")
        try:
            results_widget = self.query_one("#results-log", ResultsBox)
            results_widget.clear()
            audio_file_path = self.audio_handler.export_frames_to_flac(self.frames)
            self.update_activity("Processing transcription...")
            result = transcribe_audio(audio_file_path)
            results_widget.write_result(result)
            self.update_activity("Done")
        except Exception as e:
            self.update_activity(f"Error: {str(e)}")

    async def capture_audio(self) -> None:
        """Capture audio data while recording is active."""
        self.update_activity("Recording... Press 'K' to stop.")

        try:
            self.audio_handler.open_stream(device_index=self.device_index)

            while self.is_recording:
                try:
                    # Read a chunk of audio and append it to frames
                    data = self.audio_handler.read_chunk()
                    self.frames.append(data)

                    # Update recording progress
                    self.update_status(f"🔴 Recording... {len(self.frames)} chunks captured.")
                    await self.sleep(0.1)  # Yield to the event loop to keep the UI responsive
                except Exception as chunk_error:
                    self.update_activity(f"Error capturing audio chunk: {str(chunk_error)}")
                    break

        except Exception as e:
            self.update_activity(f"Error: {str(e)}")
            self.update_status("⚪ Recording failed. Try again.")
        finally:
            self.audio_handler.close_stream()
    
    # async def capture_audio(self) -> None:
    #     """Capture audio data while recording is active."""
    #     status_widget = self.query_one("#status-indicator", AudioStatusIndicator)
    #     activity_widget = self.query_one("#activity-indicator", ActivityIndicator)

    #     try:
    #         self.audio_handler.open_stream(device_index=self.device_index)
    #         activity_widget.update_activity("Recording... Press 'K' to stop.")

    #         while self.is_recording:
    #             try:
    #                 # Read a chunk of audio and append it to frames
    #                 data = self.audio_handler.read_chunk()
    #                 self.frames.append(data)

    #                 # Optional: Update status widget with recording progress (e.g., duration or size)
    #                 status_widget.update_status(f"🔴 Recording... {len(self.frames)} chunks captured.")
    #                 await self.sleep(0.1)  # Yield to the event loop to keep the UI responsive
    #             except Exception as chunk_error:
    #                 # Handle individual chunk reading errors without interrupting recording
    #                 activity_widget.update_activity(f"Error capturing audio chunk: {str(chunk_error)}")
    #                 break

    #     except Exception as e:
    #         activity_widget.update_activity(f"Error: {str(e)}")
    #         status_widget.update_status("⚪ Recording failed. Try again.")
    #     finally:
    #         self.audio_handler.close_stream()

    def update_status(self, message: str) -> None:
        """Helper to update the status widget."""
        status_widget = self.query_one("#status-indicator", AudioStatusIndicator)
        status_widget.update_status(message)

    def update_activity(self, message: str) -> None:
        """Helper to update the activity widget."""
        activity_widget = self.query_one("#activity-indicator", ActivityIndicator)
        activity_widget.update_activity(message)


if __name__ == "__main__":
    app = AudioTranscriptionApp()
    app.run()
