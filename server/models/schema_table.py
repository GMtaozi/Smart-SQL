"""Schema Table model"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from server.db.base import Base


class SchemaTable(Base):
    """Database table metadata model.

    Stores table schema information for NL2SQL context.
    """

    __tablename__ = "schema_tables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    datasource_id = Column(Integer, ForeignKey("datasources.id"), nullable=False, index=True)
    table_name = Column(String(255), nullable=False)
    table_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint for datasource_id + table_name
    __table_args__ = (
        UniqueConstraint('datasource_id', 'table_name', name='uq_schema_tables_datasource_table'),
    )

    # Relationships
    columns = relationship("SchemaColumn", back_populates="table", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SchemaTable(id={self.id}, name='{self.table_name}')>"
