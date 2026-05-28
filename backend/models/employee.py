from pydantic import BaseModel, Field


class EmployeeCreate(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    position: str = Field(min_length=1)


class EmployeeRead(EmployeeCreate):
    pass
