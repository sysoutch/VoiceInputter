# Active Context: VoiceInputter

## Current Focus
- Finalizing integrations and UI structure.
- Deployment preparation.

## Recent Changes
- **Telegram Bot Integration:** Added support for remote voice transcription via Telegram. Includes a dedicated connection tab and automatic transcription/reply logic.
- **Startup Optimization:** Moved blocking operations (ComfyUI language scan, microphone discovery) to background threads, resulting in near-instant application launch.
- **Robust Hotkey Recording:** Implemented a modal dialog for hotkey recording to ensure reliable capture of key combinations and multi-tap sequences.
- **Advanced Hotkey Support:** Backend logic now supports repetitive key sequences (e.g., "F8+F8+F8") with timing-based multi-tap detection.
- **UI Consolidation:** Centralized all critical workflow settings (Language, Auto-Send, Target Window, Focus) in the General tab for better accessibility.
- **De-duplicated Device List:** Filtered the microphone list to remove redundant entries caused by multiple system APIs.

## Next Steps
- Commit changes locally.

## Active Decisions and Considerations
- **Platform Expansion:** Telegram added as a secondary remote protocol alongside Matrix.
- **UI Architecture:** Consolidating settings into the General tab based on user workflow priority (Setup -> Process -> Send -> Target).
- **Concurrency:** Using thread-safe queues to bridge background services (Telegram, Matrix, Audio) with the PyQt6 main thread.
