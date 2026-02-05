# Product Context: VoiceInputter

## Why this project exists
VoiceInputter exists to bridge the gap between spoken thought and written text. Typing can be slow, physically demanding, or impossible in certain contexts. Voice input offers a faster and more accessible alternative.

## Problems it solves
- **Speed:** Speaking is generally faster than typing for many users.
- **Accessibility:** Provides an alternative for users with motor impairments or those who find typing difficult.
- **Convenience:** Allows for "hands-free" or "eyes-free" text entry in appropriate scenarios.
- **Hardware Flexibility:** Support for multiple microphones and network offloading allows users to use high-quality setups or distributed processing power.
- **Remote Collaboration:** Matrix integration allows for transcription over the internet, effectively creating a transcription server for remote users.

## How it should work
1. The user activates the voice input (e.g., via a hotkey, button, or voice trigger).
2. The system captures audio from the selected microphone.
3. The audio is processed (locally, via LAN network peer, or via Matrix bot) and sent to a Speech-to-Text engine.
4. The resulting text is inserted at the cursor position, sent to a target application, or replied to in a Matrix room.

## User Experience Goals
- **Minimal Latency:** Transcription should feel near-instantaneous.
- **High Accuracy:** Correct interpretation of speech, including punctuation and formatting. Supports multiple languages with auto-detection.
- **Modern Interface:** A native, responsive GUI that looks professional and stays visible during multitasking.
- **Flexibility:** Users can choose their input device, processing location, and transcription language.
