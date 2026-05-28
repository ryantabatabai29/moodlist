import asyncio

from fastapi import APIRouter, Header

from app.db.redis_client import get_redis
from app.schemas import PlaylistItem
from app.services.spotify import SpotifyClient

router = APIRouter()

COUNT_TTL = 24 * 3600  # 1 day


@router.get("/playlists", response_model=list[PlaylistItem])
async def get_playlists(authorization: str = Header(...)) -> list[PlaylistItem]:
    access_token = authorization.removeprefix("Bearer ")
    client = SpotifyClient(access_token)
    redis = await get_redis()

    async with client:
        liked_count, raw_playlists = await asyncio.gather(
            client.get_liked_songs_count(),
            client.get_playlists(),
        )

        valid = [pl for pl in raw_playlists if pl is not None]

        async def get_count(playlist_id: str) -> int | None:
            cached = await redis.get(f"playlist_count:{playlist_id}")
            if cached is not None:
                return None if cached == b"unavailable" else int(cached)
            try:
                count = await client.get_playlist_items_count(playlist_id)
                await redis.setex(f"playlist_count:{playlist_id}", COUNT_TTL, count)
                return count
            except Exception:
                await redis.setex(f"playlist_count:{playlist_id}", COUNT_TTL, "unavailable")
                return None

        counts = await asyncio.gather(*[get_count(pl["id"]) for pl in valid])

    items: list[PlaylistItem] = [
        PlaylistItem(
            id="liked_songs",
            name="Liked Songs",
            track_count=liked_count,
            image_url=None,
            is_liked_songs=True,
        )
    ]

    for pl, count in zip(valid, counts):
        images = pl.get("images") or []
        items.append(
            PlaylistItem(
                id=pl["id"],
                name=pl["name"],
                track_count=count,
                image_url=images[0]["url"] if images else None,
                is_liked_songs=False,
            )
        )

    return items
