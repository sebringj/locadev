/**
 * Locadev Functions-style host (native multi-arch).
 *
 * Uses Azurite for queue I/O the same way Azure Functions storage bindings do.
 * For the full Microsoft Functions host, run Core Tools on the Docker *host*
 * with AzureWebJobsStorage from sandbox.env.example (see README).
 */
import express from "express";
import {
  QueueServiceClient,
  StorageSharedKeyCredential,
} from "@azure/storage-queue";

const PORT = Number(process.env.FUNCTIONS_PORT || process.env.PORT || 80);
const QUEUE = process.env.FUNCTIONS_QUEUE || "functions-work";
const CONN =
  process.env.AzureWebJobsStorage ||
  process.env.AZURE_STORAGE_CONNECTION_STRING ||
  "";

const app = express();
app.use(express.json());

const processed = [];
let queueClient = null;
let pollTimer = null;

function parseConn(conn) {
  const parts = Object.fromEntries(
    conn
      .split(";")
      .filter(Boolean)
      .map((p) => {
        const i = p.indexOf("=");
        return [p.slice(0, i), p.slice(i + 1)];
      })
  );
  return parts;
}

async function initQueue() {
  if (!CONN) {
    console.warn("AzureWebJobsStorage not set — queue bindings disabled");
    return;
  }
  const p = parseConn(CONN);
  const account = p.AccountName || "devstoreaccount1";
  const key = p.AccountKey;
  const queueEndpoint =
    p.QueueEndpoint || `http://127.0.0.1:10001/${account}`;
  // QueueServiceClient wants service URL without account path segment for some versions;
  // Azurite path-style: http://host:port/account
  const serviceUrl = queueEndpoint.replace(/\/$/, "");
  const cred = new StorageSharedKeyCredential(account, key);
  const qs = new QueueServiceClient(serviceUrl, cred);
  queueClient = qs.getQueueClient(QUEUE);
  try {
    await queueClient.create();
    console.log(`queue ready: ${QUEUE} @ ${serviceUrl}`);
  } catch (e) {
    // already exists
    console.log(`queue ${QUEUE}: ${e.message || e}`);
  }
}

async function enqueue(obj) {
  if (!queueClient) throw new Error("queue not configured");
  const text = Buffer.from(JSON.stringify(obj)).toString("base64");
  await queueClient.sendMessage(text);
}

async function pollOnce() {
  if (!queueClient) return;
  try {
    const res = await queueClient.receiveMessages({
      numberOfMessages: 5,
      visibilityTimeout: 30,
    });
    for (const m of res.receivedMessageItems || []) {
      let body = m.messageText;
      try {
        body = Buffer.from(m.messageText, "base64").toString("utf8");
      } catch {
        /* plain */
      }
      const entry = {
        at: new Date().toISOString(),
        body,
        id: m.messageId,
      };
      processed.push(entry);
      if (processed.length > 100) processed.shift();
      console.log(`[queueEcho] processed: ${body}`);
      await queueClient.deleteMessage(m.messageId, m.popReceipt);
    }
  } catch (e) {
    console.warn("queue poll:", e.message || e);
  }
}

app.get("/api/ping", (_req, res) => {
  res.json({
    status: "ok",
    service: "locadev-sample-azure-functions",
    host: "locadev-sample-azure-functions",
    storage: queueClient ? "azurite" : "none",
  });
});

app.get("/api/httpHello", async (req, res) => {
  const name = req.query.name || "locadev";
  const payload = {
    hello: name,
    at: new Date().toISOString(),
    via: "httpHello",
  };
  try {
    await enqueue(payload);
    res.json({
      ok: true,
      message: `Hello, ${name}`,
      enqueued: true,
      queue: QUEUE,
      runtime: "locadev-sample-azure-functions",
      storage: "azurite",
    });
  } catch (e) {
    res.status(502).json({
      ok: false,
      error: String(e.message || e),
      hint: "Is Azurite up? Check AzureWebJobsStorage / queue endpoint.",
    });
  }
});

app.post("/api/httpHello", async (req, res) => {
  const name = (req.body && req.body.name) || req.query.name || "locadev";
  req.query.name = name;
  return app._router.handle(
    { ...req, method: "GET", url: `/api/httpHello?name=${encodeURIComponent(name)}` },
    res,
    () => {}
  );
});

// simpler POST handler without router hack
app.post("/api/httpHelloJson", async (req, res) => {
  const name = (req.body && req.body.name) || "locadev";
  const payload = {
    hello: name,
    at: new Date().toISOString(),
    via: "httpHello",
  };
  try {
    await enqueue(payload);
    res.json({
      ok: true,
      message: `Hello, ${name}`,
      enqueued: true,
      queue: QUEUE,
      runtime: "locadev-sample-azure-functions",
      storage: "azurite",
    });
  } catch (e) {
    res.status(502).json({ ok: false, error: String(e.message || e) });
  }
});

app.get("/api/processed", (_req, res) => {
  res.json({ count: processed.length, items: processed.slice(-20) });
});

app.get("/health", (_req, res) => {
  res.json({
    status: "ok",
    queue: Boolean(queueClient),
    processed: processed.length,
  });
});

app.get("/", (_req, res) => {
  res.json({
    service: "locadev-sample-azure-functions",
    note: "Functions-style host using Azurite for queue I/O. For full Azure Functions host use Core Tools on the Docker host with sandbox.env.example AzureWebJobsStorage.",
    endpoints: [
      "GET /api/ping",
      "GET /api/httpHello?name=",
      "GET /api/processed",
      "GET /health",
    ],
  });
});

await initQueue();
pollTimer = setInterval(pollOnce, 2000);

app.listen(PORT, "0.0.0.0", () => {
  console.log(`locadev functions-style host on :${PORT}`);
});
