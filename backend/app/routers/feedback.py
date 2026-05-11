from fastapi import APIRouter

from app.db.postgres import get_pool
from app.schemas import FeedbackRequest

router = APIRouter()


@router.post("/feedback", status_code=204)
async def submit_feedback(req: FeedbackRequest) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO generation_feedback (playlist_id, prompt, result_track_ids, rating)
        VALUES ($1, $2, $3, $4)
        """,
        req.playlist_id,
        req.prompt,
        req.result_track_ids,
        req.rating,
    )
