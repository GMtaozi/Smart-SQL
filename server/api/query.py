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
    ExportCreateRequest,
    ExportCreateResponse,
    ExportStatusResponse,
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


# In-memory task queue for async export processing
# In production, use Celery or similar
import threading
import io
import csv
from datetime import datetime
from server.models.export_task import ExportTask

# Global task registry (task_id -> task dict)
_export_tasks: dict = {}
_export_lock = threading.Lock()


def _process_export_task(task_id: str, sql: str, datasource_id: int, user_id: int, db_session_args: dict):
    """Background worker to process export task."""
    from server.db.database import get_db_context
    from server.utils.security import decrypt_password
    from sqlalchemy import text

    try:
        # Update status to processing
        with _export_lock:
            task = _export_tasks[task_id]
            task["status"] = "processing"

        with get_db_context() as db:
            # Get datasource config
            ds_query = text("""
                SELECT host, port, database_name, username, password_encrypted, db_type
                FROM datasources
                WHERE id = :datasource_id AND user_id = :user_id
            """)
            ds_result = db.execute(ds_query, {
                "datasource_id": datasource_id,
                "user_id": user_id,
            })
            ds_row = ds_result.fetchone()

            if not ds_row:
                raise Exception("数据源不存在或无权限")

            decrypted_password = decrypt_password(ds_row[4]) if ds_row[4] else ""
            config = DatasourceConfig(
                host=ds_row[0],
                port=ds_row[1],
                database=ds_row[2],
                username=ds_row[3],
                password=decrypted_password,
                db_type=ds_row[5] or "postgresql",
            )

        # Execute without limit
        executor = get_sql_executor()
        result = executor.execute_no_limit(sql, config)

        if not result.success:
            raise Exception(result.error or "查询执行失败")

        # Generate CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(result.columns)

        # Write data rows
        for row in result.rows:
            writer.writerow([row.get(col, "") for col in result.columns])

        csv_content = output.getvalue()
        output.close()

        # Update task as completed
        with _export_lock:
            task = _export_tasks[task_id]
            task["status"] = "completed"
            task["total_rows"] = result.row_count
            task["csv_content"] = csv_content
            task["completed_at"] = datetime.utcnow().isoformat()

        # Update database record
        with get_db_context() as db:
            from sqlalchemy import text as sql_text
            update_query = sql_text("""
                UPDATE export_tasks
                SET status = 'completed',
                    total_rows = :total_rows,
                    csv_content = :csv_content,
                    completed_at = NOW()
                WHERE id = :task_id
            """)
            db.execute(update_query, {
                "total_rows": result.row_count,
                "csv_content": csv_content,
                "task_id": task_id,
            })
            db.commit()

    except Exception as e:
        with _export_lock:
            task = _export_tasks[task_id]
            task["status"] = "failed"
            task["error_message"] = str(e)

        with get_db_context() as db:
            from sqlalchemy import text as sql_text
            update_query = sql_text("""
                UPDATE export_tasks
                SET status = 'failed',
                    error_message = :error_message,
                    completed_at = NOW()
                WHERE id = :task_id
            """)
            db.execute(update_query, {
                "error_message": str(e),
                "task_id": task_id,
            })
            db.commit()


@router.post("/export", response_model=ExportCreateResponse)
def create_export_task(
    request: ExportCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Create an async export task.

    1. Creates export task record
    2. Starts background thread to execute query
    3. Returns preview of first 10 rows immediately
    """
    from sqlalchemy import text
    from server.utils.security import decrypt_password

    # Validate SQL safety first
    guard = get_sql_guard()
    scan_result = guard.scan(request.sql)

    if not scan_result.passed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SQL 安全扫描未通过: {scan_result.reason}",
        )

    # Get datasource config
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

    decrypted_password = decrypt_password(ds_row[4]) if ds_row[4] else ""
    config = DatasourceConfig(
        host=ds_row[0],
        port=ds_row[1],
        database=ds_row[2],
        username=ds_row[3],
        password=decrypted_password,
        db_type=ds_row[5] or "postgresql",
    )

    # First execute with limit to get preview and count
    executor = get_sql_executor()
    preview_result = executor.execute(request.sql, config)

    if not preview_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {preview_result.error}",
        )

    # Create export task in database
    task_id = str(uuid.uuid4())
    insert_query = text("""
        INSERT INTO export_tasks
            (id, user_id, datasource_id, sql_text, status, created_at)
        VALUES
            (:id, :user_id, :datasource_id, :sql_text, 'pending', NOW())
    """)
    db.execute(insert_query, {
        "id": task_id,
        "user_id": user_id,
        "datasource_id": request.datasource_id,
        "sql_text": request.sql,
    })
    db.commit()

    # Register in-memory task
    with _export_lock:
        _export_tasks[task_id] = {
            "id": task_id,
            "user_id": user_id,
            "datasource_id": request.datasource_id,
            "sql": request.sql,
            "status": "pending",
            "total_rows": None,
            "csv_content": None,
            "error_message": None,
            "created_at": datetime.utcnow().isoformat(),
            "completed_at": None,
        }

    # Start background thread for full export
    thread = threading.Thread(
        target=_process_export_task,
        args=(task_id, request.sql, request.datasource_id, user_id, {}),
        daemon=True
    )
    thread.start()

    # Return preview data immediately
    preview_rows = preview_result.rows[:10]
    total_rows = preview_result.row_count  # This is limited to 1000, actual total may be higher

    message = f"导出任务已创建，正在处理..."
    if total_rows >= 1000:
        message = f"导出任务已创建，共有超过1000行数据，正在后台处理..."

    return ExportCreateResponse(
        task_id=task_id,
        status="processing",
        preview_rows=preview_rows,
        preview_columns=preview_result.columns,
        preview_row_count=len(preview_rows),
        total_rows=total_rows,
        message=message,
    )


@router.get("/export/{task_id}", response_model=ExportStatusResponse)
def get_export_status(
    task_id: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Get export task status. Returns CSV content when completed."""
    # Check in-memory task first
    with _export_lock:
        task = _export_tasks.get(task_id)

    if task is None:
        # Try to get from database
        from sqlalchemy import text
        query = text("""
            SELECT id, user_id, datasource_id, sql_text, status,
                   total_rows, csv_content, error_message, created_at, completed_at
            FROM export_tasks
            WHERE id = :task_id AND user_id = :user_id
        """)
        result = db.execute(query, {
            "task_id": task_id,
            "user_id": user_id,
        })
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="导出任务不存在",
            )

        task = {
            "id": str(row[0]),
            "user_id": row[1],
            "datasource_id": row[2],
            "sql": row[3],
            "status": row[4],
            "total_rows": row[5],
            "csv_content": row[6],
            "error_message": row[7],
            "created_at": str(row[8]) if row[8] else None,
            "completed_at": str(row[9]) if row[9] else None,
        }

        # Sync to memory if still processing
        if task["status"] in ("pending", "processing"):
            with _export_lock:
                _export_tasks[task_id] = task

    # Verify ownership
    if task["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此导出任务",
        )

    message = ""
    if task["status"] == "pending":
        message = "任务等待中..."
    elif task["status"] == "processing":
        message = "正在导出数据..."
    elif task["status"] == "completed":
        message = f"导出完成，共 {task['total_rows']} 行数据"
    elif task["status"] == "failed":
        message = f"导出失败: {task['error_message']}"

    return ExportStatusResponse(
        task_id=task["id"],
        status=task["status"],
        total_rows=task.get("total_rows"),
        csv_content=task.get("csv_content") if task["status"] == "completed" else None,
        error_message=task.get("error_message"),
        message=message,
    )
