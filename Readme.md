# FastAPI Grid Sample

FastAPI 기반의 간단한 게시판 API와 정적 HTML(AG Grid) 클라이언트를 함께 제공하는 데모 프로젝트입니다. 메모리 기반 데이터 스토어를 사용해 CRUD, 검색, 정렬, 페이징 흐름을 빠르게 확인할 수 있습니다.

## 프로젝트 개요
- **목적**: FastAPI + AG Grid 조합으로 게시판 CRUD/검색/정렬/페이징을 빠르게 실습하기 위한 샘플
- **특징**
  - 게시글 CRUD API 제공
  - 제목/작성자/본문 포함 검색 지원
  - 필드 기반 정렬과 페이지네이션 지원
  - Swagger(OpenAPI) 문서 자동 생성
  - CORS 설정으로 로컬 정적 서버와 연동

## 구성
```
.
├─ main.py              # FastAPI 앱/라우팅/모델 정의
├─ index.html           # 정적 HTML 클라이언트(AG Grid)
├─ requirements.txt     # Python 의존성
└─ web/                 # 정적 리소스
```

## 빠른 시작
### 1) FastAPI 서버 기동
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\Activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2) 정적 HTML 서버 실행
```bash
python -m http.server 8001
```

### 3) CORS 허용 주소
필요 시 `main.py`의 `allow_origins`를 환경에 맞게 수정 후 API 서버를 재기동하세요.
```
allow_origins=["http://127.0.0.1:8001", "http://localhost:8001"]
```

## API 문서
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json

## 기능 요약
- **목록 조회**: `/api/posts` (검색 `q`, 정렬 `sort`, 페이징 `page`, `size`)
- **상세 조회**: `/api/posts/{post_id}` (`inc_view`로 조회수 증가 여부 제어)
- **생성/수정/삭제**: `/api/posts` (POST), `/api/posts/{post_id}` (PUT/DELETE)
