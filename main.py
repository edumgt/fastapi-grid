from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import List, Optional, Literal, Tuple, Iterable

from fastapi import FastAPI, HTTPException, Query, Path, Body, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SortField = Literal["id", "title", "author", "created_at", "updated_at", "views"]
SortDir = Literal["asc", "desc"]

ALLOWED_SORT_FIELDS: Tuple[SortField, ...] = (
    "id",
    "title",
    "author",
    "created_at",
    "updated_at",
    "views",
)
ALLOWED_SORT_DIRS: Tuple[SortDir, ...] = ("asc", "desc")
DEFAULT_SORT: Tuple[SortField, SortDir] = ("created_at", "desc")
SEED_COUNT = 35


# =========================================================
# Swagger(OpenAPI) 메타데이터
# =========================================================
openapi_tags = [
    {"name": "Health", "description": "서버 상태/헬스체크"},
    {"name": "Posts", "description": "게시글 CRUD 및 검색/정렬/페이징"},
]

app = FastAPI(
    title="Board API (FastAPI)",
    description=(
        "간단한 게시판 API 샘플입니다.\n\n"
        "- **검색(q)**: 제목/작성자/본문 포함 검색\n"
        "- **정렬(sort)**: `필드:asc|desc` (예: `created_at:desc`)\n"
        "- **페이징(page,size)**: page는 1부터\n"
        "- **상세조회 inc_view**: 조회수 증가 여부 제어\n"
    ),
    version="1.2.0",
    openapi_tags=openapi_tags,
)

# =========================================================
# CORS (HTML 서버가 8001에서 뜬다는 전제)
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8001", "http://localhost:8001"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# =========================================================
# Models (Swagger 스키마로 그대로 노출)
# =========================================================
class ErrorResponse(BaseModel):
    detail: str = Field(..., description="에러 메시지", examples=["Post not found"])


class PostBase(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="게시글 제목",
        examples=["AG Grid + FastAPI 샘플 공유합니다"],
    )
    author: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="작성자",
        examples=["홍길동"],
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="게시글 본문(최대 5000자)",
        examples=["본문 내용입니다.\n\n- 항목1\n- 항목2"],
    )


class PostCreate(PostBase):
    """게시글 생성 요청 바디"""


class PostUpdate(BaseModel):
    title: Optional[str] = Field(
        None,
        min_length=1,
        max_length=120,
        description="(선택) 제목 수정",
        examples=["제목을 수정했습니다"],
    )
    author: Optional[str] = Field(
        None,
        min_length=1,
        max_length=40,
        description="(선택) 작성자 수정",
        examples=["관리자"],
    )
    content: Optional[str] = Field(
        None,
        min_length=1,
        max_length=5000,
        description="(선택) 본문 수정",
        examples=["본문을 업데이트했습니다."],
    )


class Post(PostBase):
    id: int = Field(..., description="게시글 ID", examples=[1])
    created_at: datetime = Field(..., description="생성 시각(UTC, ISO8601)", examples=["2026-01-09T00:00:00Z"])
    updated_at: datetime = Field(..., description="수정 시각(UTC, ISO8601)", examples=["2026-01-09T00:00:00Z"])
    views: int = Field(0, ge=0, description="조회수", examples=[12])


class PostListResponse(BaseModel):
    items: List[Post] = Field(..., description="현재 페이지 게시글 목록")
    total: int = Field(..., ge=0, description="검색 조건 포함 전체 게시글 수", examples=[35])
    page: int = Field(..., ge=1, description="현재 페이지(1부터)", examples=[1])
    size: int = Field(..., ge=1, le=100, description="페이지 크기", examples=[10])


# =========================================================
# Swagger 예제(Example Responses) - 각 API에 주입
# =========================================================
EX_TIME = "2026-01-09T00:00:00Z"

EX_POST_1 = {
    "id": 1,
    "title": "샘플 게시글 1",
    "author": "홍길동",
    "content": "샘플 본문입니다. (글 번호: 1)\n\nFastAPI + AG Grid + Tailwind 예시.",
    "created_at": EX_TIME,
    "updated_at": EX_TIME,
    "views": 7,
}

EX_POST_1_VIEW_INC = {
    **EX_POST_1,
    "views": 8,
    "updated_at": "2026-01-09T00:01:00Z",
}

EX_POST_LIST = {
    "items": [
        EX_POST_1,
        {
            "id": 2,
            "title": "샘플 게시글 2",
            "author": "홍길동",
            "content": "샘플 본문입니다. (글 번호: 2)\n\nFastAPI + AG Grid + Tailwind 예시.",
            "created_at": EX_TIME,
            "updated_at": EX_TIME,
            "views": 14,
        },
    ],
    "total": 35,
    "page": 1,
    "size": 10,
}

