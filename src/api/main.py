from fastapi import FastAPI
from src.api.routes import health, content_items, ingest

app = FastAPI(
    title="Dark Content Radar API",
    description="Backend API to manage curated content items from n8n & other collectors",
    version="1.0.0"
)

# Register route paths
app.include_router(health.router, tags=["Health"])
app.include_router(content_items.router, prefix="/content-items", tags=["Content Items"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
