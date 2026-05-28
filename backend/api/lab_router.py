import atexit
import uuid
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException, status
from neo4j import GraphDatabase
from neo4j.exceptions import ClientError
from pinecone import Pinecone
from pymongo import MongoClient, ReturnDocument
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