EX_HEALTH = {"ok": True, "time": EX_TIME}
EX_DELETE_OK = {"ok": True, "deleted_id": 1}
EX_404 = {"detail": "Post not found"}


# =========================================================
# In-memory DB (샘플용) + 동시성 Lock
# =========================================================
POSTS: List[Post] = []
NEXT_ID = 1
DB_LOCK = Lock()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def seed() -> None:
    global NEXT_ID
    with DB_LOCK:
        if POSTS:
            return
        now = now_utc()
        for i in range(1, SEED_COUNT + 1):
            POSTS.append(
                Post(
                    id=NEXT_ID,
                    title=f"샘플 게시글 {i}",
                    author="관리자" if i % 3 == 0 else "홍길동",
                    content=f"샘플 본문입니다. (글 번호: {i})\n\nFastAPI + AG Grid + Tailwind 예시.",
                    created_at=now,
                    updated_at=now,
                    views=(i * 7) % 123,
                )
            )
            NEXT_ID += 1


seed()


def get_post_or_404(post_id: int) -> Post:
    for p in POSTS:
        if p.id == post_id:
            return p
    raise HTTPException(status_code=404, detail="Post not found")


def parse_sort(sort: str) -> Tuple[SortField, SortDir]:
    try:
        field_str, dir_str = sort.split(":")
        field = field_str.strip()
        direction = dir_str.strip().lower()
        if field not in ALLOWED_SORT_FIELDS:
            raise ValueError("invalid sort field")
        if direction not in ALLOWED_SORT_DIRS:
            raise ValueError("invalid sort direction")
        return field, direction  # type: ignore[return-value]
    except Exception:
        return DEFAULT_SORT


def normalize_query(query: str) -> str:
    return query.strip().lower()


def filter_posts(items: Iterable[Post], query: str) -> List[Post]:
    s = normalize_query(query)
    if not s:
        return list(items)
    return [
        p for p in items
        if (s in p.title.lower() or s in p.author.lower() or s in p.content.lower())
    ]


def sort_posts(items: List[Post], sort: str) -> List[Post]:
    field, direction = parse_sort(sort)
    reverse = direction == "desc"
    return sorted(items, key=lambda p: getattr(p, field), reverse=reverse)


def paginate_items(items: List[Post], page: int, size: int) -> List[Post]:
    start = (page - 1) * size
    end = start + size
    return items[start:end]


# =========================================================
# API
# =========================================================
@app.get(
    "/api/health",
    tags=["Health"],
    summary="헬스체크",
    description="서버가 살아있는지 확인합니다.",
    responses={
        200: {
            "description": "OK",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "정상 응답",
                            "value": EX_HEALTH,
                        }
                    }
                }
            },
        }
    },
)
def health():
    return {"ok": True, "time": now_utc().isoformat()}


@app.get(
    "/api/posts",
    response_model=PostListResponse,
    tags=["Posts"],
    summary="게시글 목록 조회",
    description="검색(q), 정렬(sort), 페이징(page,size)을 지원합니다.",
    responses={
        200: {
            "description": "OK",
            "content": {
                "application/json": {
                    "examples": {
                        "page1": {
                            "summary": "목록 조회 예시(1페이지, 2개만 축약)",
                            "value": EX_POST_LIST,
                        }
                    }
                }
            },
        }
    },
)
def list_posts(
    q: str = Query(
        "",
        title="검색어",
        description="제목/작성자/본문에서 포함 검색(대소문자 무시)",
        examples=["홍길동"],
    ),
    page: int = Query(1, ge=1, title="페이지", description="1부터 시작", examples=[1]),
    size: int = Query(10, ge=1, le=100, title="페이지 크기", description="1~100", examples=[10]),
    sort: str = Query(
        "created_at:desc",
        title="정렬",
        description="형식: `필드:asc|desc` (예: created_at:desc, views:desc, id:asc)",
        examples=["created_at:desc"],
    ),
):
    items = filter_posts(POSTS, q)
    items = sort_posts(items, sort)
    total = len(items)
    paged = paginate_items(items, page, size)

    return PostListResponse(items=paged, total=total, page=page, size=size)


