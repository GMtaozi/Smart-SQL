"""Schema management schemas"""

from typing import Optional, List
from pydantic import BaseModel


class DatasourceCreateRequest(BaseModel):
    """Create datasource request."""
    name: str
    host: str
    port: int = 5432
    database_name: str
    username: str
    password: str
    db_type: str = "postgresql"


class DatasourceResponse(BaseModel):
    """Datasource response (without password)."""
    id: int
    user_id: int
    name: str
    host: str
    port: int
    database_name: str
    username: str
    db_type: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class ColumnSchema(BaseModel):
    """Column schema."""
    column_name: str
    data_type: str
    column_comment: Optional[str] = None
    is_primary_key: bool = False
    is_nullable: bool = True
    column_id: int


class TableSchemaRequest(BaseModel):
    """Create/update table schema request."""
    datasource_id: int
    table_name: str
    table_comment: Optional[str] = None
    columns: List[ColumnSchema]


class TableSchemaResponse(BaseModel):
    """Table schema response."""
    id: int
    datasource_id: int
    table_name: str
    table_comment: Optional[str] = None
    columns: List[ColumnSchema]
    created_at: str

    class Config:
        from_attributes = True


class SchemaSyncRequest(BaseModel):
    """Schema sync request - auto-discover from target database."""
    datasource_id: int
