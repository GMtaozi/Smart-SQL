"""
Schema Service - 业务逻辑层

负责数据源、表的 CRUD 操作，以及从远程数据库同步表结构。
"""

from typing import List, Optional, Tuple
import os

from sqlalchemy import text
from sqlalchemy.orm import Session

from server.db.engine import DatabaseEngineFactory
from server.utils.security import encrypt_password


class SchemaService:
    """Schema 管理服务"""

    def test_connection(
        self,
        db_type: str,
        host: str,
        port: int,
        database: str,
        username: str,
        password: str,
        db_schema: Optional[str] = None,
        extra_params: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """测试数据库连接"""
        try:
            engine = DatabaseEngineFactory.create_engine(
                db_type=db_type,
                host=host,
                port=port,
                database=database,
                username=username,
                password=password,
                schema=db_schema,
                extra_params=extra_params,
                timeout=10,
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            return True, "连接成功"
        except Exception as e:
            return False, f"连接失败: {str(e)}"

    def create_datasource(
        self,
        db: Session,
        user_id: int,
        name: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        db_type: str,
    ) -> dict:
        """创建数据源"""
        try:
            password_enc = encrypt_password(password)
            query = text("""
                INSERT INTO datasources
                    (user_id, name, host, port, database_name, username, password_encrypted, db_type, created_at)
                VALUES
                    (:user_id, :name, :host, :port, :database_name, :username, :password_enc, :db_type, NOW())
                RETURNING id, user_id, name, host, port, database_name, username, db_type, COALESCE(is_active, true), created_at
            """)
            result = db.execute(query, {
                "user_id": user_id,
                "name": name,
                "host": host,
                "port": port,
                "database_name": database_name,
                "username": username,
                "password_enc": password_enc,
                "db_type": db_type,
            })
            db.commit()
            row = result.fetchone()
            if row is None:
                raise ValueError("Failed to create datasource: no row returned")
            return {
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "host": row[3],
                "port": row[4],
                "database_name": row[5],
                "username": row[6],
                "db_type": row[7],
                "is_active": bool(row[8]) if row[8] is not None else True,
                "created_at": str(row[9]),
            }
        except Exception as e:
            db.rollback()
            import traceback
            print(f"[ERROR] create_datasource failed: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            raise

    def list_datasources(self, db: Session, user_id: int) -> List[dict]:
        """列出用户的所有数据源"""
        query = text("""
            SELECT id, user_id, name, host, port, database_name, username, db_type, COALESCE(is_active, true), created_at
            FROM datasources
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """)
        result = db.execute(query, {"user_id": user_id})
        rows = result.fetchall()
        return [
            {
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "host": row[3],
                "port": row[4],
                "database_name": row[5],
                "username": row[6],
                "db_type": row[7],
                "is_active": bool(row[8]) if row[8] is not None else True,
                "created_at": str(row[9]),
            }
            for row in rows
        ]

    def delete_datasource(self, db: Session, datasource_id: int, user_id: int) -> bool:
        """删除数据源"""
        # Get table IDs for this datasource
        tables_query = text("SELECT id FROM schema_tables WHERE datasource_id = :datasource_id")
        table_ids = [row[0] for row in db.execute(tables_query, {"datasource_id": datasource_id}).fetchall()]

        # Delete schema columns for these tables
        if table_ids:
            delete_columns = text("DELETE FROM schema_columns WHERE table_id = :table_id")
            for table_id in table_ids:
                db.execute(delete_columns, {"table_id": table_id})

        # Delete schema tables
        delete_tables = text("DELETE FROM schema_tables WHERE datasource_id = :datasource_id")
        db.execute(delete_tables, {"datasource_id": datasource_id})

        # Delete datasource
        delete_query = text("DELETE FROM datasources WHERE id = :id AND user_id = :user_id")
        db.execute(delete_query, {"id": datasource_id, "user_id": user_id})
        db.commit()
        return True

    def update_datasource(
        self,
        db: Session,
        datasource_id: int,
        user_id: int,
        name: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        db_type: Optional[str] = None,
    ) -> dict:
        """更新数据源"""
        # Verify ownership
        check_query = text("SELECT id FROM datasources WHERE id = :id AND user_id = :user_id")
        if not db.execute(check_query, {"id": datasource_id, "user_id": user_id}).fetchone():
            raise PermissionError("无权限")

        # Build update query dynamically
        updates = []
        params = {"id": datasource_id, "user_id": user_id}

        if name is not None:
            updates.append("name = :name")
            params["name"] = name
        if host is not None:
            updates.append("host = :host")
            params["host"] = host
        if port is not None:
            updates.append("port = :port")
            params["port"] = port
        if database_name is not None:
            updates.append("database_name = :database_name")
            params["database_name"] = database_name
        if username is not None:
            updates.append("username = :username")
            params["username"] = username
        if password is not None and password != "":
            updates.append("password_encrypted = :password_enc")
            params["password_enc"] = encrypt_password(password)
        if db_type is not None:
            updates.append("db_type = :db_type")
            params["db_type"] = db_type

        if updates:
            update_query = text(f"""
                UPDATE datasources
                SET {', '.join(updates)}
                WHERE id = :id AND user_id = :user_id
                RETURNING id, user_id, name, host, port, database_name, username, db_type, COALESCE(is_active, true), created_at
            """)
            result = db.execute(update_query, params)
            db.commit()
            row = result.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "name": row[2],
                    "host": row[3],
                    "port": row[4],
                    "database_name": row[5],
                    "username": row[6],
                    "db_type": row[7],
                    "is_active": bool(row[8]) if row[8] is not None else True,
                    "created_at": str(row[9]),
                }
        else:
            # No updates, just return current data
            select_query = text("""
                SELECT id, user_id, name, host, port, database_name, username, db_type, COALESCE(is_active, true), created_at
                FROM datasources WHERE id = :id AND user_id = :user_id
            """)
            result = db.execute(select_query, {"id": datasource_id, "user_id": user_id})
            row = result.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_id": row[1],
                    "name": row[2],
                    "host": row[3],
                    "port": row[4],
                    "database_name": row[5],
                    "username": row[6],
                    "db_type": row[7],
                    "is_active": bool(row[8]) if row[8] is not None else True,
                    "created_at": str(row[9]),
                }

        raise ValueError("数据源不存在")

    def create_table_schema(
        self,
        db: Session,
        user_id: int,
        datasource_id: int,
        table_name: str,
        table_comment: Optional[str],
        columns: List[dict],
    ) -> dict:
        """创建表结构"""
        # Verify datasource ownership
        check_query = text("SELECT id FROM datasources WHERE id = :id AND user_id = :user_id")
        if not db.execute(check_query, {"id": datasource_id, "user_id": user_id}).fetchone():
            raise PermissionError("无权限")

        # Insert table
        table_query = text("""
            INSERT INTO schema_tables (datasource_id, table_name, table_comment, created_at)
            VALUES (:datasource_id, :table_name, :table_comment, NOW())
            RETURNING id, created_at
        """)
        table_result = db.execute(table_query, {
            "datasource_id": datasource_id,
            "table_name": table_name,
            "table_comment": table_comment,
        })
        table_row = table_result.fetchone()
        table_id = table_row[0]
        created_at = table_row[1]

        # Insert columns
        for col in columns:
            col_query = text("""
                INSERT INTO schema_columns
                    (table_id, column_name, data_type, column_comment, is_primary_key, is_nullable, column_id, created_at)
                VALUES
                    (:table_id, :column_name, :data_type, :column_comment, :is_primary_key, :is_nullable, :column_id, NOW())
            """)
            db.execute(col_query, {
                "table_id": table_id,
                "column_name": col["column_name"],
                "data_type": col["data_type"],
                "column_comment": col.get("column_comment", ""),
                "is_primary_key": 1 if col.get("is_primary_key") else 0,
                "is_nullable": 1 if col.get("is_nullable") else 0,
                "column_id": col.get("column_id", 0),
            })

        db.commit()

        # Upsert vector embedding (if not disabled)
        if os.getenv("DISABLE_VECTOR_SYNC", "").lower() not in ("1", "true", "yes"):
            try:
                from server.services.vector_store import get_vector_store
                vector_store = get_vector_store()
                vector_store.upsert_table_embedding(
                    db=db,
                    table_id=table_id,
                    table_name=table_name,
                    table_comment=table_comment or "",
                    column_names=[c["column_name"] for c in columns],
                    column_comments=[c.get("column_comment", "") for c in columns],
                )
            except Exception as e:
                print(f"[WARN] Vector embedding skipped for table {table_name}: {str(e)[:100]}")

        return {
            "id": table_id,
            "datasource_id": datasource_id,
            "table_name": table_name,
            "table_comment": table_comment,
            "columns": columns,
            "created_at": str(created_at),
        }

    def list_tables(self, db: Session, user_id: int, datasource_id: int) -> List[dict]:
        """列出数据源的所有表"""
        # Verify ownership
        check_query = text("SELECT id FROM datasources WHERE id = :id AND user_id = :user_id")
        if not db.execute(check_query, {"id": datasource_id, "user_id": user_id}).fetchone():
            raise PermissionError("无权限")

        # Get tables
        tables_query = text("""
            SELECT id, datasource_id, table_name, table_comment, created_at
            FROM schema_tables
            WHERE datasource_id = :datasource_id
            ORDER BY table_name
        """)
        tables_result = db.execute(tables_query, {"datasource_id": datasource_id})
        table_rows = tables_result.fetchall()

        result = []
        for row in table_rows:
            # Get columns for this table
            cols_query = text("""
                SELECT column_name, data_type, column_comment, is_primary_key, is_nullable, column_id
                FROM schema_columns
                WHERE table_id = :table_id
                ORDER BY column_id
            """)
            cols_result = db.execute(cols_query, {"table_id": row[0]})
            cols = cols_result.fetchall()

            result.append({
                "id": row[0],
                "datasource_id": row[1],
                "table_name": row[2],
                "table_comment": row[3],
                "columns": [
                    {
                        "column_name": c[0],
                        "data_type": c[1],
                        "column_comment": c[2],
                        "is_primary_key": bool(c[3]),
                        "is_nullable": bool(c[4]),
                        "column_id": c[5],
                    }
                    for c in cols
                ],
                "created_at": str(row[4]),
            })

        return result

    def delete_table_schema(self, db: Session, user_id: int, table_id: int) -> bool:
        """删除表结构"""
        # Verify ownership via datasource
        check_query = text("""
            SELECT st.id FROM schema_tables st
            JOIN datasources d ON st.datasource_id = d.id
            WHERE st.id = :table_id AND d.user_id = :user_id
        """)
        if not db.execute(check_query, {"table_id": table_id, "user_id": user_id}).fetchone():
            raise PermissionError("无权限")

        # Delete embedding
        if os.getenv("DISABLE_VECTOR_SYNC", "").lower() not in ("1", "true", "yes"):
            try:
                from server.services.vector_store import get_vector_store
                vector_store = get_vector_store()
                vector_store.delete_table_embedding(db, table_id)
            except Exception:
                pass

        # Delete columns and table
        db.execute(text("DELETE FROM schema_columns WHERE table_id = :table_id"), {"table_id": table_id})
        db.execute(text("DELETE FROM schema_tables WHERE id = :table_id"), {"table_id": table_id})
        db.commit()
        return True

    def get_remote_tables(
        self,
        db: Session,
        user_id: int,
        datasource_id: int,
    ) -> List[dict]:
        """从远程数据库获取表列表"""
        # Get datasource config
        ds_query = text("""
            SELECT host, port, database_name, username, password_encrypted, db_type, db_schema
            FROM datasources WHERE id = :id AND user_id = :user_id
        """)
        ds_result = db.execute(ds_query, {"id": datasource_id, "user_id": user_id})
        ds_row = ds_result.fetchone()

        if not ds_row:
            raise ValueError("数据源不存在或无权限")

        from server.utils.security import decrypt_password
        password = decrypt_password(ds_row[4])

        # Create engine and get tables
        engine = DatabaseEngineFactory.create_engine(
            db_type=ds_row[5],
            host=ds_row[0],
            port=ds_row[1],
            database=ds_row[2],
            username=ds_row[3],
            password=password,
            schema=ds_row[6],
            timeout=10,
        )

        tables = []
        query = self._get_tables_query(ds_row[5], ds_row[2])
        with engine.connect() as conn:
            if ds_row[5] == 'mysql':
                result = conn.execute(query)
                for row in result:
                    tables.append({"table_name": row[0], "table_comment": row[1] or ""})
            elif ds_row[5] == 'pg':
                result = conn.execute(query)
                for row in result:
                    tables.append({"table_name": row[0], "table_comment": row[2] or ""})
            else:
                # Default
                result = conn.execute(query, {"database": ds_row[2]})
                for row in result:
                    tables.append({"table_name": row[0], "table_comment": row[1] or ""})

        engine.dispose()
        return tables

    def get_remote_columns(
        self,
        db: Session,
        user_id: int,
        datasource_id: int,
        table_name: str,
    ) -> List[dict]:
        """从远程数据库获取列信息"""
        # Get datasource config
        ds_query = text("""
            SELECT host, port, database_name, username, password_encrypted, db_type, db_schema
            FROM datasources WHERE id = :id AND user_id = :user_id
        """)
        ds_result = db.execute(ds_query, {"id": datasource_id, "user_id": user_id})
        ds_row = ds_result.fetchone()

        if not ds_row:
            raise ValueError("数据源不存在或无权限")

        from server.utils.security import decrypt_password
        password = decrypt_password(ds_row[4])

        engine = DatabaseEngineFactory.create_engine(
            db_type=ds_row[5],
            host=ds_row[0],
            port=ds_row[1],
            database=ds_row[2],
            username=ds_row[3],
            password=password,
            schema=ds_row[6],
            timeout=10,
        )

        columns = []
        query = self._get_columns_query(ds_row[5], ds_row[2], table_name)
        with engine.connect() as conn:
            if ds_row[5] == 'mysql':
                result = conn.execute(query, {"table_name": table_name})
                for row in result:
                    columns.append({
                        "column_name": row[0],
                        "data_type": row[1],
                        "column_comment": row[2] or "",
                        "is_nullable": row[3] == "YES",
                        "is_primary_key": row[4] == "PRI",
                    })
            elif ds_row[5] == 'pg':
                result = conn.execute(query, {"table_name": table_name})
                for row in result:
                    columns.append({
                        "column_name": row[0],
                        "data_type": row[1],
                        "column_comment": row[2] or "",
                        "is_nullable": row[3],
                        "is_primary_key": row[4],
                    })
            else:
                result = conn.execute(query, {"database": ds_row[2], "table_name": table_name})
                for row in result:
                    columns.append({
                        "column_name": row[0],
                        "data_type": row[1],
                        "column_comment": row[2] or "",
                        "is_nullable": row[3],
                        "is_primary_key": row[4],
                    })

        engine.dispose()
        return columns

    def sync_tables(
        self,
        db: Session,
        user_id: int,
        datasource_id: int,
        table_names: List[str],
    ) -> List[dict]:
        """同步选定的表结构"""
        # Get datasource config
        ds_query = text("""
            SELECT host, port, database_name, username, password_encrypted, db_type, db_schema
            FROM datasources WHERE id = :id AND user_id = :user_id
        """)
        ds_result = db.execute(ds_query, {"id": datasource_id, "user_id": user_id})
        ds_row = ds_result.fetchone()

        if not ds_row:
            raise ValueError("数据源不存在或无权限")

        from server.utils.security import decrypt_password
        password = decrypt_password(ds_row[4])

        engine = DatabaseEngineFactory.create_engine(
            db_type=ds_row[5],
            host=ds_row[0],
            port=ds_row[1],
            database=ds_row[2],
            username=ds_row[3],
            password=password,
            schema=ds_row[6],
            timeout=30,
        )

        synced_tables = []

        for table_name in table_names:
            table_comment = ""
            columns = []

            # Get columns based on database type
            if ds_row[5] == 'mysql':
                tbl_query = text("""
                    SELECT TABLE_COMMENT FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
                """)
                col_query = text("""
                    SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT,
                           IS_NULLABLE, COLUMN_KEY
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
                    ORDER BY ORDINAL_POSITION
                """)
            elif ds_row[5] == 'pg':
                tbl_query = text("""
                    SELECT COALESCE(d.description, '')
                    FROM pg_tables t
                    LEFT JOIN pg_class c ON c.relname = t.tablename AND c.relkind = 'r'
                    LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = 0
                    WHERE t.schemaname = 'public' AND t.tablename = :table_name
                """)
                col_query = text("""
                    SELECT c.column_name, c.data_type,
                           COALESCE(col_description(c.object_id, c.ordinal_position), ''),
                           c.is_nullable = 'YES', c.column_default LIKE '%nextval%'
                    FROM information_schema.columns c
                    WHERE c.table_name = :table_name
                    ORDER BY c.ordinal_position
                """)
            else:
                tbl_query = text("""
                    SELECT COALESCE(TABLE_COMMENT, '')
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = :database AND TABLE_NAME = :table_name
                """)
                col_query = text("""
                    SELECT COLUMN_NAME, DATA_TYPE, COALESCE(COLUMN_COMMENT, ''),
                           IS_NULLABLE = 'YES', COLUMN_KEY = 'PRI'
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = :database AND TABLE_NAME = :table_name
                    ORDER BY ORDINAL_POSITION
                """)

            with engine.connect() as conn:
                # Get table comment
                if ds_row[5] == 'mysql':
                    tbl_result = conn.execute(tbl_query, {"table_name": table_name})
                elif ds_row[5] == 'pg':
                    tbl_result = conn.execute(tbl_query, {"table_name": table_name})
                else:
                    tbl_result = conn.execute(tbl_query, {"database": ds_row[2], "table_name": table_name})

                tbl_row = tbl_result.fetchone()
                if tbl_row:
                    table_comment = tbl_row[0] if tbl_row[0] else ""

                # Get columns
                if ds_row[5] == 'mysql':
                    result = conn.execute(col_query, {"table_name": table_name})
                    for col_idx, row in enumerate(result):
                        columns.append({
                            "column_name": row[0],
                            "data_type": row[1],
                            "column_comment": row[2] or "",
                            "is_primary_key": row[4] == "PRI",
                            "is_nullable": row[3] == "YES",
                            "column_id": col_idx + 1,
                        })
                elif ds_row[5] == 'pg':
                    result = conn.execute(col_query, {"table_name": table_name})
                    for col_idx, row in enumerate(result):
                        columns.append({
                            "column_name": row[0],
                            "data_type": row[1],
                            "column_comment": row[2] or "",
                            "is_primary_key": bool(row[4]),
                            "is_nullable": row[3],
                            "column_id": col_idx + 1,
                        })
                else:
                    result = conn.execute(col_query, {"database": ds_row[2], "table_name": table_name})
                    for col_idx, row in enumerate(result):
                        columns.append({
                            "column_name": row[0],
                            "data_type": row[1],
                            "column_comment": row[2] or "",
                            "is_primary_key": row[4] == "PRI",
                            "is_nullable": row[3],
                            "column_id": col_idx + 1,
                        })

            # Insert table schema
            insert_table = text("""
                INSERT INTO schema_tables (datasource_id, table_name, table_comment, created_at)
                VALUES (:datasource_id, :table_name, :table_comment, NOW())
                ON CONFLICT (datasource_id, table_name) DO UPDATE
                SET table_comment = EXCLUDED.table_comment
                RETURNING id, created_at
            """)
            table_result = db.execute(insert_table, {
                "datasource_id": datasource_id,
                "table_name": table_name,
                "table_comment": table_comment,
            })
            table_row = table_result.fetchone()
            table_id = table_row[0]
            created_at = table_row[1]

            # Delete existing columns and insert new ones
            db.execute(text("DELETE FROM schema_columns WHERE table_id = :table_id"), {"table_id": table_id})

            for col in columns:
                col_query = text("""
                    INSERT INTO schema_columns
                        (table_id, column_name, data_type, column_comment, is_primary_key, is_nullable, column_id, created_at)
                    VALUES
                        (:table_id, :column_name, :data_type, :column_comment, :is_primary_key, :is_nullable, :column_id, NOW())
                """)
                db.execute(col_query, {
                    "table_id": table_id,
                    "column_name": col["column_name"],
                    "data_type": col["data_type"],
                    "column_comment": col["column_comment"],
                    "is_primary_key": 1 if col["is_primary_key"] else 0,
                    "is_nullable": 1 if col["is_nullable"] else 0,
                    "column_id": col["column_id"],
                })

            db.commit()

            # Upsert vector embedding
            if os.getenv("DISABLE_VECTOR_SYNC", "").lower() not in ("1", "true", "yes"):
                try:
                    from server.services.vector_store import get_vector_store
                    vector_store = get_vector_store()
                    vector_store.upsert_table_embedding(
                        db=db,
                        table_id=table_id,
                        table_name=table_name,
                        table_comment=table_comment,
                        column_names=[c["column_name"] for c in columns],
                        column_comments=[c["column_comment"] for c in columns],
                    )
                except Exception as e:
                    print(f"[WARN] Vector embedding skipped for table {table_name}: {str(e)[:100]}")

            synced_tables.append({
                "id": table_id,
                "datasource_id": datasource_id,
                "table_name": table_name,
                "table_comment": table_comment,
                "columns": columns,
                "created_at": str(created_at),
            })

        engine.dispose()
        return synced_tables

    def _get_tables_query(self, db_type: str, database: str):
        """根据数据库类型返回获取表的 SQL"""
        if db_type == 'mysql':
            return text("""
                SELECT TABLE_NAME, TABLE_COMMENT
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                ORDER BY TABLE_NAME
            """)
        elif db_type == 'pg':
            return text("""
                SELECT t.tablename AS table_name,
                       COALESCE(c.objsubid, 0) AS subid,
                       COALESCE(d.description, '') AS table_comment
                FROM pg_tables t
                LEFT JOIN pg_class c ON c.relname = t.tablename AND c.relkind = 'r'
                LEFT JOIN pg_description d ON d.objoid = c.oid AND d.objsubid = 0
                WHERE t.schemaname = 'public'
                ORDER BY t.tablename
            """)
        else:
            return text("""
                SELECT TABLE_NAME, COALESCE(TABLE_COMMENT, '') AS table_comment
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = :database
                ORDER BY TABLE_NAME
            """)

    def _get_columns_query(self, db_type: str, database: str, table_name: str):
        """根据数据库类型返回获取列的 SQL"""
        if db_type == 'mysql':
            return text("""
                SELECT COLUMN_NAME, DATA_TYPE, COLUMN_COMMENT,
                       IS_NULLABLE, COLUMN_KEY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table_name
                ORDER BY ORDINAL_POSITION
            """)
        elif db_type == 'pg':
            return text("""
                SELECT c.column_name, c.data_type,
                       COALESCE(col_description(c.object_id, c.ordinal_position), ''),
                       c.is_nullable = 'YES', c.column_default LIKE '%nextval%'
                FROM information_schema.columns c
                WHERE c.table_name = :table_name
                ORDER BY c.ordinal_position
            """)
        else:
            return text("""
                SELECT COLUMN_NAME, DATA_TYPE, COALESCE(COLUMN_COMMENT, ''),
                       IS_NULLABLE = 'YES', COLUMN_KEY = 'PRI'
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = :database AND TABLE_NAME = :table_name
                ORDER BY ORDINAL_POSITION
            """)


# Singleton instance
_schema_service_instance: Optional[SchemaService] = None


def get_schema_service() -> SchemaService:
    """Get or create schema service singleton."""
    global _schema_service_instance
    if _schema_service_instance is None:
        _schema_service_instance = SchemaService()
    return _schema_service_instance
