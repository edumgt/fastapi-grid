from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Auth
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    allowed_origins: str = "http://127.0.0.1:8001,http://localhost:8001"

    # Main PostgreSQL (posts/users)
    database_url: str = "postgresql+psycopg://app_user:app_password@127.0.0.1:5432/app_db"

    # Lab PostgreSQL (lab records)
    postgresql_dsn: str = "postgresql+psycopg://app_user:app_password@127.0.0.1:5432/app_db"
    postgresql_table_name: str = "lab_records"

    # AWS / DynamoDB
    aws_region: str = "ap-northeast-2"
    dynamodb_table_name: str = "Employees"

    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "lab_db"
    mongodb_collection_name: str = "documents"

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_table_name: str = "lab_records"

    # Vector DB
    vector_provider: str = "pinecone"
    pinecone_api_key: str = ""
    pinecone_index_name: str = "lab-vectors"
    weaviate_url: str = "http://localhost:8080"
    weaviate_collection_name: str = "LabVectors"

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "neo4j"
    neo4j_graph_name: str = "lab_graph"

    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")


settings = Settings()
