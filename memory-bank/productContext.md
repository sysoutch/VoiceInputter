# Product Context: VoiceInputter

## Why this project exists
VoiceInputter exists to bridge the gap between spoken thought and written text. Typing can be slow, physically demanding, or impossible in certain contexts. Voice input offers a faster and more accessible alternative.

## Problems it solves
- **Speed:** Speaking is generally faster than typing for many users.
- **Accessibility:** Provides an alternative for users with motor impairments or those who find typing difficult.
- **Convenience:** Allows for "hands-free" or "eyes-free" text entry in appropriate scenarios.

## How it should work
1. The user activates the voice input (e.g., via a hotkey or button).
2. The system captures audio from the microphone.
3. The audio is processed and sent to a Speech-to-Text engine.
4. The resulting text is inserted at the cursor position or sent to the target application.

## User Experience Goals
- **Minimal Latency:** Transcription should feel near-instantaneous.
- **High Accuracy:** Correct interpretation of speech, including punctuation and formatting.
- **Unobtrusive:** The tool should stay out of the way until needed.
