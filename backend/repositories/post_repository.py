from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.models.post import Post
from backend.models.user import User


class PostRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, post_id: int) -> Post | None:
        return self.db.scalar(
            select(Post).options(selectinload(Post.owner)).where(Post.id == post_id)
        )

    def count_filtered(self, q: str) -> int:
        return self.db.scalar(select(func.count()).select_from(self._build_query(q).subquery())) or 0

    def find_all_filtered(
        self,
        q: str,
        page: int,
        size: int,
        sort: Literal["created_at:desc", "views:desc", "id:desc", "id:asc"],
    ) -> list[Post]:
        order_by_map = {
            "created_at:desc": Post.created_at.desc(),
            "views:desc": Post.views.desc(),
            "id:desc": Post.id.desc(),
            "id:asc": Post.id.asc(),
        }
        return list(
            self.db.scalars(
                self._build_query(q).order_by(order_by_map[sort]).offset((page - 1) * size).limit(size)
            ).all()
        )

    def save(self, post: Post) -> Post:
        self.db.add(post)
        self.db.commit()
        return self.find_by_id(post.id)

    def delete(self, post: Post) -> None:
        self.db.delete(post)
        self.db.commit()

    def _build_query(self, q: str):
        query = select(Post).join(Post.owner).options(selectinload(Post.owner))
        if q:
            query = query.where(
                or_(
                    Post.title.ilike(f"%{q}%"),
                    Post.content.ilike(f"%{q}%"),
                    User.username.ilike(f"%{q}%"),
                )
            )
        return query
