# MemoryForge AI

MemoryForge AI gives agents an operating memory: structured experience that can change the next action. The interactive demo shows an agent fail a deployment, persist the reason, retrieve it on the next run, switch strategies, and succeed.

## Live demo

- App: https://memoryforge-ai-demo.ljs2546.chatgpt.site
- Video: https://youtu.be/s_crK7qGYyc

## Demo flow

1. Select **Run task**.
2. Watch the default deployment strategy time out.
3. Confirm that the failure and recommended correction appear in long-term memory.
4. Select **Run again with memory**.
5. Watch the agent retrieve the past failure, choose an asynchronous deployment, verify service health, and store the successful outcome.

## Architecture

```text
AI Agent → AWS Runtime → CockroachDB Memory → Relevant Experience → Better Action
```

The production architecture is designed around:

- Amazon Bedrock for agent reasoning
- AWS Lambda for serverless execution
- CockroachDB for durable, distributed memory storage
- vector retrieval for relevant past experience
- structured decision and outcome records for auditability

## Hackathon

Built for the CockroachDB × AWS Hackathon.

## Prerequisites

- Python 3.12
- A CockroachDB Cloud cluster with vector indexes enabled
- An AWS account with Amazon Bedrock model access and permission to deploy Lambda
- AWS CLI and AWS SAM CLI for deployment

## Install

```bash
git clone https://github.com/lsh2546/MemoryForge-AI.git
cd MemoryForge-AI
python -m venv .venv
```

Activate the virtual environment, then install dependencies:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Environment variables

Copy `.env.example` to `.env` for local work. Never commit the populated file.

| Variable | Required | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | Yes | CockroachDB PostgreSQL connection string with `sslmode=verify-full&sslrootcert=system` |
| `AWS_REGION` | Yes | Region used by the Bedrock Runtime client and Lambda |
| `EMBEDDING_MODEL_ID` | Yes | Bedrock embedding model; defaults to Titan Text Embeddings v2 |
| `MEMORYFORGE_AGENT_ID` | Local demo only | Stable agent identity used by the two-run example |

The production embedding contract is explicitly 1024 dimensions and matches
`agent_memories.embedding VECTOR(1024)`.

## Create the CockroachDB schema

Create a `memoryforge` database or choose an existing database, then apply the schema:

```bash
cockroach sql --url "$DATABASE_URL" --file schema.sql
```

The schema stores structured failures, successes, decisions, workflow state, and
1024-dimensional embeddings. `memories_embedding_idx` is a CockroachDB vector
index used by cosine-distance recall. The Lambda database user needs only
`SELECT` and `INSERT` on `agent_memories`.

## Run the decision loop locally

Export the variables from `.env`, ensure your AWS identity can call the configured
Bedrock model, and invoke the Lambda handler twice with the same task and agent ID:

```bash
python - <<'PY'
import json
from src.lambda_handler import handler

event = {
    "agent_id": "demo-agent",
    "task": "Deploy checkout-service v2.4 and verify production health",
}

print("RUN 1", json.loads(handler(event, None)["body"]))
print("RUN 2", json.loads(handler(event, None)["body"]))
PY
```

Expected causal chain:

1. Run 1 finds no relevant failure, uses `synchronous_deployment`, fails, and
   returns a new `written_memory_id`.
2. Run 2 recalls that ID, places it in `plan.adapted_from_memory`, changes the
   strategy to `async_job_with_health_check`, succeeds, and writes the outcome.

## Deploy to AWS Lambda

The included `template.yaml` gives the function Bedrock invoke permission, keeps
the CockroachDB URL server-side, and limits reserved concurrency.

```bash
sam build
sam deploy --guided
```

During guided deployment:

- choose the same AWS region in which Bedrock model access is available;
- provide `DatabaseUrl` from CockroachDB Cloud (the parameter is `NoEcho`);
- keep the default Titan embedding model unless another 1024-dimensional model
  is deliberately configured in both code and schema.

Invoke the deployed function twice with the same payload:

```bash
aws lambda invoke \
  --function-name memoryforge-ai-agent \
  --payload '{"agent_id":"demo-agent","task":"Deploy checkout-service v2.4 and verify production health"}' \
  --cli-binary-format raw-in-base64-out run-1.json

aws lambda invoke \
  --function-name memoryforge-ai-agent \
  --payload '{"agent_id":"demo-agent","task":"Deploy checkout-service v2.4 and verify production health"}' \
  --cli-binary-format raw-in-base64-out run-2.json
```

Compare `run-1.json` and `run-2.json`. The second response must contain the first
run's memory ID in both `recalled_memory_ids` and `plan.adapted_from_memory`, plus
`result.status: success`. This is the proof that CockroachDB recall changed the
next action rather than merely displaying history.

## Security notes

- Keep `DATABASE_URL` only in Lambda environment configuration or a secret store.
- Do not expose database credentials, Bedrock responses, or stack traces to a browser.
- Use a least-privilege CockroachDB user and a reserved concurrency limit.
- Parameterized SQL is used for every memory value; arbitrary SQL is not accepted.
