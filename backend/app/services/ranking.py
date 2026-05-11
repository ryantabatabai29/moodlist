import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def rank_tracks(
    prompt_vec: np.ndarray,
    track_vecs: dict[str, np.ndarray],
    top_k: int,
) -> list[str]:
    if not track_vecs:
        return []

    track_ids = list(track_vecs.keys())
    matrix = np.array([track_vecs[tid] for tid in track_ids])
    scores = cosine_similarity(prompt_vec.reshape(1, -1), matrix)[0]
    ranked = np.argsort(scores)[::-1]
    return [track_ids[i] for i in ranked[:top_k]]


def mmr_rerank(
    prompt_vec: np.ndarray,
    track_vecs: dict[str, np.ndarray],
    top_k: int,
    lmbda: float = 0.5,
) -> list[str]:
    if not track_vecs:
        return []

    track_ids = list(track_vecs.keys())
    matrix = np.array([track_vecs[tid] for tid in track_ids])
    prompt_sims = cosine_similarity(prompt_vec.reshape(1, -1), matrix)[0]

    selected: list[int] = []
    remaining = list(range(len(track_ids)))

    while len(selected) < top_k and remaining:
        if not selected:
            best = max(remaining, key=lambda i: prompt_sims[i])
        else:
            selected_matrix = matrix[selected]
            best = max(
                remaining,
                key=lambda i: lmbda * prompt_sims[i]
                - (1 - lmbda) * float(cosine_similarity(matrix[i].reshape(1, -1), selected_matrix).max()),
            )
        selected.append(best)
        remaining.remove(best)

    return [track_ids[i] for i in selected]
