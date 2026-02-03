# Progress: VoiceInputter

## What Works
- **Audio Capture:** Recording via `sounddevice` and saving to WAV.
- **Backend Integration:** Full communication with ComfyUI (Upload, Queue Prompt, WebSocket Listen).
- **Text Extraction:** Robust logic to capture transcription from specific workflow nodes ("Preview Text").
- **Output:** Auto-pasting to active window followed by `Enter` key.
- **Configuration:** Dynamic node finding based on workflow metadata.

## What's Left to Build
- **User Interface:** Currently a CLI tool; a GUI could be added later if needed.
- **Error Handling:** Can be improved for edge cases (e.g. ComfyUI not running).
- **Packaging:** Create a standalone executable.

## Current Status
The core functionality is complete and verified. The tool successfully transcribes voice input and types it into the active application.

## Known Issues
- None at this time.
