# Moodlist — Product Requirements Document
Version: 1.1 — Updated April 27, 2026  
Platform: Chrome / Firefox Extension + Backend API

---

## Changelog from v1.0
- **[REMOVED]** Spotify `GET /audio-features` — deprecated by Spotify in November 2024 for new apps; replaced with artist genre tags and scalar track metadata.
- **[UPDATED]** Lyrics sources — Genius replaced as primary (it provides metadata/URLs only, not lyric text); lrclib.net added as free primary source.
- **[UPDATED]** OAuth flow — clarified as PKCE on the extension client with token passed per-request; backend is stateless for auth.
- **[UPDATED]** Feature vector construction — weighted sum of unit-normalized sub-vectors instead of raw concatenation; avoids SBERT embedding dominating by dimensionality.
- **[UPDATED]** Playlist creation endpoint — corrected to `/me/playlists`.
- **[UPDATED]** FAISS threshold — raised to a realistic level; sklearn is sufficient for all playlist sizes at launch.
- **[ADDED]** Liked Songs ingestion path.
- **[ADDED]** Playlist snapshot ID cache invalidation.
- **[UPDATED]** Phase roadmap — restructured to reflect no audio features in Phase 1.

---

## 1. Overview
Moodlist is a browser extension that connects to a user's Spotify account and uses machine learning to generate curated subplaylists from an existing large playlist based on a natural-language mood or vibe prompt. A user selects a playlist, types a prompt — such as "hype", "late-night drive", or "focus session" — and receives a new Spotify playlist populated with a relevant subset of their own tracks.

---

## 2. Problem Statement
Spotify's native filtering is limited to basic sort options with no mood or vibe filter. Users with large, mixed-genre playlists cannot quickly surface the right energy of song for a given context. Existing third-party tools rely on broad algorithmic recommendations rather than the user's own curated library, and manual subplaylist creation is time-consuming.

Spotify provides genre tags and artist metadata for every track via its Web API. Combined with lyric sentiment data from open lyrics sources, these signals make it possible to accurately map songs to moods with lightweight ML — without processing raw audio, depending on deprecated endpoints, or requiring heavy infrastructure.

---

## 3. Goals & Non-Goals

### Goals
- Allow users to generate a mood-based subplaylist from any of their Spotify playlists (including Liked Songs) using a free-text prompt.
- Produce a new Spotify playlist in the user's account containing the matched tracks, openable immediately in Spotify.
- Return results in under 15 seconds for playlists up to 500 songs.
- Achieve relevance accuracy such that at least 80% of returned tracks are rated as a good match by users in beta testing.
- Support Chrome and Firefox at launch.

### Non-Goals (v1)
- No recommendations outside the user's selected playlist — this is not a Spotify Discover replacement.
- No raw audio processing or audio streaming access required.
- No support for podcast episodes or audiobooks.
- No social or sharing features.
- No training a custom model from scratch — pre-trained embeddings only.
- No dependency on deprecated Spotify API endpoints (`/audio-features`, `/audio-analysis`, `/recommendations`).

---

## 4. Target Users
- **Power listeners** — users with 200+ song playlists who actively curate their own libraries and find generic mood playlists insufficient.
- **Context switchers** — users who move between work, gym, commute, and social settings and need different playlist energy for each without manual effort.
- **Music enthusiasts** — users with broad taste who want to extract a specific genre or energy from an eclectic playlist without building one by hand.
- **Early adopters** — tech-savvy Spotify users comfortable installing a browser extension and willing to provide early feedback.

---

## 5. Feature Requirements

### 5.1 Browser Extension UI
- Extension popup opens on click and initiates Spotify OAuth 2.0 PKCE flow **entirely within the extension** (the extension holds the code verifier and exchanges the code for tokens). The backend never manages OAuth state; it receives the access token on each request. [UPDATED]
- Playlist selector: dropdown showing all user playlists (including a "Liked Songs" entry) with track count and cover thumbnail. [ADDED Liked Songs]
- Prompt input: free-text field with placeholder examples ("hype", "chill late night", "focus instrumental").
- Size control: slider to set the number of output tracks (10–50, default 20).
- Generate button triggers the backend pipeline and shows a loading indicator with estimated time.
- On completion, displays the generated playlist name, track count, and a direct "Open in Spotify" button.
- Error states for auth failure, API rate limits, empty result sets, and lyrics service unavailability.
- Access tokens are stored in `chrome.storage.local` (encrypted by the browser); refresh token rotation is handled by the extension. [UPDATED]

