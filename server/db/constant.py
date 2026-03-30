"""Database type constants"""

from enum import Enum


class DBType(str, Enum):
    """Supported database types"""
    MYSQL = "mysql"
    PG = "pg"                    # PostgreSQL
    ORACLE = "oracle"
    CK = "ck"                    # ClickHouse
    SQL_SERVER = "sqlServer"     # SQL Server
    DORIS = "doris"              # Apache Doris
    STARROCKS = "starrocks"      # StarRocks
    ES = "es"                    # Elasticsearch
    KINGBASE = "kingbase"        # Kingbase
    DM = "dm"                    # 达梦 DM
    REDSHIFT = "redshift"        # AWS Redshift
    EXCEL = "excel"              # Excel/CSV file

    @classmethod
    def values(cls):
        return [e.value for e in cls]

    @classmethod
    def has_value(cls, value: str) -> bool:
        return value in cls.values()


# Database type display names
DB_TYPE_NAMES = {
    DBType.MYSQL: "MySQL",
    DBType.PG: "PostgreSQL",
    DBType.ORACLE: "Oracle",
    DBType.CK: "ClickHouse",
    DBType.SQL_SERVER: "SQL Server",
    DBType.DORIS: "Apache Doris",
    DBType.STARROCKS: "StarRocks",
    DBType.ES: "Elasticsearch",
    DBType.KINGBASE: "Kingbase",
    DBType.DM: "达梦 DM",
    DBType.REDSHIFT: "AWS Redshift",
    DBType.EXCEL: "Excel/CSV",
}

# Databases that require schema parameter
DATABASES_WITH_SCHEMA = {
    DBType.SQL_SERVER,
    DBType.PG,
    DBType.ORACLE,
    DBType.DM,
    DBType.REDSHIFT,
    DBType.KINGBASE,
}

# Default ports for each database type
DEFAULT_PORTS = {
    DBType.MYSQL: 3306,
    DBType.PG: 5432,
    DBType.ORACLE: 1521,
    DBType.CK: 8123,
    DBType.SQL_SERVER: 1433,
    DBType.DORIS: 9030,
    DBType.STARROCKS: 9030,
    DBType.ES: 9200,
    DBType.KINGBASE: 54321,
    DBType.DM: 5236,
    DBType.REDSHIFT: 5439,
}
