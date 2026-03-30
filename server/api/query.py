"""Query API routes - NL to SQL generation and execution"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from server.db.database import get_db
from server.api.auth import get_current_user_id
from server.schemas.query import (
    QueryGenerateRequest,
    QueryGenerateResponse,
    QueryExecuteRequest,
    QueryExecuteResponse,
    QueryHistoryResponse,
    QueryFeedbackRequest,
)
from server.services.sql_generator import get_sql_generator
from server.services.sql_guard import get_sql_guard
from server.services.sql_executor import get_sql_executor, DatasourceConfig
from server.services.auth_service import get_auth_service

router = APIRouter(prefix="/api/query", tags=["query"])


@router.post("/generate", response_model=QueryGenerateResponse)
def generate_sql(
    request: QueryGenerateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Generate SQL from natural language query.

    Flow:
    1. RAG retrieve relevant schema context
    2. Build prompt with schema context
    3. Call LLM to generate SQL
    4. Run SQL Guard to validate safety
    5. Return generated SQL (user must confirm before execution)
    """
    # Generate SQL
    generator = get_sql_generator()
    result = generator.generate(
        user_query=request.user_query,
        datasource_id=request.datasource_id,
        db=db,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "SQL 生成失败"),
        )

    # Security scan
    guard = get_sql_guard()
    scan_result = guard.scan(result["sql"])

    if not scan_result.passed:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"SQL scan failed. SQL: {result['sql'][:500]}, reason: {scan_result.reason}")
        return QueryGenerateResponse(
            success=False,
            sql=result["sql"],  # Return the actual SQL for debugging
            used_tables=result.get("used_tables", []),
            error=f"SQL 安全扫描未通过: {scan_result.reason}",
        )

    # Log the query
    try:
        from sqlalchemy import text
        log_query = text("""
            INSERT INTO query_logs
                (user_id, datasource_id, user_query, generated_sql, status, used_tables, created_at)
            VALUES
                (:user_id, :datasource_id, :user_query, :generated_sql, 'pending', :used_tables, NOW())
        """)
        db.execute(log_query, {
            "user_id": user_id,
            "datasource_id": request.datasource_id,
            "user_query": request.user_query,
            "generated_sql": result["sql"],
            "used_tables": json.dumps(result.get("used_tables", [])),
        })
        db.commit()
    except Exception:
        db.rollback()

    return QueryGenerateResponse(
        success=True,
        sql=result["sql"],
        used_tables=result.get("used_tables", []),
    )


@router.post("/execute", response_model=QueryExecuteResponse)
def execute_sql(
    request: QueryExecuteRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Execute SQL query after user confirmation.

    Security:
    - SQL Guard validates the SQL first
    - Executor enforces read-only + timeout + row limit
    """
    # Validate SQL safety
    guard = get_sql_guard()
    scan_result = guard.scan(request.sql)

    if not scan_result.passed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SQL 安全扫描未通过: {scan_result.reason}",
        )

    # Get datasource config
    from sqlalchemy import text
    from server.utils.security import decrypt_password
    ds_query = text("""
        SELECT host, port, database_name, username, password_encrypted, db_type
        FROM datasources
        WHERE id = :datasource_id AND user_id = :user_id
    """)
    ds_result = db.execute(ds_query, {
        "datasource_id": request.datasource_id,
        "user_id": user_id,
    })
    ds_row = ds_result.fetchone()

    if not ds_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="数据源不存在或无权限",
        )

    # Decrypt the password
    print(f"[DEBUG] ds_row[4] (encrypted): {ds_row[4][:20] if ds_row[4] else 'None'}...")
    decrypted_password = decrypt_password(ds_row[4]) if ds_row[4] else ""
    print(f"[DEBUG] decrypted_password: {'***' + decrypted_password[-4:] if decrypted_password else 'EMPTY'}")

    config = DatasourceConfig(
        host=ds_row[0],
        port=ds_row[1],
        database=ds_row[2],
        username=ds_row[3],
        password=decrypted_password,
        db_type=ds_row[5] or "postgresql",
    )

    # Execute
    executor = get_sql_executor()
    result = executor.execute(request.sql, config)

    # Update query log status
    try:
        update_query = text("""
            UPDATE query_logs
            SET status = :status,
                executed_sql = :executed_sql,
                execution_time_ms = :execution_time_ms,
                row_count = :row_count,
                error_message = :error_message
            WHERE id = (
                SELECT id FROM query_logs
                WHERE user_id = :user_id AND datasource_id = :datasource_id
                ORDER BY created_at DESC
                LIMIT 1
            )
        """)
        db.execute(update_query, {
            "status": "success" if result.success else "failed",
            "executed_sql": request.sql,
            "execution_time_ms": result.execution_time_ms,
            "row_count": result.row_count,
            "error_message": result.error,
            "user_id": user_id,
            "datasource_id": request.datasource_id,
        })
        db.commit()
    except Exception:
        db.rollback()

    return QueryExecuteResponse(
        success=result.success,
        columns=result.columns,
        rows=result.rows,
        row_count=result.row_count,
        execution_time_ms=result.execution_time_ms,
        error=result.error,
    )


@router.get("/history", response_model=list[QueryHistoryResponse])
def get_query_history(
    limit: int = 50,
    offset: int = 0,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get user's query history."""
    from sqlalchemy import text
    query = text("""
        SELECT id, user_query, generated_sql, status, execution_time_ms,
               row_count, used_tables, created_at
        FROM query_logs
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """)
    result = db.execute(query, {
        "user_id": user_id,
        "limit": limit,
        "offset": offset,
    })
    rows = result.fetchall()

    result = []
    for row in rows:
        # Parse used_tables from JSON string if needed
        used_tables = row[6]
        if used_tables and isinstance(used_tables, str):
            try:
                used_tables = json.loads(used_tables)
            except (json.JSONDecodeError, TypeError):
                used_tables = []
        result.append(QueryHistoryResponse(
            id=row[0],
            user_query=row[1],
            generated_sql=row[2],
            status=row[3],
            execution_time_ms=row[4],
            row_count=row[5],
            used_tables=used_tables,
            created_at=str(row[7]),
        ))
    return result


@router.post("/feedback")
def submit_feedback(
    request: QueryFeedbackRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Submit feedback for a generated SQL."""
    from sqlalchemy import text
    query = text("""
        INSERT INTO query_feedbacks
            (query_log_id, user_id, rating, is_correct, corrected_sql, feedback_text, created_at)
        VALUES
            (:query_log_id, :user_id, :rating, :is_correct, :corrected_sql, :feedback_text, NOW())
    """)
    db.execute(query, {
        "query_log_id": request.query_log_id,
        "user_id": user_id,
        "rating": request.rating,
        "is_correct": 1 if request.is_correct else 0,
        "corrected_sql": request.corrected_sql,
        "feedback_text": request.feedback_text,
    })
    db.commit()
    return {"success": True}
