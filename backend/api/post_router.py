from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.auth_router import get_current_user
from backend.config.database import get_db
from backend.models.schemas import PostCreate, PostListResponse, PostOut, PostUpdate
from backend.models.user import User
from backend.repositories.post_repository import PostRepository
from backend.services.post_service import PostService

router = APIRouter(prefix="/api/posts", tags=["posts"])


def get_post_service(db: Session = Depends(get_db)) -> PostService:
    return PostService(PostRepository(db))


@router.get("", response_model=PostListResponse)
def list_posts(
    q: str = Query(default="", description="title/content/owner 검색어"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    sort: Literal["created_at:desc", "views:desc", "id:desc", "id:asc"] = Query(default="id:desc"),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
) -> PostListResponse:
    _ = current_user
    return service.list_posts(q, page, size, sort)


@router.get("/{post_id}", response_model=PostOut)
def get_post(
    post_id: int,
    inc_view: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
) -> PostOut:
    _ = current_user
    return service.get_post(post_id, inc_view)


@router.post("", response_model=PostOut, status_code=201)
def create_post(
    payload: PostCreate,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
) -> PostOut:
    return service.create_post(payload, current_user)


@router.put("/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    payload: PostUpdate,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
) -> PostOut:
    return service.update_post(post_id, payload, current_user)


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    service: PostService = Depends(get_post_service),
) -> dict:
    deleted_id = service.delete_post(post_id, current_user)
    return {"ok": True, "deleted_id": deleted_id}
