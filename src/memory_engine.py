"""CockroachDB-backed memory lifecycle for MemoryForge AI."""

from dataclasses import dataclass
from typing import Any
import os
import psycopg
from psycopg.rows import dict_row


@dataclass
class Memory:
    memory_type: str
    summary: str
    confidence: float
    task_context: dict[str, Any]
    decision: str | None = None
    outcome: str | None = None
    reasoning: str | None = None


class MemoryEngine:
    def __init__(self, database_url: str | None = None):
        self.database_url = database_url or os.environ["DATABASE_URL"]

    def remember(self, agent_id: str, memory: Memory, embedding: list[float]) -> str:
        query = """
            INSERT INTO agent_memories
              (agent_id, memory_type, task_context, summary, decision,
               outcome, reasoning, confidence, embedding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::VECTOR)
            RETURNING id
        """
        with psycopg.connect(self.database_url) as connection:
            return str(connection.execute(
                query,
                (
                    agent_id, memory.memory_type, memory.task_context,
                    memory.summary, memory.decision, memory.outcome,
                    memory.reasoning, memory.confidence, embedding,
                ),
            ).fetchone()[0])

    def recall(self, agent_id: str, embedding: list[float], limit: int = 5) -> list[dict]:
        query = """
            SELECT id, memory_type, summary, decision, outcome, reasoning,
                   confidence, 1 - (embedding <=> %s::VECTOR) AS relevance
            FROM agent_memories
            WHERE agent_id = %s
            ORDER BY embedding <=> %s::VECTOR
            LIMIT %s
        """
        with psycopg.connect(self.database_url, row_factory=dict_row) as connection:
            return list(connection.execute(query, (embedding, agent_id, embedding, limit)))

    @staticmethod
    def adapt_plan(default_plan: dict, memories: list[dict]) -> dict:
        """Change the next action only when a relevant, confident memory exists."""
        useful = [m for m in memories if m["relevance"] >= 0.80 and m["confidence"] >= 0.70]
        if not useful:
            return default_plan

        strongest = max(useful, key=lambda m: m["relevance"] * float(m["confidence"]))
        if strongest["memory_type"] == "failure" and strongest.get("decision"):
            return {
                **default_plan,
                "strategy": strongest["decision"],
                "adapted_from_memory": str(strongest["id"]),
                "reason": strongest.get("reasoning") or strongest["summary"],
            }
        return default_plan
