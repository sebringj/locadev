/**
 * locadev Azure Functions sample (Node v4 programming model).
 * Use with host Core Tools: `func start` + AzureWebJobsStorage → Azurite.
 * (Docker profile runs server.mjs for multi-arch; same queue name + semantics.)
 */
const { app, output } = require("@azure/functions");

const queueOut = output.storageQueue({
  queueName: "functions-work",
  connection: "AzureWebJobsStorage",
});

/** HTTP: health + enqueue a message for the queue trigger. */
app.http("httpHello", {
  methods: ["GET", "POST"],
  authLevel: "anonymous",
  extraOutputs: [queueOut],
  handler: async (request, context) => {
    const name =
      request.query.get("name") ||
      (request.method === "POST"
        ? ((await request.json().catch(() => ({}))) || {}).name
        : null) ||
      "locadev";

    const payload = {
      hello: name,
      at: new Date().toISOString(),
      via: "httpHello",
    };

    context.extraOutputs.set(queueOut, JSON.stringify(payload));
    context.log(`httpHello enqueued for ${name}`);

    return {
      status: 200,
      jsonBody: {
        ok: true,
        message: `Hello, ${name}`,
        enqueued: true,
        queue: "functions-work",
        runtime: "azure-functions",
        storage: "azurite",
      },
    };
  },
});

/** Queue: consumes messages written by httpHello (proves Azurite queue bindings). */
app.storageQueue("queueEcho", {
  queueName: "functions-work",
  connection: "AzureWebJobsStorage",
  handler: async (queueItem, context) => {
    const body =
      typeof queueItem === "string" ? queueItem : JSON.stringify(queueItem);
    context.log(`queueEcho processed: ${body}`);
  },
});

/** Simple ping without storage side effects. */
app.http("ping", {
  methods: ["GET"],
  authLevel: "anonymous",
  route: "ping",
  handler: async () => ({
    status: 200,
    jsonBody: { status: "ok", service: "locadev-sample-azure-functions" },
  }),
});
