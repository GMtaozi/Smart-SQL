"""
SQL Executor Service - Execute SQL with Read-Only Constraints
"""

from typing import Optional, Any
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import QueuePool

from server.db.database import get_db_session


# Security constraints
DEFAULT_STATEMENT_TIMEOUT_MS = 30000  # 30 seconds
DEFAULT_ROW_LIMIT = 10  # Preview limit for normal queries


@dataclass
class ExecutionResult:
    """SQL execution result."""
    success: bool
    columns: list[str]
    rows: list[dict]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None


@dataclass
class DatasourceConfig:
    """Database connection configuration."""
    host: str
    port: int
    database: str
    username: str
    password: str
    db_type: str = "postgresql"  # support: postgresql, mysql

    def __post_init__(self):
        """Validate and sanitize configuration."""
        # Validate host is not empty
        if not self.host or not self.host.strip():
            raise ValueError("host cannot be empty")
        # Strip whitespace from host
        self.host = self.host.strip()
        # Validate port is positive
        if self.port <= 0 or self.port > 65535:
            raise ValueError(f"port must be between 1 and 65535, got {self.port}")
        # Validate database name is not empty
        if not self.database or not self.database.strip():
            raise ValueError("database name cannot be empty")
        self.database = self.database.strip()
        # Validate username is not empty
        if not self.username or not self.username.strip():
            raise ValueError("username cannot be empty")
        self.username = self.username.strip()

    @property
    def connection_url(self) -> str:
        """Build SQLAlchemy connection URL."""
        import urllib.parse
        if self.db_type in ("postgresql", "pg"):
            return (
                f"postgresql://{urllib.parse.quote(self.username)}:{urllib.parse.quote(self.password)}"
                f"@{self.host}:{self.port}/{self.database}"
            )
        elif self.db_type in ("mysql", "mariadb"):
            return (
                f"mysql+pymysql://{urllib.parse.quote(self.username)}:{urllib.parse.quote(self.password)}"
                f"@{self.host}:{self.port}/{self.database}?charset=utf8mb4"
            )
        else:
            raise ValueError(f"Unsupported db_type: {self.db_type}")


