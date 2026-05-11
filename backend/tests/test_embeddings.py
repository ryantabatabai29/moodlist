import numpy as np
import pytest

from app.services.embeddings import SBERT_DIM, EmbeddingService, _normalize


def test_normalize_unit_vector():
    vec = np.array([3.0, 4.0])
    result = _normalize(vec)
    assert abs(np.linalg.norm(result) - 1.0) < 1e-6


def test_normalize_zero_vector():
    vec = np.zeros(5)
    np.testing.assert_array_equal(_normalize(vec), vec)


@pytest.fixture(scope="module")
def sbert():
    return EmbeddingService("all-MiniLM-L6-v2")


def test_encode_shape(sbert):
    assert sbert.encode("hype workout music").shape == (SBERT_DIM,)


def test_build_vector_all_components(sbert):
    lyric = np.random.rand(SBERT_DIM)
    genre = np.random.rand(SBERT_DIM)
    scalar = np.array([0.8, 0.0, 0.5])
    result = sbert.build_track_vector(lyric, genre, scalar, 0.65, 0.25, 0.10)
    assert result.shape == (SBERT_DIM,)


def test_build_vector_no_lyrics(sbert):
    genre = np.random.rand(SBERT_DIM)
    scalar = np.array([0.5, 0.0, 0.3])
    result = sbert.build_track_vector(None, genre, scalar, 0.65, 0.25, 0.10)
    assert result.shape == (SBERT_DIM,)
    assert np.linalg.norm(result) > 0


def test_build_vector_no_genre(sbert):
    lyric = np.random.rand(SBERT_DIM)
    scalar = np.array([0.5, 1.0, 0.3])
    result = sbert.build_track_vector(lyric, None, scalar, 0.65, 0.25, 0.10)
    assert result.shape == (SBERT_DIM,)


def test_build_vector_only_scalar(sbert):
    scalar = np.array([0.5, 0.0, 0.3])
    result = sbert.build_track_vector(None, None, scalar, 0.65, 0.25, 0.10)
    assert result.shape == (SBERT_DIM,)


def test_similar_prompts_closer_than_dissimilar(sbert):
    from sklearn.metrics.pairwise import cosine_similarity

    hype = sbert.encode("hype energy workout")
    also_hype = sbert.encode("intense high energy gym")
    chill = sbert.encode("relaxing calm ambient")

    sim_same = cosine_similarity(hype.reshape(1, -1), also_hype.reshape(1, -1))[0][0]
    sim_diff = cosine_similarity(hype.reshape(1, -1), chill.reshape(1, -1))[0][0]
    assert sim_same > sim_diff
