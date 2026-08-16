"""AWS Lambda entry point for the MemoryForge decision loop."""

import json
import os
import boto3
from memory_engine import Memory, MemoryEngine

bedrock = boto3.client("bedrock-runtime")
engine = MemoryEngine()


def embed(text: str) -> list[float]:
    response = bedrock.invoke_model(
        modelId=os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0"),
        body=json.dumps({"inputText": text, "dimensions": 1024, "normalize": True}),
    )
    return json.loads(response["body"].read())["embedding"]


def handler(event, _context):
    agent_id = event.get("agent_id", "demo-agent")
    task = event["task"]
    task_embedding = embed(task)
    recalled = engine.recall(agent_id, task_embedding)

    plan = engine.adapt_plan(
        {"strategy": "synchronous_deployment", "task": task}, recalled
    )

    # The executor can be replaced with a Step Functions or deployment tool call.
    if plan["strategy"] == "synchronous_deployment":
        result = {"status": "failed", "reason": "execution timed out"}
        written_memory_id = engine.remember(
            agent_id,
            Memory(
                memory_type="failure",
                summary="Synchronous deployment exceeded the execution limit.",
                decision="async_job_with_health_check",
                outcome="timeout",
                reasoning="Queue the deployment and verify health asynchronously next time.",
                confidence=0.96,
                task_context={"task": task},
            ),
            task_embedding,
        )
    else:
        result = {"status": "success", "strategy": plan["strategy"]}
        written_memory_id = engine.remember(
            agent_id,
            Memory(
                memory_type="success",
                summary="Asynchronous deployment and health check completed.",
                decision=plan["strategy"],
                outcome="healthy",
                reasoning="Strategy adapted from the previous failure.",
                confidence=0.98,
                task_context={"task": task},
            ),
            task_embedding,
        )

    return {
        "statusCode": 200,
        "body": json.dumps({
            "plan": plan,
            "result": result,
            "recalled_memory_ids": [str(memory["id"]) for memory in recalled],
            "written_memory_id": written_memory_id,
        }),
    }
