import os
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# Read Postgres connection string from environmental variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://radar:radar@localhost:5432/dark_content_radar"
)

def get_postgres_engine():
    """
    Returns a SQLAlchemy engine connected to PostgreSQL.
    """
    return create_engine(DATABASE_URL)

def init_postgres_schema_if_needed():
    """
    Reads initdb/001_schema.sql and runs it on the database if the main table does not exist.
    This serves as an automatic schema initializer if docker volume is new or connection is first established.
    """
    engine = get_postgres_engine()
    
    check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name = 'content_items'
        );
    """
    
    try:
        with engine.connect() as conn:
            exists = conn.execute(text(check_query)).scalar()
            if not exists:
                # Resolve schema file path relative to workspace
                schema_path = Path(__file__).resolve().parent.parent / "initdb" / "001_schema.sql"
                if schema_path.exists():
                    sql_content = schema_path.read_text(encoding="utf-8")
                    with conn.begin():
                        # Run the schema creation queries
                        conn.execute(text(sql_content))
                    print("Postgres schema initialized successfully via Python.")
                else:
                    print("Warning: initdb/001_schema.sql not found to initialize schema.")
            else:
                print("Postgres database schema is already present. Skipping initialization.")
    except Exception as e:
        print(f"Error checking/initializing Postgres schema: {e}")

def fetch_content_items(
    limit=500, 
    status=None, 
    content_type=None, 
    source=None, 
    topic_seed=None, 
    min_score=None, 
    min_views=None, 
    min_published_at=None, 
    max_published_at=None
):
    """
    Queries content_items table and returns a list of dictionaries.
    Filters are applied dynamically if provided.
    """
    engine = get_postgres_engine()
    query = """
        SELECT 
            id, source, external_id, content_type, title, description, url, 
            channel_title, published_at, collected_at, last_seen_at, 
            views, likes, comments, views_per_day, score, topic_seed, 
            discovery_query, language, country_code, status, notes, raw_json,
            reviewed_at, selected_at, rejected_reason, production_notes
        FROM content_items
        WHERE 1=1
    """
    params = {}
    
    if status is not None and status != "Todos":
        query += " AND status = :status"
        params["status"] = status
    if content_type is not None and content_type != "Todos":
        query += " AND content_type = :content_type"
        params["content_type"] = content_type
    if source is not None and source != "Todos":
        query += " AND source = :source"
        params["source"] = source
    if topic_seed is not None and topic_seed != "Todos":
        query += " AND topic_seed = :topic_seed"
        params["topic_seed"] = topic_seed
    if min_score is not None:
        query += " AND score >= :min_score"
        params["min_score"] = float(min_score)
    if min_views is not None:
        query += " AND views >= :min_views"
        params["min_views"] = int(min_views)
    if min_published_at is not None:
        query += " AND published_at >= :min_published_at"
        params["min_published_at"] = min_published_at
    if max_published_at is not None:
        query += " AND published_at <= :max_published_at"
        params["max_published_at"] = max_published_at

    query += " ORDER BY score DESC, published_at DESC LIMIT :limit"
    params["limit"] = limit

    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        items = [dict(row._mapping) for row in result]
            
    return items

def fetch_content_summary():
    """
    Retrieves aggregated summary statistics for content items.
    """
    engine = get_postgres_engine()
    stats = {
        "total_items": 0,
        "new_items": 0,
        "items_by_source": {},
        "max_score": 0.0,
        "max_views": 0
    }
    
    try:
        with engine.connect() as conn:
            # 1. Total items
            stats["total_items"] = conn.execute(text("SELECT COUNT(*) FROM content_items")).scalar() or 0
            
            # 2. New items (status = 'new')
            stats["new_items"] = conn.execute(text("SELECT COUNT(*) FROM content_items WHERE status = 'new'")).scalar() or 0
            
            # 3. Max score and views
            max_res = conn.execute(text("SELECT COALESCE(MAX(score), 0), COALESCE(MAX(views), 0) FROM content_items")).fetchone()
            if max_res:
                stats["max_score"] = float(max_res[0])
                stats["max_views"] = int(max_res[1])
                
            # 4. Items by source
            source_res = conn.execute(text("SELECT source, COUNT(*) FROM content_items GROUP BY source")).fetchall()
            stats["items_by_source"] = {row[0]: row[1] for row in source_res}
    except Exception as e:
        print(f"Error fetching PostgreSQL summary: {e}")
        
    return stats

def update_content_status(item_id, status):
    """
    Updates status of a content item and sets associated status transition timestamps.
    """
    engine = get_postgres_engine()
    
    query = "UPDATE content_items SET status = :status, last_seen_at = NOW()"
    params = {"status": status, "item_id": item_id}
    
    if status == "reviewed":
        query += ", reviewed_at = NOW()"
    elif status == "selected":
        query += ", selected_at = NOW()"
        
    query += " WHERE id = :item_id"
    
    with engine.begin() as conn:
        conn.execute(text(query), params)
