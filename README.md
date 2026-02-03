# VoiceInputter

A Python automation tool that integrates with a local ComfyUI API for voice-to-text input. It records audio, processes it through a ComfyUI workflow (using Whisper), and types the result into your active window.

## Features

- **Global Hotkey:** Toggle recording with `F9`.
- **ComfyUI Integration:** Uses a local ComfyUI instance for processing, leveraging the power of node-based workflows.
- **Real-time Feedback:** Listens for ComfyUI execution results via WebSockets for low latency.
- **Smart Extraction:** Automatically identifies and extracts text from the "Preview Text" node, ignoring debug data.
- **Workflow:** Records -> Uploads -> Transcribes -> Pastes -> Hits Enter.
- **Non-blocking:** Threaded architecture ensures the UI remains responsive.

## Requirements

- Python 3.8+
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) running locally on port 8188.
- A ComfyUI workflow saved as `stt.json` (must include "Apply Whisper" and "Preview Text" nodes).

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/YOUR_USERNAME/VoiceInputter.git
    cd VoiceInputter
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: You'll need to create a `requirements.txt` based on the imports: `requests`, `websocket-client`, `sounddevice`, `numpy`, `pynput`, `pyautogui`, `pyperclip`, `pygetwindow`)*

    Or install directly:
    ```bash
    pip install requests websocket-client sounddevice numpy pynput pyautogui pyperclip pygetwindow
    ```

    *Note: `pygetwindow` might require administrative privileges or specific OS permissions on some systems.*

## Usage

1.  Ensure ComfyUI is running.
2.  Place your `stt.json` workflow file in the project directory.
3.  Run the script:
    ```bash
    python voice_inputter.py
    ```
4.  Switch to any application (e.g., Notepad, Discord, VS Code).
5.  Press **F9** to start recording.
6.  Speak your query.
7.  Press **F9** again to stop.
8.  Wait a moment; the text will be typed automatically followed by an Enter press.
