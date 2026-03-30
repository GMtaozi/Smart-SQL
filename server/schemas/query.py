"""Query schemas"""

from typing import Optional, List
from pydantic import BaseModel


class QueryGenerateRequest(BaseModel):
    """NL to SQL generation request."""
    user_query: str
    datasource_id: int


class QueryGenerateResponse(BaseModel):
    """NL to SQL generation response."""
    success: bool
    sql: str
    used_tables: List[str]
    error: Optional[str] = None


class QueryExecuteRequest(BaseModel):
    """SQL execution request."""
    sql: str
    datasource_id: int


class QueryExecuteResponse(BaseModel):
    """SQL execution response."""
    success: bool
    columns: List[str]
    rows: List[dict]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None


class QueryHistoryResponse(BaseModel):
    """Query history item."""
    id: int
    user_query: str
    generated_sql: str
    status: str
    execution_time_ms: Optional[float] = None
    row_count: Optional[int] = None
    used_tables: Optional[List[str]] = None
    created_at: str


class QueryFeedbackRequest(BaseModel):
    """Query feedback request."""
    query_log_id: int
    rating: Optional[int] = None
    is_correct: bool
    corrected_sql: Optional[str] = None
    feedback_text: Optional[str] = None


class ExportCreateRequest(BaseModel):
    """Export task creation request."""
    sql: str
    datasource_id: int


class ExportCreateResponse(BaseModel):
    """Export task creation response."""
    task_id: str
    status: str
    preview_rows: List[dict]
    preview_columns: List[str]
    preview_row_count: int
    total_rows: int
    message: str


class ExportStatusResponse(BaseModel):
    """Export task status response."""
    task_id: str
    status: str  # pending, processing, completed, failed
    total_rows: Optional[int] = None
    csv_content: Optional[str] = None
    error_message: Optional[str] = None
    message: str
