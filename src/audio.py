import threading
import time
import numpy as np
import sounddevice as sd
from .config import SAMPLE_RATE, VAD_THRESHOLD, VAD_SILENCE_DURATION

class AudioManager:
    def __init__(self, request_queue, logger):
        self.queue = request_queue
        self.logger = logger
        self.audio_data = []
        self.state = "READY"
        
        # Flags
        self.manual_start_event = threading.Event()
        self.manual_stop_event = threading.Event()
        
        # Settings
        self.use_auto_stop = True
        self.use_voice_trigger = False
        self.silence_duration = VAD_SILENCE_DURATION
        
        # Start Loop
        self.thread = threading.Thread(target=self.audio_loop, daemon=True)
        self.thread.start()

    def update_settings(self, auto_stop, voice_trigger, silence_duration=None):
        self.use_auto_stop = auto_stop
        self.use_voice_trigger = voice_trigger
        if silence_duration is not None:
            try:
                self.silence_duration = float(silence_duration)
            except: pass

    def set_state(self, state):
        self.state = state

    def trigger_start(self):
        if self.state == "READY":
            self.manual_start_event.set()

    def trigger_stop(self):
        if self.state == "RECORDING":
            self.manual_stop_event.set()

    def audio_loop(self):
        silence_start = None
        has_spoken = False
        
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1) as stream:
            while True:
                try:
                    indata, overflow = stream.read(int(SAMPLE_RATE * 0.1))
                    if overflow: pass
                except Exception as e:
                    self.logger.error(f"Audio read error: {e}")
                    time.sleep(1)
                    continue

                amplitude = np.sqrt(np.mean(indata**2))
                
                # Check Manual Triggers
                if self.manual_start_event.is_set():
                    self.manual_start_event.clear()
                    if self.state == "READY":
                        self.start_recording()
                
                if self.manual_stop_event.is_set():
                    self.manual_stop_event.clear()
                    if self.state == "RECORDING":
                        self.stop_recording()

                # Logic based on state
                if self.state == "READY":
                    if self.use_voice_trigger and amplitude > VAD_THRESHOLD:
                        self.logger.info("Voice trigger detected!")
                        self.start_recording()
                        self.audio_data.append(indata.copy())
                        has_spoken = True
                        silence_start = None

                elif self.state == "RECORDING":
                    self.audio_data.append(indata.copy())
                    
                    if self.use_auto_stop:
                        if amplitude > VAD_THRESHOLD:
                            silence_start = None
                            has_spoken = True
                        elif has_spoken:
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start > self.silence_duration:
                                self.logger.info("Silence auto-stop.")
                                self.stop_recording()
                                silence_start = None
                                has_spoken = False

    def start_recording(self):
        self.audio_data = []
        self.queue.put(("audio_state", "RECORDING"))
        self.logger.info("Audio Recording Started")

    def stop_recording(self):
        self.queue.put("recording_finished")
        self.logger.info("Audio Recording Stopped")
