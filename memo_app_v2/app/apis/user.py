from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.apis.deps import get_db_session
from app.schemas.user import UserCreate, UserLogin
from app.services.user_service import UserService

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/register")
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db_session)):
    user = await UserService(db).register(payload)
    return {"id": user.id, "email": user.email, "message": "회원가입 성공"}


@router.post("/login")
async def login(payload: UserLogin, request: Request, db: AsyncSession = Depends(get_db_session)):
    user = await UserService(db).login(payload)
    request.session.clear()
    request.session["user_id"] = user.id
    request.session["email"] = user.email
    return {"message": "로그인 성공"}


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "로그아웃 성공"}
