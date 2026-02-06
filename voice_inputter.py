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
from src.matrix_client import MatrixManager
from src.telegram_client import TelegramManager

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
        self.last_item_had_enter = True # Assume true initially to avoid space on first item
        self.is_recording_hotkey = False
        self.recorded_hotkey_parts = []
        self.target_hotkey_sequence = []
        self.current_tap_sequence = []
        self.last_tap_time = 0
        
        self.processing_queue = queue.Queue()
        self.processing_tasks_count = 0
        self.client_id = str(uuid.uuid4())
        
        # Modules
        self.gui = Overlay(self.queue)
        self.audio = AudioManager(self.queue, logger)
        self.comfy = ComfyClient(logger, self.client_id)
        self.network = NetworkManager(self.comfy, logger)
        self.matrix_client = MatrixManager(logger, "UserClient") # User Client (Sender)
        self.matrix_bot = MatrixManager(logger, "BotClient")    # Bot Client (Replier)
        self.matrix_bot.register_callback(self.on_matrix_message)
        
        self.telegram = TelegramManager(logger)
        self.telegram.register_callback(self.on_telegram_message)
        
        self.active_window_handle = None
        self.current_keys = set()
        self.mic_devices = []
        
        # Recordings Management: List of dicts {'file': path, 'text': string, 'prefix_mode': str/None, 'deleted': bool}
        self.recordings = []
        os.makedirs("recordings", exist_ok=True)
        self.load_existing_recordings()
        
        # Start Processing Worker
        threading.Thread(target=self.processing_worker, daemon=True).start()

    def processing_worker(self):
        while True:
            try:
                task = self.processing_queue.get()
                
                try:
                    logger.info(f"Processing worker got task.")
                    
                    if isinstance(task, dict) and task.get('type') == 'bot_audio':
                        filename = task['file']
                        source_type = task.get('source', 'matrix')
                        room_or_chat_id = task['id']
                        
                        logger.info(f"Bot processing audio from {source_type}: {filename}")
                        
                        from src.config import INPUT_FILENAME
                        try:
                            shutil.copy(filename, INPUT_FILENAME)
                            lang = self.gui.language_var.get()
                            text = self.comfy.process(None, SAMPLE_RATE, language=lang)
                            if text:
                                logger.info(f"Bot Result: {text}")
                                if source_type == 'matrix':
                                    self.matrix_bot.send_text(room_or_chat_id, text)
                                elif source_type == 'telegram':
                                    self.telegram.send_text(room_or_chat_id, text)
                        except Exception as e:
                            logger.error(f"Bot processing error: {e}")
                            
                    else:
                        # Standard Logic
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
        
        # Logic for separator in preview area
        if self.gui.auto_enter_var.get():
            separator = "\n"
        elif self.gui.postfix_var.get():
            # If postfix is on, each part already has its separator (space, comma, etc)
            separator = ""
        else:
            separator = " "
            
        self.gui.update_text(separator.join(full_text_parts))

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

    def send_text_to_window(self, text, use_stale_handle=True):
        should_focus = self.gui.focus_target_var.get()
        logger.info(f"Sending text: {text} | Focus: {should_focus}")
        
        target = self.gui.target_window_var.get()
        
        # For Matrix messages, we typically want 'current active' not 'active when last recorded'
        # unless user specifically selected a window in dropdown.
        if target == "<Active Window>" and not use_stale_handle:
            target_handle = None
        else:
            target_handle = self.get_target_handle(target)

        if target_handle:
            if "VoiceInputter" in getattr(target_handle, 'title', ''):
                logger.warning("Target is VoiceInputter itself! Text might not appear where expected.")
            
            try:
                if should_focus:
                    if not target_handle.isActive:
                        logger.info(f"Activating window: {target_handle.title}")
                        try:
                            if target_handle.isMinimized:
                                target_handle.restore()
                            target_handle.activate()
                            time.sleep(0.5)
                        except Exception as e:
                            logger.error(f"Failed to activate window: {e}")
            except Exception as e:
                logger.error(f"Window manipulation error: {e}")
        
        pyperclip.copy(text)
        try:
            pyautogui.hotkey('ctrl', 'v')
        except Exception as e:
            logger.error(f"Paste failed: {e}")
        
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
        
        text = None
        processed = False
        
        # Matrix Send
        if self.gui.matrix_mode_var.get():
            room_id = self.gui.matrix_room_var.get()
            if room_id:
                logger.info(f"Sending recording to Matrix Room {room_id}")
                self.matrix_client.send_audio(room_id, filename)
                processed = True
            else:
                logger.error("No Matrix Room ID provided!")

        # Network Send
        if self.gui.network_client_var.get():
            peer = self.gui.get_selected_peer()
            if peer:
                logger.info(f"Sending recording to {peer}")
                text = self.network.send_audio_file(peer, filename)
                processed = True
            else:
                logger.error("No network peer selected!")
        
        # Local Processing
        if not self.gui.network_client_var.get():
            from src.config import INPUT_FILENAME
            try:
                shutil.copy(filename, INPUT_FILENAME)
                lang = self.gui.language_var.get()
                text = self.comfy.process(None, SAMPLE_RATE, language=lang)
            except Exception as e:
                logger.error(f"Local processing error: {e}")
        
        if text:
            if rec.get('deleted', False): return

            rec['text'] = text.strip()
            
            # Request UI Update (will calc prefixes)
            self.queue.put(("refresh_ui_list", None))
            
            if should_send and self.gui.auto_send_var.get():
                 self.queue.put(("send_text_for_rec", rec))

    def on_matrix_message(self, msg_type, content, room_id):
        self.queue.put(("matrix_message", msg_type, content, room_id))

    def on_telegram_message(self, msg_type, content, chat_id):
        self.queue.put(("telegram_message", msg_type, content, chat_id))

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
                            had_enter = self.gui.auto_enter_var.get()
                            
                            if not had_enter and not self.last_item_had_enter:
                                text = " " + text
                            
                            self.send_text_to_window(text)
                            self.last_item_had_enter = had_enter
                    
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
                    
                    elif cmd == "update_languages":
                        self.gui.update_languages(msg[1])
                    
                    elif cmd == "update_hotkey_display":
                        self.gui.update_hotkey_display(msg[1])
                    
                    elif cmd == "refresh_ui_list":
                         select_index = msg[1] if len(msg) > 1 else None
                         self._perform_ui_update(select_index)
                    
                    elif cmd == "record_hotkey":
                        self.is_recording_hotkey = True
                        self.recorded_hotkey_parts = []
                    
                    elif cmd == "set_hotkey_names":
                        names = msg[1]
                        self.target_hotkey_sequence = []
                        from src.config import HOTKEY
                        HOTKEY.clear()
                        
                        for n in names:
                            # Map common names back to pynput Key objects
                            k = None
                            if n == "CTRL": k = keyboard.Key.ctrl_l
                            elif n == "SHIFT": k = keyboard.Key.shift
                            elif n == "ALT": k = keyboard.Key.alt_l
                            elif n == "META": k = keyboard.Key.cmd
                            elif n.startswith("F") and len(n) > 1:
                                try: k = getattr(keyboard.Key, n.lower())
                                except: pass
                            
                            if not k:
                                # Try character
                                if len(n) == 1: k = keyboard.KeyCode.from_char(n.lower())
                                else:
                                    try: k = getattr(keyboard.Key, n.lower())
                                    except: pass
                            
                            if k: 
                                self.target_hotkey_sequence.append(k)
                                HOTKEY.add(k)
                        
                        logger.info(f"Hotkey updated to: {self.target_hotkey_sequence}")
                        
                    elif cmd == "matrix_connect":
                        # msg = ("matrix_connect", u_serv, u_user, u_tok, b_serv, b_user, b_tok)
                        try:
                            # User Client
                            if msg[1] and msg[2] and msg[3]:
                                self.matrix_client.connect(msg[1], msg[2], msg[3])
                            
                            # Bot Client
                            if len(msg) > 6 and msg[4] and msg[5] and msg[6]:
                                self.matrix_bot.connect(msg[4], msg[5], msg[6])
                        except Exception as e:
                            logger.error(f"Matrix connect dispatch error: {e}")
                    
                    elif cmd == "telegram_connect":
                        try:
                            if msg[1]: self.telegram.connect(msg[1])
                        except Exception as e:
                            logger.error(f"Telegram connect dispatch error: {e}")

                    elif cmd == "matrix_message":
                        msg_type, content, room_id = msg[1], msg[2], msg[3]
                        if msg_type == "text":
                            logger.info(f"Matrix Text Received: {content}")
                            self.gui.append_text(f"[Matrix]: {content}")
                            
                            # Type the text if Auto-Send is enabled
                            if self.gui.auto_send_var.get():
                                # For remote messages, do not use the stale active window handle from previous local recordings
                                self.send_text_to_window(content, use_stale_handle=False)
                                
                        elif msg_type == "audio":
                            logger.info(f"Matrix Audio Received: {content}")
                            self.processing_tasks_count += 1
                            self.gui.set_processing_state(True)
                            self.processing_queue.put({"type": "bot_audio", "source": "matrix", "file": content, "id": room_id})
                    
                    elif cmd == "telegram_message":
                        msg_type, content, chat_id = msg[1], msg[2], msg[3]
                        if msg_type == "text":
                            logger.info(f"Telegram Text Received: {content}")
                            self.gui.append_text(f"[Telegram]: {content}")
                            if self.gui.auto_send_var.get():
                                self.send_text_to_window(content, use_stale_handle=False)
                        elif msg_type == "audio":
                            logger.info(f"Telegram Audio Received: {content}")
                            self.processing_tasks_count += 1
                            self.gui.set_processing_state(True)
                            self.processing_queue.put({"type": "bot_audio", "source": "telegram", "file": content, "id": chat_id})
                
                    elif cmd == "processing_complete":
                        if self.processing_tasks_count > 0:
                            self.processing_tasks_count -= 1
                        self.gui.set_processing_state(self.processing_tasks_count > 0)

                    elif cmd == "set_mic":
                        try:
                            selection_idx = msg[1]
                            if 0 <= selection_idx < len(self.mic_devices):
                                real_idx = self.mic_devices[selection_idx][0]
                                name = self.mic_devices[selection_idx][1]
                                logger.info(f"Setting mic to: {name} (Index: {real_idx})")
                                self.audio.set_device(real_idx)
                        except Exception as e:
                            logger.error(f"Set mic error: {e}")

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

                elif msg == "scan_mics":
                    try:
                        devices = self.audio.get_devices()
                        self.mic_devices = devices
                        display_names = [f"{d[1]} ({d[0]})" for d in devices]
                        self.gui.update_mic_list(display_names)
                    except Exception as e:
                        logger.error(f"Scan mics error: {e}")
                
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
                    self.matrix_client.stop()
                    self.matrix_bot.stop()
                    self.telegram.stop()
                    os._exit(0)

        except Exception as e:
            logger.error(f"Coordinator error: {e}")
        
        self.gui.root.after(50, self.coordinator_loop)

    def on_press(self, key):
        if self.is_recording_hotkey:
            self.recorded_hotkey_parts.append(key)
            return

        # Check for multi-tap/sequence hotkey
        now = time.time()
        if now - self.last_tap_time > 0.5: # 500ms timeout between taps
            self.current_tap_sequence = []
        
        self.current_tap_sequence.append(key)
        self.last_tap_time = now
        
        # Check if sequence matches
        if self.target_hotkey_sequence and self.current_tap_sequence == self.target_hotkey_sequence:
            self.queue.put("toggle")
            self.current_tap_sequence = [] # Reset after trigger
            return

        # Only use chord logic if we don't have a multi-part sequence defined
        # This prevents "F8+F8" from triggering on the first "F8"
        if len(self.target_hotkey_sequence) <= 1:
            from src.config import HOTKEY
            if key in HOTKEY:
                self.current_keys.add(key)
                if all(k in self.current_keys for k in HOTKEY):
                    self.queue.put("toggle")

    def on_release(self, key):
        if self.is_recording_hotkey:
            if self.recorded_hotkey_parts:
                from src.config import HOTKEY
                HOTKEY.clear()
                HOTKEY.update(self.recorded_hotkey_parts)
                
                # Update UI display
                names = []
                for k in self.recorded_hotkey_parts:
                    if hasattr(k, 'name') and k.name: names.append(k.name.upper())
                    else: names.append(str(k).replace("Key.", "").replace("'", "").upper())
                
                display = "+".join(sorted(names))
                # MUST update UI via queue (main thread)
                self.queue.put(("update_hotkey_display", display))
                
                self.is_recording_hotkey = False
                self.recorded_hotkey_parts = []
            return

        self.current_keys.discard(key)

    def run(self):
        logger.info("VoiceInputter started.")
        self.network.start()
        self.sync_settings()
        
        # Initial scans in background to speed up startup
        threading.Thread(target=self.initial_scans, daemon=True).start()
        
        listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        listener.start()
        
        self.coordinator_loop()
        
        try:
            self.gui.root.mainloop()
        except KeyboardInterrupt:
            pass

    def initial_scans(self):
        self.queue.put("scan_mics")
        try:
            langs = self.comfy.get_languages()
            self.queue.put(("update_languages", langs))
        except Exception as e:
            logger.error(f"Background scan error: {e}")

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
