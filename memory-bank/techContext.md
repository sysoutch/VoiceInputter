# Tech Context: VoiceInputter

## Technologies Used
- **Language:** Python 3.
- **Runtime:** Standard Python Interpreter.
- **GUI:** `tkinter` (Standard Library).
- **Backend:** ComfyUI (Local API).
- **Audio:** `sounddevice` (PortAudio wrapper) + `numpy`.
- **Keyboard:** `pynput` (Hotkeys) + `pyautogui` (Typing).
- **Networking:** `requests` + `websocket-client`.

## Development Setup
- **OS:** Windows 11.
- **IDE:** Visual Studio Code.
- **Version Control:** Git + Git LFS.

## Technical Constraints
- **Threading:** `tkinter` must run in the main thread. All other tasks (Audio, Keyboard, Network) run in background threads and communicate via `queue.Queue`.
- **Audio Stream:** A single persistent `sounddevice.InputStream` is used to avoid initialization latency and conflicts.
- **ComfyUI:** Requires specific node classes ("Apply Whisper", "Preview Text") to be present in the workflow.

## Dependencies
- `requests`
- `websocket-client`
- `sounddevice`
- `numpy`
- `pynput`
- `pyautogui`
- `pyperclip`
- `pygetwindow`
