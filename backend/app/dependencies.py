from functools import lru_cache
from app.config import settings
from app.services.embeddings import EmbeddingService


@lru_cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(model_name=settings.sbert_model)
