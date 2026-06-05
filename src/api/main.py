from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import health, content_items, ingest, search

app = FastAPI(
    title="Dark Content Radar API",
    description="Backend API to manage curated content items from n8n & other collectors",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route paths
app.include_router(health.router, tags=["Health"])
app.include_router(content_items.router, prefix="/content-items", tags=["Content Items"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
app.include_router(search.configs_router, prefix="/search-configs", tags=["Search Configurations"])
app.include_router(search.runs_router, prefix="/search-runs", tags=["Search Runs"])
