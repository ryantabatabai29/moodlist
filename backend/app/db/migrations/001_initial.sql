CREATE TABLE IF NOT EXISTS artist_genre_embeddings (
    artist_id      TEXT    NOT NULL,
    model_version  INTEGER NOT NULL,
    embedding      FLOAT8[] NOT NULL,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (artist_id, model_version)
);

CREATE TABLE IF NOT EXISTS track_lyric_embeddings (
    track_id       TEXT    NOT NULL,
    model_version  INTEGER NOT NULL,
    embedding      FLOAT8[] NOT NULL,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (track_id, model_version)
);

CREATE TABLE IF NOT EXISTS generation_feedback (
    id               SERIAL PRIMARY KEY,
    playlist_id      TEXT    NOT NULL,
    prompt           TEXT    NOT NULL,
    result_track_ids TEXT[]  NOT NULL,
    rating           TEXT    NOT NULL CHECK (rating IN ('up', 'down')),
    created_at       TIMESTAMPTZ DEFAULT NOW()
);
