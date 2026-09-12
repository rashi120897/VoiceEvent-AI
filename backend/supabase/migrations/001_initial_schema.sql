-- =============================================
-- Voice Assistant SaaS - Initial Database Schema
-- =============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ----------------------------
-- Tenants table
-- ----------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    settings JSONB NOT NULL DEFAULT '{
        "system_prompt": "You are a helpful voice assistant. Answer questions based on the provided knowledge base context. Be concise and conversational.",
        "tts_voice_id": "alloy",
        "assistant_name": "Assistant",
        "max_concurrent_calls": 5
    }'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------
-- API Keys table
-- ----------------------------
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    key_hash VARCHAR(128) NOT NULL UNIQUE,
    key_prefix VARCHAR(12) NOT NULL,  -- first 8 chars for display (e.g., "va_sk_ab12...")
    name VARCHAR(255) NOT NULL DEFAULT 'Default API Key',
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_tenant_id ON api_keys(tenant_id);

-- ----------------------------
-- Documents table
-- ----------------------------
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename VARCHAR(512) NOT NULL,
    file_type VARCHAR(50) NOT NULL,  -- pdf, docx, txt
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'processing',  -- processing, ready, error
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_tenant_id ON documents(tenant_id);
CREATE INDEX idx_documents_status ON documents(status);

-- ----------------------------
-- Call Logs table
-- ----------------------------
CREATE TABLE IF NOT EXISTS call_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    twilio_call_sid VARCHAR(64) NOT NULL UNIQUE,
    caller_number VARCHAR(20),
    direction VARCHAR(10) NOT NULL DEFAULT 'inbound',  -- inbound, outbound
    duration_seconds INTEGER,
    status VARCHAR(50) NOT NULL DEFAULT 'in_progress',  -- in_progress, completed, failed
    transcript JSONB DEFAULT '[]'::jsonb,  -- Array of {role, text, timestamp}
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_call_logs_tenant_id ON call_logs(tenant_id);
CREATE INDEX idx_call_logs_twilio_call_sid ON call_logs(twilio_call_sid);
CREATE INDEX idx_call_logs_started_at ON call_logs(started_at DESC);

-- ----------------------------
-- Updated_at trigger function
-- ----------------------------
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to tenants
CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Apply trigger to documents
CREATE TRIGGER update_documents_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------
-- Row Level Security (RLS)
-- ----------------------------
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;

-- Service role can access everything (used by our backend)
CREATE POLICY "Service role full access on tenants" ON tenants
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on api_keys" ON api_keys
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on documents" ON documents
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Service role full access on call_logs" ON call_logs
    FOR ALL USING (true) WITH CHECK (true);
