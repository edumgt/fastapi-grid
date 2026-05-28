from typing import Any, Literal

from pydantic import BaseModel, Field


class LabRecordCreate(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class LabRecordUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


class LabRecordRead(LabRecordCreate):
    source: str = Field(min_length=1)


class VectorUpsertRequest(BaseModel):
    id: str = Field(min_length=1)
    values: list[float] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorQueryRequest(BaseModel):
    values: list[float] = Field(min_length=1)
    top_k: int = Field(default=3, ge=1, le=20)


class GraphNodeCreate(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(default="Entity", min_length=1)


class GraphEdgeCreate(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    weight: float = 1.0


class GraphAnalysisRequest(BaseModel):
    algorithm: Literal["pagerank", "degree"] = "pagerank"
