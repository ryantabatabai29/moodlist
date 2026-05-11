# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Moodlist — a Chrome/Firefox browser extension + FastAPI backend that generates mood-based Spotify subplaylists from a free-text prompt. A user picks a playlist, types "hype" or "late-night drive", and gets a new private Spotify playlist populated with the best-matching tracks from their own library.

See `PRD.md` for full requirements and `TASKS.md` for the phased task breakdown.

## Repo Structure (intended)

```
/extension        # Chrome/Firefox MV3 extension — React 18 + TypeScript + Vite
/backend          # FastAPI Python backend
/docker-compose.yml
```

## Backend

**Stack:** FastAPI (Python 3.11), sentence-transformers, scikit-learn, httpx, Redis, PostgreSQL.

**Run locally:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
docker-compose up -d          # starts Postgres + Redis
uvicorn app.main:app --reload
```

**Tests:**
```bash
pytest                        # all tests
pytest tests/test_ranking.py  # single file
pytest -k "test_mmr"          # single test by name
```

**Lint / format:**
```bash
ruff check .
ruff format .
```

## Extension

**Stack:** React 18, TypeScript, Vite, Manifest V3.

**Run locally** (loads unpacked into Chrome):
```bash
cd extension
npm install
npm run dev       # watch mode — outputs to dist/
```
Load `extension/dist/` as an unpacked extension in `chrome://extensions`.

**Build for submission:**
```bash
npm run build     # production bundle in dist/
```

**Typecheck / lint:**
```bash
npm run typecheck
npm run lint
```

## Key Architectural Decisions

**OAuth is PKCE on the extension client.** The extension holds the code verifier, exchanges the code for tokens, and stores them in `chrome.storage.local`. The backend is fully stateless for auth — it receives the raw Spotify access token on every request and forwards it to Spotify. There is no server-side session.

**No deprecated Spotify endpoints.** `GET /audio-features`, `GET /audio-analysis`, and `GET /recommendations` were deprecated by Spotify in November 2024 for new apps. Do not use them. Feature signals come from artist genre tags (fetched via `GET /artists`) and scalar track metadata (popularity, explicit, duration).

**Playlist creation uses `POST /me/playlists`.** Not `/users/{id}/playlists`.

**Liked Songs use `GET /me/tracks`.** This is a separate ingestion path from `GET /playlists/{id}/tracks` and must be handled explicitly.

**Cache invalidation uses `snapshot_id`.** On every generation request, fetch the playlist's current `snapshot_id` from Spotify. If it matches the cached value, skip re-ingestion. If not, invalidate and re-ingest.

**Lyrics come from lrclib.net (free, open API), not Genius.** Genius's API does not return lyric text. lrclib.net is the primary source with a 3-second per-track timeout. Musixmatch (commercial) is the fallback — only enable if lrclib.net coverage is insufficient.

**Track vector = weighted sum of unit-normalized sub-vectors:**
```
track_vec = α * norm(lyric_emb) + β * norm(genre_emb) + γ * norm(scalar_vec)
```
Default `α=0.65, β=0.25, γ=0.10`. All three weights are env-var configurable. If a sub-vector is unavailable (no lyrics, no genre tags), redistribute its weight proportionally to the others — never silently drop a track.

**One SBERT model instance, shared.** `all-MiniLM-L6-v2` loads at server startup and stays in memory. It encodes lyric text, genre tag strings, and user prompts. Do not instantiate it per-request.

**Similarity search is sklearn at launch.** `sklearn.cosine_similarity` is sufficient for ≤500 tracks. FAISS is deferred until playlists exceed ~10,000 tracks.

## Caching

| Data | Store | Key | TTL |
|---|---|---|---|
| Track scalar metadata | Redis | `track_meta:{track_id}` | 30 days |
| Genre embeddings | Postgres | `(artist_id, model_version)` | permanent |
| Lyric embeddings | Postgres | `(track_id, model_version)` | permanent |
| Playlist snapshot | Redis | `playlist_snap:{playlist_id}` | 30 days |

When the model is updated, increment `model_version` — old embeddings remain but are ignored.

## Spotify API Rate Limits

- Artist batch: 50 IDs per `GET /artists` request
- Track add: 100 URIs per `POST /playlists/{id}/tracks` request
- Global: 100 req/min; use exponential backoff on 429 responses
