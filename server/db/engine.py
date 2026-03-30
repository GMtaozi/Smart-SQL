"""Database engine factory for multiple database types"""

import urllib.parse
from typing import Optional, Dict, Any

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session

from server.db.constant import DBType, DEFAULT_PORTS


class DatabaseEngineFactory:
    """Factory for creating database engines based on type"""

    @staticmethod
    def create_engine(
        db_type: str,
        host: str,
        port: Optional[int],
        database: str,
        username: str,
        password: str,
        schema: Optional[str] = None,
        extra_params: Optional[str] = None,
        timeout: int = 30,
    ) -> Engine:
        """Create SQLAlchemy engine for the specified database type.

        Args:
            db_type: Database type (mysql, pg, oracle, etc.)
            host: Database host
            port: Database port (auto-filled if not provided)
            database: Database name
            username: Database username
            password: Database password
            schema: Schema name (for databases that need it)
            extra_params: Extra connection parameters
            timeout: Connection timeout in seconds

        Returns:
            SQLAlchemy Engine instance

        Raises:
            ValueError: If required parameters are invalid
        """
        # Validate host
        if not host or not host.strip():
            raise ValueError("host cannot be empty")
        host = host.strip()

        # Validate port
        if port is not None and (port <= 0 or port > 65535):
            raise ValueError(f"port must be between 1 and 65535, got {port}")
        port = port or DEFAULT_PORTS.get(db_type, 5432)

        if db_type == DBType.MYSQL:
            return DatabaseEngineFactory._create_mysql_engine(
                host, port, database, username, password, extra_params, timeout
            )
        elif db_type == DBType.PG:
            return DatabaseEngineFactory._create_pg_engine(
                host, port, database, username, password, extra_params, timeout
            )
        elif db_type == DBType.ORACLE:
            return DatabaseEngineFactory._create_oracle_engine(
                host, port, database, username, password, extra_params, timeout
            )
        elif db_type == DBType.CK:
            return DatabaseEngineFactory._create_clickhouse_engine(
                host, port, database, username, password, extra_params, timeout
            )
        elif db_type == DBType.SQL_SERVER:
            return DatabaseEngineFactory._create_sqlserver_engine(
                host, port, database, username, password, schema, extra_params, timeout
            )
        elif db_type == DBType.DORIS:
            return DatabaseEngineFactory._create_doris_engine(
                host, port, database, username, password, extra_params, timeout
            )
        elif db_type == DBType.STARROCKS:
            return DatabaseEngineFactory._create_starrocks_engine(
                host, port, database, username, password, extra_params, timeout
            )
        elif db_type == DBType.ES:
            return DatabaseEngineFactory._create_elasticsearch_engine(
                host, port, username, password, extra_params, timeout
            )
        elif db_type == DBType.KINGBASE:
            return DatabaseEngineFactory._create_kingbase_engine(
                host, port, database, username, password, extra_params, timeout
            )
        elif db_type == DBType.DM:
            return DatabaseEngineFactory._create_dm_engine(
                host, port, database, username, password, extra_params, timeout
            )
        elif db_type == DBType.REDSHIFT:
            return DatabaseEngineFactory._create_redshift_engine(
                host, port, database, username, password, extra_params, timeout
            )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    @staticmethod
    def _create_mysql_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        params = extra_params or ""
        if params:
            params = "&" + params if not params.startswith("?") else params

        connection_url = (
            f"mysql+pymysql://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/{database}?charset=utf8mb4{params}"
        )

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            connect_args={"connect_timeout": timeout},
        )

    @staticmethod
    def _create_pg_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        params = ""
        if extra_params:
            params = f"?{extra_params}"

        connection_url = (
            f"postgresql://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/{database}{params}"
        )

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"connect_timeout": timeout},
        )

    @staticmethod
    def _create_oracle_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        # Oracle uses SID or Service Name
        dsn = f"(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST={host})(PORT={port}))(CONNECT_DATA=(SERVICE_NAME={database})))"

        connection_url = (
            f"oracle+cx_oracle://{username}:{urllib.parse.quote(password)}"
            f"@{dsn}"
        )

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            connect_args={"connect_timeout": timeout},
        )

    @staticmethod
    def _create_clickhouse_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        params = ""
        if extra_params:
            params = f"?{extra_params}"

        connection_url = (
            f"clickhouse+native://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/{database}{params}"
        )

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            connect_args={"connect_timeout": timeout},
        )

    @staticmethod
    def _create_sqlserver_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        schema: Optional[str], extra_params: Optional[str], timeout: int
    ) -> Engine:
        params = ""
        if extra_params:
            params = f";{extra_params}"

        connection_url = (
            f"mssql+pymssql://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/{database}{params}"
        )

        connect_args = {"login_timeout": timeout}
        if schema:
            connect_args["schema"] = schema

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            connect_args=connect_args,
        )

    @staticmethod
    def _create_doris_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        # Doris uses MySQL protocol
        params = ""
        if extra_params:
            params = f"&{extra_params}"

        connection_url = (
            f"mysql+pymysql://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/{database}?charset=utf8{params}"
        )

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            connect_args={"connect_timeout": timeout},
        )

    @staticmethod
    def _create_starrocks_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        # StarRocks uses MySQL protocol
        params = ""
        if extra_params:
            params = f"&{extra_params}"

        connection_url = (
            f"mysql+pymysql://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/{database}?charset=utf8{params}"
        )

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            connect_args={"connect_timeout": timeout},
        )

    @staticmethod
    def _create_elasticsearch_engine(
        host: str, port: int,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        # Elasticsearch uses HTTP Basic auth via URL
        connection_url = (
            f"http://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/"
        )

        if extra_params:
            connection_url = connection_url.rstrip("/") + f"/?{extra_params}"

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            connect_args={"timeout": timeout},
        )

    @staticmethod
    def _create_kingbase_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        # Kingbase is compatible with PostgreSQL
        params = ""
        if extra_params:
            params = f"?{extra_params}"

        connection_url = (
            f"postgresql://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/{database}{params}"
        )

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"connect_timeout": timeout},
        )

    @staticmethod
    def _create_dm_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        # DM (达梦) database
        params = ""
        if extra_params:
            params = f"?{extra_params}"

        connection_url = (
            f"dm://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/{database}{params}"
        )

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_recycle=3600,
            connect_args={"connect_timeout": timeout},
        )

    @staticmethod
    def _create_redshift_engine(
        host: str, port: int, database: str,
        username: str, password: str,
        extra_params: Optional[str], timeout: int
    ) -> Engine:
        # Redshift uses PostgreSQL protocol
        params = ""
        if extra_params:
            params = f"?{extra_params}"

        connection_url = (
            f"postgresql://{username}:{urllib.parse.quote(password)}"
            f"@{host}:{port}/{database}{params}"
        )

        return create_engine(
            connection_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={"connect_timeout": timeout},
        )


def get_session(engine: Engine) -> Session:
    """Get a new database session from engine"""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
