"""FastAPI application entry point"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.api import auth, query, schema, ai_model, terminology, data_training
from server.db.database import init_db
from server.db.vector import init_vector_extension
from server.config import DEBUG

# Create FastAPI app
app = FastAPI(
    title="SQLbot API",
    description="Natural Language to SQL Query System",
    version="1.0.0",
    debug=DEBUG,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    init_db()
    try:
        init_vector_extension()
    except Exception as e:
        print(f"Warning: Vector extension init failed: {e}")


# Include routers
app.include_router(auth.router)
app.include_router(query.router)
app.include_router(schema.router)
app.include_router(ai_model.router)
app.include_router(terminology.router)
app.include_router(data_training.router)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "sqlbot"}


@app.get("/health")
def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn
    from server.config import HOST, PORT
    uvicorn.run(app, host=HOST, port=PORT)
