# Changelog

---

## 2026-04-28 — Initial architecture + ML pipeline

### Project scaffold
- Created full repo structure: `/backend`, `/extension`, root config files
- `docker-compose.yml` — Postgres 16 + Redis 7; migration SQL auto-runs on first start
- `.gitignore` covering Python, Node, `.env`, and Docker volumes
- `.github/workflows/ci.yml` — ruff + pytest for backend; tsc + eslint for extension

### Backend
- `app/main.py` — FastAPI app with CORS middleware and lifespan hook that warms SBERT at startup
- `app/config.py` — pydantic-settings; all weights (α/β/γ), DB URLs, model version are env-var configurable
- `app/schemas.py` — Pydantic models for all request/response types
- `app/db/` — asyncpg connection pool, async Redis client, SQL migration (3 tables: `artist_genre_embeddings`, `track_lyric_embeddings`, `generation_feedback`)
- `app/services/spotify.py` — `SpotifyClient` covering all required endpoints: playlist list, playlist tracks, liked songs, artist batch-fetch, playlist create/populate; exponential backoff on 429s
- `app/services/embeddings.py` — singleton SBERT wrapper (`all-MiniLM-L6-v2`); `build_track_vector` with proportional weight redistribution when sub-vectors are missing
- `app/services/ranking.py` — `rank_tracks` (cosine similarity) and `mmr_rerank` (max-marginal relevance for diversity); both verified with unit tests
- `app/services/cache.py` — Redis ops (snapshot_id, scalar metadata) and Postgres ops (genre/lyric embeddings keyed by `model_version`)
- `app/routers/generate.py` — full generation pipeline: snapshot check → track fetch → concurrent lyric fetch → vector build → MMR rank → Spotify playlist create/populate
- `app/routers/playlists.py` — proxies Spotify playlist list; prepends synthetic "Liked Songs" entry with track count
- `app/routers/feedback.py` — stores anonymous thumbs up/down ratings in Postgres
- `Dockerfile` — Python 3.13, bakes SBERT model at build time
- `pytest.ini` — sets `pythonpath = .` and `asyncio_mode = auto`
- Fixed `requirements.txt` for Python 3.13: upgraded numpy to `>=2.0.0`, upgraded asyncpg to `0.30.0`, removed unused `psycopg2-binary`

### Extension
- Manifest V3, React 18 + TypeScript + Vite build
- `src/auth/pkce.ts` — `generateCodeVerifier` and `generateCodeChallenge` (SHA-256 + base64url)
- `src/auth/auth.ts` — full PKCE flow: start auth, exchange code, silent refresh via refresh token, full revocation
- `src/background/index.ts` — service worker that receives the auth code from `callback.html` and calls `exchangeCode`
- `src/callback/index.ts` — minimal page that reads `?code=` from URL and messages the background SW, then closes
- `src/api/backend.ts` — typed fetch wrappers for `/playlists`, `/generate`, `/feedback`
- `src/popup/Popup.tsx` — state machine: `unauthenticated → idle → loading → result | error`
- Popup components: `PlaylistSelector`, `PromptInput` (with example chips), `SizeSlider`, `GenerateButton`, `ResultView`, `ErrorView`

### ML pipeline — verified working
- All 16 unit tests passing (`test_ranking.py`, `test_embeddings.py`)
- SBERT encodes correctly; similar prompts are geometrically closer than dissimilar ones
- MMR reranking correctly penalises redundant tracks in favour of relevant-but-diverse ones
- Weight redistribution handles missing lyric/genre embeddings without dropping tracks

### Lyrics service — verified working
- `app/services/lyrics.py` — three-tier lookup: exact match (`/api/get`) → structured search (`/api/search?track_name=&artist_name=`) → free-text search (`/api/search?q=`)
- Retry on timeout (up to 2 attempts with 0.5s backoff) eliminates false misses from transient lrclib.net slowness
- Strips BOM, LRC timestamp lines, LRC metadata tags (`[ti:]`, `[ar:]`), and inline timestamps embedded in plain lyric text
- Handles `"plainLyrics": null` correctly via `or ""` fallback
- Test coverage on 24-track diverse sample: 23/24 hits (96%); sole miss is an instrumental (Clair de Lune) with no lyrics by definition
- Musixmatch fallback deferred — lrclib.net coverage is sufficient for MVP

### Decisions made
- `psycopg2-binary` removed; `asyncpg` used exclusively for all Postgres access
- Lyrics pipeline implemented ahead of Phase 2 schedule since it was testable without Spotify credentials
- MMR reranking implemented alongside basic cosine similarity (same file, both tested)
- Phase 1 weights (`β=0.90, γ=0.10`) and Phase 2 weights (`α=0.65, β=0.25, γ=0.10`) both configurable via env vars from day one
