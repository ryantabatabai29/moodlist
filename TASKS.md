# Moodlist — Task Breakdown

Status legend: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` blocked

---

## Phase 1 — Foundation
_Goal: end-to-end pipeline working with genre tags + scalar metadata only. No lyrics yet._

### 1.1 Project Setup
- [ ] Create GitHub repo; add `.gitignore` for Python, Node, `.env`
- [x] Initialize backend: `fastapi`, `uvicorn`, `httpx`, `sentence-transformers`, `scikit-learn`, `redis`, `asyncpg`, `pydantic-settings`
- [x] Initialize extension: Vite + React 18 + TypeScript, Manifest V3 scaffold
- [x] Write `docker-compose.yml` for local Postgres + Redis
- [~] Configure GitHub Actions CI: lint + typecheck on push (file written; not yet run)

### 1.2 Spotify Developer Setup
- [ ] Register Spotify app at developer.spotify.com; record `client_id`
- [ ] Set redirect URI for extension (`chrome-extension://<id>/callback.html`)
- [ ] Confirm required OAuth scopes: `playlist-read-private`, `playlist-read-collaborative`, `user-library-read`, `playlist-modify-private`
- [ ] Apply for extended quota (25-user dev mode is fine for now; start the process early)

### 1.3 OAuth PKCE Flow (Extension)
- [~] Implement PKCE helpers: `generateCodeVerifier`, `generateCodeChallenge` (SHA-256)
- [~] Build `auth.ts`: open Spotify auth URL in a new tab, listen for redirect, extract authorization code
- [~] Exchange code for access + refresh tokens; store both in `chrome.storage.local`
- [~] Implement silent refresh: intercept 401 responses, use refresh token to get new access token, retry
- [~] Handle full revocation: clear storage and re-prompt login

### 1.4 Extension Popup UI
- [~] Scaffold `popup.tsx` with three states: `unauthenticated`, `idle`, `loading`, `result`, `error`
- [~] Unauthenticated state: "Connect Spotify" button
- [~] Idle state:
  - [~] Playlist dropdown (name + track count + cover thumbnail)
  - [~] "Liked Songs" entry at top of dropdown (separate ingestion path)
  - [~] Prompt text input with placeholder examples
  - [~] Track count slider (10–50, default 20)
  - [~] "Generate" button
- [~] Loading state: spinner + estimated time copy
- [~] Result state: playlist name, track count, "Open in Spotify" button
- [~] Error states: auth failure, rate limit, empty result, generic server error

### 1.5 Backend — Spotify Ingestion
- [~] `GET /playlists` endpoint: fetch user's playlists via Spotify, return `[{id, name, track_count, image_url, is_liked_songs}]`
- [~] Track fetcher: paginated `GET /playlists/{id}/tracks` (limit 100 per page)
- [~] Liked Songs fetcher: paginated `GET /me/tracks` (same interface as above)
- [~] Fetch + store playlist `snapshot_id`; skip re-ingestion on cache hit; invalidate on mismatch
- [~] Artist genre fetcher: collect unique artist IDs from tracks; batch `GET /artists` (50 per request)
- [~] Exponential backoff on Spotify 429 responses; surface delay to caller

### 1.6 Backend — Feature Extraction (Phase 1)
- [x] Load `all-MiniLM-L6-v2` at server startup; keep in memory (singleton)
- [x] Genre embedding: join artist genre tags as comma-separated string → SBERT encode → 384-dim vector
- [x] Scalar metadata vector: `[popularity/100, explicit (0/1), duration_ms/max_duration]`
- [x] Unit-normalize each sub-vector; apply weights with proportional redistribution for missing components
- [~] Cache genre embeddings in Postgres: `(artist_id, model_version) → embedding`
- [~] Cache scalar metadata in Redis: `track_id → {popularity, explicit, duration_ms}` with 30-day TTL

