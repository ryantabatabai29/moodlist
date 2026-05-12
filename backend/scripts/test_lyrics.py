import asyncio
import sys

sys.path.insert(0, ".")

from app.services.lyrics import fetch_lyrics  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

TRACKS = [
    # Mega-hits
    ("Bohemian Rhapsody", "Queen"),
    ("Blinding Lights", "The Weeknd"),
    ("As It Was", "Harry Styles"),
    ("Heat Waves", "Glass Animals"),
    ("drivers license", "Olivia Rodrigo"),
    # Hip-hop / rap
    ("HUMBLE.", "Kendrick Lamar"),
    ("God's Plan", "Drake"),
    ("Sicko Mode", "Travis Scott"),
    # Indie / alternative
    ("Mr. Brightside", "The Killers"),
    ("Do I Wanna Know?", "Arctic Monkeys"),
    ("The Less I Know the Better", "Tame Impala"),
    ("505", "Arctic Monkeys"),
    # Pop
    ("Levitating", "Dua Lipa"),
    ("Stay", "The Kid LAROI"),
    ("Montero", "Lil Nas X"),
    # Older / classic
    ("Hotel California", "Eagles"),
    ("Sweet Child O' Mine", "Guns N' Roses"),
    ("Smells Like Teen Spirit", "Nirvana"),
    # Non-English
    ("Despacito", "Luis Fonsi"),
    ("Bad Guy", "Billie Eilish"),
    # Instrumental (expect miss)
    ("Clair de Lune", "Claude Debussy"),
    # Deep cuts / less famous
    ("Fourth of July", "Sufjan Stevens"),
    ("Motion Picture Soundtrack", "Radiohead"),
    ("Bloodbuzz Ohio", "The National"),
]


async def main():
    hits, misses = 0, 0
    miss_list = []

    for name, artist in TRACKS:
        await asyncio.sleep(0.5)  # avoid hammering lrclib.net
        lyrics = await fetch_lyrics(name, artist)
        if lyrics:
            preview = lyrics[:60].replace("\n", " ")
            print(f'  HIT   {artist} — {name}: "{preview}…"')
            hits += 1
        else:
            print(f"  MISS  {artist} — {name}")
            miss_list.append(f"{artist} — {name}")
            misses += 1

    total = hits + misses
    print(f"\n{hits}/{total} tracks found ({hits/total*100:.0f}% coverage)")
    if miss_list:
        print("\nMisses:")
        for m in miss_list:
            print(f"  - {m}")


asyncio.run(main())
