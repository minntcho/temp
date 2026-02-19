from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import get_current_user_id, get_db_session
from app.schemas.memo import MemoCreate, MemoUpdate
from app.services.memo_service import MemoService

router = APIRouter(prefix="/memo", tags=["memo"])


@router.get("/list")
async def list_memos(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    memos = await MemoService(db).list_memos(user_id)
    return [{"id": m.id, "title": m.title, "content": m.content} for m in memos]


@router.post("")
async def create_memo(
    payload: MemoCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    memo = await MemoService(db).add_memo(user_id, payload)
    return {"id": memo.id, "title": memo.title, "content": memo.content}


@router.patch("/{memo_id}")
async def patch_memo(
    memo_id: int,
    payload: MemoUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    memo = await MemoService(db).update_memo(user_id, memo_id, payload)
    return {"id": memo.id, "title": memo.title, "content": memo.content}


@router.delete("/{memo_id}")
async def remove_memo(
    memo_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return await MemoService(db).delete_memo(user_id, memo_id)
