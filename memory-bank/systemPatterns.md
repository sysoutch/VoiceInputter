# System Patterns: VoiceInputter

## Architecture Overview
The system uses a multi-threaded architecture with a central Coordinator Loop to manage state and concurrency.

## Core Threads
1.  **Main Thread (Coordinator/UI):** Runs the `tkinter` mainloop and a `coordinator_loop`. Handles all UI updates, state transitions (`READY`, `RECORDING`, `PROCESSING`), and dispatches tasks. Polls a thread-safe `queue` for events.
2.  **Audio Thread (Daemon):** continuously captures audio from `sounddevice`. Handles VAD logic. Pushes events (`recording_finished`, `toggle`) to the main thread.
3.  **Processing Worker Thread (Daemon):** Consumes tasks from `processing_queue`. Handles ComfyUI communication sequentially. Pushes results (`send_text`, `processing_complete`) back to the main thread via queue.
4.  **Keyboard Thread:** `pynput` listener for global hotkeys.
5.  **Network Thread (Daemon):** Runs the HTTP server and discovery loop for peer-to-peer communication.

## Data Flow
-   **Audio:** Mic -> `Audio Thread` -> Buffer -> VAD -> `recording_finished` -> `Coordinator`.
-   **Processing:** `Coordinator` -> `processing_queue` -> `Worker Thread` -> ComfyUI -> Text -> `Coordinator` -> UI/Clipboard.
-   **UI Updates:** All logic threads push UI commands (`update_rec_list`, `ui_state`) to the main `queue`. The Coordinator executes them safely.

## Key Patterns
-   **Concurrent Recording/Processing:** The decoupling of audio capture and transcription allows the user to record new clips immediately while previous ones are being processed in the background.
-   **Separation of Transcription and Output:** The system distinguishes between "Auto-Process" (transcribing audio to text) and "Auto-Send" (typing text to window). This allows users to review or queue transcriptions before sending.
-   **Target Window Management:** Uses `pygetwindow` to scan and list open applications. Text injection logic checks for a specific target window and brings it to the foreground before typing, overriding the default behavior of typing into the currently active window.
-   **Dynamic Prefixes:** Prefixes (e.g., "1.", "a)") are calculated dynamically based on the item's current position in the list relative to other items of the same type. This ensures prefixes remain correct even after reordering or deleting items.
-   **State Management:** The UI reflects both audio state (Recording vs Ready) and processing state (Processing vs Idle) without blocking user interaction.
-   **Network Distribution:** Allows offloading the compute-heavy transcription process (ComfyUI) to another machine on the LAN. The client records audio and sends the file; the server processes it and returns text.
