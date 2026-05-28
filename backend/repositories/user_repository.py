from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_username(self, username: str) -> User | None:
        return self.db.scalar(select(User).where(User.username == username))

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user
