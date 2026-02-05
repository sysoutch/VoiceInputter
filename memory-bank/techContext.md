# Tech Context: VoiceInputter

## Technologies Used
- **Language:** Python 3.12.
- **Runtime:** Standard Python Interpreter.
- **GUI:** **PyQt6** (Native Qt bindings).
- **Backend:** ComfyUI (Local API).
- **Audio:** `sounddevice` (PortAudio wrapper) + `numpy`.
- **Keyboard:** `pynput` (Hotkeys) + `pyautogui` (Typing).
- **Networking:** `matrix-nio` (Matrix protocol) + `requests` (Client) + `http.server` (Server) + `socket` (Discovery) + `websocket-client` (ComfyUI).

## Development Setup
- **OS:** Windows 11.
- **IDE:** Visual Studio Code.
- **Version Control:** Git.

## Technical Constraints
- **Threading:** PyQt6 event loop must run in the main thread. All other tasks (Audio, Keyboard, Network, Matrix) run in background threads/loops and communicate via a central `queue.Queue`.
- **Audio Stream:** A single persistent `sounddevice.InputStream` is used to avoid initialization latency and conflicts.
- **ComfyUI:** Requires specific node classes ("Apply Whisper", "Preview Text") to be present in the workflow.
- **Network Mode:** Requires machines to be on the same subnet for UDP broadcast discovery.
- **High DPI:** PyQt6 automatically handles DPI awareness, but may trigger OS-level warnings on some systems.

## Dependencies
- `PyQt6` (GUI)
- `matrix-nio` (Matrix integration)
- `requests`
- `websocket-client`
- `sounddevice`
- `numpy`
- `pynput`
- `pyautogui`
- `pyperclip`
- `pygetwindow`
