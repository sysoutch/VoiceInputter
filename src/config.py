from pynput import keyboard

# Configuration
COMFY_URL = "localhost:8188"
WORKFLOW_FILE = "stt.json"
INPUT_FILENAME = "input_audio.wav"
SAMPLE_RATE = 16000
VAD_THRESHOLD = 0.01
VAD_SILENCE_DURATION = 2.0
HOTKEY = {keyboard.Key.f9}
