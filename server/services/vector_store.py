"""
Vector Store Service - pgvector RAG for Schema Retrieval
"""

from typing import Optional
from langchain_openai import OpenAIEmbeddings
from sqlalchemy import text
from sqlalchemy.orm import Session

from server.db.database import get_db_session


# Default embedding model
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
# Default dimension for embedding model
DEFAULT_EMBEDDING_DIM = 1536
# Default top-k results
DEFAULT_TOP_K = 5


class VectorStore:
    """
    pgvector-based vector store for schema retrieval.

    Uses OpenAI embeddings to vectorize schema metadata (table names, column names, descriptions)
    and stores them in pgvector for similarity search.
    """

    def __init__(
        self,
        embedding_api_key: Optional[str] = None,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL,
        embedding_dim: int = DEFAULT_EMBEDDING_DIM,
        request_timeout: int = 10,
    ):
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        self.embeddings = OpenAIEmbeddings(
            model=embedding_model,
            api_key=embedding_api_key,
            timeout=request_timeout,
        )

    def _text_to_embedding(self, text: str) -> list[float]:
        """Convert text to embedding vector."""
        return self.embeddings.embed_query(text)

    def _embedding_to_sql_vector(self, embedding: list[float]) -> str:
        """Convert Python list to PostgreSQL vector string format."""
        # pgvector expects format: '[0.1, 0.2, ...]'
        return f"[{','.join(str(x) for x in embedding)}]"

    def upsert_table_embedding(
        self,
        db: Session,
        table_id: int,
        table_name: str,
        table_comment: str,
        column_names: list[str],
        column_comments: list[str],
    ) -> bool:
        """
        Upsert embedding for a table and its columns.

        Args:
            db: Database session
            table_id: Table ID in schema_tables
            table_name: Name of the table
            table_comment: Table description/comment
            column_names: List of column names
            column_comments: List of column descriptions

        Returns:
            True if successful, False otherwise
        """
        try:
            # Build composite text for embedding
            parts = [f"表名: {table_name}"]
            if table_comment:
                parts.append(f"表描述: {table_comment}")
            for col_name, col_comment in zip(column_names, column_comments):
                parts.append(f"列: {col_name}")
                if col_comment:
                    parts.append(f"列描述: {col_comment}")

            composite_text = " | ".join(parts)
            embedding = self._text_to_embedding(composite_text)
            vector_str = self._embedding_to_sql_vector(embedding)

            # Upsert into schema_table_embeddings
            query = text("""
                INSERT INTO schema_table_embeddings
                    (table_id, embedding, metadata, updated_at)
                VALUES
                    (:table_id, :embedding::vector, :metadata, NOW())
                ON CONFLICT (table_id)
                DO UPDATE SET
                    embedding = :embedding::vector,
                    metadata = :metadata,
                    updated_at = NOW()
            """)
            db.execute(query, {
                "table_id": table_id,
                "embedding": vector_str,
                "metadata": composite_text,
            })
            db.commit()
            return True

        except Exception as e:
            db.rollback()
            raise e

    def search_similar_tables(
        self,
        db: Session,
        query_text: str,
        datasource_id: int,
        top_k: int = DEFAULT_TOP_K,
    ) -> list[dict]:
        """
        Search for most similar tables to a natural language query.

        Args:
            db: Database session
            query_text: Natural language query from user
            datasource_id: Target datasource ID to search within
            top_k: Number of results to return

        Returns:
            List of dicts with table_id, table_name, similarity score, and metadata
        """
        try:
            # Generate embedding for query
            query_embedding = self._text_to_embedding(query_text)
            query_vector = self._embedding_to_sql_vector(query_embedding)

            # Search in pgvector
            query = text("""
                SELECT
                    ste.table_id,
                    st.table_name,
                    st.table_comment,
                    1 - (ste.embedding <=> :query_vector::vector) AS similarity,
                    ste.metadata
                FROM schema_table_embeddings ste
                JOIN schema_tables st ON st.id = ste.table_id
                WHERE st.datasource_id = :datasource_id
                ORDER BY ste.embedding <=> :query_vector::vector
                LIMIT :top_k
            """)
            result = db.execute(query, {
                "query_vector": query_vector,
                "datasource_id": datasource_id,
                "top_k": top_k,
            })

            rows = result.fetchall()
            return [
                {
                    "table_id": row[0],
                    "table_name": row[1],
                    "table_comment": row[2],
                    "similarity": float(row[3]),
                    "metadata": row[4],
                }
                for row in rows
            ]

        except Exception as e:
            raise e

    def delete_table_embedding(self, db: Session, table_id: int) -> bool:
        """
        Delete embedding for a table.

        Args:
            db: Database session
            table_id: Table ID to delete embedding for

        Returns:
            True if successful
        """
        try:
            query = text("DELETE FROM schema_table_embeddings WHERE table_id = :table_id")
            db.execute(query, {"table_id": table_id})
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise e

    def init_vector_extension(self, db: Session) -> bool:
        """
        Initialize pgvector extension and create embeddings table if not exists.

        Args:
            db: Database session

        Returns:
            True if successful
        """
        try:
            # Enable pgvector extension
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

            # Create embeddings table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_table_embeddings (
                    id SERIAL PRIMARY KEY,
                    table_id INTEGER NOT NULL,
                    embedding VECTOR(:dim),
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE (table_id)
                )
            """))

            # Create index for vector similarity search
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_embedding_similarity
                ON schema_table_embeddings
                USING ivfflat (embedding vector_cosine_ops)
            """))

            db.commit()
            return True

        except Exception as e:
            db.rollback()
            raise e


# Singleton instance
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create vector store singleton."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
