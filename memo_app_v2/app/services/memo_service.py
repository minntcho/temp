from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memo import Memo
from app.schemas.memo import MemoCreate, MemoUpdate


class MemoService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_memos(self, user_id: int) -> list[Memo]:
        result = await self.db.scalars(
            select(Memo)
            .where(Memo.owner_id == user_id, Memo.status == 0)
            .order_by(desc(Memo.id))
        )
        return list(result.all())

    async def add_memo(self, user_id: int, payload: MemoCreate) -> Memo:
        memo = Memo(title=payload.title, content=payload.content, owner_id=user_id)
        self.db.add(memo)
        await self.db.commit()
        await self.db.refresh(memo)
        return memo

    async def update_memo(self, user_id: int, memo_id: int, payload: MemoUpdate) -> Memo:
        memo = await self.db.scalar(select(Memo).where(Memo.id == memo_id, Memo.status == 0))
        if not memo:
            raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다.")
        if memo.owner_id != user_id:
            raise HTTPException(status_code=403, detail="수정 권한이 없습니다.")

        if payload.title is not None:
            memo.title = payload.title
        if payload.content is not None:
            memo.content = payload.content

        await self.db.commit()
        await self.db.refresh(memo)
        return memo

    async def delete_memo(self, user_id: int, memo_id: int) -> dict:
        memo = await self.db.scalar(select(Memo).where(Memo.id == memo_id, Memo.status == 0))
        if not memo:
            raise HTTPException(status_code=404, detail="메모를 찾을 수 없습니다.")
        if memo.owner_id != user_id:
            raise HTTPException(status_code=403, detail="삭제 권한이 없습니다.")

        memo.status = 1
        await self.db.commit()
        return {"message": "삭제 완료"}
