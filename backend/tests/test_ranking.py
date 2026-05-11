import numpy as np
import pytest

from app.services.ranking import mmr_rerank, rank_tracks


def make_vecs(n: int, dim: int = 384, seed: int = 0) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {f"track_{i}": rng.random(dim) for i in range(n)}


def test_rank_tracks_returns_top_k():
    result = rank_tracks(np.ones(384), make_vecs(20), top_k=5)
    assert len(result) == 5


def test_rank_tracks_empty():
    assert rank_tracks(np.ones(384), {}, top_k=5) == []


def test_rank_tracks_fewer_than_k():
    result = rank_tracks(np.ones(384), make_vecs(3), top_k=10)
    assert len(result) == 3


def test_rank_tracks_all_ids_present():
    vecs = make_vecs(10)
    result = rank_tracks(np.ones(384), vecs, top_k=10)
    assert set(result) == set(vecs.keys())


def test_mmr_no_duplicates():
    result = mmr_rerank(np.ones(384), make_vecs(20), top_k=10)
    assert len(result) == 10
    assert len(set(result)) == 10


def test_mmr_empty():
    assert mmr_rerank(np.ones(384), {}, top_k=5) == []


def test_mmr_prefers_relevant_track():
    dim = 384
    prompt = np.zeros(dim)
    prompt[0] = 1.0

    relevant = np.zeros(dim)
    relevant[0] = 1.0
    irrelevant = np.zeros(dim)
    irrelevant[1] = 1.0

    result = mmr_rerank(prompt, {"relevant": relevant, "irrelevant": irrelevant}, top_k=1)
    assert result[0] == "relevant"


def test_mmr_reduces_redundancy():
    dim = 384
    # Prompt cares equally about dims 0 and 1
    prompt = np.zeros(dim)
    prompt[0] = 1.0
    prompt[1] = 1.0

    # clone_a and clone_b are nearly identical — strong on dim 0, nothing on dim 1
    clone_a = np.zeros(dim)
    clone_a[0] = 1.0
    clone_b = clone_a.copy()
    clone_b[0] += 1e-9

    # diverse is strong on dim 1 — different from the clones and still relevant to the prompt
    diverse = np.zeros(dim)
    diverse[1] = 1.0

    result = mmr_rerank(prompt, {"clone_a": clone_a, "clone_b": clone_b, "diverse": diverse}, top_k=2)
    assert "diverse" in result
    assert len(result) == 2
