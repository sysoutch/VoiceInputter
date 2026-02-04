# Active Context: VoiceInputter

## Current Focus
- Finalizing UI features and preparing for local build.
- Updating documentation.

## Recent Changes
- Implemented **concurrent processing**: Recording and transcription are now decoupled, allowing continuous input while processing happens in the background.
- Added **dynamic prefixes**: Supports numbered lists ("1.", "2.") and lettered lists ("a)", "b)") that auto-update on reorder.
- Enhanced UI:
    - **Auto-Send**: New toggle to separate transcription from typing. Allows processing without immediate output.
    - **Postfix Support**: New option to append characters (space, comma, dot) to the transcribed text.
    - **Center Window**: Application starts centered.
    - **Clear All**: Button to remove all recordings.
    - **Auto-Enter Modes**: Dropdown for "enter", "shift+enter", "ctrl+enter".
    - **Selection Preservation**: List selection follows item movement and deletion.
- Modularized code into `src/`.

## Next Steps
- Create local build with PyInstaller.
- Push final changes to GitHub.

## Active Decisions and Considerations
- **Concurrency:** Using a `processing_queue` ensures ComfyUI tasks run sequentially without blocking the UI or audio capture.
- **Dynamic Prefixes:** Calculated on-the-fly during UI updates to handle reordering seamlessly.
