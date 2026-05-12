import json

import asyncpg
import numpy as np
import redis.asyncio as aioredis

TRACK_META_TTL = 30 * 24 * 3600
SNAPSHOT_TTL = 30 * 24 * 3600


async def get_snapshot_id(redis: aioredis.Redis, playlist_id: str) -> str | None:
    return await redis.get(f"playlist_snap:{playlist_id}")


async def set_snapshot_id(
    redis: aioredis.Redis, playlist_id: str, snapshot_id: str
) -> None:
    await redis.setex(f"playlist_snap:{playlist_id}", SNAPSHOT_TTL, snapshot_id)


async def get_track_meta(redis: aioredis.Redis, track_id: str) -> dict | None:
    raw = await redis.get(f"track_meta:{track_id}")
    return json.loads(raw) if raw else None


async def set_track_meta(redis: aioredis.Redis, track_id: str, meta: dict) -> None:
    await redis.setex(f"track_meta:{track_id}", TRACK_META_TTL, json.dumps(meta))


async def get_genre_embedding(
    pool: asyncpg.Pool, artist_id: str, model_version: int
) -> np.ndarray | None:
    row = await pool.fetchrow(
        "SELECT embedding FROM artist_genre_embeddings WHERE artist_id=$1 AND model_version=$2",
        artist_id,
        model_version,
    )
    return np.array(row["embedding"]) if row else None


async def set_genre_embedding(
    pool: asyncpg.Pool,
    artist_id: str,
    model_version: int,
    embedding: np.ndarray,
) -> None:
    await pool.execute(
        """
        INSERT INTO artist_genre_embeddings (artist_id, model_version, embedding)
        VALUES ($1, $2, $3)
        ON CONFLICT (artist_id, model_version) DO NOTHING
        """,
        artist_id,
        model_version,
        embedding.tolist(),
    )


async def get_lyric_embedding(
    pool: asyncpg.Pool, track_id: str, model_version: int
) -> np.ndarray | None:
    row = await pool.fetchrow(
        "SELECT embedding FROM track_lyric_embeddings WHERE track_id=$1 AND model_version=$2",
        track_id,
        model_version,
    )
    return np.array(row["embedding"]) if row else None


async def set_lyric_embedding(
    pool: asyncpg.Pool,
    track_id: str,
    model_version: int,
    embedding: np.ndarray,
) -> None:
    await pool.execute(
        """
        INSERT INTO track_lyric_embeddings (track_id, model_version, embedding)
        VALUES ($1, $2, $3)
        ON CONFLICT (track_id, model_version) DO NOTHING
        """,
        track_id,
        model_version,
        embedding.tolist(),
    )
