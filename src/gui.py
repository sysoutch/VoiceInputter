from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QTextEdit, QListWidget, QCheckBox, 
                             QComboBox, QTabWidget, QLineEdit, QFrame, QScrollArea, QStyleFactory,
                             QDialog)
from PyQt6.QtCore import Qt, QTimer, QSize
from PyQt6.QtGui import QPalette, QColor, QFont, QIcon, QKeyEvent
import sys
import json
import os

# Compatibility Classes for Tkinter Variables
class BooleanVar:
    def __init__(self, value=False):
        self._value = value
        self.widget = None
        self._callback = None
    def get(self):
        if self.widget: return self.widget.isChecked()
        return self._value
    def set(self, value):
        self._value = value
        if self.widget: self.widget.setChecked(value)
    def attach(self, widget, callback=None):
        self.widget = widget
        self.widget.setChecked(self._value)
        if callback:
            self._callback = callback
            self.widget.stateChanged.connect(lambda: callback())

class StringVar:
    def __init__(self, value=""):
        self._value = value
        self.widget = None
    def get(self):
        if self.widget:
            if isinstance(self.widget, QLineEdit): return self.widget.text()
            if isinstance(self.widget, QComboBox): return self.widget.currentText()
        return self._value
    def set(self, value):
        self._value = value
        if self.widget:
            if isinstance(self.widget, QLineEdit): self.widget.setText(str(value))
            if isinstance(self.widget, QComboBox): 
                idx = self.widget.findText(str(value))
                if idx >= 0: self.widget.setCurrentIndex(idx)
                else: 
                    # If editable or just setting text to match existing
                    self.widget.setCurrentText(str(value))
    def attach(self, widget):
        self.widget = widget
        self.set(self._value)

class HotkeyRecorderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Hotkey")
        self.setFixedSize(300, 150)
        self.setModal(True)
        self.recorded_keys = set()
        self.recorded_names = []
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Press your hotkey combination..."), alignment=Qt.AlignmentFlag.AlignCenter)
        self.lbl_keys = QLabel("Waiting...")
        self.lbl_keys.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        layout.addWidget(self.lbl_keys, alignment=Qt.AlignmentFlag.AlignCenter)
        
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_box.addWidget(btn_cancel)
        self.btn_save = QPushButton("Save")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.accept)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def keyPressEvent(self, event: QKeyEvent):
        if event.isAutoRepeat(): return
        
        key = event.key()
        # Map Qt Key to something useful or just store the text
        name = event.text().upper()
        if not name or key < 32 or key > 126:
            # Special key
            if key == Qt.Key.Key_Control: name = "CTRL"
            elif key == Qt.Key.Key_Shift: name = "SHIFT"
            elif key == Qt.Key.Key_Alt: name = "ALT"
            elif key == Qt.Key.Key_Meta: name = "META"
            elif key == Qt.Key.Key_F1: name = "F1"
            elif key == Qt.Key.Key_F2: name = "F2"
            elif key == Qt.Key.Key_F3: name = "F3"
            elif key == Qt.Key.Key_F4: name = "F4"
            elif key == Qt.Key.Key_F5: name = "F5"
            elif key == Qt.Key.Key_F6: name = "F6"
            elif key == Qt.Key.Key_F7: name = "F7"
            elif key == Qt.Key.Key_F8: name = "F8"
            elif key == Qt.Key.Key_F9: name = "F9"
            elif key == Qt.Key.Key_F10: name = "F10"
            elif key == Qt.Key.Key_F11: name = "F11"
            elif key == Qt.Key.Key_F12: name = "F12"
            else: name = QKeyEvent.key_to_name(key).upper()
        
        # Allow multiple same keys (e.g. F8+F8)
        self.recorded_names.append(name)
        self.lbl_keys.setText("+".join(self.recorded_names))
        self.btn_save.setEnabled(True)
        event.accept()

