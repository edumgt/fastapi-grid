# FastAPI Grid Lab

FastAPI 백엔드에 **PostgreSQL · MongoDB · DynamoDB · Supabase · Pinecone · Weaviate · Neo4j · Redis · OpenSearch · ClickHouse · Cassandra · Qdrant** 를 통합한 멀티-데이터베이스 실습 프로젝트입니다.  
프론트엔드는 HTML + 바닐라 JS SPA로 로그인, AG Grid CRUD, 그리고 **Canvas 기반 멀티 DB 엔진**(DB 아이콘을 캔버스에서 Grid 노드에 연결하면 해당 DB의 데이터를 가져와 그리드에 합쳐 보여주는 화면)을 제공합니다.

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
   - [Redis (Key-Value)](#9-redis-key-value)
   - [OpenSearch (검색/분석)](#10-opensearch-검색분석)
   - [ClickHouse (OLAP)](#11-clickhouse-olap)
   - [Cassandra (Wide-column)](#12-cassandra-wide-column)
   - [Qdrant (Vector DB)](#13-qdrant-vector-db)
4. [환경변수](#환경변수)
5. [프로젝트 구조](#프로젝트-구조)
6. [실행 방법](#실행-방법)
7. [API 요약](#api-요약)
8. [멀티 DB 엔진 (Canvas)](#멀티-db-엔진-canvas)

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
| Key-Value (OSS) | redis | 5.2 | 캐시/키-값 저장 |
| 검색 엔진 (OSS) | opensearch-py | 2.8 | 문서 검색·인덱싱 |
| OLAP (OSS) | clickhouse-connect | 0.8 | 컬럼형 분석 DB |
| Wide-column (OSS) | cassandra-driver | 3.29 | CQL 기반 wide-column 저장 |
| Vector DB (OSS) | qdrant-client | 1.12 | 벡터 저장·검색 |

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
| Key-Value (OSS) | Redis | lab_records 형태 레코드 (JSON 문자열) |
| 검색/분석 (OSS) | OpenSearch | lab_records 인덱스 |
| OLAP (OSS) | ClickHouse | lab_records 테이블 (MergeTree) |
| Wide-column (OSS) | Cassandra | lab_records 테이블 (CQL) |
| Vector (OSS) | Qdrant | 로컬 벡터 컬렉션 |

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

### 9. Redis (Key-Value)

**역할:** lab_records 와 동일한 구조(id/title/content/tags)의 레코드를 키-값으로 저장 (캐시/세션에 가장 널리 쓰이는 OSS 인메모리 DB)

#### 연결 및 저장 방식

```python
# backend/api/lab_router.py
import redis

@lru_cache
def _redis_client():
    return redis.from_url(settings.redis_url, decode_responses=True)

# key = "lab_record:{id}", value = JSON 문자열
client.set(f"{settings.redis_key_prefix}{data['id']}", json.dumps(data))
```

목록 조회는 `SCAN MATCH "lab_record:*"` 로 키를 모은 뒤 `MGET` 으로 일괄 조회합니다 (`KEYS` 는 블로킹이라 프로덕션에서 지양).

#### Docker 실행

```bash
docker run -d -p 6379:6379 redis:7
```

#### 필요 환경변수

```
APP_REDIS_URL=redis://localhost:6379/0
APP_REDIS_KEY_PREFIX=lab_record:
```

---

### 10. OpenSearch (검색/분석)

**역할:** lab_records 문서를 검색 인덱스에 저장·검색 (Elasticsearch 라이선스 이슈로 OSS 진영에서 널리 채택된 포크)

#### 연결 및 색인

```python
from opensearchpy import OpenSearch

@lru_cache
def _opensearch_client():
    return OpenSearch(hosts=[settings.opensearch_url])

client.index(index=settings.opensearch_index_name, id=data["id"], body=data, refresh=True)
```

조회는 `match_all` 쿼리로 전체 검색, 수정은 `update` API 의 `doc` 부분 업데이트를 사용합니다.

#### Docker 실행

```bash
docker run -d -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "DISABLE_SECURITY_PLUGIN=true" \
  opensearchproject/opensearch:2.15.0
```

#### 필요 환경변수

```
APP_OPENSEARCH_URL=http://localhost:9200
APP_OPENSEARCH_INDEX_NAME=lab_records
```

---

### 11. ClickHouse (OLAP)

**역할:** lab_records 를 컬럼형 테이블에 저장 (최근 가장 빠르게 성장한 OSS 분석/OLAP DB)

#### 연결 및 테이블 생성

```python
import clickhouse_connect

client = clickhouse_connect.get_client(
    host=settings.clickhouse_host, port=settings.clickhouse_port,
    username=settings.clickhouse_user, password=settings.clickhouse_password,
)
client.command("""
    CREATE TABLE IF NOT EXISTS lab_records
    (id String, title String, content String, tags Array(String))
    ENGINE = MergeTree ORDER BY id
""")
```

ClickHouse 는 OLAP 특성상 행 단위 UPDATE/DELETE 가 비동기 mutation 이므로, `ALTER TABLE ... UPDATE/DELETE ... WHERE id = ...` 를 `settings={"mutations_sync": 1}` 로 동기 실행해 CRUD 응답을 즉시 반환합니다.

#### Docker 실행

```bash
docker run -d -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server:24
```

#### 필요 환경변수

```
APP_CLICKHOUSE_HOST=localhost
APP_CLICKHOUSE_PORT=8123
APP_CLICKHOUSE_USER=default
APP_CLICKHOUSE_PASSWORD=
APP_CLICKHOUSE_DATABASE=default
APP_CLICKHOUSE_TABLE_NAME=lab_records
```

---

### 12. Cassandra (Wide-column)

**역할:** lab_records 를 CQL 테이블에 저장 (DynamoDB 와 동일한 wide-column 카테고리의 완전 오픈소스 대안)

#### 연결 및 스키마 생성

```python
from cassandra.cluster import Cluster

cluster = Cluster(settings.cassandra_hosts.split(","), port=settings.cassandra_port)
session = cluster.connect()
session.execute("""
    CREATE KEYSPACE IF NOT EXISTS lab_keyspace
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
""")
session.execute("""
    CREATE TABLE IF NOT EXISTS lab_records
    (id text PRIMARY KEY, title text, content text, tags list<text>)
""")
```

CQL `INSERT`/`SELECT`/`UPDATE`/`DELETE` 로 일반 CRUD 와 동일하게 동작합니다.

#### Docker 실행

```bash
docker run -d -p 9042:9042 cassandra:5
```

#### 필요 환경변수

```
APP_CASSANDRA_HOSTS=127.0.0.1
APP_CASSANDRA_PORT=9042
APP_CASSANDRA_KEYSPACE=lab_keyspace
APP_CASSANDRA_TABLE_NAME=lab_records
```

---

### 13. Qdrant (Vector DB)

**역할:** 벡터 임베딩을 로컬/자체 호스팅 컬렉션에 upsert·유사도 검색 (최근 가장 인기 있는 OSS 벡터 DB). `APP_VECTOR_PROVIDER` 의 3번째 옵션으로 Pinecone·Weaviate 와 동일한 `/lab/vector/*` 엔드포인트를 공유합니다.

#### 연결

```python
from qdrant_client import QdrantClient

@lru_cache
def _qdrant_client():
    return QdrantClient(url=settings.qdrant_url)
```

#### Upsert / Query

```python
# uuid5 로 결정적 UUID 생성 (Weaviate 와 동일한 패턴), 원본 id 는 payload.external_id 로 보관
point_uuid = str(uuid.uuid5(QDRANT_UUID_NAMESPACE, payload.id))
client.upsert(collection_name=settings.qdrant_collection_name, points=[
    PointStruct(id=point_uuid, vector=payload.values, payload={"external_id": payload.id, **payload.metadata}),
])

result = client.query_points(collection_name=settings.qdrant_collection_name, query=payload.values, limit=payload.top_k)
```

#### Docker 실행

```bash
docker run -d -p 6333:6333 qdrant/qdrant:v1.12.1
```

#### 필요 환경변수

```
APP_VECTOR_PROVIDER=qdrant
APP_QDRANT_URL=http://localhost:6333
APP_QDRANT_COLLECTION_NAME=lab-vectors
```

> `APP_VECTOR_PROVIDER` 값으로 `pinecone` · `weaviate` · `qdrant` 중 하나를 선택합니다.

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
| `APP_REDIS_URL` | `redis://localhost:6379/0` | Redis 연결 URL |
| `APP_REDIS_KEY_PREFIX` | `lab_record:` | Redis 레코드 키 접두사 |
| `APP_OPENSEARCH_URL` | `http://localhost:9200` | OpenSearch 서버 URL |
| `APP_OPENSEARCH_INDEX_NAME` | `lab_records` | OpenSearch 인덱스명 |
| `APP_CLICKHOUSE_HOST` | `localhost` | ClickHouse 호스트 |
| `APP_CLICKHOUSE_PORT` | `8123` | ClickHouse HTTP 포트 |
| `APP_CLICKHOUSE_USER` | `default` | ClickHouse 사용자 |
| `APP_CLICKHOUSE_PASSWORD` | _(빈 값)_ | ClickHouse 비밀번호 |
| `APP_CLICKHOUSE_DATABASE` | `default` | ClickHouse 데이터베이스명 |
| `APP_CLICKHOUSE_TABLE_NAME` | `lab_records` | ClickHouse 테이블명 |
| `APP_CASSANDRA_HOSTS` | `127.0.0.1` | Cassandra 호스트(쉼표 구분) |
| `APP_CASSANDRA_PORT` | `9042` | Cassandra 포트 |
| `APP_CASSANDRA_KEYSPACE` | `lab_keyspace` | Cassandra 키스페이스 |
| `APP_CASSANDRA_TABLE_NAME` | `lab_records` | Cassandra 테이블명 |
| `APP_QDRANT_URL` | `http://localhost:6333` | Qdrant 서버 URL |
| `APP_QDRANT_COLLECTION_NAME` | `lab-vectors` | Qdrant 컬렉션명 |

---

## 프로젝트 구조

```
grid-lab/
├── backend/
│   ├── main.py              # FastAPI 앱 진입점 (frontend/ 정적 파일 마운트 포함)
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
│   ├── index.html            # 게시글 CRUD 탭 + 멀티 DB 엔진(Canvas) 탭
│   └── assets/
│       ├── app.js            # 게시글 CRUD 로직
│       └── engine.js         # Canvas 기반 멀티 DB 엔진 로직
├── main.py                  # 레거시 호환용 엔트리포인트
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 실행 방법

프론트엔드(`frontend/`)는 FastAPI 백엔드가 정적 파일로 직접 서빙합니다 (`backend/main.py` 의 `StaticFiles` 마운트). 별도의 프론트엔드 서버를 띄울 필요가 없습니다.

### 1) PostgreSQL + API + 프론트엔드 (Docker Compose, 권장)

```bash
docker compose up --build
```

- 통합 앱(프론트엔드 + API): http://127.0.0.1:8010
- Swagger: http://127.0.0.1:8010/docs

### 2) 로컬에서 직접 실행 (Docker 없이)

```bash
uvicorn backend.main:app --reload
```

- 통합 앱(프론트엔드 + API): http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

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

# Redis
docker run -d -p 6379:6379 redis:7

# OpenSearch
docker run -d -p 9200:9200 \
  -e "discovery.type=single-node" -e "DISABLE_SECURITY_PLUGIN=true" \
  opensearchproject/opensearch:2.15.0

# ClickHouse
docker run -d -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server:24

# Cassandra
docker run -d -p 9042:9042 cassandra:5

# Qdrant
docker run -d -p 6333:6333 qdrant/qdrant:v1.12.1
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

### Lab — Redis

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/redis/records` | 레코드 생성 |
| `GET` | `/lab/redis/records` | 목록 조회 |
| `PATCH` | `/lab/redis/records/{id}` | 부분 수정 |
| `DELETE` | `/lab/redis/records/{id}` | 삭제 |

### Lab — OpenSearch

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/opensearch/records` | 레코드 생성 |
| `GET` | `/lab/opensearch/records` | 목록 조회 |
| `PATCH` | `/lab/opensearch/records/{id}` | 부분 수정 |
| `DELETE` | `/lab/opensearch/records/{id}` | 삭제 |

### Lab — ClickHouse

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/clickhouse/records` | 레코드 생성 |
| `GET` | `/lab/clickhouse/records` | 목록 조회 |
| `PATCH` | `/lab/clickhouse/records/{id}` | 부분 수정 |
| `DELETE` | `/lab/clickhouse/records/{id}` | 삭제 |

### Lab — Cassandra

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/cassandra/records` | 레코드 생성 |
| `GET` | `/lab/cassandra/records` | 목록 조회 |
| `PATCH` | `/lab/cassandra/records/{id}` | 부분 수정 |
| `DELETE` | `/lab/cassandra/records/{id}` | 삭제 |

### Lab — Vector DB (Pinecone / Weaviate / Qdrant)

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/vector/upsert` | 벡터 저장 (`APP_VECTOR_PROVIDER=pinecone\|weaviate\|qdrant`) |
| `POST` | `/lab/vector/query` | 유사도 검색 |

### Lab — Neo4j Graph

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/lab/graph/nodes` | Entity 노드 생성 (MERGE) |
| `POST` | `/lab/graph/edges` | RELATES_TO 엣지 생성 |
| `POST` | `/lab/graph/analyze` | GDS 분석 (`pagerank` \| `degree`) |

전체 API 문서: http://127.0.0.1:8000/docs (Swagger UI)

---

## 멀티 DB 엔진 (Canvas)

로그인 후 상단의 `멀티 DB 엔진` 탭에서 Canvas 기반으로 여러 DB를 동시에 연결해 하나의 AG Grid 로 데이터를 합쳐 볼 수 있습니다.

- **팔레트**: PostgreSQL · MongoDB · Supabase · Redis · OpenSearch · ClickHouse · Cassandra · DynamoDB · Pinecone · Weaviate · Neo4j · Qdrant 12개 DB 아이콘이 표시됩니다.
- **호환 DB** (실선 테두리): PostgreSQL, MongoDB, Supabase, Redis, OpenSearch, ClickHouse, Cassandra — 모두 `id/title/content/tags` 와 동일한 레코드 구조(`/lab/<db>/records`)를 가지므로 Canvas 의 Grid 노드에 연결하면 데이터를 가져와 그리드에 합쳐 보여줍니다.
- **비호환 DB** (점선 테두리): DynamoDB(Employee), Pinecone/Weaviate/Qdrant(Vector), Neo4j(Graph) — 레코드 구조가 달라 팔레트에는 표시되지만 Grid 노드에 연결을 시도하면 "구조가 달라 연결할 수 없습니다" 안내만 표시됩니다.
- **사용 방법**: 팔레트에서 DB 아이콘을 클릭해 캔버스에 노드를 추가 → 노드의 연결 핸들을 Grid 노드까지 드래그 → 연결되면 해당 DB의 레코드를 조회해(데이터가 없으면 샘플 3건을 자동 생성) 그리드에 `source` 컬럼과 함께 합쳐서 표시합니다. 여러 DB를 동시에 연결하면 모든 source 의 행이 하나의 그리드에 누적됩니다. 노드/연결을 삭제하면 해당 source 의 행만 그리드에서 제거됩니다. 캔버스 레이아웃(노드 위치·연결 상태)은 브라우저 `localStorage` 에 저장되어 새로고침해도 유지됩니다.
