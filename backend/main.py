from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import pose, scene, coach
from providers import get_provider

app = FastAPI(
    title="Postur API",
    description="AI-powered pose coach backend",
    version="0.1.0"
)

# Allow requests from Android app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(pose.router)
app.include_router(scene.router)
app.include_router(coach.router)


@app.get("/health")
async def health():
    """Check backend status and active AI provider."""
    provider = await get_provider()
    provider_name = type(provider).__name__.replace("Provider", "").lower()
    return {
        "status": "ok",
        "provider": provider_name,
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    return {"message": "Postur API is running 🤸"}