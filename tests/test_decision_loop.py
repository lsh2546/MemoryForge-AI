import json
import os
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:26257/test")


class FakeBody:
    def read(self):
        return json.dumps({"embedding": [0.0] * 1024}).encode()


class FakeBedrock:
    def invoke_model(self, **_kwargs):
        return {"body": FakeBody()}


class FakeBoto3(types.ModuleType):
    def client(self, _name):
        return FakeBedrock()


sys.modules.setdefault("boto3", FakeBoto3("boto3"))
sys.modules.setdefault("psycopg", types.ModuleType("psycopg"))
rows = types.ModuleType("psycopg.rows")
rows.dict_row = object()
sys.modules.setdefault("psycopg.rows", rows)
json_types = types.ModuleType("psycopg.types.json")
json_types.Jsonb = lambda value: value
sys.modules.setdefault("psycopg.types", types.ModuleType("psycopg.types"))
sys.modules.setdefault("psycopg.types.json", json_types)

from src import lambda_handler  # noqa: E402


class FakeEngine:
    def __init__(self):
        self.memories = []
        self.counter = 0

    def recall(self, _agent_id, _embedding):
        return list(self.memories)

    def remember(self, _agent_id, memory, _embedding):
        self.counter += 1
        memory_id = f"memory-{self.counter}"
        self.memories.append({
            "id": memory_id,
            "memory_type": memory.memory_type,
            "summary": memory.summary,
            "decision": memory.decision,
            "outcome": memory.outcome,
            "reasoning": memory.reasoning,
            "confidence": memory.confidence,
            "relevance": 1.0,
        })
        return memory_id

    adapt_plan = staticmethod(lambda_handler.MemoryEngine.adapt_plan)


class DecisionLoopTest(unittest.TestCase):
    def test_recalled_failure_changes_second_action(self):
        fake = FakeEngine()
        original = lambda_handler.engine
        lambda_handler.engine = fake
        event = {"agent_id": "test-agent", "task": "deploy checkout and verify health"}
        try:
            first = json.loads(lambda_handler.handler(event, None)["body"])
            second = json.loads(lambda_handler.handler(event, None)["body"])
        finally:
            lambda_handler.engine = original

        self.assertEqual(first["result"]["status"], "failed")
        self.assertEqual(first["written_memory_id"], "memory-1")
        self.assertEqual(second["plan"]["adapted_from_memory"], "memory-1")
        self.assertEqual(second["plan"]["strategy"], "async_job_with_health_check")
        self.assertEqual(second["result"]["status"], "success")


if __name__ == "__main__":
    unittest.main()
