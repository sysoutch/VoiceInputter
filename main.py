import logging
import uuid
import queue
import threading
import time
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
        self.audio_buffer = []

    def get_active_window(self):
        try:
            import pygetwindow as gw
            return gw.getActiveWindow()
        except: return None

    def handle_text_output(self, text):
        # Update UI Text Area
        # If Auto-Process is ON, we assume user wants to Send immediately (Auto-Send logic inherited)
        # If Auto-Process is OFF (Manual), we Append to text box for review.
        if self.gui.auto_process_var.get():
            self.gui.update_text(text)
            self.send_text_to_window(text)
        else:
            self.gui.append_text(text)

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

    def process_transcription_task(self, audio_data):
        logger.info("Processing transcription...")
        
        if self.gui.network_client_var.get():
            target = self.gui.get_selected_peer()
            if target:
                logger.info(f"Sending audio to {target}")
                text = self.network.send_audio(target, audio_data)
            else:
                logger.warning("No peer selected")
                text = None
        else:
            text = self.comfy.process(audio_data, SAMPLE_RATE)
        
        if text:
            self.queue.put(("transcription_result", text))
        else:
            logger.warning("No text extracted.")
        
        self.queue.put(("ui", "READY"))
        self.audio.set_state("READY")

    def coordinator_loop(self):
        try:
            while True:
                try:
                    msg = self.queue.get_nowait()
                except queue.Empty:
                    break # GUI 'after' loop handles re-schedule

                if isinstance(msg, tuple):
                    cmd = msg[0]
                    arg = msg[1]
                    
                    if cmd == "ui":
                        self.gui.update_ui_state(arg)
                    elif cmd == "audio_state":
                        self.audio.set_state(arg)
                        self.gui.update_ui_state(arg)
                        if arg == "RECORDING":
                            self.active_window_handle = self.get_active_window()
                    elif cmd == "transcription_result":
                        self.handle_text_output(arg)
                    elif cmd == "send_text":
                        self.send_text_to_window(arg)
                        self.gui.update_text("") # Clear after send? Or keep?
                
                elif msg == "toggle":
                    if self.audio.state == "READY":
                        self.audio.trigger_start()
                    elif self.audio.state == "RECORDING":
                        self.audio.trigger_stop()
                
                elif msg == "recording_finished":
                    new_audio = self.audio.audio_data
                    
                    if self.gui.auto_process_var.get():
                        # Auto Process
                        self.audio_buffer = new_audio
                        self.queue.put(("ui", "PROCESSING"))
                        threading.Thread(target=self.process_transcription_task, args=(self.audio_buffer,)).start()
                        self.audio_buffer = []
                    else:
                        # Manual Mode - Buffer Audio
                        if self.audio_buffer:
                            # Ask user to Append or Replace
                            if self.gui.ask_append_replace():
                                self.audio_buffer.extend(new_audio)
                            else:
                                self.audio_buffer = new_audio
                        else:
                            self.audio_buffer = new_audio
                        
                        self.gui.show_process_btn()
                        self.gui.update_ui_state("READY")
                        self.audio.set_state("READY")

                elif msg == "manual_process":
                    if self.audio_buffer:
                        self.gui.hide_process_btn()
                        self.queue.put(("ui", "PROCESSING"))
                        threading.Thread(target=self.process_transcription_task, args=(self.audio_buffer,)).start()
                        self.audio_buffer = []
                    else:
                        logger.warning("No audio to process")

                elif msg == "scan_network":
                    peers = self.network.get_peers()
                    self.gui.update_peers(peers)

                elif msg == "quit":
                    self.network.stop()
                    os._exit(0)

        except Exception as e:
            logger.error(f"Coordinator error: {e}")
        
        # Schedule next check in GUI loop
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
            self.gui.vad_silence_var.get()
        )
        self.gui.root.after(500, self.sync_settings)

if __name__ == "__main__":
    import os
    app = VoiceInputterApp()
    app.run()