class Overlay(QMainWindow):
    def __init__(self, request_queue):
        # Create Application if it doesn't exist
        self.app = QApplication.instance() or QApplication(sys.argv)
        super().__init__()
        
        self.queue = request_queue
        
        # Window Setup
        self.setWindowTitle("VoiceInputter")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(380, 750)
        
        # Load Secrets
        secrets = {}
        try:
            if os.path.exists("secrets.json"):
                with open("secrets.json", "r") as f:
                    secrets = json.load(f)
        except: pass

        # Variables
        self.vad_auto_stop_var = BooleanVar(True)
        self.vad_trigger_var = BooleanVar(False)
        self.auto_process_var = BooleanVar(True)
        self.auto_send_var = BooleanVar(True)
        self.auto_enter_var = BooleanVar(True)
        self.auto_enter_mode_var = StringVar("enter")
        self.prefix_var = BooleanVar(False)
        self.prefix_mode_var = StringVar("- ")
        self.postfix_var = BooleanVar(False)
        self.postfix_mode_var = StringVar("space")
        self.target_window_var = StringVar("<Active Window>")
        self.focus_target_var = BooleanVar(True)
        self.network_client_var = BooleanVar(False)
        self.matrix_mode_var = BooleanVar(False)
        self.telegram_mode_var = BooleanVar(False)
        
        self.matrix_homeserver_var = StringVar(secrets.get("matrix_homeserver", "https://matrix.org"))
        self.matrix_user_var = StringVar(secrets.get("matrix_user", ""))
        self.matrix_token_var = StringVar(secrets.get("matrix_token", ""))
        self.matrix_room_var = StringVar(secrets.get("matrix_room", ""))
        
        self.bot_matrix_homeserver_var = StringVar(secrets.get("bot_matrix_homeserver", "https://matrix.org"))
        self.bot_matrix_user_var = StringVar(secrets.get("bot_matrix_user", ""))
        self.bot_matrix_token_var = StringVar(secrets.get("bot_matrix_token", ""))
        self.bot_matrix_room_var = StringVar(secrets.get("bot_matrix_room", ""))
        self.telegram_token_var = StringVar(secrets.get("telegram_token", ""))
        
        self.vad_threshold_var = StringVar("0.01")
        self.vad_silence_var = StringVar("2.0")
        self.mic_device_var = StringVar("")
        self.language_var = StringVar("auto")
        self.hotkey_var = StringVar("F9")
        
        self.current_state = "READY"
        self.is_processing = False
        self.drag_pos = None

        self.apply_dark_theme()
        self.setup_ui()
        
        # Shim for voice_inputter
        self.root = self 

    def apply_dark_theme(self):
        self.app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        self.app.setPalette(palette)
        
        # Stylesheet for specific widgets
        self.setStyleSheet("""
            QMainWindow { background: #2b2b2b; border-radius: 10px; }
            QFrame#MainFrame { background: #2b2b2b; border-radius: 10px; border: 1px solid #444; }
            QLabel { color: white; font-family: Segoe UI; }
            QPushButton { background-color: #3c3c3c; color: white; border: 1px solid #555; padding: 5px; border-radius: 4px; }
            QPushButton:hover { background-color: #505050; }
            QPushButton:pressed { background-color: #2c2c2c; }
            QTextEdit, QListWidget { background-color: #1e1e1e; border: 1px solid #333; color: white; border-radius: 4px; }
            QLineEdit { background-color: #1e1e1e; border: 1px solid #333; color: white; padding: 2px; border-radius: 2px; }
            QComboBox { background-color: #3c3c3c; color: white; border: 1px solid #555; border-radius: 2px; }
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #3c3c3c; color: white; padding: 5px 10px; }
            QTabBar::tab:selected { background: #505050; }
        """)

    def setup_ui(self):
        self.central_widget = QWidget()
        self.central_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCentralWidget(self.central_widget)
        
        # Main Layout (Vertical)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Container Frame (for border/radius)
        self.container = QFrame()
        self.container.setObjectName("MainFrame")
        self.container_layout = QVBoxLayout(self.container)
        self.main_layout.addWidget(self.container)
        
        # --- Status Header ---
        self.lbl_status = QLabel("Ready")
        self.lbl_status.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.container_layout.addWidget(self.lbl_status)
        
        # --- Main Action ---
        self.btn_record = QPushButton("RECORD")
        self.btn_record.setFixedHeight(45)
        self.btn_record.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_record.setStyleSheet("background-color: #2e7d32;")
        self.btn_record.clicked.connect(self.manual_toggle)
        self.container_layout.addWidget(self.btn_record)
        
        # --- Text Area ---
        self.txt_output = QTextEdit()
        self.txt_output.setMinimumHeight(45)
        self.container_layout.addWidget(self.txt_output, 2) # Expand factor 2
        
        # --- Recordings List ---
        self.container_layout.addWidget(QLabel("Recordings:"))
        self.list_recordings = QListWidget()
        self.list_recordings.setMinimumHeight(45)
        self.container_layout.addWidget(self.list_recordings, 1) # Expand factor 1
        
        # List Controls
        list_ctrl_layout = QHBoxLayout()
        btn_up = QPushButton("▲")
        btn_up.setFixedWidth(30)
        btn_up.clicked.connect(lambda: self.move_rec(-1))
        
        btn_down = QPushButton("▼")
        btn_down.setFixedWidth(30)
        btn_down.clicked.connect(lambda: self.move_rec(1))
        
        btn_del = QPushButton("🗑")
        btn_del.setFixedWidth(30)
        btn_del.clicked.connect(self.delete_rec)
        
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(self.clear_all_recs)
        
        list_ctrl_layout.addWidget(btn_up)
        list_ctrl_layout.addWidget(btn_down)
        list_ctrl_layout.addWidget(btn_del)
        list_ctrl_layout.addStretch()
        list_ctrl_layout.addWidget(btn_clear)
        self.container_layout.addLayout(list_ctrl_layout)
        
        # --- Send/Process ---
        action_layout = QHBoxLayout()
        self.btn_send = QPushButton("Send Text")
        self.btn_send.clicked.connect(self.manual_send)
        
        self.btn_process = QPushButton("Process All")
        self.btn_process.clicked.connect(self.manual_process)
        self.btn_process.setStyleSheet("background-color: #ef6c00;")
        
        action_layout.addWidget(self.btn_send)
        action_layout.addWidget(self.btn_process)
        self.container_layout.addLayout(action_layout)
        
        # --- Settings Tabs ---
        self.tabs = QTabWidget()
        self.container_layout.addWidget(self.tabs)
        
        # General Tab
        self.tab_gen = QWidget()
        self.tabs.addTab(self.tab_gen, "General")
        gen_layout = QVBoxLayout(self.tab_gen)
        
        # Mic
        mic_layout = QHBoxLayout()
        mic_layout.addWidget(QLabel("Mic:"))
        self.cmb_mic = QComboBox()
        self.mic_device_var.attach(self.cmb_mic)
        self.cmb_mic.currentIndexChanged.connect(self.on_mic_selected) # Custom handler
        mic_layout.addWidget(self.cmb_mic, 1)
        btn_refresh_mic = QPushButton("↻")
        btn_refresh_mic.setFixedWidth(24)
        btn_refresh_mic.clicked.connect(self.manual_scan_mics)
        mic_layout.addWidget(btn_refresh_mic)
        gen_layout.addLayout(mic_layout)
        
        # VAD Auto-Stop Row (Side by Side)
        vad_stop_layout = QHBoxLayout()
        chk_stop = QCheckBox("Auto-Stop")
        self.vad_auto_stop_var.attach(chk_stop, self.update_settings)
        vad_stop_layout.addWidget(chk_stop)
        
        vad_stop_layout.addStretch()
        vad_stop_layout.addWidget(QLabel("Silence (s):"))
        txt_sil = QLineEdit()
        self.vad_silence_var.attach(txt_sil)
        txt_sil.setFixedWidth(50)
        vad_stop_layout.addWidget(txt_sil)
        gen_layout.addLayout(vad_stop_layout)
        
        # VAD Trigger Row (Side by Side)
        vad_trig_layout = QHBoxLayout()
        chk_trig = QCheckBox("Record on Voice")
        self.vad_trigger_var.attach(chk_trig, self.update_settings)
        vad_trig_layout.addWidget(chk_trig)
        
        vad_trig_layout.addStretch()
        vad_trig_layout.addWidget(QLabel("Threshold:"))
        txt_th = QLineEdit()
        self.vad_threshold_var.attach(txt_th)
        txt_th.setFixedWidth(50)
        vad_trig_layout.addWidget(txt_th)
        gen_layout.addLayout(vad_trig_layout)
        
        chk_proc = QCheckBox("Auto-Process")
        self.auto_process_var.attach(chk_proc)
        gen_layout.addWidget(chk_proc)

        # Language Selection
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.cmb_lang = QComboBox()
        self.language_var.attach(self.cmb_lang)
        lang_layout.addWidget(self.cmb_lang, 1)
        gen_layout.addLayout(lang_layout)

        chk_send = QCheckBox("Auto-Send")
        self.auto_send_var.attach(chk_send)
        gen_layout.addWidget(chk_send)

        # Target Selection
        t_layout = QHBoxLayout()
        t_layout.addWidget(QLabel("Target:"))
        self.cmb_target = QComboBox()
        self.cmb_target.addItem("<Active Window>")
        self.target_window_var.attach(self.cmb_target)
        t_layout.addWidget(self.cmb_target, 1)
        btn_refresh_t = QPushButton("↻")
        btn_refresh_t.setFixedWidth(24)
        btn_refresh_t.clicked.connect(self.manual_scan_windows)
        t_layout.addWidget(btn_refresh_t)
        gen_layout.addLayout(t_layout)
        
        foc_layout = QHBoxLayout()
        chk_foc = QCheckBox("Focus Target")
        self.focus_target_var.attach(chk_foc)
        foc_layout.addWidget(chk_foc)
        btn_foc = QPushButton("Focus Now")
        btn_foc.clicked.connect(self.manual_focus_target)
        foc_layout.addWidget(btn_foc)
        gen_layout.addLayout(foc_layout)

        gen_layout.addStretch()

        # Text Tab
        tab_text = QWidget()
        self.tabs.addTab(tab_text, "Text")
        text_layout = QVBoxLayout(tab_text)
        
        # Auto Enter
        ae_layout = QHBoxLayout()
        chk_ae = QCheckBox("Enter")
        self.auto_enter_var.attach(chk_ae)
        ae_layout.addWidget(chk_ae)
        cmb_ae = QComboBox()
        cmb_ae.addItems(["enter", "shift+enter", "ctrl+enter"])
        self.auto_enter_mode_var.attach(cmb_ae)
        ae_layout.addWidget(cmb_ae)
        text_layout.addLayout(ae_layout)
        
        # Prefix
        p_layout = QHBoxLayout()
        chk_p = QCheckBox("Prefix")
        self.prefix_var.attach(chk_p)
        p_layout.addWidget(chk_p)
        cmb_p = QComboBox()
        cmb_p.addItems(["- ", "* ", "1. ", "a) "])
        self.prefix_mode_var.attach(cmb_p)
        p_layout.addWidget(cmb_p)
        text_layout.addLayout(p_layout)
        
        # Postfix
        pf_layout = QHBoxLayout()
        chk_pf = QCheckBox("Postfix")
        self.postfix_var.attach(chk_pf)
        pf_layout.addWidget(chk_pf)
        cmb_pf = QComboBox()
        cmb_pf.addItems(["space", ", comma", ". dot"])
        self.postfix_mode_var.attach(cmb_pf)
        pf_layout.addWidget(cmb_pf)
        text_layout.addLayout(pf_layout)
        
        text_layout.addStretch()

        # Hotkeys Tab
        self.tab_hk = QWidget()
        self.tabs.addTab(self.tab_hk, "Hotkeys")
        hk_layout = QVBoxLayout(self.tab_hk)
        
        hk_row = QHBoxLayout()
        hk_row.addWidget(QLabel("Global Toggle:"))
        self.lbl_hk = QLabel("F9")
        self.lbl_hk.setStyleSheet("background: #1e1e1e; padding: 5px; border-radius: 3px;")
        hk_row.addWidget(self.lbl_hk)
        self.btn_hk_record = QPushButton("Record")
        self.btn_hk_record.clicked.connect(self.record_hotkey)
        hk_row.addWidget(self.btn_hk_record)
        hk_layout.addLayout(hk_row)
        hk_layout.addStretch()
        
        # Connect Tab
        tab_conn = QWidget()
        self.tabs.addTab(tab_conn, "Connect")
        conn_layout = QVBoxLayout(tab_conn)
        
        chk_net = QCheckBox("Network Client")
        self.network_client_var.attach(chk_net, self.toggle_network_ui)
        conn_layout.addWidget(chk_net)
        
        self.network_frame = QWidget()
        net_layout = QHBoxLayout(self.network_frame)
        net_layout.setContentsMargins(0,0,0,0)
        self.cmb_peers = QComboBox()
        net_layout.addWidget(self.cmb_peers, 1)
        btn_scan = QPushButton("Scan")
        btn_scan.clicked.connect(self.manual_scan)
        net_layout.addWidget(btn_scan)
        conn_layout.addWidget(self.network_frame)
        self.network_frame.setVisible(False)
        
        chk_mat = QCheckBox("Matrix Integration")
        self.matrix_mode_var.attach(chk_mat, self.toggle_matrix_ui)
        conn_layout.addWidget(chk_mat)
        
        chk_tg = QCheckBox("Telegram Bot")
        self.telegram_mode_var.attach(chk_tg, self.toggle_telegram_ui)
        conn_layout.addWidget(chk_tg)
        
        # Telegram Configuration Frame
        self.telegram_frame = QWidget()
        tg_layout = QVBoxLayout(self.telegram_frame)
        tg_layout.setContentsMargins(0,0,0,0)
        
        tg_row = QHBoxLayout()
        tg_row.addWidget(QLabel("Token:"))
        self.txt_tg_token = QLineEdit()
        self.telegram_token_var.attach(self.txt_tg_token)
        self.txt_tg_token.setEchoMode(QLineEdit.EchoMode.Password)
        tg_row.addWidget(self.txt_tg_token)
        tg_layout.addLayout(tg_row)
        
        btn_tg_con = QPushButton("Connect Telegram")
        btn_tg_con.clicked.connect(self.connect_telegram)
        tg_layout.addWidget(btn_tg_con)
        
        conn_layout.addWidget(self.telegram_frame)
        self.telegram_frame.setVisible(False)
        
        # Matrix Configuration Frame (Embedded)
        self.matrix_frame = QWidget()
        mat_layout = QVBoxLayout(self.matrix_frame)
        mat_layout.setContentsMargins(0, 0, 0, 0)
        
        self.matrix_tabs = QTabWidget()
        mat_layout.addWidget(self.matrix_tabs)
        
        def make_tab(server_var, user_var, token_var, room_var):
            w = QWidget()
            l = QVBoxLayout(w)
            l.setContentsMargins(5, 5, 5, 5)
            
            def row(lbl, var, echo=QLineEdit.EchoMode.Normal):
                h = QHBoxLayout()
                h.addWidget(QLabel(lbl))
                e = QLineEdit()
                var.attach(e)
                e.setEchoMode(echo)
                h.addWidget(e)
                l.addLayout(h)
                
            row("Server:", server_var)
            row("User:", user_var)
            row("Token:", token_var, QLineEdit.EchoMode.Password)
            row("Room:", room_var)
            l.addStretch()
            return w
            
        self.matrix_tabs.addTab(make_tab(self.matrix_homeserver_var, self.matrix_user_var, self.matrix_token_var, self.matrix_room_var), "Client (User)")
        self.matrix_tabs.addTab(make_tab(self.bot_matrix_homeserver_var, self.bot_matrix_user_var, self.bot_matrix_token_var, self.bot_matrix_room_var), "Server (Bot)")
        
        btn_con = QPushButton("Connect Matrix")
        btn_con.clicked.connect(self.connect_matrix)
        mat_layout.addWidget(btn_con)
        
        conn_layout.addWidget(self.matrix_frame)
        self.matrix_frame.setVisible(False)
        
        conn_layout.addStretch()

    # --- Interaction Logic ---
    # Standard OS window handles move/resize

    # --- API Implementation ---
    def after(self, ms, func):
        QTimer.singleShot(ms, func)

    def mainloop(self):
        self.show()
        sys.exit(self.app.exec())

    def update_ui_state(self, state):
        self.current_state = state
        self._refresh_ui()

    def set_processing_state(self, is_processing):
        self.is_processing = is_processing
        self._refresh_ui()

    def _refresh_ui(self):
        if self.current_state == "RECORDING":
            self.lbl_status.setText("🔴 Recording...")
            self.lbl_status.setStyleSheet("color: #ff5252;")
            self.btn_record.setText("STOP")
            self.btn_record.setStyleSheet("background-color: #d32f2f;")
        elif self.current_state == "READY":
            if self.is_processing:
                self.lbl_status.setText("⏳ Processing...")
                self.lbl_status.setStyleSheet("color: #448aff;")
                self.btn_record.setText("RECORD")
                self.btn_record.setStyleSheet("background-color: #2e7d32;")
                self.btn_record.setEnabled(True)
            else:
                self.lbl_status.setText("Ready")
                self.lbl_status.setStyleSheet("color: white;")
                self.btn_record.setText("RECORD")
                self.btn_record.setStyleSheet("background-color: #2e7d32;")
                self.btn_record.setEnabled(True)
        elif self.current_state == "PROCESSING":
             self.lbl_status.setText("⏳ Processing...")
             self.lbl_status.setStyleSheet("color: #448aff;")
             self.btn_record.setText("...")
             self.btn_record.setEnabled(False)
             self.btn_record.setStyleSheet("background-color: #555;")

    # Queue Actions
    def manual_toggle(self): self.queue.put("toggle")
    def manual_send(self): 
        t = self.txt_output.toPlainText().strip()
        if t: self.queue.put(("send_text", t))
    def manual_process(self): self.queue.put("manual_process")
    def manual_scan(self): self.queue.put("scan_network")
    def manual_scan_mics(self): self.queue.put("scan_mics")
    def manual_scan_windows(self): self.queue.put("scan_windows")
    def manual_focus_target(self): self.queue.put("focus_target")
    def quit_app(self): self.queue.put("quit")
    
    def connect_matrix(self):
        self.queue.put(("matrix_connect", 
                        self.matrix_homeserver_var.get(), self.matrix_user_var.get(), self.matrix_token_var.get(),
                        self.bot_matrix_homeserver_var.get(), self.bot_matrix_user_var.get(), self.bot_matrix_token_var.get()))

    def update_settings(self): pass # Triggers logic via variables if needed

    def toggle_network_ui(self):
        self.network_frame.setVisible(self.network_client_var.get())
        if self.network_client_var.get(): self.manual_scan()
        
    def toggle_matrix_ui(self):
        self.matrix_frame.setVisible(self.matrix_mode_var.get())

    def toggle_telegram_ui(self):
        self.telegram_frame.setVisible(self.telegram_mode_var.get())

    def connect_telegram(self):
        self.queue.put(("telegram_connect", self.telegram_token_var.get()))

    # Lists
    def update_rec_list(self, items, select_index=None):
        self.list_recordings.clear()
        self.list_recordings.addItems(items)
        if select_index is not None and 0 <= select_index < len(items):
            self.list_recordings.setCurrentRow(select_index)

    def update_text(self, text):
        self.txt_output.setText(text)
    
    def append_text(self, text):
        self.txt_output.append(text)

    def update_peers(self, peers):
        self.cmb_peers.clear()
        self.cmb_peers.addItems(peers)

    def update_languages(self, languages):
        current = self.cmb_lang.currentText()
        self.cmb_lang.clear()
        self.cmb_lang.addItems(languages)
        idx = self.cmb_lang.findText(current)
        if idx >= 0: self.cmb_lang.setCurrentIndex(idx)
        elif "auto" in languages: self.cmb_lang.setCurrentIndex(languages.index("auto"))

    def update_mic_list(self, devices, current_index=None):
        self.cmb_mic.blockSignals(True)
        self.cmb_mic.clear()
        self.cmb_mic.addItems(devices)
        if current_index is not None and 0 <= current_index < len(devices):
            self.cmb_mic.setCurrentIndex(current_index)
        self.cmb_mic.blockSignals(False)

    def update_window_list(self, windows):
        current = self.cmb_target.currentText()
        self.cmb_target.clear()
        items = ["<Active Window>"] + windows
        self.cmb_target.addItems(items)
        idx = self.cmb_target.findText(current)
        if idx >= 0: self.cmb_target.setCurrentIndex(idx)

    def on_mic_selected(self, index):
        self.queue.put(("set_mic", index))

    def record_hotkey(self):
        dlg = HotkeyRecorderDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            display = "+".join(dlg.recorded_names)
            self.lbl_hk.setText(display)
            # Pass names to voice_inputter to map to pynput keys
            self.queue.put(("set_hotkey_names", dlg.recorded_names))

    def update_hotkey_display(self, text):
        self.lbl_hk.setText(text)
        self.btn_hk_record.setText("Record")
        self.btn_hk_record.setEnabled(True)

    def move_rec(self, direction):
        row = self.list_recordings.currentRow()
        if row >= 0: self.queue.put(("move_rec", row, direction))

    def delete_rec(self):
        row = self.list_recordings.currentRow()
        if row >= 0: self.queue.put(("delete_rec", row))

    def clear_all_recs(self):
        self.queue.put("clear_all")

    def show_process_btn(self): pass
    def hide_process_btn(self): pass
