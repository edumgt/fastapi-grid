from __future__ import annotations

from typing import Literal

from fastapi import HTTPException

from backend.models.post import Post
from backend.models.schemas import PostCreate, PostListResponse, PostOut, PostUpdate
from backend.models.user import User
from backend.repositories.post_repository import PostRepository


def _to_post_out(post: Post) -> PostOut:
    return PostOut(
        id=post.id,
        title=post.title,
        content=post.content,
        views=post.views,
        owner=post.owner.username,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


class PostService:
    def __init__(self, repo: PostRepository):
        self.repo = repo

    def list_posts(
        self,
        q: str,
        page: int,
        size: int,
        sort: Literal["created_at:desc", "views:desc", "id:desc", "id:asc"],
    ) -> PostListResponse:
        total = self.repo.count_filtered(q)
        rows = self.repo.find_all_filtered(q, page, size, sort)
        return PostListResponse(items=[_to_post_out(r) for r in rows], total=total)

    def get_post(self, post_id: int, inc_view: bool) -> PostOut:
        post = self._get_or_404(post_id)
        if inc_view:
            post.views += 1
            post = self.repo.save(post)
        return _to_post_out(post)

    def create_post(self, payload: PostCreate, owner: User) -> PostOut:
        post = Post(title=payload.title, content=payload.content, owner_id=owner.id)
        return _to_post_out(self.repo.save(post))

    def update_post(self, post_id: int, payload: PostUpdate, owner: User) -> PostOut:
        post = self._get_or_404(post_id)
        if post.owner_id != owner.id:
            raise HTTPException(status_code=403, detail="본인 글만 수정할 수 있습니다.")
        if payload.title is not None:
            post.title = payload.title
        if payload.content is not None:
            post.content = payload.content
        return _to_post_out(self.repo.save(post))

    def delete_post(self, post_id: int, owner: User) -> int:
        post = self._get_or_404(post_id)
        if post.owner_id != owner.id:
            raise HTTPException(status_code=403, detail="본인 글만 삭제할 수 있습니다.")
        self.repo.delete(post)
        return post_id

    def _get_or_404(self, post_id: int) -> Post:
        post = self.repo.find_by_id(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="게시글을 찾을 수 없습니다.")
        return post
