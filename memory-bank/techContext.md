# Tech Context: VoiceInputter

## Technologies Used
- **Language:** Python 3.
- **Runtime:** Standard Python Interpreter.
- **Backend:** ComfyUI (Local API) for Speech-to-Text processing.
- **Libraries:**
    - `requests`: HTTP communication with ComfyUI.
    - `websocket-client`: Real-time event listening from ComfyUI.
    - `sounddevice` & `numpy`: Audio recording and processing.
    - `pynput`: Global hotkey handling (F9).
    - `pyautogui` & `pyperclip`: Simulating text input and keyboard actions.
    - `pygetwindow` (optional): Active window tracking.

## Development Setup
- **OS:** Windows 11.
- **IDE:** Visual Studio Code.
- **Version Control:** Git.

## Technical Constraints
- **ComfyUI Dependency:** Requires a running instance of ComfyUI on `localhost:8188` (configurable).
- **Workflow Dependency:** Relies on a specific `stt.json` workflow structure, expecting "Apply Whisper" and "Preview Text" nodes.
- **Audio Hardware:** Requires a functional microphone accessible by `sounddevice`.

## Dependencies
- `requests`
- `websocket-client`
- `sounddevice`
- `numpy`
- `pynput`
- `pyautogui`
- `pyperclip`
