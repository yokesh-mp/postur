# Postur — Architecture Document

> AI-powered pose coach for Android. Real-time silhouette overlay, scene-aware pose suggestion, and LLM voice coaching.

---

## Table of Contents

1. [Overview](#overview)
2. [Core Features](#core-features)
3. [System Architecture](#system-architecture)
4. [API Endpoints](#api-endpoints)
5. [AI Layer Design](#ai-layer-design)
6. [Pose Library Design](#pose-library-design)
7. [Low-Latency Design](#low-latency-design)
8. [Thread Model](#thread-model)
9. [Provider Abstraction](#provider-abstraction)
10. [Project Structure](#project-structure)
11. [Tech Stack](#tech-stack)
12. [Development vs Production](#development-vs-production)

---

## Overview

Postur is an open-source Android application that uses AI to suggest poses via a white silhouette overlay on the live camera feed. The user mimics the suggested pose while a real-time voice coach powered by an LLM guides them to match it precisely.

The system is split into two components:

- **Android App (Kotlin)** — handles camera, real-time pose detection, overlay rendering, and voice playback
- **Python Backend (FastAPI)** — handles all AI logic, prompt engineering, and LLM provider switching

This separation keeps Android code clean and makes the AI layer independently testable and deployable.

---

## Core Features

| Feature | Description |
|---|---|
| Scene Analysis | Vision model analyzes a camera frame and selects an appropriate pose category |
| Pose Suggestion | Curated JSON pose library + LLM decides placement, rotation, and mirroring |
| Silhouette Overlay | White skeleton drawn on live camera feed using Android Canvas + MediaPipe |
| Real-Time Evaluation | MediaPipe compares user's live skeleton against target pose, calculating match % |
| Voice Coach | Hybrid rule engine + LLM generates natural language corrections spoken via TTS |
| Prefetching | Next pose always fetched in background so switching is instant |
| Local-First | FastAPI backend talks to Ollama (dev) or Gemini Flash (prod) automatically |

---

## System Architecture

```
┌─────────────────────────────────────────────────────┐
│               ANDROID APP (Kotlin)                  │
│                                                     │
│  CameraX ──► MediaPipe ──► Canvas Overlay           │
│                  │                                  │
│                  ▼                                  │
│           Pose Match Engine                         │
│                  │                                  │
│                  ▼                                  │
│           Voice Coach (TTS)                         │
│                                                     │
│  All AI calls → HTTP → FastAPI backend              │
└────────────────────┬────────────────────────────────┘
                     │
                     │  HTTP REST
                     │  WiFi on dev / Internet on prod
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│            FASTAPI BACKEND (Python)                 │
│                                                     │
│  POST /analyze-scene     → category + placement     │
│  GET  /next-pose         → pose keypoints + tip     │
│  POST /coach-instruction → one coaching sentence    │
│  GET  /poses             → full pose library        │
│  GET  /health            → provider status          │
│                                                     │
│  Provider abstraction (Ollama ↔ Gemini)             │
└────────────────────┬────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
┌──────────────────┐  ┌──────────────────────┐
│  Ollama (Dev)    │  │  Gemini Flash (Prod)  │
│  Mac Mini M4     │  │  Google Cloud API     │
│  llama3.2-vision │  │  gemini-1.5-flash     │
│  gemma3:4b       │  │                       │
└──────────────────┘  └──────────────────────┘
```

---

## API Endpoints

### `POST /analyze-scene`
Accepts a base64-encoded camera frame. Returns scene analysis and pose placement.

**Request:**
```json
{
  "image": "base64_encoded_jpeg_string",
  "current_category": "fitness"
}
```

**Response:**
```json
{
  "category": "fitness",
  "lighting": "good",
  "setting": "indoor",
  "subject_count": 1,
  "suggested_pose_id": "fitness_003",
  "anchor_zone": "MC",
  "mirror": false,
  "rotation_deg": 0,
  "scale_hint": "full_body",
  "confidence": 0.91
}
```

---

### `GET /next-pose`
Returns the next pose based on category and current pose ID.

**Query params:** `category=fitness&current_id=fitness_002`

**Response:**
```json
{
  "pose": {
    "id": "fitness_003",
    "name": "Warrior Lunge",
    "category": "fitness",
    "difficulty": "medium",
    "keypoints": { "..." : "..." },
    "tip": "Step forward into a deep lunge, keep front knee above ankle"
  },
  "placement": {
    "anchor_zone": "MC",
    "mirror": false,
    "rotation_deg": 5,
    "scale_hint": "full_body"
  }
}
```

---

### `POST /coach-instruction`
Accepts mismatch data. Returns one natural coaching instruction.

**Request:**
```json
{
  "mismatches": [
    { "landmark": "left_elbow", "angle_diff_deg": 35 },
    { "landmark": "right_knee", "angle_diff_deg": 20 }
  ],
  "pose_id": "fitness_003"
}
```

**Response:**
```json
{
  "instruction": "Try bending your left arm a bit more",
  "source": "llm"
}
```

---

### `GET /poses`
Returns the full pose library, optionally filtered by category.

**Query params:** `category=portrait` (optional)

---

### `GET /health`
Returns backend status and active AI provider.

**Response:**
```json
{
  "status": "ok",
  "provider": "ollama",
  "ollama_reachable": true,
  "models": ["llama3.2-vision", "gemma3:4b"]
}
```

---

## AI Layer Design

### 1. Vision Model — Scene Understanding
- **Trigger:** Once on app open, or on user request
- **Input:** Single JPEG frame (base64)
- **Dev model:** `llama3.2-vision:11b` via Ollama
- **Prod model:** `gemini-1.5-flash` (Vision)

**Prompt:**
```
Analyze this scene. Detect lighting quality, background type,
number of people, and whether it is indoor or outdoor.

Return ONLY this JSON:
{
  "category": "fitness | portrait | casual | group",
  "lighting": "good | low | harsh",
  "setting": "indoor | outdoor",
  "subject_count": 1,
  "confidence": 0.0 to 1.0
}
```

---

### 2. MediaPipe Pose Landmarker — On-Device Real-Time
- **Runs:** 100% on Android device, no network, no cost
- **Output:** 33 body landmark coordinates per frame
- **Used for:** Silhouette overlay + pose match % calculation

---

### 3. LLM — Pose Placement

**Prompt:**
```
Scene: indoor, good lighting, single person, center of frame.
Pose category: fitness.
Selected pose: fitness_003 (Warrior Lunge).

Return ONLY this JSON:
{
  "anchor_zone": "MC | ML | MR | TC | BC | TL | TR | BL | BR",
  "mirror": false,
  "rotation_deg": -15 to 15,
  "scale_hint": "full_body | upper_body | lower_body",
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

---

### 4. LLM — Voice Coaching

**Prompt:**
```
The user is matching a pose. These body parts are misaligned:
- left_elbow: 35° off target
- right_knee: 20° off target

Generate ONE short, friendly correction (max 10 words).
Return only the instruction text.
```

---

## Pose Library Design

Poses are stored in `backend/data/poses.json` and served by the FastAPI backend.

```json
{
  "id": "fitness_001",
  "name": "Power Stance",
  "category": "fitness",
  "difficulty": "easy",
  "tags": ["standing", "full_body", "symmetrical"],
  "default_tip": "Stand tall, feet wider than shoulders",
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
  }
}
```

Keypoints are **normalized coordinates** (0.0–1.0 relative to frame). The Android app converts these to pixel coordinates using MediaPipe's bounding box.

**MVP target:** 30 poses across 3 categories (fitness, portrait, casual).

---

## Low-Latency Design

### Core Principle
> The camera thread is sacred. Nothing blocks it. Ever.

### Strategy Per Operation

| Operation | Strategy | Target |
|---|---|---|
| App startup | Show default pose instantly, analyze scene in background | 0ms perceived wait |
| Pose switching | Always prefetch next pose from backend | ~0ms switch |
| Skeleton overlay | Pure Canvas math, no network | <16ms always |
| Pose match % | Calculated every 100ms via timer | Smooth, no CPU spike |
| Voice feedback | Rule engine first (instant), LLM second (async) | <100ms first sound |
| TTS playback | Pre-warm 20 common phrases on startup | Instant audio |
| Backend routing | Ping Ollama on startup, fallback to Gemini | Seamless |

### Prefetch Flow
```
User on Pose N
├── [Background] GET /next-pose → preload Pose N+1
└── User taps Next → Pose N+1 displays instantly
```

### Voice Coach Hybrid Pipeline
```
Mismatch detected
├── [0ms]    Rule engine → instant phrase → TTS cache → play
└── [async]  POST /coach-instruction → LLM → better phrase → queue next
```

---

## Thread Model

```
LANE 1 — Camera Thread (60fps, never blocked)
  CameraX → MediaPipe → Canvas draw (silhouette + user skeleton)
  Reads shared StateFlow. Never makes network calls.

LANE 2 — AI Coroutine (Dispatchers.IO, background)
  Scene analysis  → POST /analyze-scene
  Pose prefetch   → GET  /next-pose
  Coach feedback  → POST /coach-instruction (throttled, 3-4s gap)
  Writes results to shared StateFlow.

LANE 3 — Audio Thread
  TTS queue management
  Pre-warmed audio cache playback
  Enforces cooldown between spoken instructions
```

Lanes communicate exclusively via **Kotlin StateFlow**. No direct cross-lane calls.

---

## Provider Abstraction

All AI logic lives in Python behind a clean abstract interface.

```python
# backend/providers/base.py
from abc import ABC, abstractmethod

class AIProvider(ABC):

    @abstractmethod
    async def analyze_scene(self, image_base64: str) -> dict:
        pass

    @abstractmethod
    async def get_pose_placement(self, pose_id: str, scene: dict) -> dict:
        pass

    @abstractmethod
    async def get_coaching_instruction(self, mismatches: list) -> str:
        pass
```

```python
# backend/providers/__init__.py
import httpx
from .ollama import OllamaProvider
from .gemini import GeminiProvider

async def get_provider() -> AIProvider:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                return OllamaProvider()
    except Exception:
        pass
    return GeminiProvider()
```

The Android app calls one URL. It never knows whether Ollama or Gemini is behind it.

---

## Project Structure

```
postur/
│
├── android/                           ← Kotlin Android app
│   └── app/src/main/
│       ├── camera/
│       │   ├── CameraManager.kt
│       │   └── FrameAnalyzer.kt
│       ├── pose/
│       │   ├── PoseOverlayEngine.kt
│       │   ├── PoseMatchCalculator.kt
│       │   └── PosePrefetcher.kt
│       ├── coach/
│       │   ├── VoiceCoach.kt
│       │   ├── RuleEngine.kt
│       │   └── TTSManager.kt
│       ├── network/
│       │   └── PosturApiClient.kt     ← all HTTP calls to FastAPI
│       └── ui/
│           ├── CameraScreen.kt
│           ├── CaptureScreen.kt
│           └── SettingsScreen.kt
│
├── backend/                           ← Python FastAPI server
│   ├── main.py                        ← app entry point
│   ├── config.py                      ← env config
│   ├── routes/
│   │   ├── scene.py                   ← /analyze-scene
│   │   ├── pose.py                    ← /next-pose, /poses
│   │   └── coach.py                   ← /coach-instruction
│   ├── providers/
│   │   ├── base.py                    ← abstract AIProvider
│   │   ├── ollama.py                  ← Ollama implementation
│   │   └── gemini.py                  ← Gemini implementation
│   ├── data/
│   │   └── poses.json                 ← pose library
│   ├── .env.example
│   └── requirements.txt
│
├── ARCHITECTURE.md
├── README.md
├── .gitignore
└── LICENSE (MIT)
```

---

## Tech Stack

### Android
| Component | Technology |
|---|---|
| Language | Kotlin |
| UI | Jetpack Compose |
| Camera | CameraX |
| Pose Detection | MediaPipe Pose Landmarker |
| Overlay Drawing | Android Canvas |
| HTTP Client | Retrofit + OkHttp |
| Async | Kotlin Coroutines + StateFlow |
| TTS | Android TextToSpeech |
| Dependency Injection | Hilt |

### Backend
| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Framework | FastAPI |
| HTTP Client | httpx (async) |
| AI — Dev | Ollama (llama3.2-vision + gemma3:4b) |
| AI — Prod | Google Gemini 1.5 Flash API |
| Image Handling | Pillow |
| Config | python-dotenv |
| Server | Uvicorn |

---

## Development vs Production

| Aspect | Development | Production |
|---|---|---|
| Backend runs on | Mac Mini M4 (local) | Cloud server / VPS |
| AI provider | Ollama (auto-detected) | Gemini 1.5 Flash |
| Android API URL | `http://[mac-ip]:8000` | `https://api.postur.app` |
| Cost | ₹0 | Very low (Gemini Flash) |
| Config | `.env` file in `/backend` | Environment variables |

### Local Dev Setup
```bash
# Clone the repo
git clone https://github.com/yokesh-mp/postur.git
cd postur/backend

# Install Python dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env → add GEMINI_API_KEY if not using Ollama

# Start Ollama (optional, for free local AI)
OLLAMA_HOST=0.0.0.0 ollama serve

# Pull required models
ollama pull llama3.2-vision
ollama pull gemma3:4b

# Run the backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Open android/ in Android Studio
# Set BASE_URL=http://[your-mac-ip]:8000 in local.properties
```

---

*Document version: 0.2 — Added Python FastAPI backend*
*App version: pre-alpha*
