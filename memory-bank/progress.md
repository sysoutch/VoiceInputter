# Progress: VoiceInputter

## What Works
- **Audio Capture:** Continuous monitoring with `sounddevice`.
- **Microphone Selection:** Dropdown to switch input devices.
- **VAD:** Silence detection (Auto-Stop) and Voice Trigger (Auto-Start) with inline UI settings.
- **Backend:** ComfyUI integration (Upload, Queue, WebSocket) with dynamic language injection.
- **Network Mode:** Offload processing to a peer on the LAN.
- **Matrix Mode:** Remote transcription server and internet-based input via Matrix protocol.
- **UI:** Modern PyQt6 overlay with Dark Fusion theme, responsive layout, and integrated settings.
- **Concurrent Processing:** Record new clips while previous ones process.
- **Smart Logic:** Dynamic prefixes, smart spacing between transcriptions, and newline handling in the preview area.
- **Advanced Controls:** Auto-Enter modes (Shift+Enter, Ctrl+Enter), Clear All, Target Window selection.
- **Packaging:** Standalone executable build (PyInstaller).

## What's Left to Build
- Further network security features (if needed).
- Custom workflow editing within the app.

## Current Status
Feature-complete and polished.

## Known Issues
- Network mode uses unencrypted HTTP/UDP. Safe only on trusted LANs.
