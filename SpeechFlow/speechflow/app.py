from __future__ import annotations

import asyncio
import pyaudio
from pydub import AudioSegment
from textual.app import App, ComposeResult
from textual.widgets import Static, RichLog
from textual.reactive import reactive
from textual.containers import Vertical
from textual.events import Key as TextualKeyEvent


class AudioStatusIndicator(Static):
    """A styled widget that shows the current audio recording status."""
    status = reactive("⚪ Press 'K' to start recording ('Q' to quit)")

    def update_status(self, new_status: str) -> None:
        self.update(new_status)


class ActivityIndicator(Static):
    """A styled widget that shows the current activity status."""
    activity = reactive("Idle")

    def update_activity(self, new_activity: str) -> None:
        self.update(f"Activity: {new_activity}")


class ResultsBox(RichLog):
    """A large box to display transcription results."""
    def write_result(self, result: str) -> None:
        self.write(result)


class AudioTranscriptionInterface(Vertical):
    """
    A container that encapsulates all UI widgets for the
    audio transcription interface (status, activity, and results).
    """

    def compose(self) -> ComposeResult:
        """Compose the interface layout here."""
        yield AudioStatusIndicator(id="status-indicator")
        yield ActivityIndicator(id="activity-indicator")
        yield ResultsBox(id="results-log", wrap=True, highlight=True, markup=True)


class AudioTranscriptionApp(App):
    """A Textual application for live audio transcription and interaction."""

    CSS = """
        Screen {
            background: #1a1b26;  /* Dark blue-grey background */
        }

        Container {
            border: double rgb(91, 164, 91);
        }

        Horizontal {
            width: 100%;
        }

        #input-container {
            height: 5;  /* Explicit height for input container */
            margin: 1 1;
            padding: 1 2;
        }

        Input {
            width: 80%;
            height: 3;  /* Explicit height for input */
        }

        Button {
            width: 20%;
            height: 3;  /* Explicit height for button */
        }

        #bottom-pane {
            width: 100%;
            height: 82%;  /* Reduced to make room for session display */
            border: round rgb(205, 133, 63);
            content-align: center middle;
        }

        #status-indicator {
            height: 3;
            content-align: center middle;
            background: #2a2b36;
            border: solid rgb(91, 164, 91);
            margin: 1 1;
        }

        #activity-indicator {
            height: 3;
            content-align: center middle;
            background: #2a2b36;
            border: solid rgb(91, 164, 91);
            margin: 1 1;
        }

        #session-display {
            height: 3;
            content-align: center middle;
            background: #2a2b36;
            border: solid rgb(91, 164, 91);
            margin: 1 1;
        }

        Static {
            color: white;
        }

        RichLog {
            color: white;
            border: round rgb(205, 133, 63);
            padding: 1;
        }
    """

    is_recording = reactive(False)
    frames = reactive(list)
    audio = pyaudio.PyAudio()
    stream = None

    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    CHUNK = 1024

    def compose(self) -> ComposeResult:
        """Compose the main application layout."""
        # Mount the interface container
        yield AudioTranscriptionInterface()

    async def on_mount(self) -> None:
        """
        Run tasks when the app is mounted. Initialize UI statuses here.
        """
        status_widget = self.query_one("#status-indicator", AudioStatusIndicator)
        activity_widget = self.query_one("#activity-indicator", ActivityIndicator)

        status_widget.update_status("⚪ Press 'K' to start recording ('Q' to quit)")
        activity_widget.update_activity("Idle...")

    async def on_key(self, event: TextualKeyEvent) -> None:
        """Handle Textual keyboard events."""
        await self.key_pressed(event.key)

    async def key_pressed(self, event: str) -> None:
        """
        A custom method to interpret a pressed key
        and respond accordingly.
        """
        status_widget = self.query_one("#status-indicator", AudioStatusIndicator)
        activity_widget = self.query_one("#activity-indicator", ActivityIndicator)

        if event.lower() == "q":
            self.exit()

        elif event.lower() == "k":
            self.is_recording = not self.is_recording
            if self.is_recording:
                self.frames = []
                status_widget.update_status("🔴 Recording... (Press 'K' to stop)")
                activity_widget.update_activity("Recording")

                # Start capturing audio in the background
                # (You can also choose to run this via a worker if you prefer concurrency)
                # asyncio.create_task(self.capture_audio())
            else:
                status_widget.update_status("⚪ Press 'K' to start recording ('Q' to quit)")
                activity_widget.update_activity("Processing audio...")
                await self.process_audio()

    async def capture_audio(self) -> None:
        """
        Continuously capture audio data while recording is active.
        """
        device_index = self.select_audio_device()
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            input_device_index=device_index,
        )

        try:
            while self.is_recording:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                self.frames.append(data)
                await asyncio.sleep(0.01)
        finally:
            self.stream.stop_stream()
            self.stream.close()

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

    async def process_audio(self) -> None:
        """Process the captured audio for transcription."""
        activity_widget = self.query_one("#activity-indicator", ActivityIndicator)
        activity_widget.update_activity("Transcribing audio...")

        audio_data = b"".join(self.frames)
        audio_segment = AudioSegment(
            data=audio_data,
            sample_width=self.audio.get_sample_size(self.FORMAT),
            frame_rate=self.RATE,
            channels=self.CHANNELS,
        )

        # Export audio to FLAC
        audio_file_path = "temp_audio.flac"
        audio_segment.export(audio_file_path, format="flac")

        # Placeholder for actual transcription logic
        transcription = self.transcribe_audio(audio_file_path)
        self.query_one("#results-log", ResultsBox).write_result(transcription)

        activity_widget.update_activity("Done")

    def transcribe_audio(self, file_path: str) -> str:
        """
        Placeholder transcription logic.
        Replace this with a real service or library call.
        """
        return "This is a sample transcription. Replace with actual logic."


if __name__ == "__main__":
    app = AudioTranscriptionApp()
    app.run()
