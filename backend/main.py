from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from backend.api.auth_router import router as auth_router
from backend.api.employee_router import router as employee_router
from backend.api.lab_router import router as lab_router
from backend.api.post_router import router as post_router
from backend.config.database import Base, SessionLocal, engine
from backend.config.settings import settings
from backend.models.post import Post  # noqa: F401 – registers ORM model
from backend.models.user import User
from backend.services.auth_service import hash_password

app = FastAPI(title="FastAPI + PostgreSQL + AG Grid", version="2.1.0")

allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(post_router)
app.include_router(employee_router)
app.include_router(lab_router)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    _seed_data()


def _seed_data() -> None:
    with SessionLocal() as db:
        admin = db.scalar(select(User).where(User.username == "admin"))
        if not admin:
            admin = User(username="admin", password_hash=hash_password("admin1234"))
            db.add(admin)
            db.flush()

        if not db.scalar(select(Post).limit(1)):
            for idx in range(1, 16):
                db.add(
                    Post(
                        title=f"샘플 게시글 {idx}",
                        content=f"PostgreSQL 연동 샘플 본문입니다. (#{idx})",
                        views=idx,
                        owner_id=admin.id,
                    )
                )
        db.commit()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "time": datetime.now(timezone.utc).isoformat()}
