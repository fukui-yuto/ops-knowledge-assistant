-- ============================================================
-- Log Diagnosis Assistant - Metadata DB Schema
-- PostgreSQL 14+
-- ============================================================

-- 拡張: UUID生成用
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- documents: 文書マスタ
-- 全ての原本ファイル / チケット / 構成情報の親レコード
-- ============================================================
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type     TEXT NOT NULL,           -- 'procedure' | 'ticket' | 'config' | 'log'
    source_system   TEXT,                    -- 'confluence' | 'jira' | 'k8s' 等
    external_id     TEXT,                    -- 元システムでのID (例: JIRA-123)
    title           TEXT NOT NULL,
    file_path       TEXT NOT NULL,           -- 原本ストレージのパス
    content_hash    TEXT NOT NULL,           -- SHA256: 差分検知用
    metadata        JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (source_system, external_id)
);

CREATE INDEX IF NOT EXISTS idx_documents_source_type ON documents(source_type);
CREATE INDEX IF NOT EXISTS idx_documents_source_system ON documents(source_system);
CREATE INDEX IF NOT EXISTS idx_documents_metadata ON documents USING GIN (metadata);

-- ============================================================
-- chunks: チャンク管理
-- ベクトルDBとは independent に原本チャンクを保持(再構築可能性のため)
-- ============================================================
CREATE TABLE IF NOT EXISTS chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL,            -- 文書内での順序
    content         TEXT NOT NULL,
    vector_id       TEXT,                    -- ChromaDBのID(同じUUIDを使う)
    token_count     INT,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);

-- ============================================================
-- tickets: 問い合わせチケット固有情報
-- documents を 1:1 で拡張する形
-- ============================================================
CREATE TABLE IF NOT EXISTS tickets (
    document_id     UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    status          TEXT,                    -- 'open' | 'resolved' | 'closed'
    severity        TEXT,                    -- 'critical' | 'high' | 'medium' | 'low'
    affected_system TEXT,
    resolved_at     TIMESTAMP,
    resolution      TEXT                     -- 解決方法本文(回答精度の鍵)
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_affected_system ON tickets(affected_system);

-- ============================================================
-- ingestion_log: 取り込みジョブ履歴
-- ============================================================
CREATE TABLE IF NOT EXISTS ingestion_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID REFERENCES documents(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,           -- 'create' | 'update' | 'skip' | 'error'
    message         TEXT,
    executed_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ingestion_log_executed_at ON ingestion_log(executed_at DESC);

-- ============================================================
-- generation_log: 手順書生成の実行履歴
-- ============================================================
CREATE TABLE IF NOT EXISTS generation_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           TEXT NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    template_used   TEXT NOT NULL,
    reference_docs  JSONB NOT NULL DEFAULT '[]'::jsonb,
    model           TEXT NOT NULL,
    content         TEXT NOT NULL DEFAULT '',
    output_path     TEXT,
    has_todos       BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_generation_log_created_at ON generation_log(created_at DESC);
