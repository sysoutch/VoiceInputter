# Active Context: VoiceInputter

## Current Focus
- Polishing release candidate.
- Distributing build.

## Recent Changes
- **GUI Migration (PyQt6):** Replaced legacy Tkinter UI with a modern, native-feeling PyQt6 interface. Features a dark Fusion theme, fully resizable window, and responsive layout where text areas and recording lists expand to fill space.
- **Matrix Integration:** Implemented dual-client Matrix logic.
    - **Client Mode:** Sends recorded audio to a Matrix room.
    - **Bot Mode:** Receives audio from room -> transcribes locally -> sends text back to room. Also types received text messages into the active window.
- **Dynamic Language Selection:** Added a Language dropdown in the General tab that dynamically fetches supported languages (auto, english, german, etc.) from the ComfyUI "Apply Whisper" node.
- **Smart Spacing Logic:** Improved text injection to automatically handle spaces between successive transcriptions only when line breaks (Enter/Newline) are not triggered.
- **Layout Refinement:** Inline VAD settings (Silence/Threshold next to toggles) and embedded Matrix configuration within the Connect tab.

## Next Steps
- Commit changes locally.

## Active Decisions and Considerations
- **GUI Stack:** Switched to PyQt6 for better performance and standard window behavior (native resizing, DPI awareness).
- **Matrix Workflow:** Uses a Client/Server (User/Bot) paradigm to allow remote transcription offloading.
- **Language Injection:** Workflow JSON is modified in-memory before execution to inject the user-selected language into the Whisper node.
