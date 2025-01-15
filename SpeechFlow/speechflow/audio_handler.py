import pyaudio
from google.cloud import speech
from pydub import AudioSegment
from google.cloud import storage
import openai

class AudioHandler:
    def __init__(self, log_callback):
        self.is_recording = False
        self.frames = []
        self.log = log_callback
        self.audio = pyaudio.PyAudio()
        self.stream = None

        # Initialize Google Speech-to-Text client
        self.client = speech.SpeechClient()
        
        # Audio configuration
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.CHUNK = 1024
        self.BUCKET_NAME = "speechmarcel"
        self.openai_key = "your_openai_key"

        openai.api_key = self.openai_key

    def on_press(self, key):
        if key == keyboard.Key.alt:
            if not self.is_recording:
                self.log("Recording started. Hold ALT to record.")
                self.is_recording = True
                self.frames = []

    def on_release(self, key):
        if key == keyboard.Key.alt:
            if self.is_recording:
                self.log("Recording stopped. Transcribing...")
                self.is_recording = False
                audio_data = b"".join(self.frames)
                self.transcribe_and_send(audio_data)

    def capture_audio(self, device_index):
        self.stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK,
            input_device_index=device_index,
        )

        while True:
            if self.is_recording:
                data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                self.frames.append(data)

    def transcribe_and_send(self, audio_data):
        # Convert to FLAC and transcribe
        audio_segment = AudioSegment(
            data=audio_data,
            sample_width=pyaudio.PyAudio().get_sample_size(self.FORMAT),
            frame_rate=self.RATE,
            channels=self.CHANNELS
        )

        audio_file_path = "temp_audio.flac"
        audio_segment.export(audio_file_path, format="flac")
        uri = self.upload_to_gcs(audio_file_path, "temp_audio.flac")

        self.log(f"Uploaded to GCS: {uri}")
        # Further processing/transcription logic here...

    def upload_to_gcs(self, file_path, destination_blob_name):
        storage_client = storage.Client()
        bucket = storage_client.bucket(self.BUCKET_NAME)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
        return f"gs://{self.BUCKET_NAME}/{destination_blob_name}"
