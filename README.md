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
