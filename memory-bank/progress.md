# Progress: VoiceInputter

## What Works
- **Audio Capture:** Continuous monitoring with `sounddevice`.
- **Microphone Selection:** Dropdown to switch input devices.
- **VAD:** Silence detection (Auto-Stop) and Voice Trigger (Auto-Start).
- **Backend:** ComfyUI integration (Upload, Queue, WebSocket).
- **Network Mode:** Offload processing to a peer on the LAN.
- **UI:** Persistent overlay with status (Ready/Recording/Processing).
- **Concurrent Processing:** Record new clips while previous ones process.
- **Dynamic Features:** Auto-numbering prefixes that update on reorder.
- **Advanced Controls:** Auto-Enter modes (Shift+Enter, Ctrl+Enter), Clear All.
- **UX:** Center window startup, selection preservation.
- **Packaging:** Standalone executable build (PyInstaller).

## What's Left to Build
- Further network security features (if needed).
- Custom workflow editing within the app.

## Current Status
Feature-complete and polished.

## Known Issues
- Network mode uses unencrypted HTTP/UDP. Safe only on trusted LANs.
