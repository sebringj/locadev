import express from "express";
import { PGlite } from "@electric-sql/pglite";
import { vector } from "@electric-sql/pglite/vector";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = process.env.PGLITE_DATA_DIR || "/data";
const PORT = Number(process.env.PORT || 5433);
const SEED_PATH = path.join(__dirname, "seed.sql");

const app = express();
app.use(express.json({ limit: "10mb" }));

let db = null;
let ready = false;

async function init() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
  const marker = path.join(DATA_DIR, ".seeded");
  const isFirst = !fs.existsSync(marker);

  db = new PGlite(DATA_DIR, { extensions: { vector } });
  await db.waitReady;
  await db.exec("CREATE EXTENSION IF NOT EXISTS vector;");

  if (isFirst && fs.existsSync(SEED_PATH)) {
    const seed = fs.readFileSync(SEED_PATH, "utf8");
    await db.exec(seed);
    fs.writeFileSync(marker, new Date().toISOString());
    console.log("PGlite seed applied");
  }
  ready = true;
  console.log(`PGlite ready on :${PORT} data=${DATA_DIR}`);
}

app.get("/health", (_req, res) => {
  res.json({
    status: ready ? "ok" : "starting",
    backend: "pglite",
    extensions: ["vector"],
  });
});

app.get("/ready", (_req, res) => {
  if (!ready) return res.status(503).json({ status: "not ready" });
  res.json({ status: "ready" });
});

app.post("/sql", async (req, res) => {
  if (!ready) return res.status(503).json({ error: "not ready" });
  const { sql, params = [] } = req.body || {};
  if (!sql || typeof sql !== "string") {
    return res.status(400).json({ error: "body.sql required" });
  }
  try {
    const result = await db.query(sql, params);
    res.json({
      rows: result.rows ?? [],
      fields: (result.fields || []).map((f) => ({
        name: f.name,
        dataTypeID: f.dataTypeID,
      })),
      rowCount: result.rows?.length ?? 0,
    });
  } catch (err) {
    res.status(400).json({ error: String(err.message || err) });
  }
});

app.post("/exec", async (req, res) => {
  if (!ready) return res.status(503).json({ error: "not ready" });
  const { sql } = req.body || {};
  if (!sql || typeof sql !== "string") {
    return res.status(400).json({ error: "body.sql required" });
  }
  try {
    await db.exec(sql);
    res.json({ ok: true });
  } catch (err) {
    res.status(400).json({ error: String(err.message || err), ok: false });
  }
});

init()
  .then(() => {
    app.listen(PORT, "0.0.0.0", () => {
      console.log(`locadev-pglite listening on 0.0.0.0:${PORT}`);
    });
  })
  .catch((err) => {
    console.error("PGlite init failed:", err);
    process.exit(1);
  });
