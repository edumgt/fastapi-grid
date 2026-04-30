# FastAPI Grid Sample (PostgreSQL + SPA)

FastAPI를 PostgreSQL과 연동하고, 프론트엔드는 **HTML + 바닐라 JS SPA**로 로그인 및 AG Grid CRUD를 제공하도록 고도화한 샘플입니다.

## 기술 스택

### Backend
| 분류 | 기술 | 버전 | 용도 |
|------|------|------|------|
| 언어 | Python | 3.12 | 서버 개발 언어 |
| 웹 프레임워크 | [FastAPI](https://fastapi.tiangolo.com/) | 0.115 | REST API 서버 |
| ASGI 서버 | [Uvicorn](https://www.uvicorn.org/) | 0.30 | 비동기 HTTP 서버 |
| ORM | [SQLAlchemy](https://www.sqlalchemy.org/) | 2.0 | DB 모델 & 쿼리 |
| DB 드라이버 | [psycopg](https://www.psycopg.org/) | 3.2 | PostgreSQL 연결 |
| 인증 | [python-jose](https://github.com/mpdavis/python-jose) | 3.3 | JWT 토큰 생성/검증 |
| 암호화 | [passlib](https://passlib.readthedocs.io/) + bcrypt | 1.7 | 비밀번호 해싱 |
| 설정 관리 | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) | 2.3 | 환경변수 관리 |

### Database
| 분류 | 기술 | 버전 | 용도 |
|------|------|------|------|
| RDBMS | [PostgreSQL](https://www.postgresql.org/) | 16 | 메인 데이터베이스 |

### Frontend
| 분류 | 기술 | 용도 |
|------|------|------|
| 언어 | HTML5 + 바닐라 JavaScript | SPA 구현 |
| 데이터 그리드 | [AG Grid Community](https://www.ag-grid.com/) | 게시글 목록 표시 및 CRUD |
| CSS 프레임워크 | [Tailwind CSS](https://tailwindcss.com/) (CDN) | UI 스타일링 |

### Infra / DevOps
| 분류 | 기술 | 용도 |
|------|------|------|
| 컨테이너화 | [Docker](https://www.docker.com/) + Docker Compose | 앱 & DB 컨테이너 실행 |
| CI/CD | [GitHub Actions](https://github.com/features/actions) | lint · test · docker build 자동화 |

## 핵심 기능
- Docker Compose 기반 PostgreSQL 구성
- FastAPI + SQLAlchemy로 DB 영속 CRUD
- JWT 로그인/인증 (`/api/auth/login`, `/api/auth/me`)
- AG Grid 기반 게시글 목록/검색/생성/수정/삭제
- 로그인 후 단일 페이지(SPA)에서 동작

## 실행 방법

### 1) Docker Compose로 DB + API 실행
```bash
docker compose up --build
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

### 2) 프론트엔드 정적 서버 실행
```bash
python -m http.server 8001
```

브라우저에서 `http://127.0.0.1:8001/index.html` 접속.

## 기본 계정
- username: `admin`
- password: `admin1234`

## 주요 파일
- `main.py`: FastAPI 앱, 인증, DB 모델/CRUD
- `index.html`: 로그인 + AG Grid SPA
- `docker-compose.yml`: PostgreSQL/API 컨테이너 구성
- `Dockerfile`: FastAPI 컨테이너 빌드
- `.env.example`: 실행 환경 변수 예시

## API 요약
- `POST /api/auth/login`: 로그인 + JWT 발급
- `GET /api/auth/me`: 내 정보 조회
- `GET /api/posts`: 게시글 목록(검색 `q`, 페이징 `page/size`)
- `POST /api/posts`: 게시글 생성
- `PUT /api/posts/{id}`: 게시글 수정(본인 글)
- `DELETE /api/posts/{id}`: 게시글 삭제(본인 글)
