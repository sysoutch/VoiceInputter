import os
import logging
import uuid
import queue
import threading
import time
import shutil
import wave
import numpy as np
import pyautogui
import pyperclip
from pynput import keyboard

from src.config import HOTKEY, SAMPLE_RATE
from src.gui import Overlay
from src.audio import AudioManager
from src.comfy import ComfyClient
from src.network import NetworkManager

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class VoiceInputterApp:
    def __init__(self):
        self.queue = queue.Queue()
        self.client_id = str(uuid.uuid4())
        
        # Modules
        self.gui = Overlay(self.queue)
        self.audio = AudioManager(self.queue, logger)
        self.comfy = ComfyClient(logger, self.client_id)
        self.network = NetworkManager(self.comfy, logger)
        
        self.active_window_handle = None
        self.current_keys = set()
        
        # Recordings Management: List of dicts {'file': path, 'text': string}
        self.recordings = []
        os.makedirs("recordings", exist_ok=True)
        self.load_existing_recordings()

    def load_existing_recordings(self):
        try:
            files = sorted([f for f in os.listdir("recordings") if f.endswith(".wav")])
            # For existing files, we don't have text history unless we save it.
            # For now, initialize with empty text.
            self.recordings = [{'file': os.path.join("recordings", f), 'text': ""} for f in files]
            self.update_gui_list()
        except: pass

    def update_gui_list(self):
        display_list = []
        for item in self.recordings:
            name = os.path.basename(item['file'])
            txt = item['text']
            if txt:
                name += f" ({txt[:20]}...)"
            display_list.append(name)
        
        self.gui.update_rec_list(display_list)
        self.update_text_area() # Also ensure text area matches list order

    def update_text_area(self):
        # Concatenate all texts
        full_text = " ".join([r['text'] for r in self.recordings if r['text']])
        self.gui.update_text(full_text)

    def save_recording(self, audio_data):
        if not audio_data: return None
        filename = f"recordings/rec_{int(time.time())}.wav"
        try:
            audio_array = np.concatenate(audio_data, axis=0)
            audio_int16 = (audio_array * 32767).astype(np.int16)
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(audio_int16.tobytes())
            
            entry = {'file': filename, 'text': ""}
            self.recordings.append(entry)
            index = len(self.recordings) - 1
            self.update_gui_list()
            return index
        except Exception as e:
            logger.error(f"Save recording error: {e}")
            return None

    def get_active_window(self):
        try:
            import pygetwindow as gw
            return gw.getActiveWindow()
        except: return None

    def send_text_to_window(self, text):
        logger.info(f"Sending text: {text}")
        if self.active_window_handle:
            try:
                self.active_window_handle.activate()
                time.sleep(0.3)
            except: pass
        
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        
        if self.gui.auto_enter_var.get():
            time.sleep(0.1)
            pyautogui.press('enter')

    def process_transcription_task(self, index=None):
        # If index is provided, process that specific recording.
        # If index is None, process all recordings that have no text.
        
        indices_to_process = []
        if index is not None:
            indices_to_process.append(index)
        else:
            for i, rec in enumerate(self.recordings):
                # if not rec['text']: # Re-process everything? Or just missing?
                # User might want to re-process all? Or just new?
                # Usually "PROCESS ALL" implies everything currently in list.
                # But to save time, maybe skip if text exists?
                # User said "reorder files and text will also get reordered".
                # This implies text exists.
                # If manual process, maybe we assume text is missing.
                # I'll process ALL to be safe/correct (maybe user changed workflow settings).
                indices_to_process.append(i)
        
        logger.info(f"Processing {len(indices_to_process)} items...")
        
        for idx in indices_to_process:
            if idx >= len(self.recordings): continue
            
            rec = self.recordings[idx]
            filename = rec['file']
            
            # Read file data to pass to network/comfy if needed?
            # ComfyClient can read file from disk if we setup INPUT_FILENAME.
            # I'll manually copy the recording file to INPUT_FILENAME for Comfy.
            from src.config import INPUT_FILENAME
            try:
                shutil.copy(filename, INPUT_FILENAME)
            except Exception as e:
                logger.error(f"File copy error: {e}")
                continue

            text = None
            if self.gui.network_client_var.get():
                # Network Logic (Simplified: Read file, send bytes)
                # NetworkManager needs update to support file or we read it here.
                # Keeping it simple: Skip network for now or read bytes.
                logger.warning("Network not fully supported in file list mode.")
            else:
                # Comfy: Process INPUT_FILENAME (pass None as audio_data)
                text = self.comfy.process(None, SAMPLE_RATE)
            
            if text:
                self.recordings[idx]['text'] = text.strip()
                self.update_gui_list() # Updates list label and main text area
                
                # If Auto-Process (index was not None), maybe send text immediately?
                # But user wants "reorder".
                # If Auto-Process, we usually want to paste result.
                # If we paste result, we paste ONLY the new text?
                # Yes, standard behavior.
                if index is not None and self.gui.auto_process_var.get():
                     self.send_text_to_window(text)

        self.queue.put(("ui", "READY"))
        self.audio.set_state("READY")

    def coordinator_loop(self):
        try:
            while True:
                try:
                    msg = self.queue.get_nowait()
                except queue.Empty:
                    break

                if isinstance(msg, tuple):
                    cmd = msg[0]
                    
                    if cmd == "ui":
                        self.gui.update_ui_state(msg[1])
                    elif cmd == "audio_state":
                        self.audio.set_state(msg[1])
                        self.gui.update_ui_state(msg[1])
                        if msg[1] == "RECORDING":
                            self.active_window_handle = self.get_active_window()
                    elif cmd == "send_text":
                        self.send_text_to_window(msg[1])
                        # self.gui.update_text("") # Don't clear, we manage text area
                    
                    elif cmd == "move_rec":
                        index, direction = msg[1], msg[2]
                        if 0 <= index + direction < len(self.recordings):
                            self.recordings[index], self.recordings[index+direction] = self.recordings[index+direction], self.recordings[index]
                            self.update_gui_list()
                    
                    elif cmd == "delete_rec":
                        index = msg[1]
                        if 0 <= index < len(self.recordings):
                            item = self.recordings.pop(index)
                            try: os.remove(item['file'])
                            except: pass
                            self.update_gui_list()
                    
                    elif cmd == "update_rec_list":
                        self.gui.update_rec_list(msg[1])
                
                elif msg == "toggle":
                    if self.audio.state == "READY":
                        self.audio.trigger_start()
                    elif self.audio.state == "RECORDING":
                        self.audio.trigger_stop()
                
                elif msg == "recording_finished":
                    new_audio = self.audio.audio_data
                    # Save and Add to list
                    idx = self.save_recording(new_audio)
                    
                    if self.gui.auto_process_var.get() and idx is not None:
                        self.queue.put(("ui", "PROCESSING"))
                        threading.Thread(target=self.process_transcription_task, args=(idx,)).start()
                    else:
                        self.gui.show_process_btn()
                        self.gui.update_ui_state("READY")
                        self.audio.set_state("READY")

                elif msg == "manual_process":
                    if self.recordings:
                        self.queue.put(("ui", "PROCESSING"))
                        threading.Thread(target=self.process_transcription_task, args=(None,)).start()
                    else:
                        logger.warning("No recordings to process")

                elif msg == "scan_network":
                    peers = self.network.get_peers()
                    self.gui.update_peers(peers)

                elif msg == "quit":
                    self.network.stop()
                    self.audio.stop()
                    os._exit(0)

        except Exception as e:
            logger.error(f"Coordinator error: {e}")
        
        self.gui.root.after(50, self.coordinator_loop)

    def on_press(self, key):
        if key in HOTKEY:
            self.current_keys.add(key)
            if all(k in self.current_keys for k in HOTKEY):
                self.queue.put("toggle")

    def on_release(self, key):
        if key in self.current_keys:
            self.current_keys.remove(key)

    def run(self):
        logger.info("VoiceInputter started.")
        self.network.start()
        self.sync_settings()
        
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        
        self.coordinator_loop()
        
        try:
            self.gui.root.mainloop()
        except KeyboardInterrupt:
            pass

    def sync_settings(self):
        self.audio.update_settings(
            self.gui.vad_auto_stop_var.get(),
            self.gui.vad_trigger_var.get(),
            self.gui.vad_silence_var.get(),
            self.gui.vad_threshold_var.get()
        )
        self.gui.root.after(500, self.sync_settings)

if __name__ == "__main__":
    app = VoiceInputterApp()
    app.run()
