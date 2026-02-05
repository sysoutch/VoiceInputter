# System Patterns: VoiceInputter

## Architecture Overview
The system uses a multi-threaded architecture with a central Coordinator Loop to manage state and concurrency.

## Core Threads
1.  **Main Thread (Coordinator/UI):** Runs the **PyQt6** event loop and a `coordinator_loop`. Handles all UI updates, state transitions (`READY`, `RECORDING`, `PROCESSING`), and dispatches tasks. Polls a thread-safe `queue` for events.
2.  **Audio Thread (Daemon):** continuously captures audio from `sounddevice`. Handles VAD logic. Pushes events (`recording_finished`, `toggle`) to the main thread.
3.  **Processing Worker Thread (Daemon):** Consumes tasks from `processing_queue`. Handles ComfyUI communication sequentially. Pushes results (`send_text`, `processing_complete`) back to the main thread via queue.
4.  **Keyboard Thread:** `pynput` listener for global hotkeys.
5.  **Network Thread (Daemon):** Runs the HTTP server and discovery loop for peer-to-peer communication.
6.  **Matrix Threads (Managed by nio):** Asynchronous clients running in background loops for internet-based transcription offloading.

## Data Flow
-   **Audio:** Mic -> `Audio Thread` -> Buffer -> VAD -> `recording_finished` -> `Coordinator`.
-   **Processing:** `Coordinator` -> `processing_queue` -> `Worker Thread` -> ComfyUI -> Text -> `Coordinator` -> UI/Clipboard.
-   **UI Updates:** All logic threads push UI commands (`update_rec_list`, `ui_state`) to the main `queue`. The Coordinator executes them safely on the main thread using PyQt6 timers.

## Key Patterns
-   **Concurrent Recording/Processing:** The decoupling of audio capture and transcription allows the user to record new clips immediately while previous ones are being processed in the background.
-   **Separation of Transcription and Output:** The system distinguishes between "Auto-Process" (transcribing audio to text) and "Auto-Send" (typing text to window). This allows users to review or queue transcriptions before sending.
-   **Target Window Management:** Uses `pygetwindow` to scan and list open applications. Text injection logic checks for a specific target window and brings it to the foreground before typing, overriding the default behavior of typing into the currently active window.
-   **Dynamic Prefixes:** Prefixes (e.g., "1.", "a)") are calculated dynamically based on the item's current position in the list relative to other items of the same type. This ensures prefixes remain correct even after reordering or deleting items.
-   **Matrix User/Bot Logic:** Uses two separate Matrix clients to enable a machine to act both as a transcription requester (Client) and a provider (Bot).
-   **Dynamic Workflow Modification:** Injects user-selected parameters (like language) into the STT workflow JSON in-memory before execution, keeping the static workflow files clean.
-   **Native Responsive UI:** Uses PyQt6 layouts and size policies to provide a native OS window experience with full resizing support and automatic widget scaling.
-   **Smart Spacing:** A context-aware text injection pattern that only adds spaces between transcriptions when no newline/enter command has been issued, ensuring clean document formatting.
