-- Migration 0007: Add video_project_items (unified workshop elements)
-- and item_id link column in board nodes.
-- Safe to run multiple times (IF NOT EXISTS / IF column not exists guards).

CREATE TABLE IF NOT EXISTS video_project_items (
    id               BIGSERIAL PRIMARY KEY,
    video_project_id BIGINT NOT NULL REFERENCES video_projects(id) ON DELETE CASCADE,
    item_type        TEXT NOT NULL DEFAULT 'note',
    title            TEXT NULL,
    body             TEXT NULL,
    url              TEXT NULL,
    source_kind      TEXT NULL DEFAULT 'manual',
    source_id        BIGINT NULL,
    metadata_json    JSONB NULL,
    status           TEXT NOT NULL DEFAULT 'open',
    pinned           BOOLEAN NOT NULL DEFAULT false,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vpi_project_id ON video_project_items(video_project_id);
CREATE INDEX IF NOT EXISTS idx_vpi_item_type  ON video_project_items(item_type);
CREATE INDEX IF NOT EXISTS idx_vpi_status     ON video_project_items(status);
CREATE INDEX IF NOT EXISTS idx_vpi_pinned     ON video_project_items(pinned);
CREATE INDEX IF NOT EXISTS idx_vpi_updated_at ON video_project_items(updated_at DESC);

-- Add item_id to board nodes (links a node to a library item)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='video_project_board_nodes' AND column_name='item_id'
    ) THEN
        ALTER TABLE video_project_board_nodes
            ADD COLUMN item_id BIGINT NULL REFERENCES video_project_items(id) ON DELETE SET NULL;
    END IF;
END;
$$;
