import asyncio
import re

import httpx

LRCLIB_BASE = "https://lrclib.net/api"
TIMEOUT = 3.0
MAX_RETRIES = 2


async def fetch_lyrics(track_name: str, artist_name: str) -> str | None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # 1. Exact match
        lyrics = await _try(client, _get_exact, track_name, artist_name)
        if lyrics:
            return lyrics
        # 2. Structured fuzzy search (handles punctuation/spelling differences)
        lyrics = await _try(client, _search_structured, track_name, artist_name)
        if lyrics:
            return lyrics
        # 3. Free-text search as last resort
        return await _try(client, _search_freetext, track_name, artist_name)


async def _try(
    client: httpx.AsyncClient, fn, track_name: str, artist_name: str
) -> str | None:
    for attempt in range(MAX_RETRIES):
        try:
            return await fn(client, track_name, artist_name)
        except httpx.TimeoutException:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(0.5)
        except httpx.HTTPError:
            break
    return None


async def _get_exact(
    client: httpx.AsyncClient, track_name: str, artist_name: str
) -> str | None:
    resp = await client.get(
        f"{LRCLIB_BASE}/get",
        params={"track_name": track_name, "artist_name": artist_name},
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return _extract(resp.json())


async def _search_structured(
    client: httpx.AsyncClient, track_name: str, artist_name: str
) -> str | None:
    resp = await client.get(
        f"{LRCLIB_BASE}/search",
        params={"track_name": track_name, "artist_name": artist_name},
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return _first_with_lyrics(resp.json())


async def _search_freetext(
    client: httpx.AsyncClient, track_name: str, artist_name: str
) -> str | None:
    resp = await client.get(
        f"{LRCLIB_BASE}/search",
        params={"q": f"{track_name} {artist_name}"},
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return _first_with_lyrics(resp.json())


def _first_with_lyrics(results: list) -> str | None:
    for entry in results:
        lyrics = _extract(entry)
        if lyrics:
            return lyrics
    return None


def _extract(data: dict) -> str | None:
    plain = (data.get("plainLyrics") or "").lstrip("﻿").strip()
    if plain and not plain.startswith("["):
        return _strip_inline_timestamps(plain)
    synced = data.get("syncedLyrics") or plain
    return _strip_lrc_timestamps(synced) or None


def _strip_inline_timestamps(text: str) -> str:
    return re.sub(r"\[\d{2}:\d{2}\.\d+\]", "", text).strip()


def _strip_lrc_timestamps(lrc: str) -> str:
    lines = []
    for line in lrc.lstrip("﻿").splitlines():
        if not line.startswith("["):
            if line.strip():
                lines.append(line.strip())
            continue
        bracket_end = line.index("]")
        tag = line[1:bracket_end]
        if not tag[:2].isdigit():
            continue
        text = line[bracket_end + 1 :].strip()
        if text:
            lines.append(text)
    return "\n".join(lines)
