# VoiceInputter

VoiceInputter is a modern, native Windows tool that turns your voice into text and types it directly into any application. By leveraging local AI power (via ComfyUI/Whisper), it provides high-accuracy transcription with minimal latency and full control over your data.

![UI Screenshot](screenshot.png)

---

## 🚀 Key Features

### 🎙️ Effortless Control
- **Standard Native Interface:** A professional PyQt6 window that is responsive, resizable, and fits perfectly in your Windows workflow.
- **Configurable Hotkeys:** Set your own global toggle combination (e.g., `CTRL+F9`) or even repetitive sequences (e.g., `F8+F8`).
- **Voice Trigger (VAD):** Automatically start recording when you speak and stop when you're finished.

- **Microphone Selection:** Easily switch between different input devices directly from the UI.

### 🧠 Smart Text Processing
- **Multi-Language Support:** Choose specific languages or let the AI auto-detect what you're saying. Options are dynamically synced with your AI engine.
- **Smart Spacing:** Automatically adds spaces between successive transcriptions so your sentences flow naturally.
- **Dynamic Formatting:** Supports auto-numbering, bullet points, and custom prefixes/postfixes that update as you work.
- **Auto-Enter Modes:** Choose how text is submitted (Enter, Shift+Enter, etc.) to match the behavior of different apps and chat platforms.

### 🌐 Advanced Connectivity
- **Matrix Integration:** Turn any machine into a transcription server or send voice clips directly to your Matrix rooms for remote processing.
- **LAN Network Mode:** Offload the heavy AI processing to another powerful PC on your local network.

---

## 🛠️ User Setup

### 1. Requirements
- **Windows 10/11**
- **ComfyUI** running locally (or on a network machine) on port `8188`.
- A ComfyUI workflow saved as `stt.json` in the app directory (must include "Apply Whisper" and "Preview Text" nodes).

### 2. Getting Started
1.  Download the latest `voice_inputter.exe`.
2.  Ensure your ComfyUI instance is running.
3.  Launch the app.
4.  Select your target window, press **F9**, and start speaking!

### 3. Configuration
For automated login to Matrix or Network modes, you can create a `secrets.json` file:
```json
{
    "matrix_homeserver": "https://matrix.org",
    "matrix_user": "@your_user:matrix.org",
    "matrix_token": "your_access_token",
    "matrix_room": "!your_room_id:matrix.org"
}
```

---

## 👨‍💻 Developer Section

### Prerequisites
- Python 3.10+
- `pip install -r requirements.txt`

### Development Setup
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/sysoutch/VoiceInputter.git
    cd VoiceInputter
    ```
2.  **Run in development mode:**
    ```bash
    python voice_inputter.py
    ```

### Building from Source
We use PyInstaller to create the standalone executable:
```bash
pyinstaller --onefile --windowed --add-data "stt.json;." voice_inputter.py
```

### Project Structure
- `src/gui.py`: Modern PyQt6 interface and layout logic.
- `src/comfy.py`: API client for ComfyUI with dynamic workflow injection.
- `src/matrix_client.py`: Dual-client Matrix protocol integration.
- `src/audio.py`: Low-latency audio capture and VAD management.
- `voice_inputter.py`: Central coordinator and event loop.

### Internal Logic
- **Threaded Architecture:** UI, Audio capture, and AI processing run on separate threads to ensure a lag-free experience.
- **Dynamic Injection:** The app modifies the STT workflow JSON in-memory before execution to inject parameters like language selection.
- **State Machine:** Uses a central event queue to manage transitions between Ready, Recording, and Processing states.
