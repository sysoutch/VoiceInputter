# Active Context: VoiceInputter

## Current Focus
- Refactoring the monolithic script into a modular structure.
- Enhancing the UI with drag capability and text editing features.
- Pushing updates to GitHub.

## Recent Changes
- Implemented "Record on Voice Input" (Auto-Start) and "Auto-Stop" (VAD).
- Added a persistent UI overlay with status indicators and manual controls.
- Fixed code artifact issues.

## Next Steps
- Split `voice_inputter.py` into `src/` modules (`gui`, `audio`, `comfy`, `main`).
- Add "Draggable Window" functionality.
- Add "Text Edit" area to the overlay.
- Add "Auto-Enter" and "Auto-Send" toggles.
- Update GitHub repository.

## Active Decisions and Considerations
- **Modularization:** Splitting the code will make it easier to manage the growing UI and Audio logic.
- **UI Interaction:** The overlay is becoming a control panel. Need to balance compactness with new features (Text Area).
