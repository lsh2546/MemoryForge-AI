import { spawn } from "node:child_process";
import path from "node:path";
import readline from "node:readline";

const clusterId = "a43aabf0-4598-4b71-95f1-26d28ff1be5a";
const memoryId = process.argv[2];

if (!/^[0-9a-f-]{36}$/i.test(memoryId ?? "")) {
  throw new Error("Usage: node managed_mcp_query.mjs <memory-uuid>");
}

const child = spawn(
  process.execPath,
  [
    path.resolve(path.dirname(process.execPath), "..", "node_modules", "pnpm", "bin", "pnpm.mjs"),
    "dlx",
    "mcp-remote",
    "https://cockroachlabs.cloud/mcp",
    "--header",
    `mcp-cluster-id: ${clusterId}`,
  ],
  { stdio: ["pipe", "pipe", "inherit"] },
);

const lines = readline.createInterface({ input: child.stdout });
const pending = new Map();
let requestId = 0;

lines.on("line", (line) => {
  if (!line.trim()) return;
  const message = JSON.parse(line);
  const waiter = pending.get(message.id);
  if (!waiter) return;
  pending.delete(message.id);
  if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
  else waiter.resolve(message.result);
});

function send(payload) {
  child.stdin.write(`${JSON.stringify(payload)}\n`);
}

function request(method, params = {}) {
  const id = ++requestId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    send({ jsonrpc: "2.0", id, method, params });
  });
}

await request("initialize", {
  protocolVersion: "2025-03-26",
  capabilities: {},
  clientInfo: { name: "memoryforge-evidence", version: "1.0.0" },
});
send({ jsonrpc: "2.0", method: "notifications/initialized", params: {} });

const listed = await request("tools/list");
if (!listed.tools.some((tool) => tool.name === "select_query")) {
  throw new Error("Managed MCP select_query tool not available");
}

const query = `
SELECT id, agent_id, memory_type, summary, decision, outcome, confidence
FROM agent_memories
WHERE id = '${memoryId}'::UUID;
`.trim();

const candidates = [
  { database: "defaultdb", query },
  { database_name: "defaultdb", query },
  { database: "defaultdb", sql: query },
];

let result;
for (const args of candidates) {
  result = await request("tools/call", { name: "select_query", arguments: args });
  if (!result?.isError) break;
}

if (!result || result.isError) throw new Error("Managed MCP select_query failed");
console.log(JSON.stringify({ tool: "select_query", memoryId, result }, null, 2));
child.stdin.end();
child.kill();
