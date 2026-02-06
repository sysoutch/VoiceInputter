# Progress: VoiceInputter

## What Works
- **Audio Capture:** Continuous monitoring with `sounddevice` with de-duplicated device listing.
- **Microphone Selection:** Clean dropdown with unique input devices.
- **VAD:** Silence detection (Auto-Stop) and Voice Trigger (Auto-Start) with inline UI settings.
- **Backend:** ComfyUI integration (Upload, Queue, WebSocket) with dynamic language selection.
- **Network Mode:** Offload processing to a peer on the LAN.
- **Matrix Mode:** Remote transcription server and internet-based input via Matrix protocol.
- **Telegram Mode:** Remote voice transcription and bot interaction via Telegram.
- **UI:** Modern PyQt6 overlay with Dark Fusion theme, consolidated workflow settings, and responsive layout.
- **Startup:** Instant launch with background hardware/network initialization.
- **Advanced Hotkeys:** Support for complex chords and repetitive sequences (e.g. F8+F8) via robust recording dialog.
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
