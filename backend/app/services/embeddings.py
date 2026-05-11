import numpy as np
from sentence_transformers import SentenceTransformer

SBERT_DIM = 384


class EmbeddingService:
    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name)

    def encode(self, text: str) -> np.ndarray:
        return self.model.encode(text, normalize_embeddings=False)

    def build_track_vector(
        self,
        lyric_emb: np.ndarray | None,
        genre_emb: np.ndarray | None,
        scalar_vec: np.ndarray,
        alpha: float,
        beta: float,
        gamma: float,
    ) -> np.ndarray:
        # Pad scalar to SBERT dim so all sub-vectors are the same shape
        scalar_padded = np.zeros(SBERT_DIM)
        scalar_padded[: len(scalar_vec)] = scalar_vec

        components: list[tuple[float, np.ndarray]] = []
        if lyric_emb is not None:
            components.append((alpha, lyric_emb))
        if genre_emb is not None:
            components.append((beta, genre_emb))
        components.append((gamma, scalar_padded))

        total_weight = sum(w for w, _ in components)
        result = np.zeros(SBERT_DIM)
        for w, vec in components:
            result += (w / total_weight) * _normalize(vec)
        return result


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec
