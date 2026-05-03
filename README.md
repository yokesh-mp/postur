# Postur 🤸

> AI-powered pose coach for Android — real-time silhouette overlay, scene-aware pose suggestion, and LLM voice coaching.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-Android-green.svg)
![Status](https://img.shields.io/badge/status-pre--alpha-orange.svg)

---

## What is Postur?

Postur shows a **white silhouette overlay** on your live camera feed and guides you to match the pose using an **AI voice coach**. The app analyzes your scene, picks the right pose for your environment, and gives you real-time spoken corrections until you nail it.

Think of it as a smart photography assistant that lives in your camera.

---

## Features

- 🎯 **Scene-Aware Pose Suggestion** — Gemini Vision analyzes your environment and picks a suitable pose category automatically
- 👻 **Live Silhouette Overlay** — White skeleton drawn directly on your camera feed using MediaPipe + Android Canvas
- 🎙️ **AI Voice Coach** — LLM generates natural language corrections like *"Raise your left arm slightly"*, spoken aloud in real time
- 📊 **Pose Match Score** — See how closely your body matches the target pose, updated every 100ms
- ⚡ **Zero-Lag Design** — Camera thread is never blocked; poses are prefetched so switching is instant
- 🔌 **Local-First AI** — Run fully free against a local Ollama instance; auto-switches to Gemini Flash in production
- 📖 **Open Source** — MIT licensed, contributor friendly

---

## Screenshots

> Coming soon — app is in pre-alpha development

---

## How It Works

```
Open App → AI scans your scene → Pose silhouette appears on camera
     ↓
Mimic the pose → Real-time skeleton comparison → Match % shown on screen
     ↓
Voice coach guides you → "Lower your right shoulder a little"
     ↓
85%+ match → Capture the photo → Try next pose
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Kotlin |
| UI | Jetpack Compose |
| Camera | CameraX |
| Pose Detection | MediaPipe Pose Landmarker (on-device) |
| AI — Dev | Ollama (llama3.2-vision + gemma3:4b) |
| AI — Prod | Gemini 1.5 Flash API |
| Async | Kotlin Coroutines + StateFlow |
| Voice | Android TextToSpeech |

---

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full system design including:
- Three-lane thread model (camera / AI / audio)
- AI provider abstraction (Ollama ↔ Gemini swap)
- Low-latency design decisions
- Pose library JSON schema
- Voice coach hybrid pipeline

---

## Getting Started

### Prerequisites

- Android Studio Hedgehog or later
- Android device or emulator (API 26+)
- For local AI: [Ollama](https://ollama.com) running on your machine

### Clone the Repo

```bash
git clone https://github.com/yokesh-mp/postur.git
cd postur
```

### Configure AI Backend

Create a `local.properties` file in the root (if it doesn't exist) and add:

```properties
# For local Ollama development (free)
OLLAMA_URL=http://192.168.x.x:11434

# For Gemini production
GEMINI_API_KEY=your_api_key_here
```

> The app automatically pings your Ollama instance on startup. If unreachable, it falls back to Gemini.

### Run Ollama Locally (optional but recommended for dev)

```bash
# Install Ollama from https://ollama.com
# Then pull the required models

ollama pull llama3.2-vision
ollama pull gemma3:4b

# Start Ollama server accessible on your network
OLLAMA_HOST=0.0.0.0 ollama serve
```

### Build and Run

Open the project in Android Studio and run on your device.

---

## Pose Library

Postur ships with a curated set of poses across three categories:

| Category | Description | Count |
|---|---|---|
| Fitness | Power stances, stretches, athletic poses | ~15 poses |
| Portrait | Photography-friendly portrait poses | ~15 poses |
| Casual | Relaxed everyday poses | ~10 poses |

Poses are stored in `app/src/main/assets/poses.json`. Community contributions of new poses are welcome!

---

## Roadmap

### v0.1 — MVP
- [ ] CameraX + MediaPipe integration
- [ ] White silhouette overlay on camera
- [ ] Basic pose library (30 poses)
- [ ] Pose match % calculation
- [ ] Gemini / Ollama provider abstraction

### v0.2 — Voice Coach
- [ ] Rule-based instant feedback
- [ ] LLM-powered natural language coaching
- [ ] TTS pre-warming for common phrases

### v0.3 — Smart Scene Analysis
- [ ] Gemini Vision scene scanning
- [ ] Auto pose category selection
- [ ] Manual category override in settings

### v1.0 — Play Store Release
- [ ] Polish UI
- [ ] Pose capture + share
- [ ] Play Store listing
- [ ] Open source contributor guide

---

## Contributing

Contributions are very welcome! This project is intentionally open source so the community can:
- Add new poses to the JSON library
- Improve pose match accuracy
- Add new AI provider backends
- Improve the voice coaching prompts

Please open an issue before submitting a large PR so we can discuss the approach.

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

## Author

Built by [@yokesh-mp](https://github.com/yokesh-mp)

*Have feedback or ideas? Open an issue — all suggestions welcome.*
