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
        self.running = True
        
        # Settings
        self.use_auto_stop = True
        self.use_voice_trigger = False
        self.silence_duration = VAD_SILENCE_DURATION
        self.threshold = VAD_THRESHOLD
        
        # Start Loop
        self.thread = threading.Thread(target=self.audio_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            try:
                self.thread.join(timeout=1.0)
            except: pass

    def update_settings(self, auto_stop, voice_trigger, silence_duration=None, threshold=None):
        self.use_auto_stop = auto_stop
        self.use_voice_trigger = voice_trigger
        if silence_duration is not None:
            try:
                self.silence_duration = float(silence_duration)
            except: pass
        if threshold is not None:
            try:
                self.threshold = float(threshold)
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
        stream = None
        
        while self.running:
            # Determine if we need stream
            # We need stream if RECORDING, or if READY and Voice Trigger is enabled
            need_stream = (self.state == "RECORDING") or \
                          (self.state == "READY" and self.use_voice_trigger)

            # Manage Stream State
            if need_stream and stream is None:
                try:
                    stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1)
                    stream.start()
                    self.logger.info("Audio Stream Started")
                except Exception as e:
                    self.logger.error(f"Failed to start stream: {e}")
                    time.sleep(1)
                    continue
            
            elif not need_stream and stream is not None:
                try:
                    stream.stop()
                    stream.close()
                except: pass
                stream = None
                self.logger.info("Audio Stream Stopped")

            # Processing
            if stream:
                try:
                    indata, overflow = stream.read(int(SAMPLE_RATE * 0.1))
                    if overflow: pass
                    
                    amplitude = np.sqrt(np.mean(indata**2))
                    
                    # Logic based on state
                    if self.state == "READY":
                        if self.use_voice_trigger and amplitude > self.threshold:
                            self.logger.info("Voice trigger detected!")
                            self.start_recording()
                            self.audio_data.append(indata.copy())
                            has_spoken = True
                            silence_start = None

                    elif self.state == "RECORDING":
                        self.audio_data.append(indata.copy())
                        
                        if self.use_auto_stop:
                            if amplitude > self.threshold:
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
                                    
                except Exception as e:
                    self.logger.error(f"Audio read error: {e}")
                    # If error, close stream to retry
                    try:
                        stream.close()
                    except: pass
                    stream = None
                    time.sleep(1)
            else:
                # Idle loop when no stream needed
                time.sleep(0.1)

            # Check Manual Triggers (Must check even if stream is closed)
            if self.manual_start_event.is_set():
                self.manual_start_event.clear()
                if self.state == "READY":
                    self.start_recording()
            
            if self.manual_stop_event.is_set():
                self.manual_stop_event.clear()
                if self.state == "RECORDING":
                    self.stop_recording()

        # Cleanup on exit
        if stream:
            try:
                stream.stop()
                stream.close()
            except: pass

    def start_recording(self):
        self.audio_data = []
        self.queue.put(("audio_state", "RECORDING"))
        self.logger.info("Audio Recording Started")

    def stop_recording(self):
        self.queue.put("recording_finished")
        self.logger.info("Audio Recording Stopped")
