from fastapi import APIRouter, Header

from app.schemas import PlaylistItem
from app.services.spotify import SpotifyClient

router = APIRouter()


@router.get("/playlists", response_model=list[PlaylistItem])
async def get_playlists(authorization: str = Header(...)) -> list[PlaylistItem]:
    access_token = authorization.removeprefix("Bearer ")
    client = SpotifyClient(access_token)

    liked_count = await client.get_liked_songs_count()
    raw_playlists = await client.get_playlists()

    items: list[PlaylistItem] = [
        PlaylistItem(
            id="liked_songs",
            name="Liked Songs",
            track_count=liked_count,
            image_url=None,
            is_liked_songs=True,
        )
    ]

    for pl in raw_playlists:
        if pl is None:
            continue
        images = pl.get("images") or []
        items.append(
            PlaylistItem(
                id=pl["id"],
                name=pl["name"],
                track_count=pl.get("tracks", {}).get("total", 0),
                image_url=images[0]["url"] if images else None,
                is_liked_songs=False,
            )
        )

    return items
