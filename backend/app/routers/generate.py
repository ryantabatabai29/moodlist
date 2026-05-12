import asyncio
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.db.postgres import get_pool
from app.db.redis_client import get_redis
from app.dependencies import get_embedding_service
from app.schemas import GenerateRequest, GenerateResponse
from app.services.cache import (
    get_genre_embedding,
    get_lyric_embedding,
    get_snapshot_id,
    get_track_meta,
    set_genre_embedding,
    set_lyric_embedding,
    set_snapshot_id,
    set_track_meta,
)
from app.services.lyrics import fetch_lyrics
from app.services.ranking import mmr_rerank
from app.services.spotify import SpotifyClient, SpotifyTrack

router = APIRouter()

MAX_DURATION_MS = 600_000


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    pool = await get_pool()
    redis = await get_redis()
    sbert = get_embedding_service()
    client = SpotifyClient(req.access_token)

    # Fetch tracks and playlist metadata
    if req.playlist_id == "liked_songs":
        tracks = await client.get_liked_songs()
        playlist_name = "Liked Songs"
    else:
        info = await client.get_playlist_info(req.playlist_id)
        playlist_name = info["name"]
        current_snapshot = info["snapshot_id"]
        cached_snapshot = await get_snapshot_id(redis, req.playlist_id)
        tracks = await client.get_playlist_tracks(req.playlist_id)
        if current_snapshot != cached_snapshot:
            await set_snapshot_id(redis, req.playlist_id, current_snapshot)

    if not tracks:
        raise HTTPException(status_code=422, detail="Playlist is empty")

    # Batch-fetch artist objects for genre tags
    artist_ids = list({aid for t in tracks for aid in t.artist_ids})
    artist_map: dict[str, object] = {}
    for i in range(0, len(artist_ids), 50):
        batch = await client.get_artists(artist_ids[i : i + 50])
        for a in batch:
            artist_map[a.id] = a

    # Fetch lyrics concurrently for tracks without a cached lyric embedding
    async def maybe_fetch_lyrics(track: SpotifyTrack) -> tuple[str, str | None]:
        cached = await get_lyric_embedding(pool, track.id, settings.model_version)
        if cached is not None:
            return track.id, None
        artist = track.artist_names[0] if track.artist_names else ""
        lyrics = await fetch_lyrics(track.name, artist)
        return track.id, lyrics

    lyric_results = await asyncio.gather(*[maybe_fetch_lyrics(t) for t in tracks])
    lyrics_by_id = dict(lyric_results)

    # Build per-track vectors
    track_vecs: dict[str, np.ndarray] = {}

    for track in tracks:
        # Scalar metadata (cached in Redis)
        meta = await get_track_meta(redis, track.id)
        if meta is None:
            meta = {
                "popularity": track.popularity,
                "explicit": int(track.explicit),
                "duration_ms": track.duration_ms,
            }
            await set_track_meta(redis, track.id, meta)

        scalar = np.array(
            [
                meta["popularity"] / 100,
                float(meta["explicit"]),
                min(meta["duration_ms"] / MAX_DURATION_MS, 1.0),
            ]
        )

        # Genre embedding (cached in Postgres per primary artist)
        genre_emb: np.ndarray | None = None
        if track.artist_ids:
            genre_emb = await get_genre_embedding(
                pool, track.artist_ids[0], settings.model_version
            )
            if genre_emb is None:
                artist = artist_map.get(track.artist_ids[0])
                if artist and artist.genres:  # type: ignore[union-attr]
                    genre_text = ", ".join(artist.genres)  # type: ignore[union-attr]
                    genre_emb = sbert.encode(genre_text)
                    await set_genre_embedding(
                        pool, track.artist_ids[0], settings.model_version, genre_emb
                    )

        # Lyric embedding (cached in Postgres per track)
        lyric_emb: np.ndarray | None = await get_lyric_embedding(
            pool, track.id, settings.model_version
        )
        if lyric_emb is None:
            lyrics = lyrics_by_id.get(track.id)
            if lyrics:
                lyric_emb = sbert.encode(lyrics)
                await set_lyric_embedding(
                    pool, track.id, settings.model_version, lyric_emb
                )

        track_vecs[track.uri] = sbert.build_track_vector(
            lyric_emb=lyric_emb,
            genre_emb=genre_emb,
            scalar_vec=scalar,
            alpha=settings.lyric_weight,
            beta=settings.genre_weight,
            gamma=settings.scalar_weight,
        )

    if not track_vecs:
        raise HTTPException(status_code=422, detail="No tracks could be embedded")

    # Encode prompt and rank
    prompt_vec = sbert.encode(req.prompt)
    ranked_uris = mmr_rerank(prompt_vec, track_vecs, req.size, settings.mmr_lambda)

    if not ranked_uris:
        raise HTTPException(status_code=422, detail="No tracks matched the prompt")

    # Create Spotify playlist and populate it
    output_name = f"{req.prompt.title()} — from {playlist_name}"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    description = f"Moodlist: '{req.prompt}' from {playlist_name}. Generated {today}."

    new_playlist_id = await client.create_playlist(output_name, description)
    await client.add_tracks(new_playlist_id, ranked_uris)

    return GenerateResponse(
        playlist_url=f"https://open.spotify.com/playlist/{new_playlist_id}",
        playlist_name=output_name,
        track_count=len(ranked_uris),
    )
