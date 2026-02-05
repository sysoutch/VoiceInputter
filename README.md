# VoiceInputter

A Python automation tool that integrates with a local ComfyUI API for advanced voice-to-text input. It records audio, processes it through a ComfyUI workflow (using Whisper), and types the result directly into your active window.

![UI Screenshot](screenshot.png)

## Key Features

### 🎙️ Advanced Audio Control
- **Microphone Selection:** Select your preferred input device from a dropdown list with real-time switching.
- **Voice Activity Detection (VAD):**
  - **Auto-Stop:** Automatically stops recording when you stop speaking.
  - **Voice Trigger:** Automatically starts recording when you begin speaking.
- **Concurrent Processing:** Record a new clip immediately while the previous one is being transcribed. No waiting required.

### 🌐 Network & Matrix Modes
- **Network Client:** Can send recorded audio to another VoiceInputter instance for processing (useful for offloading heavy inference).
- **Matrix Integration:** Offload transcription to a separate machine (the "Bot") via a Matrix room.
  - **The Workflow:** 
    1. **Send:** Your local Client records and uploads audio to the room.
    2. **Process:** The remote Bot transcribes it via local ComfyUI and replies with text.
    3. **Type:** Your local Client receives the text and types it into your selected window.

### 🧠 Smart Text Processing
- **Language Selection:** Choose your transcription language dynamically (English, German, Auto, etc.) via a dropdown that fetches options directly from ComfyUI.
- **Smart Spacing:** Automatically handles spaces between successive transcriptions only when line breaks are not triggered.
- **Dynamic Prefixes:** Automatically add prefixes like `1.`, `2.`, `3.`, `a)`, `b)`, `- ` which auto-update on reorder.
- **Postfix Support:** Automatically append characters like `Space`, `Comma`, or `Dot`.
- **Auto-Enter Modes:** Choose how the text is submitted: `Enter`, `Shift+Enter`, or `Ctrl+Enter`.

### 🖥️ Modern Native Interface
- **PyQt6 GUI:** A responsive, dark-themed native window with full resizing support.
- **Always-on-Top Overlay:** Stays visible over your applications for easy monitoring.
- **Target Window Selection:** Choose a specific application to receive text input, or stick to the default "Active Window" mode.
- **Focus Controls:** Auto-focus the target window before typing or manually activate it with the "Go" button.
- **Clipboard Management:** Uses clipboard injection for fast and reliable text entry.

## Requirements

- Python 3.10+
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) running locally on port 8188.
- A ComfyUI workflow saved as `stt.json` (must include "Apply Whisper" and "Preview Text" nodes).

## Configuration

To avoid entering your credentials every time, you can create a `secrets.json` file in the root directory. This file is ignored by Git for security.

```json
{
    "matrix_homeserver": "https://matrix.org",
    "matrix_user": "@your_user:matrix.org",
    "matrix_token": "your_access_token",
    "matrix_room": "!your_room_id:matrix.org",

    "bot_matrix_homeserver": "https://matrix.org",
    "bot_matrix_user": "@your_bot:matrix.org",
    "bot_matrix_token": "your_bot_access_token",
    "bot_matrix_room": "!your_room_id:matrix.org"
}
```

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/sysoutch/VoiceInputter.git
    cd VoiceInputter
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Start ComfyUI:** Ensure your local ComfyUI instance is running.
2.  **Launch the App:**
    ```bash
    python voice_inputter.py
    ```
3.  **Controls:**
    - **F9 (Global Hotkey):** Toggle recording manually.
    - **UI Controls:** Use the interface to toggle VAD settings, change prefix modes, or manage the recording queue.

## Building from Source

To create a standalone executable:

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```
2.  Run the build command:
    ```bash
    pyinstaller --onefile --windowed --add-data "stt.json;." voice_inputter.py
    ```

## Project Structure

- `src/`: Core modules (Audio, GUI, Matrix, Network, ComfyUI client).
- `voice_inputter.py`: Main entry point and coordinator.
- `stt.json`: The ComfyUI workflow definition.
