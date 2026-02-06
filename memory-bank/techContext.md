# Tech Context: VoiceInputter

## Technologies Used
- **Language:** Python 3.12.
- **GUI:** PyQt6 (Native Qt bindings).
- **Backend:** ComfyUI (Local API).
- **Audio:** `sounddevice` (PortAudio wrapper) + `numpy`.
- **Audio Processing:** `pydub` (used for Telegram audio conversion).
- **Keyboard:** `pynput` (Hotkeys) + `pyautogui` (Typing).
- **Networking:** 
    - `python-telegram-bot` (Telegram integration).
    - `matrix-nio` (Matrix integration).
    - `requests` (Client) + `http.server` (Server) + `socket` (Discovery).
    - `websocket-client` (ComfyUI communication).

## Development Setup
- **OS:** Windows 11.
- **IDE:** Visual Studio Code.
- **Version Control:** Git.

## Technical Constraints
- **Threading:** PyQt6 event loop must run in the main thread. All background services (Audio, Keyboard, Network, Matrix, Telegram) communicate via a central thread-safe `queue`.
- **Audio Formats:** Local capture uses RAW/WAV; Telegram integration performs runtime conversion from OGG/Opus to WAV via `pydub`.
- **Startup:** Blocking discovery calls must be performed in background threads to maintain UI responsiveness.
- **High DPI:** Handled natively by PyQt6.

## Dependencies
- `PyQt6` (GUI)
- `python-telegram-bot` (Telegram)
- `matrix-nio` (Matrix)
- `pydub` (Audio conversion)
- `sounddevice`
- `numpy`
- `requests`
- `websocket-client`
- `pynput`
- `pyautogui`
- `pyperclip`
- `pygetwindow`
