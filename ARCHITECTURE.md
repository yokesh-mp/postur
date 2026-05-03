# Postur — Architecture Document

> AI-powered pose coach for Android. Real-time silhouette overlay, scene-aware pose suggestion, and LLM voice coaching.

---

## Table of Contents

1. [Overview](#overview)
2. [Core Features](#core-features)
3. [System Architecture](#system-architecture)
4. [AI Layer Design](#ai-layer-design)
5. [Pose Library Design](#pose-library-design)
6. [Low-Latency Design](#low-latency-design)
7. [Thread Model](#thread-model)
8. [Provider Abstraction](#provider-abstraction)
9. [Project Structure](#project-structure)
10. [Tech Stack](#tech-stack)
11. [Development vs Production](#development-vs-production)

---

## Overview

Postur is an open-source Android application that uses AI to suggest poses via a white silhouette overlay on the live camera feed. The user mimics the suggested pose while a real-time voice coach powered by an LLM guides them to match it precisely.

The app is designed with a **dual AI backend** — it runs against a local Ollama instance during development (free, fast, private) and switches to Gemini Flash API for production (low cost, scalable).

---

## Core Features

| Feature | Description |
|---|---|
| Scene Analysis | Gemini Vision / Ollama Vision analyzes the camera frame and selects an appropriate pose category |
| Pose Suggestion | A curated JSON pose library provides skeleton keypoints; LLM decides placement, rotation, and mirroring |
| Silhouette Overlay | White skeleton drawn on live camera feed using Android Canvas, powered by MediaPipe keypoints |
| Real-Time Evaluation | MediaPipe compares user's live skeleton against the target pose, calculating match % per body part |
| Voice Coach | Hybrid rule engine + LLM generates natural language corrections; Android TTS speaks them aloud |
| Prefetching | Next pose is always fetched in the background so switching poses is instant |
| Local-First | Runs against Mac Mini (Ollama) on LAN during dev; falls back to Gemini Flash automatically |

---

## System Architecture

```
User Opens App
      │
      ▼
┌─────────────────────────────────────────────────┐
│               POSTUR ANDROID APP                │
│                                                 │
│  ┌──────────────┐    ┌───────────────────────┐  │
│  │ CameraX      │    │ AI Service Layer      │  │
│  │ (live feed)  │    │ (provider abstracted) │  │
│  └──────┬───────┘    └──────────┬────────────┘  │
│         │                       │               │
│         ▼                       ▼               │
│  ┌──────────────┐    ┌───────────────────────┐  │
│  │ MediaPipe    │    │ OllamaProvider   OR   │  │
│  │ Pose         │    │ GeminiProvider        │  │
│  │ Landmarker   │    │ (same interface)      │  │
│  └──────┬───────┘    └──────────┬────────────┘  │
│         │                       │               │
│         ▼                       ▼               │
│  ┌──────────────────────────────────────────┐   │
│  │           Pose Overlay Engine            │   │
│  │  • Draws white silhouette on Canvas      │   │
│  │  • Draws live user skeleton              │   │
│  │  • Calculates match % (every 100ms)      │   │
│  └──────────────────┬───────────────────────┘   │
│                     │                           │
│                     ▼                           │
│  ┌──────────────────────────────────────────┐   │
│  │           Voice Coach Engine             │   │
│  │  • Rule engine → instant feedback        │   │
│  │  • LLM → natural language instruction    │   │
│  │  • TTS → speaks correction aloud         │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## AI Layer Design

Postur uses three distinct AI systems, each with a specific responsibility:

### 1. Vision Model — Scene Understanding
- **Trigger:** Once on app open, or when user taps "Rescan Scene"
- **Input:** Single camera frame (JPEG snapshot)
- **Output:** Structured JSON with pose category, lighting quality, subject count
- **Dev backend:** `llama3.2-vision:11b` via Ollama
- **Prod backend:** Gemini 1.5 Flash Vision

**Prompt:**
```
Analyze this scene. Detect lighting quality, background type,
number of people, indoor or outdoor setting.
Suggest a pose category from: [fitness, portrait, casual, group].

Return ONLY this JSON:
{
  "category": "...",
  "lighting": "good | low | harsh",
  "setting": "indoor | outdoor",
  "subject_count": 1,
  "confidence": 0.0 to 1.0
}
```

---

### 2. MediaPipe Pose Landmarker — Real-Time On-Device
- **Trigger:** Every camera frame (60fps)
- **Output:** 33 body landmark coordinates (x, y, z, visibility)
- **Usage:** Draw user skeleton overlay + calculate pose match %
- **Runs:** 100% on-device, no network, no cost
- **Key landmarks used:** shoulders, elbows, wrists, hips, knees, ankles

---

### 3. LLM — Pose Placement + Voice Coaching

#### Pose Placement (once per pose)
- **Input:** Scene analysis result + selected pose ID
- **Output:** Placement instructions for the skeleton overlay

**Prompt:**
```
Scene: indoor, good lighting, single person, center of frame, facing forward.
Pose category: fitness.
Selected pose: fitness_003 (Power Stance).

Return ONLY this JSON:
{
  "anchor_zone": "MC",
  "mirror": false,
  "rotation_deg": 0,
  "scale_hint": "full_body",
  "tip": "one short pose tip for the user"
}
```

**Anchor zone grid:**
```
┌──────┬──────┬──────┐
│  TL  │  TC  │  TR  │
├──────┼──────┼──────┤
│  ML  │  MC  │  MR  │
├──────┼──────┼──────┤
│  BL  │  BC  │  BR  │
└──────┴──────┴──────┘
```

#### Voice Coaching (every 3-4 seconds when mismatch detected)
- **Input:** Which body parts are misaligned + by how much
- **Output:** One short natural language correction instruction
- **Dev backend:** `gemma3:4b` via Ollama
- **Prod backend:** Gemini 1.5 Flash

**Prompt:**
```
The user is trying to match a pose. These body parts are off:
- Left elbow: 35° off target
- Right knee: 20° off target

Generate ONE short, friendly correction instruction (max 10 words).
Return only the instruction text, nothing else.
```

---

## Pose Library Design

Poses are stored as a local JSON file bundled with the app.

```json
{
  "id": "fitness_001",
  "name": "Power Stance",
  "category": "fitness",
  "difficulty": "easy",
  "tags": ["standing", "full_body", "symmetrical"],
  "keypoints": {
    "left_shoulder":  [0.30, 0.35],
    "right_shoulder": [0.70, 0.35],
    "left_elbow":     [0.20, 0.55],
    "right_elbow":    [0.80, 0.55],
    "left_wrist":     [0.15, 0.72],
    "right_wrist":    [0.85, 0.72],
    "left_hip":       [0.35, 0.60],
    "right_hip":      [0.65, 0.60],
    "left_knee":      [0.35, 0.78],
    "right_knee":     [0.65, 0.78],
    "left_ankle":     [0.35, 0.95],
    "right_ankle":    [0.65, 0.95]
  },
  "default_tip": "Stand tall, feet wider than shoulders"
}
```

**Keypoints are normalized coordinates** (0.0 to 1.0 relative to frame). The Pose Overlay Engine converts these to actual pixel coordinates using the person's bounding box from MediaPipe.

**MVP target:** 30–50 poses across 3 categories (fitness, portrait, casual).

---

## Low-Latency Design

### Guiding Principle
> The camera thread is sacred. Nothing blocks it. Ever.

### Strategy Per Operation

| Operation | Strategy | Result |
|---|---|---|
| App startup | Show default pose instantly, analyze scene in background | Zero perceived wait |
| Pose switching | Always prefetch next pose | ~0ms switch time |
| Skeleton overlay | Pure Canvas math, no network | <16ms always |
| Pose match % | Calculated every 100ms, not every frame | Smooth, no CPU spike |
| Voice feedback | Rule engine first (instant), LLM second (async) | <100ms first response |
| TTS playback | Pre-warm 20 common phrases on startup | Instant audio |
| AI provider | Ping Mac Mini on startup, fallback to Gemini | Seamless switching |

### Prefetch Flow
```
User is on Pose N
      │
      ├── [Background] Fetch Pose N+1 keypoints
      ├── [Background] Get LLM placement for Pose N+1
      └── [Background] Generate tip for Pose N+1

User taps Next
      │
      └── [Instant] Display already-loaded Pose N+1
```

### Voice Coach Hybrid Pipeline
```
Mismatch detected
      │
      ├── [0ms]    Rule engine → instant phrase → TTS cache → play
      └── [async]  LLM call → better instruction → queue for next cycle
```

---

## Thread Model

```
┌─────────────────────────────────────────────────────┐
│  LANE 1 — Camera Thread (60fps, never blocked)      │
│  • CameraX frame capture                            │
│  • MediaPipe pose detection                         │
│  • Canvas draw: target silhouette + user skeleton   │
│  • Reads shared state (never writes to AI layer)    │
├─────────────────────────────────────────────────────┤
│  LANE 2 — AI Coroutine (background, Dispatchers.IO) │
│  • Scene analysis (once on open)                    │
│  • Pose selection + placement                       │
│  • Voice coach LLM calls (throttled, 3-4s min gap) │
│  • Prefetch next pose                               │
│  • Writes results to shared StateFlow               │
├─────────────────────────────────────────────────────┤
│  LANE 3 — Audio Thread                              │
│  • TTS queue management                             │
│  • Pre-warmed audio cache playback                  │
│  • Enforces cooldown between instructions           │
└─────────────────────────────────────────────────────┘
```

Lanes communicate via **Kotlin StateFlow** — Lane 2 updates, Lane 1 observes. No direct calls between lanes.

---

## Provider Abstraction

The entire AI backend is hidden behind a single interface. The app never calls Ollama or Gemini directly.

```kotlin
interface AIProvider {
    suspend fun analyzeScene(frame: Bitmap): SceneResult
    suspend fun getPosePlacement(poseId: String, scene: SceneResult): PlacementResult
    suspend fun getPoseTip(poseId: String): String
    suspend fun getCoachingInstruction(mismatch: PoseMismatch): String
}
```

```kotlin
// Factory picks the right provider at runtime
object AIProviderFactory {
    suspend fun create(): AIProvider {
        return if (isMacMiniReachable()) {
            OllamaProvider(baseUrl = BuildConfig.OLLAMA_URL)
        } else {
            GeminiProvider(apiKey = BuildConfig.GEMINI_API_KEY)
        }
    }
}
```

This means:
- Development uses Ollama (free, fast on LAN)
- Production uses Gemini Flash (cheap, scalable)
- Open source users can plug in any backend

---

## Project Structure

```
postur/
├── app/
│   └── src/main/
│       ├── ai/
│       │   ├── AIProvider.kt              # Interface contract
│       │   ├── OllamaProvider.kt          # Local Mac Mini backend
│       │   ├── GeminiProvider.kt          # Cloud backend
│       │   ├── AIProviderFactory.kt       # Runtime provider selection
│       │   └── models/
│       │       ├── SceneResult.kt
│       │       ├── PlacementResult.kt
│       │       └── PoseMismatch.kt
│       ├── camera/
│       │   ├── CameraManager.kt           # CameraX setup
│       │   └── FrameAnalyzer.kt           # MediaPipe integration
│       ├── pose/
│       │   ├── PoseLibrary.kt             # JSON loader
│       │   ├── PoseOverlayEngine.kt       # Canvas drawing
│       │   ├── PoseMatchCalculator.kt     # Match % logic
│       │   └── PosePrefetcher.kt          # Background prefetch
│       ├── coach/
│       │   ├── VoiceCoach.kt              # Orchestrator
│       │   ├── RuleEngine.kt              # Instant rule-based feedback
│       │   └── TTSManager.kt              # Android TTS + cache
│       ├── ui/
│       │   ├── camera/CameraScreen.kt     # Main screen
│       │   ├── capture/CaptureScreen.kt   # Photo saved screen
│       │   └── settings/SettingsScreen.kt
│       └── assets/
│           └── poses.json                 # Pose library
├── ARCHITECTURE.md                        # This document
├── README.md
├── .gitignore
└── LICENSE (MIT)
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Kotlin |
| UI | Jetpack Compose |
| Camera | CameraX |
| Pose Detection | MediaPipe Pose Landmarker |
| Overlay Drawing | Android Canvas |
| AI (Dev) | Ollama — llama3.2-vision + gemma3:4b |
| AI (Prod) | Gemini 1.5 Flash API |
| Async | Kotlin Coroutines + StateFlow |
| TTS | Android TextToSpeech |
| DI | Hilt |
| Build | Gradle (Kotlin DSL) |

---

## Development vs Production

| Aspect | Development | Production |
|---|---|---|
| AI Backend | Ollama on Mac Mini M4 (LAN) | Gemini 1.5 Flash API |
| Cost | ₹0 | Very low (Flash is cheap) |
| Latency | 10–50ms (LAN) | 200–400ms (internet) |
| Config | `OLLAMA_URL` in local.properties | `GEMINI_API_KEY` in local.properties |
| Switch | Automatic (ping-based) | Automatic fallback |

**For open source contributors:** Clone the repo, run Ollama locally, set `OLLAMA_URL=http://localhost:11434` in `local.properties`, and develop for free with no API keys needed.

---

*Document version: 0.1 — Initial architecture design*
*App version: pre-alpha*
