CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS notes (
  id text PRIMARY KEY,
  body text,
  embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id text PRIMARY KEY,
  role text NOT NULL,
  content text NOT NULL,
  created_at timestamptz DEFAULT now()
);

INSERT INTO notes (id, body) VALUES
  ('note-1', 'Welcome to locadev PGlite app database.'),
  ('note-2', 'Vector extension is available for embedding demos.')
ON CONFLICT (id) DO NOTHING;

INSERT INTO chat_messages (id, role, content) VALUES
  ('msg-1', 'system', 'You are a local sandbox assistant.'),
  ('msg-2', 'user', 'Hello locadev'),
  ('msg-3', 'assistant', 'Hi — running against the local stack.')
ON CONFLICT (id) DO NOTHING;
