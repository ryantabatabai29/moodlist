from typing import Literal
from pydantic import BaseModel, Field


class PlaylistItem(BaseModel):
    id: str
    name: str
    track_count: int
    image_url: str | None = None
    is_liked_songs: bool = False


class GenerateRequest(BaseModel):
    playlist_id: str
    prompt: str
    size: int = Field(default=20, ge=10, le=50)
    access_token: str


class GenerateResponse(BaseModel):
    playlist_url: str
    playlist_name: str
    track_count: int


class FeedbackRequest(BaseModel):
    playlist_id: str
    prompt: str
    result_track_ids: list[str]
    rating: Literal["up", "down"]
