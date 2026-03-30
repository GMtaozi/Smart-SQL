"""pgvector initialization"""

from sqlalchemy import text
from server.db.database import engine


def init_vector_extension():
    """Initialize pgvector extension and create embedding table."""
    with engine.connect() as conn:
        # Enable pgvector extension
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

        # Create schema_table_embeddings table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_table_embeddings (
                id SERIAL PRIMARY KEY,
                table_id INTEGER NOT NULL,
                embedding VECTOR(1536),
                metadata TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (table_id)
            )
        """))
        conn.commit()

        # Create IVFFlat index for similarity search
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_embedding_similarity
                ON schema_table_embeddings
                USING ivfflat (embedding vector_cosine_ops)
            """))
            conn.commit()
        except Exception:
            # Index might already exist or pgvector version doesn't support it
            pass
