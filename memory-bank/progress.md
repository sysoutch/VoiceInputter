# Progress: VoiceInputter

## What Works
- **Audio Capture:** Continuous monitoring with `sounddevice`.
- **VAD:** Silence detection (Auto-Stop) and Voice Trigger (Auto-Start).
- **Backend:** ComfyUI integration (Upload, Queue, WebSocket).
- **UI:** Persistent overlay with status (Ready/Recording/Processing).
- **Concurrent Processing:** Record new clips while previous ones process.
- **Dynamic Features:** Auto-numbering prefixes that update on reorder.
- **Advanced Controls:** Auto-Enter modes (Shift+Enter, Ctrl+Enter), Clear All.
- **UX:** Center window startup, selection preservation.

## What's Left to Build
- **Packaging:** Standalone executable (PyInstaller).

## Current Status
Feature-complete. Ready for packaging.

## Known Issues
- None.