### 5.2 Spotify Data Ingestion [UPDATED — audio features removed]
- Fetch all tracks from the selected playlist via paginated `GET /playlists/{id}/tracks`. For Liked Songs, use `GET /me/tracks` instead. [ADDED Liked Songs path]
- Store the playlist `snapshot_id` alongside cached data. On subsequent requests, fetch the current `snapshot_id` and skip ingestion if it matches the cache, invalidate if it does not. [ADDED cache invalidation]
- For each unique artist across all playlist tracks, batch-fetch artist objects via `GET /artists` (up to 50 IDs per request) to retrieve genre tag arrays. [UPDATED — replaces audio features]
- Extracted signals per track:
  - **Genre tags** — comma-joined string of all artist genre tags (e.g. `"indie rock, alternative, shoegaze"`), embedded as text using Sentence-BERT.
  - **Scalar metadata** — `popularity` (0–100, normalized to 0–1), `explicit` (boolean → 0/1), `duration_ms` (normalized).
- Cache genre embeddings in Postgres keyed by artist ID, versioned by model version.
- Cache track-level scalar metadata in Redis with a 30-day TTL.

> **Note on audio features:** `GET /audio-features` and `GET /audio-analysis` were deprecated by Spotify in November 2024 for apps created after that date. This project does not depend on them. If a future Spotify API revision restores these endpoints, energy, valence, tempo, and danceability are high-value signals and should be incorporated in the next feature update.

### 5.3 Lyrics Fetching & NLP Embedding [UPDATED — sources changed]
- **Primary lyrics source: lrclib.net** — free, open, no scraping required. Query using track name + artist name. Returns plain lyric text and synced LRC format. [UPDATED]
- **Fallback: Musixmatch** — requires commercial license for full lyrics; use only if lrclib.net returns no result. Free tier returns 30% of lyrics and is not suitable for production. [UPDATED]
- **Genius is not used as a lyrics source** — the Genius API provides song metadata and annotation URLs only, not lyric text. Scraping Genius HTML violates their ToS. [ADDED clarification]
- Handle missing lyrics gracefully — tracks without lyrics are embedded using genre tags and scalar metadata alone.
- Pass lyric text through Sentence-BERT (`all-MiniLM-L6-v2`) to produce a 384-dimensional embedding vector per song.
- Cache lyric embeddings in Postgres keyed by track ID, versioned by model version.
- Set a 3-second per-track timeout for lrclib.net requests; skip and log if exceeded.

### 5.4 Feature Construction & ML Ranking [UPDATED — vector construction revised]
**Per-track vector construction:**

Each track is represented as a weighted sum of unit-normalized sub-vectors:

```
track_vec = α * normalize(lyric_embedding)
          + β * normalize(genre_embedding)
          + γ * normalize(scalar_metadata_vec)
```

Default weights: `α = 0.65, β = 0.25, γ = 0.10`. These are tunable via backend config and will be empirically optimized during Phase 3 QA. Using a weighted sum of normalized vectors (rather than raw concatenation) prevents any single sub-vector from dominating by dimensionality. [UPDATED]

- `lyric_embedding`: 384-dim SBERT vector from lyric text. Zero vector if lyrics unavailable.
- `genre_embedding`: 384-dim SBERT vector from the comma-joined genre tag string for the track's artist(s).
- `scalar_metadata_vec`: 3-dim vector of `[popularity_norm, explicit, duration_norm]`.

**Prompt encoding and retrieval:**

- Encode the user's free-text prompt using the same Sentence-BERT model.
- Compute cosine similarity between the prompt embedding and each `track_vec`.
- Rank tracks by similarity score; return the top-k tracks where k is the user-specified size.
- Apply max-marginal relevance re-ranking server-side to prevent returning clusters of nearly identical tracks.

**Similarity search:**

Use `sklearn.cosine_similarity` for all playlist sizes at launch. FAISS is not needed until playlists exceed ~10,000 tracks — well beyond the current 500-track scope. [UPDATED — FAISS threshold raised]

