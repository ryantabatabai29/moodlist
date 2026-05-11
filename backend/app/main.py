from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.dependencies import get_embedding_service
from app.db.postgres import init_db
from app.db.redis_client import init_redis
from app.routers import playlists, generate, feedback


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_embedding_service()  # warm SBERT at startup
    await init_db()
    await init_redis()
    yield


app = FastAPI(title="Moodlist API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(playlists.router)
app.include_router(generate.router)
app.include_router(feedback.router)
