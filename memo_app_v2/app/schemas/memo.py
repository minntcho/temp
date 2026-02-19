from pydantic import BaseModel, Field


class MemoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class MemoUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    content: str | None = None