### 5.5 Subplaylist Creation [UPDATED — endpoint corrected]
- Create a new Spotify playlist via `POST /me/playlists` (not `/users/{id}/playlists`). [UPDATED]
- Add ranked tracks via `POST /playlists/{id}/tracks` in a single batched request (max 100 tracks per call; batch if size > 100).
- Auto-generated playlist name: `"{Prompt} — from {Source Playlist Name}"` (e.g. `"Hype — from My Liked Songs"`).
- Set playlist description to include the source playlist name, prompt used, and generation date.
- Playlist is created as private by default; user can make it public manually in Spotify.

---

## 6. Technical Architecture

### 6.1 Components
- **Browser extension** — Chrome/Firefox (Manifest V3), React popup UI. Handles OAuth PKCE flow directly; passes access token to backend on each request. Makes no other direct Spotify API calls. [UPDATED]
- **Backend API** — FastAPI (Python 3.11+) handling orchestration, feature extraction, and Spotify write operations. Stateless with respect to auth — receives and forwards the user's access token per request. [UPDATED]
- **Embedding model** — Sentence-BERT (`all-MiniLM-L6-v2`) via the `sentence-transformers` library, running in-process on the backend server. Handles lyric text, genre tag strings, and user prompts.
- **Feature cache** — Redis for track scalar metadata (30-day TTL); Postgres for lyric embeddings and genre embeddings (permanent, versioned by model).
- **Lyrics service** — lrclib.net primary, Musixmatch commercial fallback. Fetched asynchronously with a 3-second timeout per track. [UPDATED]
- **Similarity search** — `sklearn.cosine_similarity` for all launch-era playlists (≤500 tracks).
- **Spotify API** — Spotify Web API v1 for read (playlists, tracks, artist metadata) and write (create playlist, add tracks). No deprecated endpoints used. [UPDATED]

### 6.2 Data Flow [UPDATED]
1. User authenticates via OAuth PKCE in the extension. Tokens stored in `chrome.storage.local`.
2. Extension sends `{playlist_id, prompt, size, access_token}` to `POST /generate`.
3. Backend fetches playlist `snapshot_id`; checks if cache is valid. If valid, skips ingestion. If not, fetches tracks via Spotify.
4. Backend batch-fetches artist objects to get genre tags; checks Postgres genre embedding cache.
5. Backend fetches lyrics concurrently from lrclib.net for all uncached tracks; checks Postgres lyric embedding cache.
6. Track vectors are constructed as weighted sums of normalized sub-vectors. Prompt is embedded using Sentence-BERT.
7. Cosine similarity is computed; top-k tracks are selected and re-ranked for diversity.
8. New Spotify playlist is created via `/me/playlists` and tracks are added.
9. Backend returns playlist URL and metadata to the extension popup.

### 6.3 Tech Stack

| Layer | Technology |
|---|---|
| Extension | Chrome Extension (MV3), React 18, TypeScript |
| Backend | FastAPI (Python 3.11) |
| ML / embeddings | sentence-transformers, scikit-learn |
| Caching | Redis (scalar metadata), PostgreSQL (embeddings) |
| Lyrics | lrclib.net (primary), Musixmatch commercial (fallback) |
| Spotify integration | Spotify Web API v1, OAuth 2.0 PKCE |
| Hosting | AWS EC2/ECS, RDS (Postgres), ElastiCache (Redis) |
| CI/CD | GitHub Actions, Docker |

FAISS removed from v1 stack — reintroduce if playlist scale exceeds 10,000 tracks. [UPDATED]

---

## 7. Performance Requirements

| Metric | Target |
|---|---|
| Generation time (cold, no cache) | < 15 seconds for a 500-track playlist |
| Generation time (warm, cached) | < 5 seconds |
| Similarity search latency | < 100ms for playlists up to 500 tracks (sklearn) |
| Spotify API usage | Stay within 100 req/min; exponential backoff on 429s |
| lrclib.net timeout | 3 seconds per track; gracefully skipped if exceeded |
| Backend uptime | 99.5% monthly |
| Concurrent users at launch | 50 simultaneous generation requests |

---

## 8. Success Metrics

### Launch (first 60 days)
- 500 active users complete at least one subplaylist generation.
- 80%+ user-rated relevance on a post-generation thumbs up/down prompt in the extension.
- Average generation time under 12 seconds across all sessions.
- Extension store rating of 4.0+ stars.

