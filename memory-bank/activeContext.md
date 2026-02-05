# Active Context: VoiceInputter

## Current Focus
- Polishing release candidate.
- Distributing build.

## Recent Changes
- **Microphone Selection:** Added dropdown for selecting audio input device with real-time switching logic.
- **Network Client:** Implemented audio file transmission to peer instances for offloaded processing.
- **Build:** Created local executable with PyInstaller.
- Implemented **concurrent processing**: Recording and transcription are now decoupled, allowing continuous input while processing happens in the background.
- Added **dynamic prefixes**: Supports numbered lists ("1.", "2.") and lettered lists ("a)", "b)") that auto-update on reorder.
- Enhanced UI:
    - **Target Window Selection**: Dropdown to select a specific application window as the target for text output.
    - **Focus Target Controls**: "Focus" toggle to control auto-activation, and "Go" button to manually activate.
    - **Postfix Support**: New option to append characters.
    - **Auto-Enter Modes**: Dropdown for "enter", "shift+enter", "ctrl+enter".

## Next Steps
- Push changes to GitHub.
- Create new release tag.

## Active Decisions and Considerations
- **Network Mode:** Currently sends raw .wav files via HTTP POST to the peer's `/transcribe` endpoint.
- **Audio Device Switching:** Requires closing and re-opening the `sounddevice` stream to take effect reliably.
- **Concurrency:** Using a `processing_queue` ensures ComfyUI tasks run sequentially without blocking the UI or audio capture.
