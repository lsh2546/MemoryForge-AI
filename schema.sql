CREATE TABLE IF NOT EXISTS agent_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id STRING NOT NULL,
  memory_type STRING NOT NULL CHECK (memory_type IN ('preference','failure','success','decision','workflow')),
  task_context JSONB NOT NULL,
  summary STRING NOT NULL,
  decision STRING,
  outcome STRING,
  reasoning STRING,
  embedding VECTOR(1536),
  confidence DECIMAL NOT NULL DEFAULT 0.5,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS memories_agent_time_idx
  ON agent_memories (agent_id, created_at DESC);

CREATE VECTOR INDEX IF NOT EXISTS memories_embedding_idx
  ON agent_memories (embedding vector_cosine_ops);
