import asyncio
import logging
from dataclasses import dataclass, field

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


SPOTIFY_BASE = "https://api.spotify.com/v1"
MAX_RETRIES = 5


@dataclass
class SpotifyTrack:
    id: str
    uri: str
    name: str
    artist_ids: list[str]
    artist_names: list[str]
    popularity: int
    explicit: bool
    duration_ms: int


@dataclass
class SpotifyArtist:
    id: str
    name: str
    genres: list[str] = field(default_factory=list)


class SpotifyClient:
    def __init__(self, access_token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        self._http = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self) -> "SpotifyClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.aclose()

    async def get_playlists(self) -> list[dict]:
        items: list[dict] = []
        url: str | None = f"{SPOTIFY_BASE}/me/playlists"
        params: dict | None = {"limit": 50}

        while url:
            data = await self._get(url, params=params)
            items.extend(data.get("items", []))
            url = data.get("next")
            params = None

        return items

    async def get_liked_songs_count(self) -> int:
        data = await self._get(f"{SPOTIFY_BASE}/me/tracks", params={"limit": 1})
        return data["total"]

    async def get_playlist_items_count(self, playlist_id: str) -> int:
        data = await self._get(
            f"{SPOTIFY_BASE}/playlists/{playlist_id}/items",
            params={"limit": 1},
        )
        return data.get("total", 0)

    async def get_playlist_info(self, playlist_id: str) -> dict:
        return await self._get(
            f"{SPOTIFY_BASE}/playlists/{playlist_id}",
            params={"fields": "id,name,snapshot_id,owner.id"},
        )

    async def get_playlist_tracks(self, playlist_id: str) -> list[SpotifyTrack]:
        tracks: list[SpotifyTrack] = []
        url: str | None = f"{SPOTIFY_BASE}/playlists/{playlist_id}/items"
        params: dict | None = {"limit": 100}

        while url:
            data = await self._get(url, params=params)
            for item in data.get("items", []):
                track = item.get("item")
                if track and track.get("id"):
                    tracks.append(_parse_track(track))
            url = data.get("next")
            params = None

        return tracks

    async def get_liked_songs(self) -> list[SpotifyTrack]:
        tracks: list[SpotifyTrack] = []
        url: str | None = f"{SPOTIFY_BASE}/me/tracks"
        params: dict | None = {"limit": 50}

        while url:
            data = await self._get(url, params=params)
            for item in data.get("items", []):
                track = item.get("track")
                if track and track.get("id"):
                    tracks.append(_parse_track(track))
            url = data.get("next")
            params = None

        return tracks

    async def get_artists(self, artist_ids: list[str]) -> list[SpotifyArtist]:
        if not artist_ids:
            return []
        data = await self._get(
            f"{SPOTIFY_BASE}/artists",
            params={"ids": ",".join(artist_ids[:50])},
        )
        return [
            SpotifyArtist(id=a["id"], name=a["name"], genres=a.get("genres", []))
            for a in data.get("artists", [])
            if a
        ]

    async def create_playlist(self, name: str, description: str) -> str:
        data = await self._post(
            f"{SPOTIFY_BASE}/me/playlists",
            json={"name": name, "description": description, "public": False},
        )
        return data["id"]

    async def add_tracks(self, playlist_id: str, track_uris: list[str]) -> None:
        for i in range(0, len(track_uris), 100):
            await self._post(
                f"{SPOTIFY_BASE}/playlists/{playlist_id}/items",
                json={"uris": track_uris[i : i + 100]},
            )

    async def _get(self, url: str, params: dict | None = None) -> dict:
        for attempt in range(MAX_RETRIES):
            resp = await self._http.get(url, headers=self._headers, params=params)

            if resp.status_code == 401:
                raise HTTPException(status_code=401, detail="Spotify token expired")
            if resp.status_code == 403:
                raise HTTPException(status_code=403, detail="Spotify access forbidden")
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 2**attempt))
                await asyncio.sleep(retry_after)
                continue
            if resp.status_code == 404:
                raise HTTPException(
                    status_code=404, detail="Spotify resource not found"
                )
            if not resp.is_success:
                logger.error("Spotify %s %s: %s", resp.status_code, url, resp.text)
            resp.raise_for_status()
            return resp.json()

        raise HTTPException(
            status_code=429, detail="Spotify rate limit — try again later"
        )

    async def _post(self, url: str, json: dict) -> dict:
        resp = await self._http.post(url, headers=self._headers, json=json)
        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Spotify token expired")
        resp.raise_for_status()
        return resp.json()


def _parse_track(raw: dict) -> SpotifyTrack:
    artists = raw.get("artists", [])
    return SpotifyTrack(
        id=raw["id"],
        uri=raw["uri"],
        name=raw["name"],
        artist_ids=[a["id"] for a in artists],
        artist_names=[a["name"] for a in artists],
        popularity=raw.get("popularity", 50),
        explicit=raw.get("explicit", False),
        duration_ms=raw.get("duration_ms", 0),
    )
