# System Patterns: VoiceInputter

## Architecture Overview
The system uses a multi-threaded architecture to separate audio processing, UI rendering, and backend communication.

## Core Threads
1.  **Main Thread (UI):** Runs the `tkinter` mainloop. Handles all UI updates and user interactions. Polls a thread-safe `queue` for events from other threads.
2.  **Audio Thread (Daemon):** Continuously captures audio from `sounddevice`. Handles VAD logic (Voice Trigger and Auto-Stop). Pushes events (`ui`, `toggle`, `auto_stop`) to the main thread.
3.  **Processing Thread (Worker):** Spawned on demand to handle ComfyUI communication (Upload -> Queue -> Listen -> Extract). Pushes final text or errors back to the main thread.
4.  **Keyboard Thread:** `pynput` listener running in background to detect global hotkeys.

## Data Flow
-   **Audio:** Mic -> `Audio Thread` -> Buffer -> VAD Check -> `self.audio_data`.
-   **Events:** `Audio Thread` / `Keyboard Thread` -> `self.queue` -> `Main Thread (process_queue)` -> UI Update / Action.
-   **Transcription:** `Main Thread` -> triggers `Processing Thread` -> ComfyUI API -> WebSocket -> `Processing Thread` -> `Main Thread` (via Clipboard/Keyboard).

## Key Components
-   **Overlay:** Persistent top-most window.
-   **VAD:** Energy-based silence/speech detection.
-   **ComfyUI Client:** Handles specific workflow node targeting ("Preview Text").
