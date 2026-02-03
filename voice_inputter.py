import json
import logging
import os
import queue
import threading
import time
import uuid
import wave
import tkinter as tk
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
HOTKEY = {keyboard.Key.f9}

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
        self.state = "READY" # READY, RECORDING, PROCESSING
        self.audio_data = []
        self.sample_rate = 16000
        
        self.queue = queue.Queue()
        self.current_keys = set()
        
        # Audio Control Flags
        self.manual_stop_event = threading.Event()
        self.manual_start_event = threading.Event()
        
        # VAD Settings (Internal state updated from UI)
        self.use_auto_stop = True
        self.use_voice_trigger = False
        
        # Dragging State
        self.drag_data = {"x": 0, "y": 0}
        
        # UI Setup
        self.root = tk.Tk()
        self.vad_auto_stop_var = tk.BooleanVar(value=True)
        self.vad_trigger_var = tk.BooleanVar(value=False)
        self.auto_enter_var = tk.BooleanVar(value=True)
        self.setup_overlay()

        # Load workflow
        try:
            with open(WORKFLOW_FILE, 'r', encoding='utf-8') as f:
                self.workflow = json.load(f)
            logger.info(f"Loaded workflow from {WORKFLOW_FILE}")
        except Exception as e:
            logger.error(f"Failed to load workflow file: {e}")
            self.workflow = {}
            
        # Start persistent audio thread
        self.audio_thread = threading.Thread(target=self.audio_loop, daemon=True)
        self.audio_thread.start()

    def setup_overlay(self):
        """Configures the Tkinter overlay window."""
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.9)
        
        screen_width = self.root.winfo_screenwidth()
        self.root.geometry(f"250x300+{screen_width-280}+50")
        
        # Bind dragging
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.do_drag)
        
        # Frame
        self.frame = tk.Frame(self.root, bg="#333333")
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Make frame draggable too
        self.frame.bind("<Button-1>", self.start_drag)
        self.frame.bind("<B1-Motion>", self.do_drag)

        # Status Label
        self.label = tk.Label(self.frame, text="Ready", font=("Arial", 12, "bold"), bg="#333333", fg="white")
        self.label.pack(pady=(5, 5))
        self.label.bind("<Button-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.do_drag)
        
        # Main Button
        self.action_btn = tk.Button(self.frame, text="RECORD", command=self.manual_toggle, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.action_btn.pack(pady=(0, 5), fill=tk.X, padx=10)
        
        # Text Area
        self.text_area = tk.Text(self.frame, height=5, width=25, font=("Arial", 10))
        self.text_area.pack(pady=5, padx=10)
        
        # Send Button
        self.send_btn = tk.Button(self.frame, text="SEND", command=self.manual_send, bg="#2196F3", fg="white", font=("Arial", 9, "bold"))
        self.send_btn.pack(pady=(0, 5), fill=tk.X, padx=10)
        
        # Options
        opts_frame = tk.Frame(self.frame, bg="#333333")
        opts_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.chk_auto_stop = tk.Checkbutton(opts_frame, text="Auto-Stop", var=self.vad_auto_stop_var, command=self.update_settings,
                                            bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_stop.pack(anchor="w")
        
        self.chk_voice_trigger = tk.Checkbutton(opts_frame, text="Record on Voice Input", var=self.vad_trigger_var, command=self.update_settings,
                                                bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_voice_trigger.pack(anchor="w")

        self.chk_auto_enter = tk.Checkbutton(opts_frame, text="Auto-Enter", var=self.auto_enter_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_enter.pack(anchor="w")
        
        # Close
        self.close_btn = tk.Button(self.frame, text="x", command=self.quit_app, bg="#333333", fg="white", font=("Arial", 8), bd=0)
        self.close_btn.place(relx=1.0, x=-2, y=0, anchor="ne")
        
        self.update_ui_state("READY")

    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def do_drag(self, event):
        x = self.root.winfo_x() - self.drag_data["x"] + event.x
        y = self.root.winfo_y() - self.drag_data["y"] + event.y
        self.root.geometry(f"+{x}+{y}")

    def update_settings(self):
        self.use_auto_stop = self.vad_auto_stop_var.get()
        self.use_voice_trigger = self.vad_trigger_var.get()

    def update_ui_state(self, state):
        self.state = state
        if state == "READY":
            self.label.config(text="Ready", bg="#333333", fg="white")
            self.frame.config(bg="#333333")
            self.action_btn.config(text="RECORD", bg="#4CAF50", fg="white", state="normal")
        elif state == "RECORDING":
            self.label.config(text="🔴 Recording...", bg="red", fg="white")
            self.frame.config(bg="red")
            self.action_btn.config(text="STOP", bg="white", fg="red", state="normal")
        elif state == "PROCESSING":
            self.label.config(text="⏳ Processing...", bg="#2196F3", fg="white")
            self.frame.config(bg="#2196F3")
            self.action_btn.config(text="...", state="disabled", bg="#1976D2")

    def manual_toggle(self):
        if self.state == "RECORDING":
            self.manual_stop_event.set()
        elif self.state == "READY":
            self.manual_start_event.set()

    def manual_send(self):
        text = self.text_area.get("1.0", tk.END).strip()
        if text:
            self.send_text_to_window(text)
            # Clear logic? User might want to keep it?
            # Usually send clears it.
            self.text_area.delete("1.0", tk.END)

    def process_queue(self):
        try:
            while True:
                msg = self.queue.get_nowait()
                if isinstance(msg, tuple):
                    cmd, arg = msg
                    if cmd == "ui":
                        self.update_ui_state(arg)
                    elif cmd == "audio_state":
                        self.state = arg # Sync state
                        self.update_ui_state(arg)
                        if arg == "RECORDING":
                            self.active_window_handle = self.get_active_window()
                    elif cmd == "transcription_result":
                        self.handle_transcription(arg)
                elif msg == "process_transcription":
                    threading.Thread(target=self.process_transcription).start()
                elif msg == "quit":
                    os._exit(0)
        except queue.Empty:
            pass
        self.root.after(50, self.process_queue)

    def audio_loop(self):
        """Continuous audio processing loop."""
        THRESHOLD = 0.01
        SILENCE_LIMIT = 2.0
        
        silence_start = None
        has_spoken = False
        
        with sd.InputStream(samplerate=self.sample_rate, channels=1) as stream:
            while True:
                try:
                    indata, overflow = stream.read(int(self.sample_rate * 0.1)) # 100ms
                    if overflow: pass 
                except Exception as e:
                    logger.error(f"Audio read error: {e}")
                    time.sleep(1)
                    continue

                amplitude = np.sqrt(np.mean(indata**2))
                
                # Check Manual Triggers
                if self.manual_start_event.is_set():
                    self.manual_start_event.clear()
                    if self.state == "READY":
                        self.start_recording_logic()
                
                if self.manual_stop_event.is_set():
                    self.manual_stop_event.clear()
                    if self.state == "RECORDING":
                        self.stop_recording_logic()

                # State Logic
                if self.state == "READY":
                    # Voice Trigger
                    if self.use_voice_trigger and amplitude > THRESHOLD:
                        logger.info("Voice trigger detected!")
                        self.start_recording_logic()
                        self.audio_data.append(indata.copy())
                        has_spoken = True
                        silence_start = None

                elif self.state == "RECORDING":
                    self.audio_data.append(indata.copy())
                    
                    # Auto-Stop
                    if self.use_auto_stop:
                        if amplitude > THRESHOLD:
                            silence_start = None
                            has_spoken = True
                        elif has_spoken:
                            if silence_start is None:
                                silence_start = time.time()
                            elif time.time() - silence_start > SILENCE_LIMIT:
                                logger.info("Silence auto-stop.")
                                self.stop_recording_logic()
                                silence_start = None
                                has_spoken = False

    def start_recording_logic(self):
        self.active_window_handle = self.get_active_window()
        self.audio_data = []
        self.queue.put(("audio_state", "RECORDING"))
        logger.info("Recording started...")

    def stop_recording_logic(self):
        logger.info("Recording stopped.")
        self.queue.put(("audio_state", "PROCESSING"))
        self.queue.put("process_transcription")

    # --- ComfyUI & System Integration ---

    def check_connection(self):
        try:
            requests.get(f"http://{COMFY_URL}/system_stats", timeout=2)
            return True
        except: return False

    def get_active_window(self):
        try:
            import pygetwindow as gw
            return gw.getActiveWindow()
        except: return None

    def find_node_by_class(self, class_type):
        for node_id, node in self.workflow.items():
            if node.get("class_type") == class_type: return node_id
        return None

    def find_node_by_title(self, title):
        for node_id, node in self.workflow.items():
            if node.get("_meta", {}).get("title") == title: return node_id
        return None

    def save_audio(self):
        if not self.audio_data: return False
        audio_array = np.concatenate(self.audio_data, axis=0)
        audio_int16 = (audio_array * 32767).astype(np.int16)
        with wave.open(INPUT_FILENAME, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())
        return True

    def upload_audio(self):
        try:
            with open(INPUT_FILENAME, 'rb') as f:
                files = {"image": (INPUT_FILENAME, f), "overwrite": (None, "true")}
                requests.post(f"http://{COMFY_URL}/upload/image", files=files, timeout=5)
            return True
        except: return False

    def process_transcription(self):
        ws = None
        try:
            if not self.save_audio(): 
                self.queue.put(("ui", "READY"))
                return
            
            abs_path = os.path.abspath(INPUT_FILENAME)
            load_node_id = self.find_node_by_class("LoadAudio")
            if load_node_id:
                self.workflow[load_node_id]["inputs"]["audio"] = abs_path

            whisper_node_id = self.find_node_by_class("Apply Whisper")
            preview_text_node_id = self.find_node_by_title("Preview Text")
            if not whisper_node_id: whisper_node_id = "98"

            ws = websocket.WebSocket()
            ws.connect(f"ws://{COMFY_URL}/ws?clientId={CLIENT_ID}")
            
            prompt_payload = {"prompt": self.workflow, "client_id": CLIENT_ID}
            resp = requests.post(f"http://{COMFY_URL}/prompt", json=prompt_payload)
            prompt_id = resp.json().get("prompt_id")
            
            final_text = ""
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executed':
                        data = message['data']
                        if data['prompt_id'] == prompt_id:
                            node_id = data.get('node')
                            is_target = False
                            if preview_text_node_id and node_id == preview_text_node_id: is_target = True
                            elif not preview_text_node_id and node_id == whisper_node_id: is_target = True
                            
                            if is_target:
                                output = data.get('output', {})
                                if isinstance(output, dict):
                                    if 'string' in output: final_text = output['string']
                                    elif 'text' in output: final_text = output['text']
                                    elif 'ui' in output and 'text' in output['ui']: final_text = output['ui']['text'][0]
                                    else:
                                        for v in output.values():
                                            if isinstance(v, list) and len(v)>0 and isinstance(v[0], str) and not v[0].endswith('.wav'):
                                                final_text = v[0]
                                                break
                                if isinstance(final_text, list): final_text = final_text[0]
                                if final_text: break

                    if message['type'] == 'executing' and message['data']['node'] is None:
                        if message['data']['prompt_id'] == prompt_id: break
            
            if final_text:
                self.queue.put(("transcription_result", final_text.strip()))
            else:
                self.queue.put(("ui", "READY"))

        except Exception as e:
            logger.error(f"Process failed: {e}")
            self.queue.put(("ui", "READY"))
        finally:
            if ws: ws.close()

    def handle_transcription(self, text):
        if not text: return
        
        # Logic: Auto-Enter vs Append
        if self.auto_enter_var.get():
            # Update text area to show what's being sent
            self.text_area.delete("1.0", tk.END)
            self.text_area.insert("1.0", text)
            self.send_text_to_window(text)
            self.queue.put(("ui", "READY"))
        else:
            # Append text
            current = self.text_area.get("1.0", tk.END).strip()
            if current:
                self.text_area.insert(tk.END, " " + text)
            else:
                self.text_area.insert(tk.END, text)
            self.text_area.see(tk.END)
            self.queue.put(("ui", "READY"))

    def send_text_to_window(self, text):
        print(text)
        if self.active_window_handle:
            try:
                self.active_window_handle.activate()
                time.sleep(0.3)
            except: pass
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        
        if self.auto_enter_var.get():
            time.sleep(0.1)
            pyautogui.press('enter')

    def on_press(self, key):
        if key in HOTKEY:
            self.current_keys.add(key)
            if all(k in self.current_keys for k in HOTKEY):
                if self.state == "RECORDING": self.manual_stop_event.set()
                elif self.state == "READY": self.manual_start_event.set()

    def on_release(self, key):
        if key in self.current_keys:
            self.current_keys.remove(key)

    def quit_app(self):
        self.root.quit()
        self.queue.put("quit")

    def run(self):
        logger.info(f"VoiceInputter started. Press F9 to toggle.")
        self.check_connection()
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        self.process_queue()
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    app = VoiceInputter()
    app.run()
