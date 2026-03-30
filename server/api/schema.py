"""Schema API routes - 数据源/表/字段管理
================================================================================
⚠️ 架构守护规则 / ARCHITECTURE GUARDRAILS ⚠️

1. 【职责单一】：本文件仅作为 API 路由层 (Controller)。
   - 禁止在此处编写复杂的业务逻辑 (如 SQL 生成、向量计算)。
   - 复杂逻辑请移至 server/services/ 目录。

2. 【向后兼容】：修改接口时，严禁破坏现有客户端调用。
   - 新增字段必须 Optional 或有默认值。
   - 禁止直接删除或重命名现有字段。

3. 【事务管理】：所有数据库写操作必须使用 try-except 块包裹。
   - 确保异常发生时能回滚，且连接池被正确释放。

4. 【数据安全】：
   - 严禁通过 API 返回数据库密码或敏感配置。
   - 所有输入输出必须经过 Pydantic 模型严格校验。

================================================================================
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from server.db.database import get_db
from server.api.auth import get_current_user_id
from server.services.schema_service import get_schema_service

router = APIRouter(prefix="/api/schema", tags=["schema"])


# Request/Response schemas
class ConnectionTestRequest(BaseModel):
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    password: str
    db_schema: Optional[str] = None
    extra_params: Optional[str] = None


class DatasourceCreateRequest(BaseModel):
    name: str
    host: str
    port: int = 5432
    database_name: str
    username: str
    password: str
    db_type: str = "postgresql"


class DatasourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    db_type: Optional[str] = None


class DatasourceResponse(BaseModel):
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


class ColumnSchema(BaseModel):
    column_name: str
    data_type: str
    column_comment: Optional[str] = None
    is_primary_key: bool = False
    is_nullable: bool = True
    column_id: int


class TableSchemaRequest(BaseModel):
    datasource_id: int
    table_name: str
    table_comment: Optional[str] = None
    columns: List[ColumnSchema]


class TableSchemaResponse(BaseModel):
    id: int
    datasource_id: int
    table_name: str
    table_comment: Optional[str] = None
    columns: List[ColumnSchema]
    created_at: str


class TableInfo(BaseModel):
    table_name: str
    table_comment: str = ""


class ColumnInfo(BaseModel):
    column_name: str
    data_type: str
    column_comment: str = ""
    is_primary_key: bool = False
    is_nullable: bool = True


class SyncTablesRequest(BaseModel):
    table_names: List[str]


# Endpoints
@router.post("/datasources/test-connection")
def test_connection(request: ConnectionTestRequest):
    """测试数据库连接"""
    service = get_schema_service()
    success, message = service.test_connection(
        db_type=request.db_type,
        host=request.host,
        port=request.port,
        database=request.database_name,
        username=request.username,
        password=request.password,
        db_schema=request.db_schema,
        extra_params=request.extra_params,
    )
    return {"success": success, "message": message}


@router.post("/datasources", response_model=DatasourceResponse)
def create_datasource(
    request: DatasourceCreateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """创建数据源"""
    import traceback
    try:
        result = get_schema_service().create_datasource(
            db=db,
            user_id=user_id,
            name=request.name,
            host=request.host,
            port=request.port,
            database_name=request.database_name,
            username=request.username,
            password=request.password,
            db_type=request.db_type,
        )
        return DatasourceResponse(**result)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"create_datasource failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"创建数据源失败: {str(e)}"
        )


@router.get("/datasources", response_model=List[DatasourceResponse])
def list_datasources(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出用户的所有数据源"""
    results = get_schema_service().list_datasources(db=db, user_id=user_id)
    return [DatasourceResponse(**r) for r in results]


@router.put("/datasources/{datasource_id}", response_model=dict)
def update_datasource(
    datasource_id: int,
    request: DatasourceUpdateRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """更新数据源"""
    try:
        result = get_schema_service().update_datasource(
            db=db,
            datasource_id=datasource_id,
            user_id=user_id,
            name=request.name,
            host=request.host,
            port=request.port,
            database_name=request.database_name,
            username=request.username,
            password=request.password,
            db_type=request.db_type,
        )
        return {"message": "数据源更新成功"}
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"更新数据源失败: {str(e)}")


@router.delete("/datasources/{datasource_id}")
def delete_datasource(
    datasource_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除数据源"""
    try:
        get_schema_service().delete_datasource(db=db, datasource_id=datasource_id, user_id=user_id)
        return {"success": True}
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/tables", response_model=TableSchemaResponse)
def create_table_schema(
    request: TableSchemaRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """创建表结构"""
    try:
        columns = [c.model_dump() for c in request.columns]
        result = get_schema_service().create_table_schema(
            db=db,
            user_id=user_id,
            datasource_id=request.datasource_id,
            table_name=request.table_name,
            table_comment=request.table_comment,
            columns=columns,
        )
        return TableSchemaResponse(**result)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/tables", response_model=List[TableSchemaResponse])
def list_tables(
    datasource_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """列出数据源的所有表"""
    try:
        results = get_schema_service().list_tables(
            db=db, user_id=user_id, datasource_id=datasource_id
        )
        return results
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/tables/{table_id}")
def delete_table_schema(
    table_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """删除表结构"""
    try:
        get_schema_service().delete_table_schema(db=db, user_id=user_id, table_id=table_id)
        return {"success": True}
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权限")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/datasources/{datasource_id}/tables", response_model=List[TableInfo])
def get_remote_tables(
    datasource_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """从远程数据库获取表列表"""
    try:
        results = get_schema_service().get_remote_tables(
            db=db, user_id=user_id, datasource_id=datasource_id
        )
        return [TableInfo(**r) for r in results]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/datasources/{datasource_id}/tables/{table_name}/columns", response_model=List[ColumnInfo])
def get_remote_columns(
    datasource_id: int,
    table_name: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """从远程数据库获取列信息"""
    try:
        results = get_schema_service().get_remote_columns(
            db=db, user_id=user_id, datasource_id=datasource_id, table_name=table_name
        )
        return [ColumnInfo(**r) for r in results]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/datasources/{datasource_id}/sync", response_model=List[TableSchemaResponse])
def sync_tables(
    datasource_id: int,
    request: SyncTablesRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """同步选定的表结构"""
    try:
        results = get_schema_service().sync_tables(
            db=db,
            user_id=user_id,
            datasource_id=datasource_id,
            table_names=request.table_names,
        )
        return results
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
