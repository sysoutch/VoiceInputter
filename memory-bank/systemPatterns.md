# System Patterns: VoiceInputter

## Architecture Overview
The system uses a multi-threaded architecture with a central Coordinator Loop to manage state and concurrency.

## Core Threads
1.  **Main Thread (Coordinator/UI):** Runs the PyQt6 event loop and a `coordinator_loop`. Handles all UI updates, state transitions, and dispatches tasks. Polls a thread-safe `queue` for events.
2.  **Audio Thread (Daemon):** continuously captures audio from `sounddevice`. Handles VAD logic. Pushes events to the main thread.
3.  **Processing Worker Thread (Daemon):** Consumes tasks from `processing_queue`. Handles ComfyUI communication sequentially.
4.  **Keyboard Thread:** `pynput` listener for global hotkeys.
5.  **Service Threads (Daemon):** 
    -   **Network Thread:** Handles peer-to-peer LAN communication.
    -   **Matrix Threads:** Asynchronous clients for Matrix integration.
    -   **Telegram Thread:** Event loop for the Telegram bot interaction.

## Data Flow
-   **Local Audio:** Mic -> `Audio Thread` -> `Coordinator`.
-   **Remote Audio (Matrix/Telegram):** Service Client -> Download -> `Coordinator` -> `Worker Thread`.
-   **AI Processing:** `Worker Thread` -> ComfyUI API -> Result Text -> `Coordinator`.
-   **Output:** `Coordinator` -> UI Display / OS Typing / Service Reply.

## Key Patterns
-   **Multi-tap Hotkey Detection:** A timing-based pattern that allows repetitive key sequences (e.g. F8+F8) to trigger system actions, distinct from standard held-key combinations.
-   **Modal Capturing Dialog:** Uses a modal UI pattern for hotkey recording to guarantee input focus and eliminate threading/focus conflicts during configuration.
-   **Background Service Initialization:** Hardware and network discovery (microphones, ComfyUI features) are moved to background threads to ensure near-zero UI startup latency.
-   **Source-Agnostic Bot Logic:** The processing worker handles transcription requests uniformly, whether they originate from local recording, Matrix, or Telegram, routing results back to the appropriate source.
-   **Integrated Tabbed Configuration:** Grouping settings by functional priority (General, Text, Hotkeys, Connect) to keep the overlay compact while exposing deep configuration.
-   **Native Responsive Layout:** Leveraging Qt's layout engine to provide a professional window that adapts to user resizing while maintaining accessibility of core controls.
-   **Context-Aware Spacing:** Logic that intelligently inserts spaces between inputs only when no line-break has occurred, ensuring clean document formatting.
