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
import string

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
        self.processing_queue = queue.Queue()
        self.processing_tasks_count = 0
        self.client_id = str(uuid.uuid4())
        
        # Modules
        self.gui = Overlay(self.queue)
        self.audio = AudioManager(self.queue, logger)
        self.comfy = ComfyClient(logger, self.client_id)
        self.network = NetworkManager(self.comfy, logger)
        
        self.active_window_handle = None
        self.current_keys = set()
        
        # Recordings Management: List of dicts {'file': path, 'text': string, 'prefix_mode': str/None, 'deleted': bool}
        self.recordings = []
        os.makedirs("recordings", exist_ok=True)
        self.load_existing_recordings()
        
        # Start Processing Worker
        threading.Thread(target=self.processing_worker, daemon=True).start()

    def processing_worker(self):
        while True:
            try:
                # Task is tuple: (recording_dict, should_send_text)
                # Prefix settings are now stored in recording_dict, so we don't need to pass them in task
                task = self.processing_queue.get()
                
                try:
                    logger.info(f"Processing worker got task.")
                    # Handle legacy or new task format
                    if len(task) >= 2:
                        rec = task[0]
                        should_send = task[1]
                        
                    if not rec.get('deleted', False):
                        self.process_single_item(rec, should_send)
                    else:
                        logger.info("Skipping deleted recording.")
                except Exception as e:
                    logger.error(f"Processing worker error: {e}")
                finally:
                    self.queue.put(("processing_complete",))
                    self.processing_queue.task_done()

            except Exception as e:
                logger.error(f"Processing worker fatal error: {e}")

    def load_existing_recordings(self):
        try:
            files = sorted([f for f in os.listdir("recordings") if f.endswith(".wav")])
            # For existing files, assume no prefix mode initially
            self.recordings = [{'file': os.path.join("recordings", f), 'text': "", 'prefix_mode': None, 'postfix_mode': None} for f in files]
            self.update_gui_list()
        except: pass

    def calculate_full_text(self, rec):
        text = rec.get('text', "")
        if not text: return "" # Don't show prefix if no text? Or show? Usually show only when text exists.
        
        # Calculate Prefix
        prefix = ""
        mode = rec.get('prefix_mode')
        if mode:
            # Calculate index in group
            count = 0
            found = False
            for item in self.recordings:
                if item is rec:
                    found = True
                    break
                if item.get('prefix_mode') == mode: count += 1
            
            if found:
                prefix = self.generate_prefix(count, mode)
        
        # Calculate Postfix
        postfix = ""
        postfix_mode = rec.get('postfix_mode')
        if postfix_mode:
            if postfix_mode == "space": postfix = " "
            elif postfix_mode == ", comma": postfix = ", "
            elif postfix_mode == ". dot": postfix = ". "
            
        return prefix + text + postfix

    def update_gui_list(self, select_index=None):
        # Dispatch to queue with optional selection index
        self.queue.put(("refresh_ui_list", select_index))

    def _perform_ui_update(self, select_index=None):
        # Actual update logic running in Main Thread
        display_list = []
        full_text_parts = []
        for item in self.recordings:
            name = os.path.basename(item['file'])
            full_text = self.calculate_full_text(item)
            
            if full_text:
                # Show preview in list
                preview = full_text if len(full_text) < 20 else full_text[:20] + "..."
                name += f" ({preview})"
                full_text_parts.append(full_text)
            
            display_list.append(name)
        
        self.gui.update_rec_list(display_list, select_index)
        self.gui.update_text(" ".join(full_text_parts))

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
            
            # Capture Prefix Mode
            prefix_mode = None
            if self.gui.prefix_var.get():
                prefix_mode = self.gui.prefix_mode_var.get()
                
            # Capture Postfix Mode
            postfix_mode = None
            if self.gui.postfix_var.get():
                postfix_mode = self.gui.postfix_mode_var.get()

            entry = {'file': filename, 'text': "", 'prefix_mode': prefix_mode, 'postfix_mode': postfix_mode}
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

    def get_target_handle(self, target_name):
        if target_name == "<Active Window>":
            return self.active_window_handle
        
        target_handle = None
        if target_name:
            try:
                import pygetwindow as gw
                # Try exact match first from all windows (safer than substring)
                all_wins = gw.getAllWindows()
                for w in all_wins:
                    if w.title == target_name:
                        target_handle = w
                        break
                
                # Disabled substring fallback to prevent focusing wrong windows (e.g. "Chat" matching "Chat Settings")
                if target_handle:
                    logger.info(f"Found target handle: {target_handle.title}")
                else:
                    logger.warning(f"Target window not found (exact match): {target_name}")
            except Exception as e:
                logger.error(f"Error finding target window: {e}")
        return target_handle

    def send_text_to_window(self, text):
        should_focus = self.gui.focus_target_var.get()
        logger.info(f"Sending text: {text} | Focus: {should_focus}")
        
        target = self.gui.target_window_var.get()
        target_handle = self.get_target_handle(target)

        if target_handle:
            try:
                if should_focus:
                    if not target_handle.isActive:
                        logger.info(f"Activating window: {target_handle.title}")
                        try:
                            if target_handle.isMinimized:
                                target_handle.restore()
                            target_handle.activate()
                            time.sleep(0.3)
                        except Exception as e:
                            logger.error(f"Failed to activate window: {e}")
            except Exception as e:
                logger.error(f"Window manipulation error: {e}")
        
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        
        if self.gui.auto_enter_var.get():
            time.sleep(0.1)
            mode = self.gui.auto_enter_mode_var.get()
            if mode == "shift+enter":
                pyautogui.hotkey('shift', 'enter')
            elif mode == "ctrl+enter":
                pyautogui.hotkey('ctrl', 'enter')
            else:
                pyautogui.press('enter')

    def generate_prefix(self, idx, mode):
        if mode == "- ": return "- "
        if mode == "* ": return "* "
        if mode.startswith("1."):
            return f"{idx + 1}. "
        if mode.startswith("a)"):
            def num_to_col(n):
                s = ""
                while n >= 0:
                    s = chr(ord('a') + n % 26) + s
                    n = n // 26 - 1
                return s
            return f"{num_to_col(idx)}) "
        return ""

    def process_single_item(self, rec, should_send):
        filename = rec['file']
        
        from src.config import INPUT_FILENAME
        try:
            shutil.copy(filename, INPUT_FILENAME)
        except Exception as e:
            logger.error(f"File copy error: {e}")
            return

        text = None
        if self.gui.network_client_var.get():
            logger.warning("Network not fully supported in file list mode.")
        else:
            text = self.comfy.process(None, SAMPLE_RATE)
        
        if text:
            if rec.get('deleted', False): return

            rec['text'] = text.strip()
            
            # Request UI Update (will calc prefixes)
            self.queue.put(("refresh_ui_list", None))
            
            if should_send and self.gui.auto_send_var.get():
                 self.queue.put(("send_text_for_rec", rec))

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
                    
                    elif cmd == "send_text_for_rec":
                        rec = msg[1]
                        if not rec.get('deleted', False):
                            text = self.calculate_full_text(rec)
                            self.send_text_to_window(text)
                    
                    elif cmd == "move_rec":
                        index, direction = msg[1], msg[2]
                        if 0 <= index + direction < len(self.recordings):
                            self.recordings[index], self.recordings[index+direction] = self.recordings[index+direction], self.recordings[index]
                            self.update_gui_list(select_index=index+direction)
                    
                    elif cmd == "delete_rec":
                        index = msg[1]
                        if 0 <= index < len(self.recordings):
                            item = self.recordings.pop(index)
                            item['deleted'] = True
                            try: os.remove(item['file'])
                            except: pass
                            
                            new_sel = index - 1 if index > 0 else 0
                            if not self.recordings: new_sel = None
                            self.update_gui_list(select_index=new_sel)
                    
                    elif cmd == "update_rec_list":
                        # Legacy handler
                        self.gui.update_rec_list(msg[1])
                    
                    elif cmd == "update_text_area":
                        self.gui.update_text(msg[1])
                    
                    elif cmd == "refresh_ui_list":
                         select_index = msg[1] if len(msg) > 1 else None
                         self._perform_ui_update(select_index)
                        
                    elif cmd == "processing_complete":
                        if self.processing_tasks_count > 0:
                            self.processing_tasks_count -= 1
                        self.gui.set_processing_state(self.processing_tasks_count > 0)
                
                elif msg == "toggle":
                    if self.audio.state == "READY":
                        self.audio.trigger_start()
                    elif self.audio.state == "RECORDING":
                        self.audio.trigger_stop()
                
                elif msg == "recording_finished":
                    new_audio = self.audio.audio_data
                    # Save and Add to list
                    idx = self.save_recording(new_audio)
                    
                    # Immediately Ready for next
                    self.gui.update_ui_state("READY")
                    self.audio.set_state("READY")
                    
                    if idx is not None:
                        rec = self.recordings[idx]
                        should_send = self.gui.auto_process_var.get()
                        
                        if should_send:
                            self.processing_tasks_count += 1
                            self.gui.set_processing_state(True)
                            self.processing_queue.put((rec, True))
                        else:
                            self.gui.show_process_btn()

                elif msg == "manual_process":
                    if self.recordings:
                        self.processing_tasks_count += len(self.recordings)
                        self.gui.set_processing_state(True)
                        for rec in self.recordings:
                            self.processing_queue.put((rec, False))
                    else:
                        logger.warning("No recordings to process")
                
                elif msg == "clear_all":
                    for rec in self.recordings:
                        rec['deleted'] = True
                        try: os.remove(rec['file'])
                        except: pass
                    self.recordings = []
                    self.update_gui_list()

                elif msg == "scan_network":
                    peers = self.network.get_peers()
                    self.gui.update_peers(peers)
                
                elif msg == "scan_windows":
                    try:
                        import pygetwindow as gw
                        titles = sorted([t for t in gw.getAllTitles() if t.strip()])
                        self.gui.update_window_list(titles)
                    except Exception as e:
                        logger.error(f"Scan windows error: {e}")
                
                elif msg == "focus_target":
                    target = self.gui.target_window_var.get()
                    if target != "<Active Window>":
                        handle = self.get_target_handle(target)
                        if handle:
                            try:
                                logger.info(f"Manually activating: {handle.title}")
                                if handle.isMinimized: handle.restore()
                                handle.activate()
                            except Exception as e:
                                logger.error(f"Manual focus failed: {e}")
                    else:
                        logger.info("Cannot manually focus <Active Window> placeholder.")

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
