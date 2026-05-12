import asyncio
import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]


async def main():
    async with httpx.AsyncClient(timeout=10.0) as client:
        print("=== /api/get (exact match) ===")
        r = await client.get(
            "https://lrclib.net/api/get",
            params={
                "track_name": "Mr. Brightside",
                "artist_name": "The Killers",
            },
        )
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            d = r.json()
            print(f"  trackName: {d.get('trackName')}")
            print(f"  artistName: {d.get('artistName')}")

        print("\n=== /api/search?track_name=...&artist_name=... (structured) ===")
        r = await client.get(
            "https://lrclib.net/api/search",
            params={
                "track_name": "Mr. Brightside",
                "artist_name": "The Killers",
            },
        )
        print(f"Status: {r.status_code}")
        results = r.json() if r.status_code == 200 else []
        for entry in results[:3]:
            print(
                f"  [{entry.get('id')}] {entry.get('artistName')} — {entry.get('trackName')} (has lyrics: {bool(entry.get('plainLyrics') or entry.get('syncedLyrics'))})"
            )

        print("\n=== /api/search?q=Mr. Brightside The Killers (free-text) ===")
        r = await client.get(
            "https://lrclib.net/api/search",
            params={
                "q": "Mr. Brightside The Killers",
            },
        )
        print(f"Status: {r.status_code}")
        results = r.json() if r.status_code == 200 else []
        for entry in results[:3]:
            print(
                f"  [{entry.get('id')}] {entry.get('artistName')} — {entry.get('trackName')} (has lyrics: {bool(entry.get('plainLyrics') or entry.get('syncedLyrics'))})"
            )

        print("\n=== /api/search?q=Mr Brightside The Killers (no period) ===")
        r = await client.get(
            "https://lrclib.net/api/search",
            params={
                "q": "Mr Brightside The Killers",
            },
        )
        print(f"Status: {r.status_code}")
        results = r.json() if r.status_code == 200 else []
        for entry in results[:3]:
            print(
                f"  [{entry.get('id')}] {entry.get('artistName')} — {entry.get('trackName')} (has lyrics: {bool(entry.get('plainLyrics') or entry.get('syncedLyrics'))})"
            )


asyncio.run(main())
