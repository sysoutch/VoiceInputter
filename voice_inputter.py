import json
import logging
import os
import queue
import threading
import time
import uuid
import wave
from datetime import datetime

import numpy as np
import pyautogui
import pyperclip
import requests
import sounddevice as sd
import websocket
from pynput import keyboard

# Configuration
COMFY_URL = "localhost:8188"
CLIENT_ID = str(uuid.uuid4())
WORKFLOW_FILE = "stt.json"
INPUT_FILENAME = "input_audio.wav"
HOTKEY = {keyboard.Key.f9}  # Using F9 as the toggle hotkey

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class VoiceInputter:
    def __init__(self):
        self.active_window_handle = None
        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 16000
        self.recording_thread = None
        self.processing_thread = None
        self.current_keys = set()
        
        # Load workflow
        try:
            with open(WORKFLOW_FILE, 'r', encoding='utf-8') as f:
                self.workflow = json.load(f)
            logger.info(f"Loaded workflow from {WORKFLOW_FILE}")
        except Exception as e:
            logger.error(f"Failed to load workflow file: {e}")
            self.workflow = {}

    def check_connection(self):
        """Checks if ComfyUI is reachable."""
        try:
            response = requests.get(f"http://{COMFY_URL}/system_stats", timeout=2)
            if response.status_code == 200:
                logger.info("Connected to ComfyUI successfully.")
                return True
        except Exception as e:
            logger.error(f"Cannot reach ComfyUI at {COMFY_URL}. Is it running? Error: {e}")
        return False

    def get_active_window(self):
        """Captures the current active window handle/title."""
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                logger.info(f"Captured active window: {window.title}")
                return window
        except Exception as e:
            logger.error(f"Error capturing active window: {e}")
        return None

    def refocus_window(self, window):
        """Refocuses the specified window."""
        if window:
            try:
                logger.info(f"Refocusing window: {window.title}")
                window.activate()
                time.sleep(0.5) # Give it a moment to focus
            except Exception as e:
                logger.error(f"Error refocusing window: {e}")

    def find_node_by_class(self, class_type):
        """Finds a node ID by its class_type in the workflow JSON."""
        for node_id, node in self.workflow.items():
            if node.get("class_type") == class_type:
                return node_id
        return None

    def find_node_by_title(self, title):
        """Finds a node ID by its title in the _meta field."""
        for node_id, node in self.workflow.items():
            if node.get("_meta", {}).get("title") == title:
                return node_id
        return None

    def record_audio(self):
        """Audio recording loop."""
        logger.info("Recording started...")
        self.audio_data = []
        def callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio status: {status}")
            self.audio_data.append(indata.copy())

        with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=callback):
            while self.is_recording:
                time.sleep(0.1)
        logger.info("Recording stopped.")

    def save_audio(self):
        """Saves recorded audio to a WAV file."""
        if not self.audio_data:
            return False
        
        audio_array = np.concatenate(self.audio_data, axis=0)
        # Convert to 16-bit PCM
        audio_int16 = (audio_array * 32767).astype(np.int16)
        
        with wave.open(INPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        
        logger.info(f"Audio saved to {INPUT_FILENAME}")
        return True

    def upload_audio(self):
        """Uploads the audio file to ComfyUI."""
        try:
            with open(INPUT_FILENAME, 'rb') as f:
                files = {"image": (INPUT_FILENAME, f), "overwrite": (None, "true")}
                response = requests.post(f"http://{COMFY_URL}/upload/image", files=files, timeout=5)
                if response.status_code == 200:
                    logger.info("Audio uploaded successfully.")
                    return True
                else:
                    logger.error(f"Upload failed with status {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"Failed to upload audio: {e}")
        return False

    def process_transcription(self):
        """Final version: Extracts from Whisper node directly with robust history fetching."""
        ws = None
        try:
            if not self.workflow:
                logger.error("Workflow not loaded.")
                return

            if not self.save_audio(): return
            abs_path = os.path.abspath(INPUT_FILENAME)

            # 1. Update the LoadAudio Node
            load_node_id = self.find_node_by_class("LoadAudio")
            if load_node_id:
                self.workflow[load_node_id]["inputs"]["audio"] = abs_path
            else:
                logger.warning("Could not find 'LoadAudio' node in workflow.")

            # Identify relevant nodes dynamically
            whisper_node_id = self.find_node_by_class("Apply Whisper")
            preview_text_node_id = self.find_node_by_title("Preview Text")
            
            if not whisper_node_id:
                whisper_node_id = "98" # Fallback
            
            if not preview_text_node_id:
                # Fallback: look for any PreviewAny node that isn't the alignments one?
                # Or just rely on Whisper
                logger.info(f"Identified Whisper node ID: {whisper_node_id}")
            else:
                logger.info(f"Identified Whisper node ID: {whisper_node_id}, Preview Text node ID: {preview_text_node_id}")
            
            # 2. Connect and Queue
            ws = websocket.WebSocket()
            ws.connect(f"ws://{COMFY_URL}/ws?clientId={CLIENT_ID}")
            
            prompt_payload = {"prompt": self.workflow, "client_id": CLIENT_ID}
            resp = requests.post(f"http://{COMFY_URL}/prompt", json=prompt_payload)
            prompt_id = resp.json().get("prompt_id")
            logger.info(f"Prompt {prompt_id} sent. Waiting for Whisper...")

            # 3. Wait for execution results via WebSocket
            # We listen for 'executed' messages which contain the output data
            final_text = ""
            
            logger.info("Listening for WebSocket messages...")
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    
                    # Log unexpected messages for debugging
                    if message['type'] not in ['status', 'execution_start', 'executing', 'executed', 'progress']:
                         logger.debug(f"WS Message: {message['type']}")

                    if message['type'] == 'executed':
                        data = message['data']
                        node_id = data.get('node')
                        
                        # Check if this is our prompt
                        if data.get('prompt_id') == prompt_id:
                            output = data.get('output', {})
                            
                            # Determine if we should process this node
                            is_target = False
                            if preview_text_node_id and node_id == preview_text_node_id:
                                is_target = True
                            elif not preview_text_node_id and node_id == whisper_node_id:
                                is_target = True
                            
                            # If it's the specific Preview Text node, we definitely want it
                            if is_target:
                                found_text = ""
                                if isinstance(output, dict):
                                    # Try specific keys
                                    possible_keys = ['string', 'text', 'transcription', 'ui'] 
                                    for key in possible_keys:
                                        if key in output:
                                            val = output[key]
                                            # Handle standard output list
                                            if isinstance(val, list) and len(val) > 0:
                                                if isinstance(val[0], str):
                                                    found_text = val[0]
                                                elif isinstance(val[0], dict) and 'text' in val[0]:
                                                    # Sometimes UI output (like PreviewText) comes as a list of dicts
                                                    found_text = val[0]['text']
                                            elif isinstance(val, str):
                                                found_text = val
                                            
                                            # Handle 'ui' output specifically (common for Preview nodes)
                                            if key == 'ui':
                                                 if isinstance(val, dict) and 'text' in val:
                                                     val_text = val['text']
                                                     if isinstance(val_text, list) and len(val_text) > 0:
                                                         found_text = val_text[0]
                                            
                                            if found_text: break
                                    
                                    # Fallback: check values if specific keys missing
                                    if not found_text:
                                        for k, val in output.items():
                                            if isinstance(val, list) and len(val) > 0 and isinstance(val[0], str):
                                                 if len(val[0]) > 1 and not val[0].endswith('.wav'): 
                                                    found_text = val[0]
                                                    break

                                if found_text:
                                    final_text = found_text
                                    # If we found the text from the specific Preview node, we can stop
                                    if node_id == preview_text_node_id:
                                        break

                    if message['type'] == 'executing' and message['data']['node'] is None:
                        if message['data']['prompt_id'] == prompt_id:
                            # Execution finished
                            break
            
            if final_text and isinstance(final_text, str):
                self.handle_final_text(final_text.strip())
            else:
                logger.warning(f"Execution finished but string extraction failed for Node {whisper_node_id}.")

        except Exception as e:
            logger.error(f"Process failed: {e}", exc_info=True)
        finally:
            if ws: ws.close()
    
    def handle_final_text(self, text):
        if not text: return
        print(text)
        logger.info(f"Pasting text to active window.")
        
        if self.active_window_handle:
            try:
                self.active_window_handle.activate()
                time.sleep(0.3) 
            except:
                pass

        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.1)
        pyautogui.press('enter')
    
    def play_tts(self, filename):
        """Downloads and plays TTS audio."""
        try:
            import pygame
            url = f"http://{COMFY_URL}/view?filename={filename}&type=output"
            response = requests.get(url)
            with open("output_tts.wav", "wb") as f:
                f.write(response.content)
            
            pygame.mixer.init()
            pygame.mixer.music.load("output_tts.wav")
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.quit()
        except Exception as e:
            logger.error(f"Failed to play TTS: {e}")

    def on_press(self, key):
        if key in HOTKEY:
            self.current_keys.add(key)
            if all(k in self.current_keys for k in HOTKEY):
                self.toggle_recording()

    def on_release(self, key):
        if key in self.current_keys:
            self.current_keys.remove(key)

    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.active_window_handle = self.get_active_window()
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.start()
        else:
            self.is_recording = False
            if self.recording_thread:
                self.recording_thread.join()
            
            # Start processing in separate thread
            self.processing_thread = threading.Thread(target=self.process_transcription)
            self.processing_thread.start()

    def run(self):
        logger.info(f"VoiceInputter started. Press {HOTKEY} to toggle recording. Press Ctrl+C in this terminal to exit.")
        self.check_connection()
        try:
            with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as listener:
                listener.join()
        except KeyboardInterrupt:
            logger.info("Exiting...")

if __name__ == "__main__":
    app = VoiceInputter()
    app.run()
