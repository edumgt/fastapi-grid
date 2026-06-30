import atexit
import json
import uuid
from functools import lru_cache
from typing import Any

import clickhouse_connect
import redis as redis_client_lib
from cassandra.cluster import Cluster
from fastapi import APIRouter, HTTPException, status
from neo4j import GraphDatabase
from neo4j.exceptions import ClientError
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError as OpenSearchNotFoundError
from pinecone import Pinecone
from pymongo import MongoClient, ReturnDocument
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sqlalchemy import JSON, Column, MetaData, String, Table, create_engine, delete, insert, select, update
from supabase import Client, create_client
import weaviate
from weaviate.classes.query import MetadataQuery

from backend.config.settings import settings
from backend.models.lab import (
    GraphAnalysisRequest,
    GraphEdgeCreate,
    GraphNodeCreate,
    LabRecordCreate,
    LabRecordRead,
    LabRecordUpdate,
    VectorQueryRequest,
    VectorUpsertRequest,
)

router = APIRouter(prefix="/lab", tags=["lab"])
WEAVIATE_UUID_NAMESPACE = uuid.UUID("f33e9e58-8f5e-44cb-a272-4f2f96699e2f")
QDRANT_UUID_NAMESPACE = uuid.UUID("a3f0e4b2-6c1d-4e9a-9b3f-7d2c8e5a1f60")

postgres_metadata = MetaData()
postgres_table = Table(
    settings.postgresql_table_name,
    postgres_metadata,
    Column("id", String, primary_key=True),
    Column("title", String, nullable=False),
    Column("content", String, nullable=False),
    Column("tags", JSON, nullable=False),
)


@lru_cache
def _mongo_client():
    return MongoClient(settings.mongodb_uri)


@lru_cache
def _mongo_collection():
    return _mongo_client()[settings.mongodb_db_name][settings.mongodb_collection_name]


@lru_cache
def _postgres_engine():
    engine = create_engine(settings.postgresql_dsn)
    postgres_metadata.create_all(engine)
    return engine


@lru_cache
def _supabase_client() -> Client:
    if not settings.supabase_url or not settings.supabase_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supabase 설정(APP_SUPABASE_URL, APP_SUPABASE_KEY)이 필요합니다.",
        )
    return create_client(settings.supabase_url, settings.supabase_key)


@lru_cache
def _neo4j_driver():
    return GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))


@lru_cache
def _pinecone_index():
    if not settings.pinecone_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pinecone 설정(APP_PINECONE_API_KEY)이 필요합니다.",
        )
    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(settings.pinecone_index_name)


@lru_cache
def _weaviate_client():
    return weaviate.connect_to_local()


@lru_cache
def _weaviate_collection():
    return _weaviate_client().collections.get(settings.weaviate_collection_name)


@atexit.register
def _close_weaviate_client():
    if _weaviate_client.cache_info().currsize:
        _weaviate_client().close()


@atexit.register
def _close_mongo_client():
    if _mongo_client.cache_info().currsize:
        _mongo_client().close()


@atexit.register
def _dispose_postgres_engine():
    if _postgres_engine.cache_info().currsize:
        _postgres_engine().dispose()


@atexit.register
def _close_neo4j_driver():
    if _neo4j_driver.cache_info().currsize:
        _neo4j_driver().close()


@lru_cache
def _redis_client():
    return redis_client_lib.from_url(settings.redis_url, decode_responses=True)


def _redis_key(record_id: str) -> str:
    return f"{settings.redis_key_prefix}{record_id}"


@atexit.register
def _close_redis_client():
    if _redis_client.cache_info().currsize:
        _redis_client().close()


@lru_cache
def _opensearch_client():
    return OpenSearch(hosts=[settings.opensearch_url])


@lru_cache
def _clickhouse_client():
    client = clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )
    client.command(
        f"""
        CREATE TABLE IF NOT EXISTS {settings.clickhouse_table_name}
        (
            id String,
            title String,
            content String,
            tags Array(String)
        ) ENGINE = MergeTree ORDER BY id
        """
    )
    return client


