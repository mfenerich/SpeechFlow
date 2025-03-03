import asyncio
import os
from pathlib import Path

from textual import on
from textual.app import App
from textual.widgets import Select, Static
from textual.events import Key as TextualKeyEvent
from textual.reactive import reactive

from speechflow.core.constants import CHUNK_LENGTH_S, SAMPLE_RATE, FORMAT, CHANNELS
from speechflow.core.audio_handler import AudioHandler
from speechflow.core.interface import (
    AudioTranscriptionInterface,
    AudioStatusIndicator,
    ActivityIndicator,
    ResultsBox,
)

from speechflow.app.audio_processor import AudioProcessor
from speechflow.app.ui_controller import UIController


class MainApp(App):
    """Main application for audio capture and transcription."""
    
    # Reactive properties for UI state
    is_recording = reactive(False)
    device_selected = reactive(False)
    
    def __init__(self, **kwargs):
        """Initialize the main application."""
        super().__init__(**kwargs)
        
        # Initialize audio handler with shared constants
        self.audio_handler = AudioHandler(
            sample_rate=SAMPLE_RATE,
            chunk_length_s=CHUNK_LENGTH_S,
            fmt=FORMAT,
            channels=CHANNELS,
        )
        
        # Initialize processor and controller
        self.audio_processor = AudioProcessor(self.audio_handler)
        self.ui_controller = UIController()
        
    async def on_load(self) -> None:
        """Load application resources and initialize services."""
        # Load CSS stylesheet
        css_path = Path(__file__).parent.parent / "core/styles.tcss"
        self.stylesheet.read(str(css_path))
        
        # Initialize transcription service
        await self.audio_processor.initialize()
        
        # Set up UI controller callbacks
        self.ui_controller.set_callbacks(
            status_callback=self.update_status,
            activity_callback=self.update_activity,
            results_callback=self.update_results
        )
        
    async def on_exit(self) -> None:
        """Ensure graceful shutdown."""
        await self.audio_processor.close()
        
    def compose(self):
        """Compose widgets for the application layout."""
        # Get available audio devices
        devices = self.audio_handler.get_audio_devices()
        
        if not devices:
            # No audio devices found
            yield AudioStatusIndicator(
                id="status-indicator",
                text="No audio devices found",
            )
        else:
            # Device selection dropdown
            yield Select.from_values(
                devices,
                id="audio-device-select",
                prompt="Select an audio device",
            )
            
            # Display active services
            yield Static(
                f"Transcription Service: {os.getenv('TRANSCRIPTION_SERVICE', 'Not Set')} /// Chat Service: {os.getenv('CHAT_SERVICE', 'Not Set')}",
                id="service-values",
                classes="service-indicator",
            )
            
            # Main interface components
            yield AudioTranscriptionInterface()
            
    async def on_mount(self) -> None:
        """Run tasks when the app is mounted."""
        self.ui_controller.set_status_idle()
        
    @on(Select.Changed, "#audio-device-select")
    def on_device_selected(self, event: Select.Changed) -> None:
        """Handle audio device selection."""
        selected_option = event.value  # e.g., (key, label)
        device_index = int(selected_option[0])  # Convert key -> int
        
        # Update controller and processor with selected device
        self.ui_controller.select_device(device_index)
        self.audio_processor.set_device(device_index)
        self.device_selected = True
        
        # Disable the Select widget to prevent re-selection
        select_widget = self.query_one("#audio-device-select", Select)
        select_widget.disabled = True
        
    async def on_key(self, event: TextualKeyEvent) -> None:
        """Handle global key events."""
        await self.handle_key_press(event.key.lower())
        
    async def handle_key_press(self, key: str) -> None:
        """Toggle recording or quit based on key press."""
        if key == "q":
            self.exit()
            return
            
        if key == "k":
            # Toggle recording state
            is_recording = self.ui_controller.toggle_recording()
            self.is_recording = is_recording
            
            if is_recording:
                # Start capturing audio in the background
                self.audio_processor.start_recording()
                self.run_worker(self.capture_audio)
            else:
                # Process the recorded audio
                self.run_worker(self.process_audio)
                
    async def capture_audio(self) -> None:
        """Capture audio data while recording is active."""
        try:
            # Open the audio stream
            success = self.audio_processor.open_audio_stream()
            if not success:
                self.ui_controller.update_activity("Failed to open audio stream.")
                self.is_recording = False
                return
                
            # Capture audio chunks until recording is stopped
            while self.is_recording:
                success = self.audio_processor.capture_audio_chunk()
                if not success:
                    self.ui_controller.update_activity("Captured empty audio chunk.")
                    break
                
                # Update UI with frame count
                frame_count = self.audio_processor.get_frame_count()
                self.ui_controller.update_recording_status(frame_count)
                await asyncio.sleep(0)
                
        except Exception as e:
            self.ui_controller.update_activity(f"Error: {e}")
            self.ui_controller.update_status("⚪ Recording failed. Try again.")
            
        finally:
            # Clean up audio stream
            self.audio_processor.close_audio_stream()
            if not self.is_recording:
                # Only set to idle if we've stopped recording
                self.ui_controller.update_activity("Idle...")
                
    async def process_audio(self) -> None:
        """Process the recorded audio."""
        self.ui_controller.update_activity("Processing transcription...")
        
        try:
            # Get results widget for updating
            results_widget = self.query_one("#results-log", ResultsBox)
            
            # Process audio and stream responses
            async for response in self.audio_processor.process_audio():
                results_widget.clear()
                results_widget.write_result(response)
                
            self.ui_controller.update_activity("Transcription complete.")
            
        except Exception as e:
            self.ui_controller.update_activity(f"Error: {str(e)}")
            
    def update_status(self, message: str) -> None:
        """Helper to update the status widget."""
        status_widget = self.query_one("#status-indicator", AudioStatusIndicator)
        status_widget.update_status(message)
        
    def update_activity(self, message: str) -> None:
        """Helper to update the activity widget."""
        activity_widget = self.query_one("#activity-indicator", ActivityIndicator)
        activity_widget.update_activity(message)
        
    def update_results(self, message: str) -> None:
        """Helper to update the results widget."""
        results_widget = self.query_one("#results-log", ResultsBox)
        results_widget.clear()
        results_widget.write_result(message)