### 1.7 Backend — Ranking & Playlist Write
- [~] `POST /generate` endpoint: accepts `{playlist_id, prompt, size, access_token}`
- [x] Prompt embedding: encode prompt string with same SBERT model
- [x] Cosine similarity: `sklearn.cosine_similarity(prompt_vec, track_vecs)` → ranked list
- [x] Return top-k track URIs (k = requested size)
- [~] Create Spotify playlist: `POST /me/playlists` with name `"{prompt} — from {playlist_name}"`
- [~] Set description: source playlist name + prompt + generation date
- [~] Add tracks: `POST /playlists/{id}/tracks`; batch in groups of 100 if needed
- [~] Return `{playlist_url, playlist_name, track_count}` to extension

### 1.8 Phase 1 Integration Test
- [ ] End-to-end manual test: auth → select playlist → prompt → generate → open in Spotify
- [ ] Verify Liked Songs path works independently
- [ ] Verify cache invalidation fires when playlist changes (change a playlist, re-run, confirm re-ingestion)
- [ ] Verify 429 backoff handling doesn't crash the request

---

## Phase 2 — Lyric Intelligence
_Goal: add lrclib.net lyrics + SBERT lyric embeddings; switch to full weighted vector._

### 2.1 Lyrics Fetching
- [x] `lrclib.net` client: exact match → structured search fallback → free-text fallback; 3-second timeout with retry
- [x] Extract plain lyric text (prefer unsynced; strip LRC timestamps and inline timestamps if only synced available)
- [-] Fallback to Musixmatch — deferred; lrclib.net coverage sufficient (96% on test set)
- [ ] Log lyric fetch outcome per track: `hit`, `miss`, `timeout`, `fallback`
- [x] Graceful degradation: tracks with no lyrics get zero lyric embedding; weights auto-redistribute to `β + γ`

### 2.2 Lyric Embedding & Cache
- [x] Encode lyric text with SBERT → 384-dim lyric embedding per track
- [~] Store in Postgres: `(track_id, model_version) → lyric_embedding`
- [~] On ingestion: check Postgres cache first; only call lrclib.net for uncached tracks
- [x] Batch lyric fetches concurrently with `asyncio.gather` (respect 3-second per-track timeout)

### 2.3 Combined Vector & Weights
- [x] Full vector formula: `track_vec = α*norm(lyric_emb) + β*norm(genre_emb) + γ*norm(scalar_vec)`
- [x] Handle missing lyric embedding: redistribute `α` proportionally to `β` and `γ`
- [x] Handle missing genre embedding: redistribute `β` to `α` and `γ`
- [x] Expose `α`, `β`, `γ` as env-var config (no redeploy needed to tune weights)

### 2.4 Cache Layer Hardening
- [x] Postgres migrations: `artist_genre_embeddings`, `track_lyric_embeddings` tables with `model_version` column
- [x] Redis key schema: `track_meta:{track_id}` with 30-day TTL; `playlist_snap:{playlist_id}` with 30-day TTL
- [ ] Log cache hit/miss rates per request for observability

### 2.5 Phase 2 Integration Test
- [ ] Compare ranking output Phase 1 vs Phase 2 on the same playlist + prompt
- [ ] Verify lyric cache hit on second generation of same playlist
- [ ] Confirm zero-lyric tracks are not penalized catastrophically in ranking
- [ ] Measure lyric coverage rate across a test playlist of 100 tracks

---

## Phase 3 — Quality & Polish

### 3.1 Diversity Re-ranking
- [x] Implement max-marginal relevance (MMR): iteratively select tracks that are relevant to prompt but dissimilar to already-selected tracks
- [x] Expose MMR lambda as config (`λ=0.5` default: equal weight relevance vs. diversity)
- [x] Unit test MMR against a playlist with obvious clusters (e.g. 10 nearly identical tracks)

### 3.2 Relevance Feedback
- [~] Add thumbs up / thumbs down to extension result state (per playlist, not per track)
- [~] `POST /feedback` endpoint: store `{playlist_id, prompt, result_track_ids, rating}` in Postgres
- [~] Do not store any user PII — no Spotify user ID, only anonymous session token

