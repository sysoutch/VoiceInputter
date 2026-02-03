# System Patterns: VoiceInputter

## Architecture Overview
The system follows a pipeline architecture triggered by user interaction (hotkey), leveraging an external processing engine (ComfyUI) for heavy lifting.

## Core Flow
1.  **Trigger:** User presses `F9`.
2.  **Capture:** System records audio from the microphone until `F9` is pressed again.
3.  **Process:**
    -   Audio is saved to a local WAV file.
    -   File is uploaded to ComfyUI.
    -   Workflow is submitted to ComfyUI via HTTP API.
4.  **Listen:** System connects to ComfyUI WebSocket to listen for execution events.
5.  **Extract:**
    -   Listens for `executed` event.
    -   Identifies the target node (e.g., "Preview Text") to ensure correct output.
    -   Extracts the transcription string.
6.  **Output:**
    -   Refocuses the originally active window.
    -   Pastes text via Clipboard (Ctrl+V).
    -   Simulates `Enter` key press.

## Key Components
1.  **VoiceInputter Class:** Encapsulates all logic.
    -   `record_audio()`: Handles `sounddevice` stream.
    -   `process_transcription()`: Orchestrates upload, queueing, and result retrieval.
    -   `handle_final_text()`: Manages clipboard and keyboard simulation.
2.  **ComfyUI Workflow (`stt.json`):** Defines the server-side processing chain (LoadAudio -> Whisper -> Preview).

## Design Patterns
-   **Event-Driven:** Uses `pynput` for keyboard events and WebSocket for server responses.
-   **Polling vs Push:** Shifted from polling `/history` to listening for WebSocket push events for lower latency.
