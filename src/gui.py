import tkinter as tk
from tkinter import messagebox
import tkinter.ttk as ttk
import queue
import json
import os

class Overlay:
    def __init__(self, request_queue):
        self.queue = request_queue
        self.root = tk.Tk()
        self.root.title("VoiceInputter")
        
        # Load Secrets
        secrets = {}
        try:
            if os.path.exists("secrets.json"):
                with open("secrets.json", "r") as f:
                    secrets = json.load(f)
        except Exception as e:
            print(f"Error loading secrets: {e}")

        # Variables
        self.vad_auto_stop_var = tk.BooleanVar(value=True)
        self.vad_trigger_var = tk.BooleanVar(value=False)
        self.auto_process_var = tk.BooleanVar(value=True)
        self.auto_send_var = tk.BooleanVar(value=True)
        self.auto_enter_var = tk.BooleanVar(value=True)
        self.auto_enter_mode_var = tk.StringVar(value="enter")
        self.prefix_var = tk.BooleanVar(value=False)
        self.prefix_mode_var = tk.StringVar(value="- ")
        self.postfix_var = tk.BooleanVar(value=False)
        self.postfix_mode_var = tk.StringVar(value="space")
        self.target_window_var = tk.StringVar(value="<Active Window>")
        self.focus_target_var = tk.BooleanVar(value=True)
        self.always_on_top_var = tk.BooleanVar(value=True)
        self.network_client_var = tk.BooleanVar(value=False)
        self.matrix_mode_var = tk.BooleanVar(value=False)
        self.matrix_homeserver_var = tk.StringVar(value=secrets.get("matrix_homeserver", "https://matrix.org"))
        self.matrix_user_var = tk.StringVar(value=secrets.get("matrix_user", ""))
        self.matrix_token_var = tk.StringVar(value=secrets.get("matrix_token", ""))
        self.matrix_room_var = tk.StringVar(value=secrets.get("matrix_room", ""))
        
        # Bot Variables
        self.bot_matrix_homeserver_var = tk.StringVar(value=secrets.get("bot_matrix_homeserver", "https://matrix.org"))
        self.bot_matrix_user_var = tk.StringVar(value=secrets.get("bot_matrix_user", ""))
        self.bot_matrix_token_var = tk.StringVar(value=secrets.get("bot_matrix_token", ""))
        self.bot_matrix_room_var = tk.StringVar(value=secrets.get("bot_matrix_room", ""))
        
        self.vad_threshold_var = tk.StringVar(value="0.01")
        self.vad_silence_var = tk.StringVar(value="2.0")
        self.mic_device_var = tk.StringVar()
        
        # State
        self.drag_data = {"x": 0, "y": 0}
        self.resize_data = {}
        self.is_processing = False
        self.current_state = "READY"
        
        self.setup_window()
        self.setup_ui()
        self.update_ui_state("READY")

    def setup_window(self):
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.8)
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = 350
        height = 550
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Bind dragging (on root, but we override in widgets usually)
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.do_drag)

    def setup_ui(self):
        self.frame = tk.Frame(self.root, bg="#333333")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Header
        self.label = tk.Label(self.frame, text="Ready", font=("Arial", 12, "bold"), bg="#333333", fg="white")
        self.label.pack(pady=(5, 5))
        self.label.bind("<Button-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.do_drag)
        
        # Main Button
        self.action_btn = tk.Button(self.frame, text="RECORD", command=self.manual_toggle, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.action_btn.pack(pady=(0, 5), fill=tk.X, padx=10)
        
        # Text Area
        self.text_area = tk.Text(self.frame, height=4, font=("Arial", 10))
        self.text_area.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)
        
        # Recordings List
        self.list_frame = tk.Frame(self.frame, bg="#333333")
        self.list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.scrollbar = tk.Scrollbar(self.list_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.rec_list = tk.Listbox(self.list_frame, height=4, yscrollcommand=self.scrollbar.set, font=("Arial", 9), bg="#444444", fg="white", bd=0)
        self.rec_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.rec_list.yview)

        # List Controls
        self.ctrl_frame = tk.Frame(self.frame, bg="#333333")
        self.ctrl_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        
        self.btn_up = tk.Button(self.ctrl_frame, text="▲", command=lambda: self.move_rec(-1), width=3, bg="#555555", fg="white", font=("Arial", 8))
        self.btn_up.pack(side=tk.LEFT, padx=2)
        
        self.btn_down = tk.Button(self.ctrl_frame, text="▼", command=lambda: self.move_rec(1), width=3, bg="#555555", fg="white", font=("Arial", 8))
        self.btn_down.pack(side=tk.LEFT, padx=2)
        
        self.btn_del = tk.Button(self.ctrl_frame, text="🗑", command=self.delete_rec, width=3, bg="#F44336", fg="white", font=("Arial", 8))
        self.btn_del.pack(side=tk.LEFT, padx=2)
        
        self.btn_clear = tk.Button(self.ctrl_frame, text="CLEAR", command=self.clear_all_recs, width=6, bg="#D32F2F", fg="white", font=("Arial", 8))
        self.btn_clear.pack(side=tk.RIGHT, padx=2)

        # Send/Process Buttons
        self.send_btn = tk.Button(self.frame, text="SEND TEXT", command=self.manual_send, bg="#2196F3", fg="white", font=("Arial", 9, "bold"))
        self.send_btn.pack(pady=(0, 5), fill=tk.X, padx=10)

        self.process_btn = tk.Button(self.frame, text="PROCESS ALL", command=self.manual_process, bg="#FF9800", fg="white", font=("Arial", 9, "bold"))
        self.process_btn.pack(pady=(0, 5), fill=tk.X, padx=10)

        # Mic Selection
        mic_frame = tk.Frame(self.frame, bg="#333333")
        mic_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        tk.Label(mic_frame, text="Mic:", bg="#333333", fg="white").pack(side=tk.LEFT)
        
        self.combo_mic = ttk.Combobox(mic_frame, textvariable=self.mic_device_var, width=25, state="readonly")
        self.combo_mic.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.combo_mic.bind("<<ComboboxSelected>>", self.on_mic_selected)
        
        self.btn_refresh_mic = tk.Button(mic_frame, text="↻", command=self.manual_scan_mics, bg="#555555", fg="white", font=("Arial", 8), width=2)
        self.btn_refresh_mic.pack(side=tk.LEFT)

        # Options Frame
        opts_frame = tk.Frame(self.frame, bg="#333333")
        opts_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Auto-Stop
        astop_frame = tk.Frame(opts_frame, bg="#333333")
        astop_frame.pack(anchor="w", fill=tk.X)
        self.chk_auto_stop = tk.Checkbutton(astop_frame, text="Auto-Stop", var=self.vad_auto_stop_var, command=self.update_settings,
                                            bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_stop.pack(side=tk.LEFT)
        self.ent_silence = tk.Entry(astop_frame, textvariable=self.vad_silence_var, width=4, bg="#555555", fg="white", bd=0)
        self.ent_silence.pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(astop_frame, text="s", bg="#333333", fg="white").pack(side=tk.LEFT)
        
        # Voice Trigger
        vt_frame = tk.Frame(opts_frame, bg="#333333")
        vt_frame.pack(anchor="w", fill=tk.X)
        self.chk_voice_trigger = tk.Checkbutton(vt_frame, text="Record on Voice", var=self.vad_trigger_var, command=self.update_settings,
                                                bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_voice_trigger.pack(side=tk.LEFT)
        self.ent_threshold = tk.Entry(vt_frame, textvariable=self.vad_threshold_var, width=5, bg="#555555", fg="white", bd=0)
        self.ent_threshold.pack(side=tk.LEFT, padx=(5, 0))

        # Auto-Process
        ap_frame = tk.Frame(opts_frame, bg="#333333")
        ap_frame.pack(anchor="w", fill=tk.X)
        self.chk_auto_process = tk.Checkbutton(ap_frame, text="Auto-Process", var=self.auto_process_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_process.pack(side=tk.LEFT)
        
        # Auto-Send
        asend_frame = tk.Frame(opts_frame, bg="#333333")
        asend_frame.pack(anchor="w", fill=tk.X)
        self.chk_auto_send = tk.Checkbutton(asend_frame, text="Auto-Send", var=self.auto_send_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_send.pack(side=tk.LEFT)

        # Auto-Enter Row
        ae_frame = tk.Frame(opts_frame, bg="#333333")
        ae_frame.pack(anchor="w", fill=tk.X)
        self.chk_auto_enter = tk.Checkbutton(ae_frame, text="Auto-Enter", var=self.auto_enter_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_enter.pack(side=tk.LEFT)
        
        self.combo_auto_enter = ttk.Combobox(ae_frame, textvariable=self.auto_enter_mode_var, values=["enter", "shift+enter", "ctrl+enter"], width=10, state="readonly")
        self.combo_auto_enter.pack(side=tk.LEFT, padx=5)

        # Prefix Row
        p_frame = tk.Frame(opts_frame, bg="#333333")
        p_frame.pack(anchor="w", fill=tk.X)
        self.chk_prefix = tk.Checkbutton(p_frame, text="Prefix", var=self.prefix_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_prefix.pack(side=tk.LEFT)
        
        self.combo_prefix = ttk.Combobox(p_frame, textvariable=self.prefix_mode_var, values=["- ", "* ", "1. ", "a) "], width=10, state="readonly")
        self.combo_prefix.pack(side=tk.LEFT, padx=25)
        
        # Postfix Row
        pf_frame = tk.Frame(opts_frame, bg="#333333")
        pf_frame.pack(anchor="w", fill=tk.X)
        self.chk_postfix = tk.Checkbutton(pf_frame, text="Postfix", var=self.postfix_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_postfix.pack(side=tk.LEFT)
        
        self.combo_postfix = ttk.Combobox(pf_frame, textvariable=self.postfix_mode_var, values=["space", ", comma", ". dot"], width=10, state="readonly")
        self.combo_postfix.pack(side=tk.LEFT, padx=20)
        
        # Target Window Row
        target_frame = tk.Frame(opts_frame, bg="#333333")
        target_frame.pack(anchor="w", fill=tk.X)
        tk.Label(target_frame, text="Target:", bg="#333333", fg="white").pack(side=tk.LEFT)
        
        self.combo_target = ttk.Combobox(target_frame, textvariable=self.target_window_var, values=["<Active Window>"], width=20, state="readonly")
        self.combo_target.pack(side=tk.LEFT, padx=5)
        
        self.btn_refresh_target = tk.Button(target_frame, text="↻", command=self.manual_scan_windows, bg="#555555", fg="white", font=("Arial", 8), width=2)
        self.btn_refresh_target.pack(side=tk.LEFT)
        
        self.chk_focus = tk.Checkbutton(target_frame, text="Focus", var=self.focus_target_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_focus.pack(side=tk.LEFT, padx=5)
        
        self.btn_focus_now = tk.Button(target_frame, text="Go", command=self.manual_focus_target, bg="#555555", fg="white", font=("Arial", 8), width=3)
        self.btn_focus_now.pack(side=tk.LEFT)
        
        self.chk_network = tk.Checkbutton(opts_frame, text="Network Client", var=self.network_client_var, command=self.toggle_network_ui,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_network.pack(anchor="w")
        
        self.chk_matrix = tk.Checkbutton(opts_frame, text="Matrix Client", var=self.matrix_mode_var, command=self.toggle_matrix_ui,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_matrix.pack(anchor="w")

        # Network Frame
        self.network_frame = tk.Frame(self.frame, bg="#333333")
        self.combo_peers = ttk.Combobox(self.network_frame, values=[], width=15)
        self.combo_peers.pack(side=tk.LEFT, padx=5)
        self.btn_scan = tk.Button(self.network_frame, text="Scan", command=self.manual_scan, bg="#FF9800", fg="white", font=("Arial", 8))
        self.btn_scan.pack(side=tk.LEFT)

        # Matrix Frame
        self.matrix_frame = tk.Frame(self.frame, bg="#333333")
        
        # Notebook for User/Bot tabs
        self.matrix_notebook = ttk.Notebook(self.matrix_frame)
        self.matrix_notebook.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # User Tab
        self.user_tab = tk.Frame(self.matrix_notebook, bg="#333333")
        self.matrix_notebook.add(self.user_tab, text="User (Sender)")
        
        u_row1 = tk.Frame(self.user_tab, bg="#333333")
        u_row1.pack(fill=tk.X, pady=2)
        tk.Label(u_row1, text="Server:", bg="#333333", fg="white", width=6).pack(side=tk.LEFT)
        tk.Entry(u_row1, textvariable=self.matrix_homeserver_var, bg="#555555", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        u_row2 = tk.Frame(self.user_tab, bg="#333333")
        u_row2.pack(fill=tk.X, pady=2)
        tk.Label(u_row2, text="User:", bg="#333333", fg="white", width=6).pack(side=tk.LEFT)
        tk.Entry(u_row2, textvariable=self.matrix_user_var, bg="#555555", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        u_row3 = tk.Frame(self.user_tab, bg="#333333")
        u_row3.pack(fill=tk.X, pady=2)
        tk.Label(u_row3, text="Token:", bg="#333333", fg="white", width=6).pack(side=tk.LEFT)
        tk.Entry(u_row3, textvariable=self.matrix_token_var, show="*", bg="#555555", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        u_row4 = tk.Frame(self.user_tab, bg="#333333")
        u_row4.pack(fill=tk.X, pady=2)
        tk.Label(u_row4, text="Room:", bg="#333333", fg="white", width=6).pack(side=tk.LEFT)
        tk.Entry(u_row4, textvariable=self.matrix_room_var, bg="#555555", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Bot Tab
        self.bot_tab = tk.Frame(self.matrix_notebook, bg="#333333")
        self.matrix_notebook.add(self.bot_tab, text="Bot (Replier)")
        
        b_row1 = tk.Frame(self.bot_tab, bg="#333333")
        b_row1.pack(fill=tk.X, pady=2)
        tk.Label(b_row1, text="Server:", bg="#333333", fg="white", width=6).pack(side=tk.LEFT)
        tk.Entry(b_row1, textvariable=self.bot_matrix_homeserver_var, bg="#555555", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        b_row2 = tk.Frame(self.bot_tab, bg="#333333")
        b_row2.pack(fill=tk.X, pady=2)
        tk.Label(b_row2, text="User:", bg="#333333", fg="white", width=6).pack(side=tk.LEFT)
        tk.Entry(b_row2, textvariable=self.bot_matrix_user_var, bg="#555555", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        b_row3 = tk.Frame(self.bot_tab, bg="#333333")
        b_row3.pack(fill=tk.X, pady=2)
        tk.Label(b_row3, text="Token:", bg="#333333", fg="white", width=6).pack(side=tk.LEFT)
        tk.Entry(b_row3, textvariable=self.bot_matrix_token_var, show="*", bg="#555555", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        b_row4 = tk.Frame(self.bot_tab, bg="#333333")
        b_row4.pack(fill=tk.X, pady=2)
        tk.Label(b_row4, text="Room:", bg="#333333", fg="white", width=6).pack(side=tk.LEFT)
        tk.Entry(b_row4, textvariable=self.bot_matrix_room_var, bg="#555555", fg="white").pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_matrix_connect = tk.Button(self.matrix_frame, text="Connect All", command=self.connect_matrix, bg="#9C27B0", fg="white", font=("Arial", 9))
        self.btn_matrix_connect.pack(fill=tk.X, pady=5)

        # Close Button
        self.close_btn = tk.Button(self.frame, text="x", command=self.quit_app, bg="#333333", fg="white", font=("Arial", 8), bd=0)
        self.close_btn.place(relx=1.0, x=-2, y=0, anchor="ne")

        # Resize Grip
        self.sizegrip = ttk.Sizegrip(self.frame)
        self.sizegrip.place(relx=1.0, rely=1.0, anchor="se")
        self.sizegrip.bind("<ButtonPress-1>", self.start_resize)
        self.sizegrip.bind("<B1-Motion>", self.do_resize)

    # ... (Rest of logic) ...
    
    def update_ui_state(self, state):
        self.current_state = state
        self._refresh_ui()

    def set_processing_state(self, is_processing):
        self.is_processing = is_processing
        self._refresh_ui()

    def _refresh_ui(self):
        if self.current_state == "RECORDING":
            self.label.config(text="🔴 Recording...", bg="red", fg="white")
            self.frame.config(bg="red")
            self.action_btn.config(text="STOP", bg="white", fg="red", state="normal")
        elif self.current_state == "READY":
            if self.is_processing:
                self.label.config(text="⏳ Processing...", bg="#2196F3", fg="white")
                self.frame.config(bg="#2196F3")
                self.action_btn.config(text="RECORD", bg="#4CAF50", fg="white", state="normal")
            else:
                self.label.config(text="Ready", bg="#333333", fg="white")
                self.frame.config(bg="#333333")
                self.action_btn.config(text="RECORD", bg="#4CAF50", fg="white", state="normal")
        elif self.current_state == "PROCESSING":
            self.label.config(text="⏳ Processing...", bg="#2196F3", fg="white")
            self.frame.config(bg="#2196F3")
            self.action_btn.config(text="...", state="disabled", bg="#1976D2")

    def manual_toggle(self): self.queue.put("toggle")
    def manual_send(self):
        text = self.text_area.get("1.0", tk.END).strip()
        if text: self.queue.put(("send_text", text))
    def manual_process(self): self.queue.put("manual_process")
    def manual_scan(self): self.queue.put("scan_network")
    def manual_scan_mics(self): self.queue.put("scan_mics")
    def on_mic_selected(self, event):
        idx = self.combo_mic.current()
        if idx >= 0:
            self.queue.put(("set_mic", idx))
        else:
            # Try to find by value
            try:
                val = self.combo_mic.get()
                values = self.combo_mic['values']
                if val in values:
                    idx = values.index(val)
                    self.queue.put(("set_mic", idx))
            except Exception as e:
                pass
    def manual_scan_windows(self): self.queue.put("scan_windows")
    def manual_focus_target(self): self.queue.put("focus_target")
    def connect_matrix(self):
        self.queue.put(("matrix_connect", 
                        self.matrix_homeserver_var.get(),
                        self.matrix_user_var.get(),
                        self.matrix_token_var.get(),
                        self.bot_matrix_homeserver_var.get(),
                        self.bot_matrix_user_var.get(),
                        self.bot_matrix_token_var.get()))
    def quit_app(self):
        self.queue.put("quit")
    
    def toggle_network_ui(self):
        if self.network_client_var.get():
            self.network_frame.pack(fill=tk.X, padx=10, pady=5)
            self.manual_scan()
        else: self.network_frame.pack_forget()

    def toggle_matrix_ui(self):
        if self.matrix_mode_var.get():
            self.matrix_frame.pack(fill=tk.X, padx=10, pady=5)
        else: self.matrix_frame.pack_forget()

    def update_peers(self, peers):
        self.combo_peers['values'] = peers
        if peers and not self.combo_peers.get(): self.combo_peers.current(0)
    def get_selected_peer(self): return self.combo_peers.get()
    
    def update_mic_list(self, devices, current_index=None):
        self.combo_mic['values'] = devices
        if devices:
            if current_index is not None and 0 <= current_index < len(devices):
                self.combo_mic.current(current_index)
            elif not self.combo_mic.get():
                try: self.combo_mic.current(0)
                except: pass

    def update_window_list(self, windows):
        current = self.target_window_var.get()
        values = ["<Active Window>"] + windows
        self.combo_target['values'] = values
        
        if current in values:
            self.combo_target.set(current)
        else:
            self.combo_target.current(0)

    def show_process_btn(self): self.process_btn.pack(pady=(0, 5), fill=tk.X, padx=10)
    def hide_process_btn(self): self.process_btn.pack_forget()

    def ask_append_replace(self):
        # maybe "Append to last recording" vs "New recording"?
        # User wants to manage files. So always new recording?
        # But if they stop and start, it creates rec_1, rec_2.
        # So manual append/replace is maybe obsolete or just "Add to queue"?
        # I'll keep it simple: Always add to queue.
        # But wait, existing logic is "buffer audio".
        # I'll remove ask_append_replace from here and handle in main logic.
        return True

    def update_settings(self): pass

    def update_text(self, text):
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text)
    def append_text(self, text):
        current = self.text_area.get("1.0", tk.END).strip()
        if current: self.text_area.insert(tk.END, " " + text)
        else: self.text_area.insert(tk.END, text)
        self.text_area.see(tk.END)

    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def do_drag(self, event):
        x = self.root.winfo_x() - self.drag_data["x"] + event.x
        y = self.root.winfo_y() - self.drag_data["y"] + event.y
        self.root.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        self.resize_data = {"x": event.x_root, "y": event.y_root, 
                            "width": self.root.winfo_width(), "height": self.root.winfo_height()}

    def do_resize(self, event):
        delta_x = event.x_root - self.resize_data["x"]
        delta_y = event.y_root - self.resize_data["y"]
        new_width = max(200, self.resize_data["width"] + delta_x)
        new_height = max(200, self.resize_data["height"] + delta_y)
        self.root.geometry(f"{new_width}x{new_height}")

    # List Methods
    def update_rec_list(self, items, select_index=None):
        self.rec_list.delete(0, tk.END)
        for item in items:
            self.rec_list.insert(tk.END, item)
        
        if select_index is not None and 0 <= select_index < len(items):
            self.rec_list.selection_clear(0, tk.END)
            self.rec_list.selection_set(select_index)
            self.rec_list.activate(select_index)
            self.rec_list.see(select_index)
            
    def move_rec(self, direction):
        # Direction: -1 (up), 1 (down)
        sel = self.rec_list.curselection()
        if not sel: return
        index = sel[0]
        self.queue.put(("move_rec", index, direction))

    def delete_rec(self):
        sel = self.rec_list.curselection()
        if not sel: return
        index = sel[0]
        self.queue.put(("delete_rec", index))
        
    def clear_all_recs(self):
        self.queue.put("clear_all")
