# Voice and encrypted-vault validation — October 17, 2026

Tested Weather 0.2.1 at commit 066f02f against an isolated copy of Sapphire dev 70b975bc42675dce51d1563b8b66097307b5d142. No plugin source changes were required.

## Results

- 30 Python tests and 4 JavaScript tests passed again.
- 8 actual-host HTTP/session checks passed again, including stale chat context, private-chat switching, an in-flight privacy change, limbo refusal, canonical tool/cache sharing and test-server shutdown.
- 9 additional tool/voice/vault integration assertions passed.
- An actual local-model audio round trip passed.

## Real encrypted-vault lifecycle

A fresh disposable ChatSessionManager and vault used Sapphire's real scrypt/AES-GCM implementation. Test chat messages and settings were encrypted in SQLite, and a unique message sentinel was absent from the database bytes. Weather's dashboard context and conversational tool refused the unlocked private chat before provider access. Locking removed the chat from listings, refused activation and made its stored message undecryptable. An incorrect passphrase failed. The correct passphrase restored the chat and message; Weather still refused the private chat after unlock.

This verifies the tested chat lifecycle and Weather's refusal boundary, not a general cryptographic audit or forensic assessment of every storage medium. A public Weather cache is process memory and is not itself a vault; these checks establish that private requests cannot retrieve it through the tested entry points.

## Voice integration and actual audio

The real ToolCallingEngine executed weather_get and returned a successful one-day forecast. The real ConversationDriver carried a recognized request through that engine and delivered a speech chunk to its output sink. Separate checks exercised Sapphire's real privacy-gate logic for local versus cloud STT/TTS metadata and confirmed that a private-cloud-STT refusal stopped transcription.

For the actual audio test, already-cached Kokoro and faster-whisper base.en models ran on CPU, with Hugging Face and Transformers in offline mode. Synthesized input said: "What is the weather in London England today?" Sapphire's real FasterWhisperProvider recognized: "What is the weather in London, England today?" The real ConversationDriver and ToolCallingEngine invoked Weather. Kokoro generated a WAV reply from the resulting conditions; transcribing that reply recovered the forecast wording and temperature.

Controlled boundaries: the spoken request was synthesized, language-model tool selection and answer construction were deterministic, the external weather response was a fixture, and the output sink decoded WAV rather than playing through a physical speaker. This was not a live-LLM or physical microphone/speaker acceptance test. Earlier live-provider results remain recorded separately; fixture weather here is not an observed London forecast.

## Observed speech limitation

An earlier audio trial saying "Los Angeles California" was recognized by the cached base.en recognizer as "Lowe's Angels, California". This is an observed speech-recognition limitation and was not silently corrected or counted as a pass. Weather cannot establish the intended city from incorrectly recognized words. Check the recognized city, clarify it, or use the saved default city when speaking. Larger/different speech models were not evaluated or installed.

## Isolation and remaining scope

Tests used scratch profiles, chats, vaults and a copied host. Existing Sapphire/DES/AXIS/TRI checkouts were not modified. Installed speech libraries and cached weights were reused read-only; no packages or speech models were installed. Synthetic test audio contained no user recording or private conversation. The HTTP test server stopped and its port refused connections afterward.

Remaining unverified: a live LLM autonomously choosing and explaining the tool, physical microphone/speaker behavior, full everyday Sapphire startup, proxy-on live routing, older Sapphire releases and broad speech-recognition accuracy. These results support community review/testing; they do not establish universal production readiness.