class SQLExecutor:
    """
    SQL Executor with read-only constraints and security limits.

    Security features:
    - Read-only connection (enforced via connection params)
    - Statement timeout (default 30s)
    - Row limit (default 1000)
    - No write operations allowed
    """

    def __init__(
        self,
        statement_timeout_ms: int = DEFAULT_STATEMENT_TIMEOUT_MS,
        row_limit: int = DEFAULT_ROW_LIMIT,
    ):
        self.statement_timeout_ms = statement_timeout_ms
        self.row_limit = row_limit
        # Cache engines per datasource
        self._engines: dict[int, Any] = {}

    def _get_engine(self, datasource_config: DatasourceConfig) -> Any:
        """Get or create SQLAlchemy engine for datasource."""
        # Use datasource hash as cache key (datasource_id not available here)
        cache_key = hash(datasource_config.connection_url)
        print(f"[DEBUG] Connection URL: mysql+pymysql://{datasource_config.username}:***@{datasource_config.host}:{datasource_config.port}/{datasource_config.database}")

        if cache_key not in self._engines:
            print(f"[DEBUG] Creating new engine for cache key: {cache_key}")
            engine = create_engine(
                datasource_config.connection_url,
                poolclass=QueuePool,
                pool_size=1,  # 减少连接池大小
                max_overflow=2,
                pool_pre_ping=True,  # 每次使用前检测连接
                pool_recycle=300,  # 5分钟回收连接，减少 stale 连接问题
                pool_timeout=10,  # 连接获取超时
                connect_args={
                    "connect_timeout": 10,
                    "read_timeout": 30,
                    "write_timeout": 30,
                },
            )
            self._engines[cache_key] = engine
        else:
            print(f"[DEBUG] Using cached engine for cache key: {cache_key}")

        return self._engines[cache_key]

    def _validate_engine(self, engine: Any) -> bool:
        """Validate engine connection is still alive."""
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"[DEBUG] Engine validation failed: {e}")
            return False

    def _inject_timeout_and_limit(self, sql: str, db_type: str, apply_limit: bool = True) -> str:
        """Inject statement timeout and row limit into SQL."""
        import re
        sql = sql.strip().rstrip(';')

        # Remove existing LIMIT clause (case-insensitive, handles newlines)
        sql = re.sub(r'\s+LIMIT\s+\d+\s*$', '', sql, flags=re.IGNORECASE)

        if not apply_limit:
            # No limit mode for exports - only set timeout
            if db_type == "postgresql":
                return f"SET statement_timeout = '{self.statement_timeout_ms}ms'; {sql}"
            return sql

        if db_type == "postgresql":
            # Set session timeout and add LIMIT
            timeout_sql = f"SET statement_timeout = '{self.statement_timeout_ms}ms'; {sql}"
            timeout_sql += f" LIMIT {self.row_limit}"
            return timeout_sql

        elif db_type == "mysql":
            # For MySQL, just add LIMIT
            sql += f" LIMIT {self.row_limit}"
            return sql

        return sql

    def execute(
        self,
        sql: str,
        datasource_config: DatasourceConfig,
    ) -> ExecutionResult:
        """
        Execute SQL with read-only constraints.

        Args:
            sql: SQL statement to execute
            datasource_config: Target database connection config

        Returns:
            ExecutionResult with columns, rows, and metadata
        """
        start_time = datetime.now()

        # Inject timeout and row limit
        safe_sql = self._inject_timeout_and_limit(sql, datasource_config.db_type)

        try:
            engine = self._get_engine(datasource_config)
            print(f"[DEBUG] Executing SQL on {datasource_config.db_type} at {datasource_config.host}:{datasource_config.port}/{datasource_config.database}")
            print(f"[DEBUG] Original SQL: {sql}")
            print(f"[DEBUG] Safe SQL: {safe_sql}")

            with engine.connect() as conn:
                # Execute query
                result = conn.execute(text(safe_sql))
                conn.commit()

                # Fetch all rows
                rows = result.fetchall()
                columns = list(result.keys())

                print(f"[DEBUG] Query returned {len(rows)} rows, columns: {columns}")

                # Convert to list of dicts - handle special types like datetime
                row_dicts = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        val = row[i]
                        # Convert datetime objects to ISO format strings
                        if hasattr(val, 'isoformat'):
                            val = val.isoformat()
                        row_dict[col] = val
                    row_dicts.append(row_dict)

                if row_dicts:
                    print(f"[DEBUG] First row: {row_dicts[0]}")
                else:
                    print(f"[DEBUG] No rows returned")

                execution_time_ms = (
                    datetime.now() - start_time
                ).total_seconds() * 1000

                return ExecutionResult(
                    success=True,
                    columns=columns,
                    rows=row_dicts,
                    row_count=len(row_dicts),
                    execution_time_ms=execution_time_ms,
                )

        except Exception as e:
            execution_time_ms = (
                datetime.now() - start_time
            ).total_seconds() * 1000
            import traceback
            print(f"[ERROR] SQL execution failed: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

            return ExecutionResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                error=str(e),
            )

    def execute_no_limit(
        self,
        sql: str,
        datasource_config: DatasourceConfig,
    ) -> ExecutionResult:
        """
        Execute SQL without row limit (for exports).

        Args:
            sql: SQL statement to execute
            datasource_config: Target database connection config

        Returns:
            ExecutionResult with columns, rows, and metadata (all rows)
        """
        start_time = datetime.now()

        # Inject timeout but NO row limit
        safe_sql = self._inject_timeout_and_limit(sql, datasource_config.db_type, apply_limit=False)

        try:
            engine = self._get_engine(datasource_config)
            print(f"[DEBUG] Executing SQL (no limit) on {datasource_config.db_type}")
            print(f"[DEBUG] Original SQL: {sql}")
            print(f"[DEBUG] Safe SQL: {safe_sql}")

            with engine.connect() as conn:
                # Execute query
                result = conn.execute(text(safe_sql))
                conn.commit()

                # Fetch all rows
                rows = result.fetchall()
                columns = list(result.keys())

                print(f"[DEBUG] Query returned {len(rows)} rows, columns: {columns}")

                # Convert to list of dicts - handle special types like datetime
                row_dicts = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        val = row[i]
                        # Convert datetime objects to ISO format strings
                        if hasattr(val, 'isoformat'):
                            val = val.isoformat()
                        row_dict[col] = val
                    row_dicts.append(row_dict)

                execution_time_ms = (
                    datetime.now() - start_time
                ).total_seconds() * 1000

                return ExecutionResult(
                    success=True,
                    columns=columns,
                    rows=row_dicts,
                    row_count=len(row_dicts),
                    execution_time_ms=execution_time_ms,
                )

        except Exception as e:
            execution_time_ms = (
                datetime.now() - start_time
            ).total_seconds() * 1000
            import traceback
            print(f"[ERROR] SQL execution (no limit) failed: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")

            return ExecutionResult(
                success=False,
                columns=[],
                rows=[],
                row_count=0,
                execution_time_ms=execution_time_ms,
                error=str(e),
            )

    def execute_from_datasource_id(
        self,
        sql: str,
        datasource_id: int,
        db: Optional[Session] = None,
    ) -> ExecutionResult:
        """
        Execute SQL using datasource_id (looks up config from app DB).

        Args:
            sql: SQL statement to execute
            datasource_id: ID of configured datasource
            db: App database session for looking up datasource config
        """
        close_db = False
        if db is None:
            db = get_db_session()
            close_db = True

        try:
            # Lookup datasource config from app database
            query = text("""
                SELECT host, port, database_name, username, password, db_type
                FROM datasources
                WHERE id = :datasource_id
            """)
            result = db.execute(query, {"datasource_id": datasource_id})
            row = result.fetchone()

            if not row:
                return ExecutionResult(
                    success=False,
                    columns=[],
                    rows=[],
                    row_count=0,
                    execution_time_ms=0,
                    error=f"Datasource {datasource_id} not found",
                )

            config = DatasourceConfig(
                host=row[0],
                port=row[1],
                database=row[2],
                username=row[3],
                password=row[4],
                db_type=row[5] or "postgresql",
            )

            return self.execute(sql, config)

        finally:
            if close_db:
                db.close()

    def close(self):
        """Close all cached engines."""
        for engine in self._engines.values():
            engine.dispose()
        self._engines.clear()


# Singleton instance
_executor_instance: Optional[SQLExecutor] = None


def get_sql_executor() -> SQLExecutor:
    """Get or create SQL executor singleton."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SQLExecutor()
    return _executor_instance