### Engagement (90 days)
- 30% of users who complete a first generation return within 2 weeks to generate another.
- Average of 3+ playlists generated per active user per month.
- Lyric embedding cache hit rate exceeds 60%.
- lrclib.net lyric coverage exceeds 65% across a typical playlist.

---

## 9. Risks & Mitigations [UPDATED]

| Risk | Mitigation |
|---|---|
| Spotify API rate limiting | Batch artist fetches (50 per call), cache aggressively in Redis, implement exponential backoff with user-facing messaging on delay. |
| lrclib.net availability | Async fetch with 3-second timeout; Musixmatch commercial fallback; tracks without lyrics fall back to genre + metadata vectors alone. Target 65%+ lyric coverage. |
| Musixmatch licensing cost | Evaluate lrclib.net coverage in closed beta before signing Musixmatch commercial license. May not be needed if lrclib.net coverage is sufficient. |
| Prompt ambiguity | Provide prompt examples in the UI. In v2, add a pre-defined mood tag selector as an alternative input mode. |
| Spotify OAuth token expiry | Extension handles silent re-auth via refresh token rotation. Users are only re-prompted if the refresh token is fully revoked. |
| Low relevance for niche prompts | Evaluate against a test set of 20 standardized prompts during QA. Tune `α/β/γ` weight config based on results. |
| Spotify developer quota | Apply for extended quota early; the initial 25-user dev quota is sufficient for closed beta while the extension is in review. |
| Data privacy | No user listening history is stored. Track embeddings are keyed by Spotify track ID only. Access tokens are held client-side in `chrome.storage.local` and sent per-request; the backend stores no user credentials. |
| Genre tag sparsity | Some tracks have artists with no Spotify genre tags. In this case, `β` weight is redistributed to `α` (lyric embedding). Tracks with neither lyrics nor genre tags rank purely on scalar metadata. |

---

## 10. Phased Roadmap [UPDATED]

### Phase 1 — Foundation
Spotify OAuth (PKCE in extension), playlist fetch (playlists + Liked Songs), artist genre tag ingestion, basic cosine similarity on genre embeddings + scalar metadata, extension popup UI, Spotify playlist write. Validates the end-to-end pipeline before adding lyric complexity.

### Phase 2 — Lyric Intelligence
lrclib.net integration, Sentence-BERT lyric embeddings, weighted combined vector ranking, Redis + Postgres caching layer, snapshot_id-based cache invalidation.

### Phase 3 — Quality & Polish
Diversity re-ranking (max-marginal relevance), relevance feedback (thumbs up/down stored for future fine-tuning), empirical tuning of `α/β/γ` weights against a standardized prompt test set, prompt example suggestions, refined error state UX.

### Phase 4 — Closed Beta
50-user closed beta, relevance accuracy audit against the 80% target, performance profiling, Musixmatch licensing evaluation based on lrclib.net coverage results, Spotify app quota extension request submitted.

### Phase 5 — v1 Launch
Chrome Web Store and Firefox Add-ons submission, public launch, usage monitoring, roadmap planning for v2 (fine-tuned contrastive model, Safari support, multi-prompt combining, FAISS if user scale justifies it).

---

## 11. Open Questions

| Question | Status |
|---|---|
| **Weight tuning** (`α/β/γ`) — optimal ratio between lyric embeddings, genre embeddings, and scalar metadata. | Requires empirical tuning during Phase 3 QA. Defaults: `α=0.65, β=0.25, γ=0.10`. |
| **Model fine-tuning** — should beta thumbs up/down data be used to fine-tune Sentence-BERT on music-specific mood labels? | Depends on volume and quality of beta feedback. Revisit after Phase 4. |
| **Monetization** — freemium model (e.g. 5 free generations/month) or fully free with optional donation support? | To be decided before public launch. |
| **Playlist naming** — auto-generated names vs. letting users name the subplaylist before generation kicks off. | Needs UX research. Default to auto-generated for v1. |
| **Multi-prompt** — should v1 support combining prompts ("hype + instrumental")? | Likely v2 scope. The weighted-sum vector architecture supports it natively — average the two prompt embeddings before similarity search. |
| **Musixmatch licensing** — is a commercial license needed, or does lrclib.net coverage make it unnecessary? | Evaluate during Phase 4 closed beta before committing. |