@lru_cache
def _cassandra_session():
    cluster = Cluster(settings.cassandra_hosts.split(","), port=settings.cassandra_port)
    session = cluster.connect()
    session.execute(
        f"""
        CREATE KEYSPACE IF NOT EXISTS {settings.cassandra_keyspace}
        WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """
    )
    session.set_keyspace(settings.cassandra_keyspace)
    session.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {settings.cassandra_table_name} (
            id text PRIMARY KEY,
            title text,
            content text,
            tags list<text>
        )
        """
    )
    return session


@atexit.register
def _shutdown_cassandra_session():
    if _cassandra_session.cache_info().currsize:
        session = _cassandra_session()
        cluster = session.cluster
        session.shutdown()
        cluster.shutdown()


@lru_cache
def _qdrant_client():
    return QdrantClient(url=settings.qdrant_url)


def _ensure_qdrant_collection(dimension: int) -> None:
    client = _qdrant_client()
    if not client.collection_exists(settings.qdrant_collection_name):
        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )


def _to_record(source: str, item: dict[str, Any]) -> LabRecordRead:
    return LabRecordRead(
        id=str(item["id"]),
        title=str(item["title"]),
        content=str(item["content"]),
        tags=list(item.get("tags", [])),
        source=source,
    )


@router.post("/mongo/records", response_model=LabRecordRead, status_code=status.HTTP_201_CREATED)
def create_mongo_record(payload: LabRecordCreate):
    collection = _mongo_collection()
    document = payload.model_dump()
    collection.insert_one(document)
    return _to_record("mongodb", document)


@router.get("/mongo/records", response_model=list[LabRecordRead])
def list_mongo_records(limit: int = 20):
    collection = _mongo_collection()
    docs = collection.find({}, {"_id": 0}).limit(limit)
    return [_to_record("mongodb", doc) for doc in docs]


@router.patch("/mongo/records/{record_id}", response_model=LabRecordRead)
def update_mongo_record(record_id: str, payload: LabRecordUpdate):
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 필드가 없습니다.")
    collection = _mongo_collection()
    result = collection.find_one_and_update(
        {"id": record_id},
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MongoDB 레코드를 찾을 수 없습니다.")
    result.pop("_id", None)
    return _to_record("mongodb", result)


@router.delete("/mongo/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mongo_record(record_id: str):
    collection = _mongo_collection()
    deleted = collection.delete_one({"id": record_id})
    if deleted.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MongoDB 레코드를 찾을 수 없습니다.")


@router.post("/postgres/records", response_model=LabRecordRead, status_code=status.HTTP_201_CREATED)
def create_postgres_record(payload: LabRecordCreate):
    engine = _postgres_engine()
    data = payload.model_dump()
    with engine.begin() as conn:
        conn.execute(insert(postgres_table).values(**data))
    return _to_record("postgresql", data)


@router.get("/postgres/records", response_model=list[LabRecordRead])
def list_postgres_records(limit: int = 20):
    engine = _postgres_engine()
    with engine.begin() as conn:
        rows = conn.execute(select(postgres_table).limit(limit)).mappings().all()
    return [_to_record("postgresql", dict(row)) for row in rows]


@router.patch("/postgres/records/{record_id}", response_model=LabRecordRead)
def update_postgres_record(record_id: str, payload: LabRecordUpdate):
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 필드가 없습니다.")
    engine = _postgres_engine()
    with engine.begin() as conn:
        updated = conn.execute(
            update(postgres_table).where(postgres_table.c.id == record_id).values(**changes).returning(postgres_table)
        ).mappings().first()
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PostgreSQL 레코드를 찾을 수 없습니다.")
    return _to_record("postgresql", dict(updated))


@router.delete("/postgres/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_postgres_record(record_id: str):
    engine = _postgres_engine()
    with engine.begin() as conn:
        deleted = conn.execute(delete(postgres_table).where(postgres_table.c.id == record_id))
    if deleted.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PostgreSQL 레코드를 찾을 수 없습니다.")


@router.post("/supabase/records", response_model=LabRecordRead, status_code=status.HTTP_201_CREATED)
def create_supabase_record(payload: LabRecordCreate):
    client = _supabase_client()
    data = payload.model_dump()
    client.table(settings.supabase_table_name).insert(data).execute()
    return _to_record("supabase", data)


@router.get("/supabase/records", response_model=list[LabRecordRead])
def list_supabase_records(limit: int = 20):
    client = _supabase_client()
    response = client.table(settings.supabase_table_name).select("*").limit(limit).execute()
    return [_to_record("supabase", item) for item in response.data]


@router.patch("/supabase/records/{record_id}", response_model=LabRecordRead)
def update_supabase_record(record_id: str, payload: LabRecordUpdate):
    client = _supabase_client()
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 필드가 없습니다.")
    response = client.table(settings.supabase_table_name).update(changes).eq("id", record_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supabase 레코드를 찾을 수 없습니다.")
    return _to_record("supabase", response.data[0])


@router.delete("/supabase/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supabase_record(record_id: str):
    client = _supabase_client()
    response = client.table(settings.supabase_table_name).delete().eq("id", record_id).execute()
    if not response.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supabase 레코드를 찾을 수 없습니다.")


@router.post("/redis/records", response_model=LabRecordRead, status_code=status.HTTP_201_CREATED)
def create_redis_record(payload: LabRecordCreate):
    client = _redis_client()
    data = payload.model_dump()
    client.set(_redis_key(data["id"]), json.dumps(data))
    return _to_record("redis", data)


@router.get("/redis/records", response_model=list[LabRecordRead])
def list_redis_records(limit: int = 20):
    client = _redis_client()
    keys: list[str] = []
    for key in client.scan_iter(match=f"{settings.redis_key_prefix}*", count=100):
        keys.append(key)
        if len(keys) >= limit:
            break
    values = client.mget(keys) if keys else []
    return [_to_record("redis", json.loads(value)) for value in values if value]


@router.patch("/redis/records/{record_id}", response_model=LabRecordRead)
def update_redis_record(record_id: str, payload: LabRecordUpdate):
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 필드가 없습니다.")
    client = _redis_client()
    key = _redis_key(record_id)
    existing = client.get(key)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redis 레코드를 찾을 수 없습니다.")
    data = json.loads(existing)
    data.update(changes)
    client.set(key, json.dumps(data))
    return _to_record("redis", data)


@router.delete("/redis/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_redis_record(record_id: str):
    client = _redis_client()
    deleted = client.delete(_redis_key(record_id))
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redis 레코드를 찾을 수 없습니다.")


@router.post("/opensearch/records", response_model=LabRecordRead, status_code=status.HTTP_201_CREATED)
def create_opensearch_record(payload: LabRecordCreate):
    client = _opensearch_client()
    data = payload.model_dump()
    client.index(index=settings.opensearch_index_name, id=data["id"], body=data, refresh=True)
    return _to_record("opensearch", data)


@router.get("/opensearch/records", response_model=list[LabRecordRead])
def list_opensearch_records(limit: int = 20):
    client = _opensearch_client()
    try:
        response = client.search(
            index=settings.opensearch_index_name,
            body={"query": {"match_all": {}}, "size": limit},
        )
    except OpenSearchNotFoundError:
        return []
    return [_to_record("opensearch", hit["_source"]) for hit in response["hits"]["hits"]]


@router.patch("/opensearch/records/{record_id}", response_model=LabRecordRead)
def update_opensearch_record(record_id: str, payload: LabRecordUpdate):
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 필드가 없습니다.")
    client = _opensearch_client()
    try:
        client.update(
            index=settings.opensearch_index_name,
            id=record_id,
            body={"doc": changes},
            refresh=True,
        )
        result = client.get(index=settings.opensearch_index_name, id=record_id)
    except OpenSearchNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OpenSearch 레코드를 찾을 수 없습니다.")
    return _to_record("opensearch", result["_source"])


@router.delete("/opensearch/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opensearch_record(record_id: str):
    client = _opensearch_client()
    try:
        client.delete(index=settings.opensearch_index_name, id=record_id, refresh=True)
    except OpenSearchNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OpenSearch 레코드를 찾을 수 없습니다.")


@router.post("/clickhouse/records", response_model=LabRecordRead, status_code=status.HTTP_201_CREATED)
def create_clickhouse_record(payload: LabRecordCreate):
    client = _clickhouse_client()
    data = payload.model_dump()
    client.insert(
        settings.clickhouse_table_name,
        [[data["id"], data["title"], data["content"], data["tags"]]],
        column_names=["id", "title", "content", "tags"],
    )
    return _to_record("clickhouse", data)


@router.get("/clickhouse/records", response_model=list[LabRecordRead])
def list_clickhouse_records(limit: int = 20):
    client = _clickhouse_client()
    result = client.query(
        f"SELECT id, title, content, tags FROM {settings.clickhouse_table_name} LIMIT {int(limit)}"
    )
    return [_to_record("clickhouse", dict(zip(result.column_names, row))) for row in result.result_rows]


@router.patch("/clickhouse/records/{record_id}", response_model=LabRecordRead)
def update_clickhouse_record(record_id: str, payload: LabRecordUpdate):
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 필드가 없습니다.")
    client = _clickhouse_client()
    table = settings.clickhouse_table_name
    existing = client.query(f"SELECT id FROM {table} WHERE id = {{id:String}}", parameters={"id": record_id})
    if not existing.result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClickHouse 레코드를 찾을 수 없습니다.")
    set_clause = ", ".join(
        f"{key} = {{{key}:Array(String)}}" if key == "tags" else f"{key} = {{{key}:String}}" for key in changes
    )
    client.command(
        f"ALTER TABLE {table} UPDATE {set_clause} WHERE id = {{id:String}}",
        parameters={**changes, "id": record_id},
        settings={"mutations_sync": 1},
    )
    result = client.query(
        f"SELECT id, title, content, tags FROM {table} WHERE id = {{id:String}}", parameters={"id": record_id}
    )
    return _to_record("clickhouse", dict(zip(result.column_names, result.result_rows[0])))


@router.delete("/clickhouse/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clickhouse_record(record_id: str):
    client = _clickhouse_client()
    table = settings.clickhouse_table_name
    existing = client.query(f"SELECT id FROM {table} WHERE id = {{id:String}}", parameters={"id": record_id})
    if not existing.result_rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ClickHouse 레코드를 찾을 수 없습니다.")
    client.command(
        f"ALTER TABLE {table} DELETE WHERE id = {{id:String}}",
        parameters={"id": record_id},
        settings={"mutations_sync": 1},
    )


@router.post("/cassandra/records", response_model=LabRecordRead, status_code=status.HTTP_201_CREATED)
def create_cassandra_record(payload: LabRecordCreate):
    session = _cassandra_session()
    data = payload.model_dump()
    session.execute(
        f"INSERT INTO {settings.cassandra_table_name} (id, title, content, tags) VALUES (%s, %s, %s, %s)",
        (data["id"], data["title"], data["content"], data["tags"]),
    )
    return _to_record("cassandra", data)


@router.get("/cassandra/records", response_model=list[LabRecordRead])
def list_cassandra_records(limit: int = 20):
    session = _cassandra_session()
    rows = session.execute(
        f"SELECT id, title, content, tags FROM {settings.cassandra_table_name} LIMIT %s", (limit,)
    )
    return [
        _to_record("cassandra", {"id": row.id, "title": row.title, "content": row.content, "tags": list(row.tags or [])})
        for row in rows
    ]


@router.patch("/cassandra/records/{record_id}", response_model=LabRecordRead)
def update_cassandra_record(record_id: str, payload: LabRecordUpdate):
    changes = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not changes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="수정할 필드가 없습니다.")
    session = _cassandra_session()
    table = settings.cassandra_table_name
    existing = session.execute(f"SELECT id FROM {table} WHERE id = %s", (record_id,)).one()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cassandra 레코드를 찾을 수 없습니다.")
    set_clause = ", ".join(f"{key} = %s" for key in changes)
    session.execute(f"UPDATE {table} SET {set_clause} WHERE id = %s", (*changes.values(), record_id))
    row = session.execute(f"SELECT id, title, content, tags FROM {table} WHERE id = %s", (record_id,)).one()
    return _to_record("cassandra", {"id": row.id, "title": row.title, "content": row.content, "tags": list(row.tags or [])})


@router.delete("/cassandra/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cassandra_record(record_id: str):
    session = _cassandra_session()
    table = settings.cassandra_table_name
    existing = session.execute(f"SELECT id FROM {table} WHERE id = %s", (record_id,)).one()
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cassandra 레코드를 찾을 수 없습니다.")
    session.execute(f"DELETE FROM {table} WHERE id = %s", (record_id,))


@router.post("/vector/upsert")
def upsert_vector(payload: VectorUpsertRequest):
    provider = settings.vector_provider.lower()
    if provider == "pinecone":
        index = _pinecone_index()
        index.upsert(vectors=[{"id": payload.id, "values": payload.values, "metadata": payload.metadata}])
        return {"provider": "pinecone", "status": "upserted", "id": payload.id}
    if provider == "weaviate":
        collection = _weaviate_collection()
        object_uuid = str(uuid.uuid5(WEAVIATE_UUID_NAMESPACE, payload.id))
        collection.data.insert(
            uuid=object_uuid,
            properties={"external_id": payload.id, "metadata": payload.metadata},
            vector=payload.values,
        )
        return {"provider": "weaviate", "status": "upserted", "id": payload.id}
    if provider == "qdrant":
        _ensure_qdrant_collection(len(payload.values))
        point_uuid = str(uuid.uuid5(QDRANT_UUID_NAMESPACE, payload.id))
        _qdrant_client().upsert(
            collection_name=settings.qdrant_collection_name,
            points=[
                PointStruct(
                    id=point_uuid,
                    vector=payload.values,
                    payload={"external_id": payload.id, **payload.metadata},
                )
            ],
        )
        return {"provider": "qdrant", "status": "upserted", "id": payload.id}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="지원하지 않는 VECTOR_PROVIDER 입니다.")


@router.post("/vector/query")
def query_vector(payload: VectorQueryRequest):
    provider = settings.vector_provider.lower()
    if provider == "pinecone":
        index = _pinecone_index()
        result = index.query(vector=payload.values, top_k=payload.top_k, include_metadata=True)
        matches = result.to_dict().get("matches", [])
        return {"provider": "pinecone", "matches": matches}
    if provider == "weaviate":
        collection = _weaviate_collection()
        result = collection.query.near_vector(
            near_vector=payload.values,
            limit=payload.top_k,
            return_metadata=MetadataQuery(distance=True),
        )
        matches = [
            {"id": obj.uuid, "distance": obj.metadata.distance, "properties": obj.properties}
            for obj in result.objects
        ]
        return {"provider": "weaviate", "matches": matches}
    if provider == "qdrant":
        result = _qdrant_client().query_points(
            collection_name=settings.qdrant_collection_name,
            query=payload.values,
            limit=payload.top_k,
        )
        matches = [
            {"id": point.payload.get("external_id", str(point.id)), "score": point.score, "payload": point.payload}
            for point in result.points
        ]
        return {"provider": "qdrant", "matches": matches}
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="지원하지 않는 VECTOR_PROVIDER 입니다.")


@router.post("/graph/nodes", status_code=status.HTTP_201_CREATED)
def create_graph_node(payload: GraphNodeCreate):
    driver = _neo4j_driver()
    with driver.session(database=settings.neo4j_database) as session:
        result = session.run(
            """
            MERGE (n:Entity {id: $id})
            SET n.label = $label
            RETURN n.id AS id, n.label AS label
            """,
            id=payload.id,
            label=payload.label,
        ).single()
    return {"id": result["id"], "label": result["label"]}


@router.post("/graph/edges", status_code=status.HTTP_201_CREATED)
def create_graph_edge(payload: GraphEdgeCreate):
    driver = _neo4j_driver()
    with driver.session(database=settings.neo4j_database) as session:
        session.run(
            """
            MERGE (a:Entity {id: $source})
            MERGE (b:Entity {id: $target})
            MERGE (a)-[r:RELATES_TO]->(b)
            SET r.weight = $weight
            """,
            source=payload.source,
            target=payload.target,
            weight=payload.weight,
        )
    return {"source": payload.source, "target": payload.target, "weight": payload.weight}


@router.post("/graph/analyze")
def analyze_graph(payload: GraphAnalysisRequest):
    driver = _neo4j_driver()
    graph_name = settings.neo4j_graph_name
    with driver.session(database=settings.neo4j_database) as session:
        try:
            session.run("CALL gds.graph.drop($graph_name, false) YIELD graphName", graph_name=graph_name).consume()
        except ClientError as exc:
            if "does not exist" not in str(exc):
                raise
        session.run(
            """
            CALL gds.graph.project(
              $graph_name,
              'Entity',
              {RELATES_TO: {orientation: 'NATURAL', properties: 'weight'}}
            )
            """,
            graph_name=graph_name,
        ).consume()

        if payload.algorithm == "degree":
            result = session.run(
                """
                CALL gds.degree.stream($graph_name)
                YIELD nodeId, score
                RETURN gds.util.asNode(nodeId).id AS id, score
                ORDER BY score DESC
                LIMIT 10
                """,
                graph_name=graph_name,
            )
        else:
            result = session.run(
                """
                CALL gds.pageRank.stream($graph_name)
                YIELD nodeId, score
                RETURN gds.util.asNode(nodeId).id AS id, score
                ORDER BY score DESC
                LIMIT 10
                """,
                graph_name=graph_name,
            )

        ranking = [{"id": row["id"], "score": row["score"]} for row in result]

    return {"algorithm": payload.algorithm, "top_nodes": ranking}
