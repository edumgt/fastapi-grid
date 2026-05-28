from typing import Generator

import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config.settings import settings

engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DynamoDbClientFactory:
    @staticmethod
    def resource():
        return boto3.resource("dynamodb", region_name=settings.aws_region)

    @staticmethod
    def table():
        return DynamoDbClientFactory.resource().Table(settings.dynamodb_table_name)
