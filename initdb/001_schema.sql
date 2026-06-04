-- Schema definition for Dark Content Radar

CREATE TABLE IF NOT EXISTS content_items (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'video',
    title TEXT NOT NULL,
    description TEXT,
    url TEXT NOT NULL,
    channel_title TEXT,
    published_at TIMESTAMPTZ,
    collected_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    views BIGINT DEFAULT 0,
    likes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    views_per_day REAL DEFAULT 0,
    score REAL DEFAULT 0,
    topic_seed TEXT,
    discovery_query TEXT,
    language TEXT,
    country_code TEXT,
    status TEXT DEFAULT 'new',
    notes TEXT,
    raw_json JSONB,
    reviewed_at TIMESTAMPTZ,
    selected_at TIMESTAMPTZ,
    rejected_reason TEXT,
    production_notes TEXT,
    CONSTRAINT unique_source_external_id UNIQUE(source, external_id)
);

-- Indexes for performance & quick queries
CREATE INDEX IF NOT EXISTS idx_content_items_score_desc ON content_items (score DESC);
CREATE INDEX IF NOT EXISTS idx_content_items_published_at_desc ON content_items (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_items_status ON content_items (status);
CREATE INDEX IF NOT EXISTS idx_content_items_source_external_id ON content_items (source, external_id);
CREATE INDEX IF NOT EXISTS idx_content_items_content_type ON content_items (content_type);
CREATE INDEX IF NOT EXISTS idx_content_items_topic_seed ON content_items (topic_seed);

-- Optional table to track collection events and status changes
CREATE TABLE IF NOT EXISTS content_item_events (
    id BIGSERIAL PRIMARY KEY,
    content_item_id BIGINT REFERENCES content_items(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    data JSONB
);

-- Index for the foreign key in content_item_events
CREATE INDEX IF NOT EXISTS idx_content_item_events_content_item_id ON content_item_events(content_item_id);
