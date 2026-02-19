import os

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.apis import memo, user, view
from app.core.db import lifespan
from app.models import memo as memo_model  # noqa: F401
from app.models import user as user_model  # noqa: F401

app = FastAPI(title="MemoLogin V2", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET_KEY", "dev-secret-key"),
)

app.include_router(view.router)
app.include_router(user.router)
app.include_router(memo.router)
