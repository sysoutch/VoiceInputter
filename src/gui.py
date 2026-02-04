import tkinter as tk
from tkinter import messagebox
import tkinter.ttk as ttk
import queue

class Overlay:
    def __init__(self, request_queue):
        self.queue = request_queue
        self.root = tk.Tk()
        
        # Variables
        self.vad_auto_stop_var = tk.BooleanVar(value=True)
        self.vad_trigger_var = tk.BooleanVar(value=False)
        self.auto_process_var = tk.BooleanVar(value=True)
        self.auto_enter_var = tk.BooleanVar(value=True)
        self.auto_enter_mode_var = tk.StringVar(value="enter")
        self.prefix_var = tk.BooleanVar(value=False)
        self.prefix_mode_var = tk.StringVar(value="- ")
        self.always_on_top_var = tk.BooleanVar(value=True)
        self.network_client_var = tk.BooleanVar(value=False)
        self.vad_threshold_var = tk.StringVar(value="0.01")
        self.vad_silence_var = tk.StringVar(value="2.0")
        
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
        self.text_area = tk.Text(self.frame, height=4, width=25, font=("Arial", 10))
        self.text_area.pack(pady=5, padx=10)
        
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

        # Options Frame
        opts_frame = tk.Frame(self.frame, bg="#333333")
        opts_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Auto-Stop
        as_frame = tk.Frame(opts_frame, bg="#333333")
        as_frame.pack(anchor="w", fill=tk.X)
        self.chk_auto_stop = tk.Checkbutton(as_frame, text="Auto-Stop", var=self.vad_auto_stop_var, command=self.update_settings,
                                            bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_stop.pack(side=tk.LEFT)
        self.ent_silence = tk.Entry(as_frame, textvariable=self.vad_silence_var, width=4, bg="#555555", fg="white", bd=0)
        self.ent_silence.pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(as_frame, text="s", bg="#333333", fg="white").pack(side=tk.LEFT)
        
        # Voice Trigger
        vt_frame = tk.Frame(opts_frame, bg="#333333")
        vt_frame.pack(anchor="w", fill=tk.X)
        self.chk_voice_trigger = tk.Checkbutton(vt_frame, text="Record on Voice", var=self.vad_trigger_var, command=self.update_settings,
                                                bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_voice_trigger.pack(side=tk.LEFT)
        self.ent_threshold = tk.Entry(vt_frame, textvariable=self.vad_threshold_var, width=5, bg="#555555", fg="white", bd=0)
        self.ent_threshold.pack(side=tk.LEFT, padx=(5, 0))

        # Toggles
        self.chk_auto_process = tk.Checkbutton(opts_frame, text="Auto-Process", var=self.auto_process_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_process.pack(anchor="w")

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
        
        self.chk_network = tk.Checkbutton(opts_frame, text="Network Client", var=self.network_client_var, command=self.toggle_network_ui,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_network.pack(anchor="w")

        # Network Frame
        self.network_frame = tk.Frame(self.frame, bg="#333333")
        self.combo_peers = ttk.Combobox(self.network_frame, values=[], width=15)
        self.combo_peers.pack(side=tk.LEFT, padx=5)
        self.btn_scan = tk.Button(self.network_frame, text="Scan", command=self.manual_scan, bg="#FF9800", fg="white", font=("Arial", 8))
        self.btn_scan.pack(side=tk.LEFT)

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
    def quit_app(self):
        self.queue.put("quit")
    
    def toggle_network_ui(self):
        if self.network_client_var.get():
            self.network_frame.pack(fill=tk.X, padx=10, pady=5)
            self.manual_scan()
        else: self.network_frame.pack_forget()

    def update_peers(self, peers):
        self.combo_peers['values'] = peers
        if peers and not self.combo_peers.get(): self.combo_peers.current(0)
    def get_selected_peer(self): return self.combo_peers.get()

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
