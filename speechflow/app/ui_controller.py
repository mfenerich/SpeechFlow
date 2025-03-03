from typing import Callable, Optional


class UIController:
    """Controls UI state and events for the audio transcription app."""
    
    def __init__(self):
        """Initialize the UI controller."""
        self.is_recording = False
        self.device_selected = False
        self.device_index: Optional[int] = None
        
        # Callback functions for UI updates
        self.on_status_update: Optional[Callable[[str], None]] = None
        self.on_activity_update: Optional[Callable[[str], None]] = None
        self.on_results_update: Optional[Callable[[str], None]] = None
        
    def set_callbacks(self, 
                     status_callback: Callable[[str], None],
                     activity_callback: Callable[[str], None],
                     results_callback: Callable[[str], None]) -> None:
        """Set UI update callback functions.
        
        Args:
            status_callback: Function to call when status changes
            activity_callback: Function to call when activity changes
            results_callback: Function to call when results change
        """
        self.on_status_update = status_callback
        self.on_activity_update = activity_callback
        self.on_results_update = results_callback
        
    def update_status(self, message: str) -> None:
        """Update the status indicator.
        
        Args:
            message: Status message to display
        """
        if self.on_status_update:
            self.on_status_update(message)
            
    def update_activity(self, message: str) -> None:
        """Update the activity indicator.
        
        Args:
            message: Activity message to display
        """
        if self.on_activity_update:
            self.on_activity_update(message)
            
    def update_results(self, message: str) -> None:
        """Update the results box.
        
        Args:
            message: Result message to display
        """
        if self.on_results_update:
            self.on_results_update(message)
            
    def select_device(self, device_index: int) -> None:
        """Handle device selection.
        
        Args:
            device_index: Index of the selected device
        """
        self.device_index = device_index
        self.device_selected = True
        self.update_status(f"⚪ Device selected ({self.device_index}). Press 'K' to start recording ('Q' to quit)")
        
    def toggle_recording(self) -> bool:
        """Toggle recording state.
        
        Returns:
            bool: New recording state
        """
        if not self.device_selected:
            self.update_status("⚪ Please select an audio device first.")
            return False
            
        self.is_recording = not self.is_recording
        
        if self.is_recording:
            self.set_status_recording()
        else:
            self.set_status_idle(processing=True)
            
        return self.is_recording
        
    def set_status_idle(self, processing: bool = False) -> None:
        """Set status to idle state.
        
        Args:
            processing: Whether audio is being processed
        """
        if processing:
            self.update_status("⚪ Press 'K' to start recording ('Q' to quit)")
            self.update_activity("Processing audio...")
        else:
            self.update_status("⚪ Press 'K' to start recording ('Q' to quit)")
            self.update_activity("Idle...")
            
    def set_status_recording(self) -> None:
        """Set status to recording state."""
        self.update_status("🔴 Recording... (Press 'K' to stop)")
        self.update_activity("Recording")
        
    def update_recording_status(self, frame_count: int) -> None:
        """Update status with recording progress.
        
        Args:
            frame_count: Number of audio frames captured
        """
        self.update_status(f"🔴 Recording... {frame_count} chunks captured.")