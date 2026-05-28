# FastAPI Grid Lab

FastAPI 백엔드에 **PostgreSQL · MongoDB · DynamoDB · Supabase · Pinecone · Weaviate · Neo4j** 를 통합한 멀티-데이터베이스 실습 프로젝트입니다.  
프론트엔드는 HTML + 바닐라 JS SPA로 로그인 및 AG Grid CRUD를 제공합니다.

---

## 목차

1. [기술 스택](#기술-스택)
2. [백엔드 아키텍처](#백엔드-아키텍처)
3. [의존성 상세](#의존성-상세)
   - [PostgreSQL · SQLAlchemy · psycopg](#1-postgresql--sqlalchemy--psycopg)
   - [JWT 인증 · passlib · python-jose](#2-jwt-인증--passlib--python-jose)
   - [DynamoDB · boto3](#3-dynamodb--boto3)
   - [MongoDB · pymongo](#4-mongodb--pymongo)
   - [Supabase · supabase-py](#5-supabase--supabase-py)
   - [Pinecone (Vector DB)](#6-pinecone-vector-db)
   - [Weaviate (Vector DB)](#7-weaviate-vector-db)
   - [Neo4j · GDS (Graph DB)](#8-neo4j--gds-graph-db)
4. [환경변수](#환경변수)
5. [프로젝트 구조](#프로젝트-구조)
6. [실행 방법](#실행-방법)
7. [API 요약](#api-요약)

---

## 기술 스택

### Backend
| 분류 | 기술 | 버전 | 용도 |
|---|---|---|---|
| 언어 | Python | 3.12 | 서버 개발 |
| 웹 프레임워크 | FastAPI | 0.115 | REST API |
| ASGI 서버 | Uvicorn | 0.34 | 비동기 HTTP 서버 |
| ORM | SQLAlchemy | 2.0 | PostgreSQL 모델 & 쿼리 |
| DB 드라이버 | psycopg\[binary\] | 3.2 | PostgreSQL 연결 |
| 인증 | python-jose | 3.3 | JWT 생성·검증 |
| 암호화 | passlib\[bcrypt\] | 1.7 | 비밀번호 해싱 |
| 설정 관리 | pydantic-settings | 2.8 | 환경변수 파싱 (APP\_ 접두사) |
| AWS SDK | boto3 | 1.37 | DynamoDB CRUD |
| MongoDB 드라이버 | pymongo | 4.10 | MongoDB CRUD |
| Supabase 클라이언트 | supabase-py | 2.11 | Supabase REST API |
| Vector DB (cloud) | pinecone | 5.4 | 벡터 저장·검색 |
| Vector DB (self-host) | weaviate-client | 4.9 | 벡터 저장·검색 |
| Graph DB | neo4j | 5.26 | 그래프 저장·분석 |

### Database
| 유형 | 기술 | 역할 |
|---|---|---|
| RDBMS | PostgreSQL 16 | 사용자·게시글·lab_records |
| Document | MongoDB | lab documents |
| Key-Value/Wide-column | AWS DynamoDB | Employee 엔티티 |
| BaaS | Supabase (PostgreSQL) | lab_records (Supabase 테이블) |
| Vector | Pinecone | 클라우드 벡터 인덱스 |
| Vector | Weaviate | 로컬 벡터 컬렉션 |
| Graph | Neo4j | Entity 노드·관계·GDS 분석 |

### Frontend
| 분류 | 기술 | 용도 |
|---|---|---|
| 언어 | HTML5 + 바닐라 JS | SPA |
| 데이터 그리드 | AG Grid Community | 게시글 CRUD 표시 |
| CSS | Tailwind CSS (CDN) | UI 스타일 |

---

## 백엔드 아키텍처

`backend/` 패키지는 **계층형(Layered) 아키텍처**로 구성됩니다.

```
backend/
├── main.py                     # FastAPI 앱 조립 (라우터 등록, CORS, startup)
├── config/
│   ├── settings.py             # pydantic-settings — 전체 환경변수 단일 진실 소스
│   └── database.py             # SQLAlchemy engine/session + DynamoDbClientFactory
├── models/
│   ├── user.py                 # SQLAlchemy ORM — User 테이블
│   ├── post.py                 # SQLAlchemy ORM — Post 테이블
│   ├── employee.py             # Pydantic — DynamoDB Employee 스키마
│   ├── lab.py                  # Pydantic — Lab/Vector/Graph 요청·응답 스키마
│   └── schemas.py              # Pydantic — 인증·게시글 요청·응답 스키마
├── repositories/               # 데이터 접근 레이어 (DB 직접 호출)
│   ├── user_repository.py
│   ├── post_repository.py
│   └── employee_repository.py
├── services/                   # 비즈니스 로직 레이어
│   ├── auth_service.py         # 비밀번호 해싱, JWT 발급·검증
│   ├── post_service.py
│   └── employee_service.py
└── api/                        # FastAPI 라우터 레이어
    ├── auth_router.py          # /api/auth/*
    ├── post_router.py          # /api/posts/*
    ├── employee_router.py      # /employees/* (DynamoDB)
    └── lab_router.py           # /lab/* (MongoDB·PostgreSQL·Supabase·Vector·Graph)
```

**계층 간 의존 방향:** `api → services → repositories → models ← config`  
각 계층은 자신의 아래 계층만 호출하고, 위 계층을 역참조하지 않습니다.

---

## 의존성 상세

### 1. PostgreSQL · SQLAlchemy · psycopg

**역할:** 사용자·게시글 영속 저장 (메인 DB), lab_records 테이블 (lab router)

#### SQLAlchemy 2.0 — ORM vs Core 이중 사용

```python
# ORM 방식 (users / posts 테이블) — backend/config/database.py
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass
```

```python
# Core 방식 (lab_records 테이블) — backend/api/lab_router.py
postgres_table = Table(
    settings.postgresql_table_name, postgres_metadata,
    Column("id", String, primary_key=True),
    Column("tags", JSON, nullable=False),
    ...
)
with engine.begin() as conn:
    conn.execute(insert(postgres_table).values(**data))
```

ORM은 관계가 있는 복잡한 도메인 모델(User ↔ Post)에, Core는 스키마가 단순하고 동적인 lab 테이블에 사용합니다.

#### psycopg 3 (Binary) 드라이버

```
psycopg[binary]==3.2.3
```

`psycopg[binary]`는 C 확장을 미리 컴파일한 wheel을 사용해 순수 Python 구현보다 빠릅니다.  
SQLAlchemy DSN 접두사: `postgresql+psycopg://`

#### Dependency Injection으로 세션 관리

```python
# backend/config/database.py
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 라우터에서 사용
@router.get("/api/posts")
def list_posts(db: Session = Depends(get_db)):
    ...
```

요청당 세션을 열고, 응답 후 반드시 닫아 커넥션 누수를 방지합니다.

---

### 2. JWT 인증 · passlib · python-jose

**역할:** 사용자 비밀번호 해싱 및 stateless JWT 토큰 인증

#### 비밀번호 해싱 — passlib + bcrypt

```python
# backend/services/auth_service.py
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return _pwd_context.hash(password)        # 솔트 자동 생성·포함

def verify_password(raw: str, hashed: str) -> bool:
    return _pwd_context.verify(raw, hashed)   # 타이밍 어택 안전한 비교
```

bcrypt는 비용 파라미터(work factor)로 연산 속도를 조절할 수 있어 brute-force에 강합니다.

#### JWT 발급·검증 — python-jose

```python
def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)  # HS256

def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload.get("sub")   # username
    except JWTError:
        return None
```

`OAuth2PasswordBearer`로 `Authorization: Bearer <token>` 헤더를 자동 추출하고, `get_current_user` 의존성이 토큰을 검증해 User 객체를 주입합니다.

---

### 3. DynamoDB · boto3

**역할:** Employee 엔티티를 AWS DynamoDB에 저장·조회

#### 연결 방식

```python
# backend/config/database.py
import boto3

class DynamoDbClientFactory:
    @staticmethod
    def resource():
        return boto3.resource("dynamodb", region_name=settings.aws_region)

    @staticmethod
    def table():
        return DynamoDbClientFactory.resource().Table(settings.dynamodb_table_name)
```

boto3는 AWS SDK로 환경변수 `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` 또는 IAM Role을 자동으로 읽어 인증합니다.  
로컬 개발 시에는 [LocalStack](https://localstack.cloud/) 또는 [DynamoDB Local](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html)로 대체할 수 있습니다.

#### DynamoDB 데이터 모델 특징

| 항목 | 내용 |
|---|---|
| 기본 키 구조 | Partition Key(`id`) + Sort Key(`name`) 복합 키 |
| 쿼리 방식 | `get_item` (단건), `scan` (전체) |
| 스키마 | Schemaless — 추가 속성 자유롭게 저장 가능 |
| 트랜잭션 | 미사용 (단순 put/delete) |

```python
# backend/repositories/employee_repository.py
def find_by_id_and_name(self, employee_id: str, name: str):
    response = self.table.get_item(Key={"id": employee_id, "name": name})
    return response.get("Item")

def find_all(self) -> list[dict]:
    return self.table.scan().get("Items", [])  # 전체 스캔 — 대용량 시 pagination 필요
```

> **주의:** `scan()`은 테이블 전체를 읽으므로 프로덕션에서는 `query()` + GSI 사용을 권장합니다.

#### 필요 환경변수

```
APP_AWS_REGION=ap-northeast-2
APP_DYNAMODB_TABLE_NAME=Employees
# AWS 자격증명은 별도 환경변수 또는 ~/.aws/credentials
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

---

### 4. MongoDB · pymongo

**역할:** Lab 문서(LabRecord)를 MongoDB 컬렉션에 저장·조회·수정·삭제

#### 연결 및 싱글턴 관리

```python
# backend/api/lab_router.py
from functools import lru_cache
from pymongo import MongoClient

@lru_cache
def _mongo_client():
    return MongoClient(settings.mongodb_uri)

@lru_cache
def _mongo_collection():
    return _mongo_client()[settings.mongodb_db_name][settings.mongodb_collection_name]

@atexit.register
def _close_mongo_client():
    if _mongo_client.cache_info().currsize:
        _mongo_client().close()
```

`lru_cache`로 앱 수명 동안 단일 `MongoClient` 인스턴스를 유지하고, `atexit`으로 종료 시 커넥션 풀을 정리합니다.

#### 주요 작업 패턴

```python
# 생성
collection.insert_one(payload.model_dump())

# 수정 (부분 업데이트)
collection.find_one_and_update(
    {"id": record_id},
    {"$set": changes},
    return_document=ReturnDocument.AFTER,
)

# 조회 (_id 필드 제외)
collection.find({}, {"_id": 0}).limit(limit)
```

`_id`(ObjectId)는 응답에서 제외합니다. MongoDB의 `$set` 연산자는 지정한 필드만 업데이트하므로 PATCH 의미론과 자연스럽게 매핑됩니다.

#### 필요 환경변수

```
APP_MONGODB_URI=mongodb://localhost:27017
APP_MONGODB_DB_NAME=lab_db
APP_MONGODB_COLLECTION_NAME=documents
```

---

### 5. Supabase · supabase-py

**역할:** Supabase 프로젝트의 `lab_records` 테이블에 CRUD (PostgreSQL 기반 BaaS)

#### 연결

```python
from supabase import create_client, Client

@lru_cache
def _supabase_client() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise HTTPException(400, "Supabase 설정이 필요합니다.")
    return create_client(settings.supabase_url, settings.supabase_key)
```

`supabase_url`은 `https://<project-id>.supabase.co`, `supabase_key`는 `anon` 또는 `service_role` 키입니다.

#### 쿼리 빌더 패턴

```python
client = _supabase_client()

# 생성
client.table("lab_records").insert(data).execute()

# 조회
response = client.table("lab_records").select("*").limit(limit).execute()
items = response.data   # list[dict]

# 수정
client.table("lab_records").update(changes).eq("id", record_id).execute()

# 삭제
client.table("lab_records").delete().eq("id", record_id).execute()
```

supabase-py는 PostgREST API를 래핑하므로 실제 통신은 HTTP(S)입니다.  
Row Level Security(RLS)가 활성화된 경우 `service_role` 키를 사용하거나 정책을 맞게 설정해야 합니다.

#### Supabase 테이블 사전 생성 (SQL)

```sql
CREATE TABLE lab_records (
  id      TEXT PRIMARY KEY,
  title   TEXT NOT NULL,
  content TEXT NOT NULL,
  tags    JSONB NOT NULL DEFAULT '[]'
);
```

#### 필요 환경변수

```
APP_SUPABASE_URL=https://<project-id>.supabase.co
APP_SUPABASE_KEY=<anon-or-service-role-key>
APP_SUPABASE_TABLE_NAME=lab_records
```

---

### 6. Pinecone (Vector DB)

**역할:** 벡터 임베딩을 클라우드 인덱스에 upsert·유사도 검색

#### 연결

```python
from pinecone import Pinecone

@lru_cache
def _pinecone_index():
    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index_name)
```

#### Upsert (벡터 저장)

```python
index.upsert(vectors=[{
    "id":       payload.id,
    "values":   payload.values,    # list[float] — 차원 수는 인덱스 생성 시 고정
    "metadata": payload.metadata,  # 임의 dict
}])
```

#### Query (유사도 검색)

```python
result = index.query(
    vector=payload.values,
    top_k=payload.top_k,
    include_metadata=True,
)
matches = result.to_dict().get("matches", [])
# 각 match: {"id": ..., "score": ..., "metadata": {...}}
```

Pinecone의 유사도 기본값은 **cosine similarity**이며, 인덱스 생성 시 `metric="dotproduct"` 또는 `"euclidean"`으로 변경 가능합니다.

#### 인덱스 사전 생성 (Pinecone 콘솔 또는 SDK)

```python
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key="...")
pc.create_index(
    name="lab-vectors",
    dimension=1536,          # 예: OpenAI text-embedding-3-small
    metric="cosine",
    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
)
```

#### 필요 환경변수

```
APP_VECTOR_PROVIDER=pinecone
APP_PINECONE_API_KEY=<your-api-key>
APP_PINECONE_INDEX_NAME=lab-vectors
```

---

### 7. Weaviate (Vector DB)

**역할:** 로컬(또는 자체 호스팅) 벡터 컬렉션에 객체 저장·유사도 검색

#### 연결 (로컬 Docker)

```python
import weaviate

@lru_cache
def _weaviate_client():
    return weaviate.connect_to_local()   # 기본: localhost:8080

@lru_cache
def _weaviate_collection():
    return _weaviate_client().collections.get(settings.weaviate_collection_name)
```

#### Upsert

```python
import uuid

NAMESPACE = uuid.UUID("f33e9e58-8f5e-44cb-a272-4f2f96699e2f")

object_uuid = str(uuid.uuid5(NAMESPACE, payload.id))   # 결정적 UUID
collection.data.insert(
    uuid=object_uuid,
    properties={"external_id": payload.id, "metadata": payload.metadata},
    vector=payload.values,
)
```

`uuid5`(네임스페이스 기반)를 사용해 동일 `id`의 재삽입 시 충돌을 방지합니다.

#### Query (near_vector 검색)

```python
from weaviate.classes.query import MetadataQuery

result = collection.query.near_vector(
    near_vector=payload.values,
    limit=payload.top_k,
    return_metadata=MetadataQuery(distance=True),
)
matches = [
    {"id": obj.uuid, "distance": obj.metadata.distance, "properties": obj.properties}
    for obj in result.objects
]
```

`distance`는 0에 가까울수록 유사합니다 (cosine distance 기준).

#### Weaviate Docker 실행

```bash
docker run -d \
  -p 8080:8080 -p 50051:50051 \
  -e ENABLE_MODULES='' \
  cr.weaviate.io/semitechnologies/weaviate:1.25.0
```

컬렉션 사전 생성:

```python
client.collections.create(
    name="LabVectors",
    vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
)
```

#### 필요 환경변수

```
APP_VECTOR_PROVIDER=weaviate
APP_WEAVIATE_URL=http://localhost:8080
APP_WEAVIATE_COLLECTION_NAME=LabVectors
```

> `APP_VECTOR_PROVIDER` 값으로 `pinecone` 또는 `weaviate` 중 하나를 선택합니다.

---

### 8. Neo4j · GDS (Graph DB)

**역할:** Entity 노드·엣지 저장 및 Graph Data Science(GDS) 알고리즘으로 그래프 분석

#### 연결 (Bolt 프로토콜)

```python
from neo4j import GraphDatabase

@lru_cache
def _neo4j_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,                              # bolt://localhost:7687
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
```

#### 노드 생성 (Cypher — MERGE)

```python
with driver.session(database=settings.neo4j_database) as session:
    result = session.run(
        """
        MERGE (n:Entity {id: $id})
        SET n.label = $label
        RETURN n.id AS id, n.label AS label
        """,
        id=payload.id, label=payload.label,
    ).single()
```

`MERGE`는 존재하면 매치, 없으면 생성합니다 (upsert 의미론).

#### 엣지 생성

```python
session.run(
    """
    MERGE (a:Entity {id: $source})
    MERGE (b:Entity {id: $target})
    MERGE (a)-[r:RELATES_TO]->(b)
    SET r.weight = $weight
    """,
    source=payload.source, target=payload.target, weight=payload.weight,
)
```

#### GDS 그래프 분석 (PageRank / Degree Centrality)

```python
# 1. 가상 그래프 프로젝션 생성
session.run("""
    CALL gds.graph.project(
        $graph_name, 'Entity',
        {RELATES_TO: {orientation: 'NATURAL', properties: 'weight'}}
    )
""", graph_name=graph_name)

# 2. PageRank 스트림
session.run("""
    CALL gds.pageRank.stream($graph_name)
    YIELD nodeId, score
    RETURN gds.util.asNode(nodeId).id AS id, score
    ORDER BY score DESC LIMIT 10
""", graph_name=graph_name)

# 3. Degree Centrality 스트림
session.run("""
    CALL gds.degree.stream($graph_name)
    YIELD nodeId, score
    ...
""")
```

GDS 알고리즘은 **Neo4j GDS 플러그인**이 설치되어 있어야 합니다.  
분석 전 기존 프로젝션을 `gds.graph.drop`으로 제거해 충돌을 방지합니다.

#### Neo4j Docker 실행 (GDS 포함)

```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  neo4j:5.26
```

#### 필요 환경변수

```
APP_NEO4J_URI=bolt://localhost:7687
APP_NEO4J_USER=neo4j
APP_NEO4J_PASSWORD=password
APP_NEO4J_DATABASE=neo4j
APP_NEO4J_GRAPH_NAME=lab_graph
```

---

## 환경변수

모든 환경변수는 `APP_` 접두사를 사용합니다. `.env.example`을 복사해 사용하세요.

```bash
cp .env.example .env
```

| 변수 | 기본값 | 설명 |
|---|---|---|
| `APP_SECRET_KEY` | `change-me-in-production` | JWT 서명 키 |
| `APP_ALGORITHM` | `HS256` | JWT 알고리즘 |
| `APP_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | 토큰 유효 시간 |
| `APP_ALLOWED_ORIGINS` | `http://127.0.0.1:8001,...` | CORS 허용 오리진 |
| `APP_DATABASE_URL` | `postgresql+psycopg://...` | 메인 PostgreSQL |
| `APP_POSTGRESQL_DSN` | `postgresql+psycopg://...` | Lab PostgreSQL |
| `APP_POSTGRESQL_TABLE_NAME` | `lab_records` | Lab 테이블명 |
| `APP_AWS_REGION` | `ap-northeast-2` | DynamoDB 리전 |
| `APP_DYNAMODB_TABLE_NAME` | `Employees` | DynamoDB 테이블명 |
| `APP_MONGODB_URI` | `mongodb://localhost:27017` | MongoDB 연결 문자열 |
| `APP_MONGODB_DB_NAME` | `lab_db` | MongoDB 데이터베이스명 |
| `APP_MONGODB_COLLECTION_NAME` | `documents` | MongoDB 컬렉션명 |
| `APP_SUPABASE_URL` | _(필수)_ | Supabase 프로젝트 URL |
| `APP_SUPABASE_KEY` | _(필수)_ | Supabase API 키 |
| `APP_SUPABASE_TABLE_NAME` | `lab_records` | Supabase 테이블명 |
| `APP_VECTOR_PROVIDER` | `pinecone` | `pinecone` 또는 `weaviate` |
| `APP_PINECONE_API_KEY` | _(필수)_ | Pinecone API 키 |
| `APP_PINECONE_INDEX_NAME` | `lab-vectors` | Pinecone 인덱스명 |
| `APP_WEAVIATE_URL` | `http://localhost:8080` | Weaviate 서버 URL |
| `APP_WEAVIATE_COLLECTION_NAME` | `LabVectors` | Weaviate 컬렉션명 |
| `APP_NEO4J_URI` | `bolt://localhost:7687` | Neo4j Bolt URI |
| `APP_NEO4J_USER` | `neo4j` | Neo4j 사용자 |
| `APP_NEO4J_PASSWORD` | `password` | Neo4j 비밀번호 |
| `APP_NEO4J_DATABASE` | `neo4j` | Neo4j 데이터베이스명 |
| `APP_NEO4J_GRAPH_NAME` | `lab_graph` | GDS 프로젝션 이름 |

---

## 프로젝트 구조

```
grid-lab/
├── backend/
│   ├── main.py              # FastAPI 앱 진입점
│   ├── config/
│   │   ├── settings.py      # 전체 환경변수 정의
│   │   └── database.py      # SQLAlchemy + DynamoDB 팩토리
│   ├── models/
│   │   ├── user.py          # User ORM 모델
│   │   ├── post.py          # Post ORM 모델
│   │   ├── employee.py      # Employee Pydantic 모델
│   │   ├── lab.py           # Lab/Vector/Graph Pydantic 모델
│   │   └── schemas.py       # 인증·게시글 Pydantic 스키마
│   ├── repositories/
│   │   ├── user_repository.py
│   │   ├── post_repository.py
│   │   └── employee_repository.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── post_service.py
│   │   └── employee_service.py
│   └── api/
│       ├── auth_router.py       # /api/auth/*
│       ├── post_router.py       # /api/posts/*
│       ├── employee_router.py   # /employees/*
│       └── lab_router.py        # /lab/*
├── frontend/
│   ├── index.html
│   └── assets/app.js
├── main.py                  # 레거시 호환용 엔트리포인트
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 실행 방법

### 1) PostgreSQL + API (Docker Compose)

```bash
docker compose up --build
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

### 2) 프론트엔드

```bash
python -m http.server 8001
```

브라우저에서 `http://127.0.0.1:8001/frontend/index.html` 접속.

### 3) 외부 서비스 (선택)

각 서비스를 사용하려면 해당 환경변수를 `.env`에 설정하고 서비스를 실행하세요.

```bash
# MongoDB
docker run -d -p 27017:27017 mongo:7

# Weaviate
docker run -d -p 8080:8080 -p 50051:50051 \
  cr.weaviate.io/semitechnologies/weaviate:1.25.0

# Neo4j (GDS 포함)
docker run -d -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["graph-data-science"]' \
  neo4j:5.26
```

Supabase · Pinecone · DynamoDB는 각 클라우드 콘솔에서 자격증명을 발급받아 `.env`에 입력하세요.

### 기본 계정

- username: `admin`
- password: `admin1234`

---

## API 요약

### 인증

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/api/auth/login` | 로그인 + JWT 발급 |
| `GET` | `/api/auth/me` | 현재 사용자 조회 |

### 게시글 (PostgreSQL ORM)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `GET` | `/api/posts` | 목록 (검색 `q`, 페이징 `page/size`, 정렬 `sort`) |
| `GET` | `/api/posts/{id}` | 상세 조회 (`inc_view=true` 시 조회수 증가) |
| `POST` | `/api/posts` | 생성 |
| `PUT` | `/api/posts/{id}` | 수정 (본인 글) |
| `DELETE` | `/api/posts/{id}` | 삭제 (본인 글) |

### Employee (DynamoDB)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/employees` | Employee 생성 (DynamoDB put_item) |
| `GET` | `/employees` | 전체 목록 (scan) |
| `GET` | `/employees/{id}/{name}` | 단건 조회 |
| `DELETE` | `/employees/{id}/{name}` | 삭제 |

### Lab — MongoDB

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/mongo/records` | 문서 생성 |
| `GET` | `/lab/mongo/records` | 목록 조회 |
| `PATCH` | `/lab/mongo/records/{id}` | 부분 수정 |
| `DELETE` | `/lab/mongo/records/{id}` | 삭제 |

### Lab — PostgreSQL Core

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/postgres/records` | 레코드 생성 |
| `GET` | `/lab/postgres/records` | 목록 조회 |
| `PATCH` | `/lab/postgres/records/{id}` | 부분 수정 |
| `DELETE` | `/lab/postgres/records/{id}` | 삭제 |

### Lab — Supabase

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/supabase/records` | 레코드 생성 |
| `GET` | `/lab/supabase/records` | 목록 조회 |
| `PATCH` | `/lab/supabase/records/{id}` | 부분 수정 |
| `DELETE` | `/lab/supabase/records/{id}` | 삭제 |

### Lab — Vector DB (Pinecone / Weaviate)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/vector/upsert` | 벡터 저장 |
| `POST` | `/lab/vector/query` | 유사도 검색 |

### Lab — Neo4j Graph

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/graph/nodes` | Entity 노드 생성 (MERGE) |
| `POST` | `/lab/graph/edges` | RELATES_TO 엣지 생성 |
| `POST` | `/lab/graph/analyze` | GDS 분석 (`pagerank` \| `degree`) |

전체 API 문서: http://127.0.0.1:8000/docs (Swagger UI)
