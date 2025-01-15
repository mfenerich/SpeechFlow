from textual.app import App
from textual.events import Key as TextualKeyEvent
from textual.reactive import reactive

from .interface import AudioTranscriptionInterface, AudioStatusIndicator, ActivityIndicator, ResultsBox
from .audio_handler import AudioHandler
from .transcription import transcribe_audio

from pathlib import Path

class AudioTranscriptionApp(App):

    is_recording = reactive(False)
    frames = reactive(list)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio_handler = AudioHandler()
        self.device_index = None

    async def on_load(self) -> None:
        css_path = Path(__file__).parent / "styles.css"
        self.stylesheet.read(str(css_path))

    def compose(self):
        yield AudioTranscriptionInterface()

    async def on_mount(self) -> None:
        """Run tasks when the app is mounted."""
        # Continue with the rest of your setup
        status_widget = self.query_one("#status-indicator", AudioStatusIndicator)
        activity_widget = self.query_one("#activity-indicator", ActivityIndicator)

        status_widget.update_status("⚪ Press 'K' to start recording ('Q' to quit)")
        activity_widget.update_activity("Idle...")


    async def on_key(self, event: TextualKeyEvent) -> None:
        await self.handle_key_press(event.key)

    async def handle_key_press(self, key: str) -> None:
        status_widget = self.query_one("#status-indicator", AudioStatusIndicator)
        activity_widget = self.query_one("#activity-indicator", ActivityIndicator)

        if key.lower() == "q":
            self.exit()

        elif key.lower() == "k":
            self.is_recording = not self.is_recording
            if self.is_recording:
                self.frames = []
                status_widget.update_status("🔴 Recording... (Press 'K' to stop)")
                activity_widget.update_activity("Recording")

                # if self.device_index is None:
                #     self.device_index = self.audio_handler.select_audio_device()

                # Start capturing audio in the background
                # self.run_worker(self.capture_audio)
            else:
                status_widget.update_status("⚪ Press 'K' to start recording ('Q' to quit)")
                activity_widget.update_activity("Processing audio...")
                await self.process_audio()

    async def capture_audio(self) -> None:
        try:
            self.audio_handler.open_stream(device_index=self.device_index)
            while self.is_recording:
                data = self.audio_handler.read_chunk()
                self.frames.append(data)
        finally:
            self.audio_handler.close_stream()

    async def process_audio(self) -> None:
        activity_widget = self.query_one("#activity-indicator", ActivityIndicator)
        activity_widget.update_activity("Transcribing audio...")

        audio_file_path = self.audio_handler.export_frames_to_flac(self.frames)
        result = transcribe_audio(audio_file_path)
        self.query_one("#results-log", ResultsBox).write_result(result)

        activity_widget.update_activity("Done")


if __name__ == "__main__":
    app = AudioTranscriptionApp()
    app.run()
