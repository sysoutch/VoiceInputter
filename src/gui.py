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
        self.always_on_top_var = tk.BooleanVar(value=True)
        self.network_client_var = tk.BooleanVar(value=False)
        
        # State
        self.drag_data = {"x": 0, "y": 0}
        
        self.setup_window()
        self.setup_ui()
        self.update_ui_state("READY")

    def setup_window(self):
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.8)
        
        screen_width = self.root.winfo_screenwidth()
        self.root.geometry(f"300x400+{screen_width-320}+20")
        
        # Bind dragging
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.do_drag)

    def setup_ui(self):
        self.frame = tk.Frame(self.root, bg="#333333")
        self.frame.pack(fill=tk.BOTH, expand=True)

        # Header / Status
        self.label = tk.Label(self.frame, text="Ready", font=("Arial", 12, "bold"), bg="#333333", fg="white")
        self.label.pack(pady=(5, 5))
        
        # Main Button
        self.action_btn = tk.Button(self.frame, text="RECORD", command=self.manual_toggle, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.action_btn.pack(pady=(0, 5), fill=tk.X, padx=10)
        
        # Text Area for Modification
        self.text_area = tk.Text(self.frame, height=5, width=25, font=("Arial", 10))
        self.text_area.pack(pady=5, padx=10)
        
        # Send Button (visible when not auto-entering)
        self.send_btn = tk.Button(self.frame, text="SEND TEXT", command=self.manual_send, bg="#2196F3", fg="white", font=("Arial", 9, "bold"))
        self.send_btn.pack(pady=(0, 5), fill=tk.X, padx=10)

        # Process Button (hidden by default)
        self.process_btn = tk.Button(self.frame, text="PROCESS TEXT", command=self.manual_process, bg="#FF9800", fg="white", font=("Arial", 9, "bold"))

        # Options Frame
        opts_frame = tk.Frame(self.frame, bg="#333333")
        opts_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Toggles
        # Auto-Stop Row with Input
        as_frame = tk.Frame(opts_frame, bg="#333333")
        as_frame.pack(anchor="w", fill=tk.X)
        
        self.chk_auto_stop = tk.Checkbutton(as_frame, text="Auto-Stop", var=self.vad_auto_stop_var, command=self.update_settings,
                                            bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_stop.pack(side=tk.LEFT)

        self.vad_silence_var = tk.StringVar(value="2.0")
        self.ent_silence = tk.Entry(as_frame, textvariable=self.vad_silence_var, width=4, bg="#555555", fg="white", bd=0)
        self.ent_silence.pack(side=tk.LEFT, padx=(5, 0))
        tk.Label(as_frame, text="s", bg="#333333", fg="white").pack(side=tk.LEFT)
        
        vt_frame = tk.Frame(opts_frame, bg="#333333")
        vt_frame.pack(anchor="w", fill=tk.X)
        
        self.chk_voice_trigger = tk.Checkbutton(vt_frame, text="Record on Voice", var=self.vad_trigger_var, command=self.update_settings,
                                                bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_voice_trigger.pack(side=tk.LEFT)

        self.vad_threshold_var = tk.StringVar(value="0.01")
        self.ent_threshold = tk.Entry(vt_frame, textvariable=self.vad_threshold_var, width=5, bg="#555555", fg="white", bd=0)
        self.ent_threshold.pack(side=tk.LEFT, padx=(5, 0))

        self.chk_auto_process = tk.Checkbutton(opts_frame, text="Auto-Process", var=self.auto_process_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_process.pack(anchor="w")

        self.chk_auto_enter = tk.Checkbutton(opts_frame, text="Auto-Enter", var=self.auto_enter_var,
                                             bg="#333333", fg="white", selectcolor="#555555", activebackground="#333333", activeforeground="white")
        self.chk_auto_enter.pack(anchor="w")
        
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

    def update_ui_state(self, state):
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
        self.queue.put("toggle")

    def manual_send(self):
        text = self.text_area.get("1.0", tk.END).strip()
        if text:
            self.queue.put(("send_text", text))

    def manual_process(self):
        self.queue.put("manual_process")

    def manual_scan(self):
        self.queue.put("scan_network")

    def toggle_network_ui(self):
        if self.network_client_var.get():
            self.network_frame.pack(fill=tk.X, padx=10, pady=5)
            self.manual_scan()
        else:
            self.network_frame.pack_forget()

    def update_peers(self, peers):
        self.combo_peers['values'] = peers
        if peers and not self.combo_peers.get():
            self.combo_peers.current(0)
            
    def get_selected_peer(self):
        return self.combo_peers.get()

    def show_process_btn(self):
        self.process_btn.pack(pady=(0, 5), fill=tk.X, padx=10)
    
    def hide_process_btn(self):
        self.process_btn.pack_forget()

    def ask_append_replace(self):
        return messagebox.askyesno("Audio Pending", "Audio already exists. Append to it?\n(Yes=Append, No=Replace)", parent=self.root)

    def update_settings(self):
        # We push settings to queue so main logic can pick them up?
        # Or main logic polls UI variables? UI runs in main thread.
        # Main logic (Coordinator) should poll this.
        pass

    def update_text(self, text):
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text)

    def append_text(self, text):
        current = self.text_area.get("1.0", tk.END).strip()
        if current:
            self.text_area.insert(tk.END, " " + text)
        else:
            self.text_area.insert(tk.END, text)
        self.text_area.see(tk.END)

    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def do_drag(self, event):
        x = self.root.winfo_x() - self.drag_data["x"] + event.x
        y = self.root.winfo_y() - self.drag_data["y"] + event.y
        self.root.geometry(f"+{x}+{y}")

    def quit_app(self):
        self.root.quit()
        self.queue.put("quit")
