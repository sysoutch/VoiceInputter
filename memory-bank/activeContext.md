# Active Context: VoiceInputter

## Current Focus
- Polishing the text extraction and output mechanism.
- Maintaining documentation of the implemented features.

## Recent Changes
- Implemented robust text extraction from ComfyUI using WebSocket `executed` messages.
- Specifically targeted the "Preview Text" node to avoid alignment JSON data.
- Added automatic "Enter" key press after pasting text.
- Cleaned up console output to print only the raw transcription.

## Next Steps
- Verify the system reliability in different scenarios (e.g., failed transcription, ComfyUI errors).
- Update the `README.md` with usage instructions and dependencies.

## Active Decisions and Considerations
- **Output Handling:** We are now using WebSocket event listening instead of polling the history endpoint. This is faster and avoids race conditions.
- **Node Targeting:** We search for nodes by title ("Preview Text") in the workflow metadata to ensure we grab the correct output.