### 3.3 Weight Tuning
- [ ] Build a test set of 20 standardized prompts × 3 diverse playlists
- [ ] Run ranking with default weights; score by manual relevance review
- [ ] Sweep `α` in `[0.5, 0.6, 0.65, 0.7, 0.8]`, holding others proportional
- [ ] Update default config to best-performing weights

### 3.4 UX Polish
- [~] Add prompt example chips below the input field (clickable to populate)
- [ ] Show per-track progress during cold generation (e.g. "Fetching lyrics… 34/120")
- [ ] Improve error copy for each error state (rate limit, no lyrics found, no matches above threshold)
- [~] Add "Regenerate" button on result screen (re-runs with same inputs, different MMR seed)

### 3.5 Performance Profiling
- [ ] Profile cold-cache 500-track generation end-to-end; identify bottleneck (ingestion vs. lyric fetch vs. embedding)
- [ ] Ensure total time stays under 15 seconds; optimize the bottleneck step
- [ ] Verify warm-cache path completes in under 5 seconds

---

## Phase 4 — Closed Beta

### 4.1 Infrastructure
- [ ] Provision AWS EC2 instance (or ECS task) sized for SBERT in-process (`all-MiniLM-L6-v2` ~90MB)
- [ ] Provision RDS Postgres instance; run all migrations
- [ ] Provision ElastiCache Redis instance
- [ ] Configure environment variables and secrets (Spotify client_id, Musixmatch key if licensed)
- [ ] Set up basic CloudWatch alarms: CPU, memory, 5xx error rate

### 4.2 CI/CD
- [x] Dockerfile for backend: Python 3.11 slim, pre-download SBERT model at build time
- [~] GitHub Actions: CI file written; not yet run on push
- [ ] Extension build pipeline: `npm run build` → produce zip for both Chrome and Firefox

### 4.3 Beta Rollout
- [ ] Recruit 50 beta users
- [ ] Distribute extension `.zip` via direct download or Chrome Dev Dashboard (unlisted)
- [ ] Instrument logging: generation count, latency, lyric coverage rate, cache hit rate per request
- [ ] Collect thumbs up/down feedback for accuracy audit

### 4.4 Beta Audit
- [ ] Compute lyric coverage rate across beta sessions — evaluate if Musixmatch license is needed
- [ ] Compute accuracy: target ≥80% thumbs up on completed generations
- [ ] Run performance audit: confirm P90 generation time under 15 seconds
- [ ] Review Spotify API quota usage; submit extended quota request if approaching limits

---

## Phase 5 — v1 Launch

### 5.1 Store Submission
- [ ] Write Chrome Web Store listing: description, screenshots, privacy policy
- [ ] Write Firefox Add-ons listing
- [ ] Submit both; address any policy review feedback

### 5.2 Launch Readiness
- [ ] Confirm backend uptime SLO infrastructure (99.5% target)
- [ ] Set up error alerting (Sentry or equivalent)
- [ ] Confirm no deprecated Spotify endpoints in use
- [ ] Smoke test production environment end-to-end before public announcement

### 5.3 Post-Launch
- [ ] Monitor extension store reviews; respond within 48 hours
- [ ] Track 30-day retention and generations-per-user metrics
- [ ] Open v2 planning doc: fine-tuned contrastive model, Safari support, multi-prompt combining

---

## Deferred / v2

- [ ] FAISS index for playlists >10,000 tracks
- [ ] Multi-prompt input ("hype + instrumental") — architecture already supports averaging prompt embeddings
- [ ] Fine-tune SBERT on beta thumbs-up/down data if volume is sufficient
- [ ] Pre-defined mood tag selector as alternative to free-text input
- [ ] Safari / web extension support
- [ ] Monetization decision (freemium vs. donation)
- [ ] Musixmatch commercial license (if lrclib.net coverage is insufficient in beta)