@app.get(
    "/api/posts/{post_id}",
    response_model=Post,
    tags=["Posts"],
    summary="게시글 상세 조회",
    description="게시글을 1건 조회합니다. 기본값으로 조회수를 증가시킵니다(inc_view=true).",
    responses={
        200: {
            "description": "OK",
            "content": {
                "application/json": {
                    "examples": {
                        "no_view_inc": {
                            "summary": "조회수 증가 없이 조회(inc_view=false)",
                            "value": EX_POST_1,
                        },
                        "view_inc": {
                            "summary": "조회수 증가 포함 조회(inc_view=true)",
                            "value": EX_POST_1_VIEW_INC,
                        },
                    }
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "해당 ID의 게시글이 없음",
            "content": {
                "application/json": {
                    "examples": {
                        "not_found": {"summary": "404 예시", "value": EX_404}
                    }
                }
            },
        },
    },
)
def read_post(
    post_id: int = Path(..., ge=1, title="게시글 ID", description="조회할 게시글의 ID", examples=[1]),
    inc_view: bool = Query(True, title="조회수 증가 여부", description="true면 조회수+1 및 updated_at 갱신", examples=[True]),
):
    with DB_LOCK:
        p = get_post_or_404(post_id)
        if inc_view:
            p.views += 1
            p.updated_at = now_utc()
        return p


@app.post(
    "/api/posts",
    response_model=Post,
    status_code=status.HTTP_201_CREATED,
    tags=["Posts"],
    summary="게시글 생성",
    description="게시글을 생성합니다.",
    responses={
        201: {
            "description": "Created",
            "content": {
                "application/json": {
                    "examples": {
                        "created": {
                            "summary": "생성 성공 예시",
                            "value": {
                                **EX_POST_1,
                                "id": 36,
                                "title": "새 글 제목",
                                "author": "홍길동",
                                "content": "새 글 본문입니다.",
                                "views": 0,
                            },
                        }
                    }
                }
            },
        }
    },
)
def create_post(
    body: PostCreate = Body(
        ...,
        description="생성할 게시글 정보",
        examples={
            "create": {
                "summary": "요청 바디 예시",
                "value": {"title": "새 글 제목", "author": "홍길동", "content": "새 글 본문입니다."},
            }
        },
    ),
):
    global NEXT_ID
    with DB_LOCK:
        now = now_utc()
        p = Post(
            id=NEXT_ID,
            title=body.title,
            author=body.author,
            content=body.content,
            created_at=now,
            updated_at=now,
            views=0,
        )
        POSTS.append(p)
        NEXT_ID += 1
        return p


@app.put(
    "/api/posts/{post_id}",
    response_model=Post,
    tags=["Posts"],
    summary="게시글 수정",
    description="게시글을 수정합니다. `PostUpdate`에서 전달된 필드만 반영합니다.",
    responses={
        200: {
            "description": "OK",
            "content": {
                "application/json": {
                    "examples": {
                        "updated": {
                            "summary": "수정 성공 예시(제목만 수정)",
                            "value": {
                                **EX_POST_1,
                                "title": "제목을 수정했습니다",
                                "updated_at": "2026-01-09T00:02:00Z",
                            },
                        }
                    }
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "해당 ID의 게시글이 없음",
            "content": {
                "application/json": {
                    "examples": {"not_found": {"summary": "404 예시", "value": EX_404}}
                }
            },
        },
    },
)
def update_post(
    post_id: int = Path(..., ge=1, title="게시글 ID", description="수정할 게시글의 ID", examples=[1]),
    body: PostUpdate = Body(
        ...,
        description="수정할 필드(보낸 것만 반영)",
        examples={
            "update_title": {
                "summary": "요청 바디 예시(제목만 수정)",
                "value": {"title": "제목을 수정했습니다"},
            },
            "update_all": {
                "summary": "요청 바디 예시(여러 필드 수정)",
                "value": {"title": "수정 제목", "author": "관리자", "content": "수정 본문"},
            },
        },
    ),
):
    with DB_LOCK:
        p = get_post_or_404(post_id)
        data = body.model_dump(exclude_unset=True)

        for k, v in data.items():
            setattr(p, k, v)

        p.updated_at = now_utc()
        return p


@app.delete(
    "/api/posts/{post_id}",
    tags=["Posts"],
    summary="게시글 삭제",
    description="게시글을 삭제합니다.",
    responses={
        200: {
            "description": "OK",
            "content": {
                "application/json": {
                    "examples": {
                        "deleted": {"summary": "삭제 성공 예시", "value": EX_DELETE_OK}
                    }
                }
            },
        },
        404: {
            "model": ErrorResponse,
            "description": "해당 ID의 게시글이 없음",
            "content": {
                "application/json": {
                    "examples": {"not_found": {"summary": "404 예시", "value": EX_404}}
                }
            },
        },
    },
)
def delete_post(
    post_id: int = Path(..., ge=1, title="게시글 ID", description="삭제할 게시글의 ID", examples=[1]),
):
    with DB_LOCK:
        p = get_post_or_404(post_id)
        POSTS.remove(p)
        return {"ok": True, "deleted_id": post_id}
