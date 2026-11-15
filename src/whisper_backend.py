"""Local transcription using faster-whisper, loaded only when selected."""
import threading

from .config import INPUT_FILENAME

LANGUAGE_CODES = {
    "english": "en", "german": "de", "french": "fr", "italian": "it",
    "spanish": "es", "japanese": "ja", "chinese": "zh",
}


class WhisperBackend:
    def __init__(self, logger, model_name="base"):
        self.logger = logger
        self.model_name = model_name
        self.model = None
        self.lock = threading.Lock()
        self.last_error = None

    def process(self, audio_data, sample_rate, language="auto"):
        self.last_error = None
        try:
            with self.lock:
                if self.model is None:
                    from faster_whisper import WhisperModel
                    self.logger.info("Loading local Whisper model %s", self.model_name)
                    self.model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                name = language.lower()
                selected_language = None if name == "auto" else LANGUAGE_CODES.get(name, name)
                segments, _ = self.model.transcribe(INPUT_FILENAME, language=selected_language)
                return " ".join(segment.text.strip() for segment in segments).strip()
        except Exception as exc:
            self.last_error = str(exc)
            self.logger.error("Local Whisper transcription failed: %s", exc)
            return None


class TranscriptionBackend:
    def __init__(self, comfy, whisper):
        self.comfy = comfy
        self.whisper = whisper
        self.selected = "ComfyUI"
        self.last_error = None

    def process(self, audio_data, sample_rate, language="auto"):
        backend = self.whisper if self.selected == "Whisper (local)" else self.comfy
        result = backend.process(audio_data, sample_rate, language=language)
        self.last_error = getattr(backend, "last_error", None)
        return result
