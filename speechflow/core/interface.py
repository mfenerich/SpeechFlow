from textual.containers import Vertical
from textual.widgets import Static, RichLog
from textual.reactive import reactive
from textual.app import ComposeResult


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
    A container that encapsulates all UI widgets for the audio transcription interface.
    """

    def compose(self) -> ComposeResult:
        """Compose the interface layout here."""
        yield AudioStatusIndicator(id="status-indicator")
        yield ActivityIndicator(id="activity-indicator")
        yield ResultsBox(id="results-log", wrap=True, highlight=True, markup=True)
